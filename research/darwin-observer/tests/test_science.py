import importlib.util,sys
from pathlib import Path
import numpy as np
import pytest
from scipy.integrate import solve_ivp
from darwin.physics import *
from darwin.truth import generate,hidden_step
from darwin.data import Record,assert_disjoint
from darwin.observers import observe
from darwin.symbolic import stlsq,physical_check,equations
from darwin.identification import local_observability,HYPOTHESES,fit
from darwin.discovery import discover,GuardedDarwin
from darwin.control import NMPC
from darwin.detection import diagnose,calibrate_threshold
ROOT=Path(__file__).resolve().parents[1]

def load_vendor(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def test_mass_and_stoichiometry():
    x=BASE+np.array([.1,.5,-.1,.1,1.,-.5]);u=U0.copy();f=rhs(x,u,np.zeros(NP));v=np.dot(u[:3],1/RHO)
    assert abs(f[0]+f[2]-(u[0]-v*(x[0]+x[2]))/V)<1e-10
    assert abs(f[1]+f[2]-(u[1]-v*(x[1]+x[2]))/V)<1e-10
    p=np.zeros(NP);p[6]=.3
    d=rhs(x,u,p)-f
    assert d[0]==pytest.approx(d[1]);assert d[0]==pytest.approx(-d[2]);assert d[3]==0

def test_dimension_ledger():
    # dimensions (kmol,m,K,h,kJ), independent dimensional algebra of balances.
    C=np.array([1,-3,0,0,0]);flow=np.array([0,3,0,-1,0]);vol=np.array([0,3,0,0,0])
    k=np.array([0,0,0,-1,0]);heat=np.array([-1,0,0,0,1]);cp=np.array([-1,0,-1,0,1]);temp=np.array([0,0,1,0,0])
    assert np.array_equal(flow+C-vol,k+C)
    assert np.array_equal(heat+k+C+vol,np.array([0,0,0,-1,1]))
    assert np.array_equal((heat+k+C+vol)-(vol+C+cp),temp+np.array([0,0,0,-1,0]))

def test_equilibrium_and_asymmetry():
    assert np.max(abs(rhs(BASE,U0,np.zeros(NP))))<1e-9
    assert BASE[4]==pytest.approx(340.30348938,abs=1e-7)
    x=BASE.copy();x[5]+=10
    assert rhs(x,U0,np.zeros(NP))[4]==pytest.approx(rhs(BASE,U0,np.zeros(NP))[4])
    assert rhs(x,U0,np.zeros(NP))[5]<-1

def test_independent_integration():
    x=BASE+np.array([.1,.2,-.1,0,2.,-.5]);u=U0.copy();u[3]=780
    ref=solve_ivp(lambda t,z:rhs(z,u,np.zeros(NP)),(0,.015),x,method='DOP853',rtol=1e-11,atol=1e-12).y[:,-1]
    assert np.max(abs(transition(x,u,np.zeros(NP))-ref))<3e-5
    assert np.max(abs(transition(x,u,np.zeros(NP),nsub=6)-ref))<2e-6

def test_oracle_equivalence():
    src=load_vendor('old_oracle',ROOT/'vendor/oracle_kf_v01.py');x=BASE+np.array([.04,.1,-.02,.01,1.,2.]);u=U0.copy();u[3]=640
    assert np.allclose(rhs(x,u,np.zeros(NP)),src.deriv(x,u),rtol=1e-12,atol=1e-10)
    assert np.allclose(transition(x,u,np.zeros(NP),nsub=6),src.step(x,u,substep=.0025),rtol=1e-12,atol=1e-10)

def test_full_legacy_equivalence():
    src=load_vendor('old_legacy',ROOT/'vendor/legacy_model.py');p=src.Parameters();x=src.steady()['x'];u=LEGACY_U0.copy()
    assert np.max(abs(rhs(x,u,np.zeros(NP),1)-src.rhs(0,x,np.array([u[0],u[3],u[5]]))))<1e-9
    eq=equilibrium(LEGACY_U0,variant=1)
    assert np.max(abs(eq-x))<1e-7
    assert abs(eq[4]-BASE[4])>5

def test_exact_invisible_chemical_direction():
    # Non-observability certificate: same CA and heat capacity, different CC.
    v=np.array([0.,-CP[2]/CP[1],1.,0.,0.,0.])*.12
    inputs=np.tile(U0,(40,1));a=simulate(BASE,inputs,np.zeros(NP));b=simulate(BASE+v,inputs,np.zeros(NP))
    assert np.max(abs(a[:,4:]-b[:,4:]))<2e-9
    assert np.max(abs(a[:,2]-b[:,2]))>.1
    assert local_observability(BASE,U0)['rank']<6

@pytest.mark.parametrize('kind',['ukf','ekf','adaptive'])
def test_observer_finite_covariance_and_causality(kind):
    e=generate(401);r=observe(e.operational,kind=kind);rp=observe(e.operational.prefix(45),kind=kind)
    assert np.array_equal(r['x'][:46],rp['x'])
    assert np.min(np.linalg.eigvalsh(r['cov']))>0
    assert np.sqrt(np.mean((r['x'][20:,2]-e.truth[20:,2])**2))<.04

def test_truth_is_not_in_operational_record():
    e=generate(42);a=observe(e.operational)['x'];e.truth[:]=999
    assert np.array_equal(a,observe(e.operational)['x'])
    assert not hasattr(e.operational,'truth') and not hasattr(e.operational,'metadata')

def test_missing_measurements():
    e=generate(7,'C_dropout');r=observe(e.operational);assert np.all(np.isfinite(r['x']))
    z=e.operational.measurements.copy();z[30:40]=np.nan
    r=observe(Record(7,e.operational.inputs,z));assert np.all(np.isfinite(r['x']))

def test_determinism_and_split_guards():
    a=generate(8);b=generate(8);assert np.array_equal(a.truth,b.truth)
    assert a.operational.fingerprint()==b.operational.fingerprint()
    with pytest.raises(ValueError):assert_disjoint([a.operational],[b.operational])
    assert_disjoint([a.operational],[generate(9).operational])

def test_sparse_known_equation():
    rng=np.random.default_rng(73);x=rng.uniform(-1,1,400);A=np.c_[np.ones(len(x)),x,x*x,np.sin(3*x)]
    c=stlsq(A,1.2*x-.4*x*x,threshold=.05)
    assert np.allclose(c,[0,1.2,-.4,0],atol=1e-5)

def test_invalid_and_singular_expression_rejected():
    p=np.zeros(NP);p[4]=5.;assert not physical_check(Model(p))['valid']
    p=np.zeros(NP);p[6]=-8.;assert not physical_check(Model(p))['valid']
    assert physical_check(Model())['valid']

def test_no_forced_discovery_and_overfit():
    tr=[generate(300+i).operational for i in range(4)];va=[generate(400+i).operational for i in range(4)]
    d=discover(tr,va,allowed=['H0','UA_constant','UA_quadratic','sensor_bias'])
    assert not d['accepted'];assert d['selected']=='H0'
    assert len(d['ranking'])==4 and all('reason' in r for r in d['ranking'])

def test_holdout_recovers_known_structure():
    tr=[generate(100+i,'A_rich').operational for i in range(4)];va=[generate(200+i,'A_rich').operational for i in range(4)]
    d=discover(tr,va,allowed=['H0','UA_constant','UA_power'])
    assert d['accepted'] and d['selected']=='UA_power'
    assert abs(d['model']['params'][2]-.4)<.04

def test_false_alarms_calibrated_on_other_episodes():
    th,_=calibrate_threshold([observe(generate(9100+i).operational) for i in range(30)])
    hits=[diagnose(observe(generate(9300+i).operational),th)['detected'] for i in range(30)]
    assert sum(hits)<=6
    alt=[diagnose(observe(generate(9400+i,'C_bias').operational),th)['detected'] for i in range(10)]
    assert sum(alt)>=8

def test_unproven_update_rejected_and_reversal():
    g=GuardedDarwin();assert not g.approve(dict(accepted=True,model=Model().as_dict()))
    p=np.zeros(NP);p[0]=-.3
    d=dict(accepted=True,model=Model(p,'test').as_dict(),id='unit-test',train_seeds=[1],validation_seeds=[2],paired_CI=[1.,2.],relative_gain=.2)
    assert g.approve(d)
    u=U0.copy();u[3]=1300
    g.update(u,BASE[4:]);assert not g.accepted and g.fallbacks==1
    assert np.all(g.active.model.params==0)

def test_monitor_rolls_back_bad_forecast():
    g=GuardedDarwin();p=np.zeros(NP);p[0]=-.4
    assert g.approve(dict(accepted=True,model=Model(p).as_dict(),id='test',train_seeds=[1],validation_seeds=[2],paired_CI=[1.,2.],relative_gain=.2))
    ep=generate(901)
    for u,y in zip(ep.operational.inputs,ep.operational.measurements[1:]):g.update(u,y)
    assert g.fallbacks>=1

def test_control_constraints_and_infeasibility():
    c=NMPC();u,d=c.action(BASE,U0,2.47);assert 22.7<=u<=1366.2
    hot=BASE.copy();hot[4]=365;u,d=c.action(hot,U0,2.7)
    assert u==1366.2 and not d['feasible']

def test_equations_export():
    p=np.zeros(NP);p[2]=.4;e=equations(Model(p));assert 'latex' in e[0] and 'sympy' in e[0] and e[0]['unit']=='kJ/(h K)'

def test_controller_rejects_future_moves_outside_discovery_envelope(monkeypatch):
    import darwin.control as ctl
    calls=[]
    def proposed(x,u,sequence,previous,sp,p):
        calls.append(p.copy())
        seq=np.full(6,453.6)
        if p[0]!=0:seq[5]=1300.  # First move is valid; a future move is not.
        return seq,(1.,0.,342.)
    monkeypatch.setattr(ctl,'optimize',proposed)
    p=np.zeros(NP);p[0]=-.1
    c=NMPC();_,diagnostic=c.action(BASE,U0,2.47,Model(p))
    assert diagnostic['model_fallback'] and len(calls)==2
    assert np.all(calls[-1]==0) and np.all(c.sequence==453.6)
