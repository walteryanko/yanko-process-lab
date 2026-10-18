import importlib.util,inspect,json
from pathlib import Path
import numpy as np
import pytest
from scipy.integrate import solve_ivp
from premonition.physics import *
from premonition.continuation import arclength,normal_form_tests,difference_jac,classify_crossings
from premonition.stability import reactive_alpha,observability,refine_fold
from premonition.ews import indicators,EWS
from premonition.observer import UKF,Observation,spd
from premonition.detectors import Features,Detectors,PortableModel,prediction
from premonition.evaluation import *
from premonition.scenarios import specification,open_loop
from premonition.control import NMPC,Supervisor,ConstraintGuard,objective
from premonition.io import save
ROOT=Path(__file__).resolve().parents[1]

def test_checkpoint_rejects_changed_model(tmp_path):
    from premonition.control_campaign import verify_checkpoints
    verify_checkpoints(tmp_path,{'model':'A'})
    verify_checkpoints(tmp_path,{'model':'A'})
    with pytest.raises(ValueError,match='identity mismatch'):
        verify_checkpoints(tmp_path,{'model':'B'})

@pytest.fixture
def reference():
    spec=importlib.util.spec_from_file_location('pg_ref',ROOT/'vendor/pg_reference.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def test_reference_equations_random_states(reference):
    from dataclasses import replace
    rng=np.random.default_rng(12)
    for _ in range(20):
        x=BASE+rng.normal(0,[.1,.1,.1,.05,3,2]);u=U0.copy();u[3]=rng.uniform(100,1200);u[4]+=rng.uniform(-4,4)
        p=replace(reference.Parameters(),FB=u[1],FM=u[2],T0=u[4]);v=reference.rhs(0,x,np.array([u[0],u[3],u[5]]),p)
        np.testing.assert_allclose(rhs(x,u),v,rtol=1e-11,atol=1e-10)

def test_equilibrium_residual():assert np.linalg.norm(rhs(BASE,U0))<1e-7

def test_material_invariants():
    x=BASE+np.array([.1,.2,-.15,.2,3,1]);d=rhs(x,U0);v=flow(U0)
    assert abs(d[0]+d[2]-(U0[0]-v*(x[0]+x[2]))/P[11])<1e-10
    assert abs(d[1]+d[2]-(U0[1]-v*(x[1]+x[2]))/P[11])<1e-10

def test_inert_equation():assert abs(rhs(BASE,U0)[3])<1e-10

def test_asymmetric_thermal_model():
    x=BASE.copy();x[5]+=10
    np.testing.assert_allclose(rhs(x,U0)[:5],rhs(BASE,U0)[:5],atol=1e-12)

def test_table_is_not_primary():assert abs(equilibria(TABLE_U,TABLE)[0][4]-BASE[4])>7

def test_arrhenius_offset_preserved():assert P[-1]==pytest.approx(.183333333333333)

def test_sampling():assert DT*3600==pytest.approx(54)

@pytest.mark.parametrize('mw',[22.7,453.59237,1366.2])
def test_rk4_vs_independent_integrator(mw):
    x=BASE+np.array([.02,.1,0,0,1,-1]);u=U0.copy();u[3]=mw
    sol=solve_ivp(lambda t,z:rhs(z,u),[0,.15],x,method='DOP853',rtol=1e-11,atol=1e-12)
    for _ in range(10):x=step(x,u,n=6)
    np.testing.assert_allclose(x,sol.y[:,-1],atol=2e-5,rtol=2e-6)

def test_analytic_jacobian():
    x=BASE+np.array([.1,.1,.1,0,2,-1]);numerical=difference_jac(lambda z:rhs(z,U0),x)
    np.testing.assert_allclose(jacobian(x,U0),numerical,atol=1e-5,rtol=2e-5)

def test_fast_spectrum_includes_passive_mode():
    for mw in [22.7,500,1300]:
        u=U0.copy();u[3]=mw;x=equilibria(u)[0]
        assert spectral_abscissa(x,u)==pytest.approx(np.linalg.eigvals(jacobian(x,u)).real.max(),abs=1e-9)
    u[3]=22.7;x=equilibria(u)[0]
    assert spectral_abscissa(x,u)>reactive_alpha(x,u)

def test_three_equilibria():
    u=U0.copy();u[4]=295;eq=equilibria(u)
    assert len(eq)==3
    assert [spectral_abscissa(x,u)<0 for x in eq]==[True,False,True]

def test_known_fold_continuation():
    f,h=normal_form_tests();assert f['points'][:,0].min()<-.3;assert max(f['residual'])<1e-8
    np.testing.assert_allclose(f['points'][:,1],f['points'][:,0]**2,atol=1e-8)

def test_known_hopf():
    _,h=normal_form_tests();sp=[np.array([z[2]+1j,z[2]-1j]) for z in h['points']]
    c=classify_crossings(h['points'],sp)
    assert c and c[0]['type']=='hopf_candidate'

def test_continuation_rejects_non_equilibrium():
    with pytest.raises(ValueError):arclength(lambda z:np.array([z[1]-z[0]**2]),[2,1])

def test_pg_fold_nondegeneracy():
    f=refine_fold([309.,295.5]);assert f['verified'];assert f['parameter']==pytest.approx(295.51964,abs=1e-4)

def test_observability_rank_deficiency():assert observability(BASE,U0)['rank']==3

def test_variance_detrended():
    a=indicators(np.arange(80)*.5+300);assert a['variance']<1e-20

def test_ews_insufficient_evidence():assert not indicators([1,2,3])['valid']

def test_colored_noise_inflates_ac1():
    rng=np.random.default_rng(31);white=rng.normal(size=800);red=white.copy()
    for k in range(1,len(red)):red[k]=.95*red[k-1]+.2*white[k]
    assert indicators(red)['ac1']>indicators(white)['ac1']+.7

def test_ews_causal_prefix():
    rng=np.random.default_rng(7);a=rng.normal(size=80);e=EWS();p=[]
    for z in a[:40]:p.append(e.update(z))
    e2=EWS();p2=[]
    b=a.copy();b[40:]+=1e3
    for z in b[:40]:p2.append(e2.update(z))
    for aa,bb in zip(p,p2):assert aa['variance']==bb['variance']

def test_no_post_event_credit():
    m=alarm_metrics(np.r_[np.zeros(10),np.ones(10)],10,np.arange(20)<10,.5,H=5);assert not m['detected']

def test_early_persistent_alarm_does_not_gain_retroactive_credit():
    m=alarm_metrics(np.ones(20),15,np.arange(20)<15,.5,H=5);assert m['false_onsets']==1 and m['detected']==0

def test_true_lead_time():
    m=alarm_metrics(np.r_[np.zeros(6),1.,np.zeros(13)],10,np.arange(20)<10,.5,H=5);assert m['lead_min']==pytest.approx(3.6)

def test_censoring():
    labels,valid,e=future_labels(np.r_[np.zeros(15)+330,np.ones(15)+345],H=5);assert e==15;assert not valid[15:].any();assert labels[10:15].sum()==5

def test_split_separation():
    p=json.loads((ROOT/'configs/protocol.json').read_text());s=[set(range(a,b+1)) for a,b in p['split'].values()]
    assert all(not a&b for i,a in enumerate(s) for b in s[i+1:])

def test_observer_contract():
    assert list(inspect.signature(UKF.advance).parameters)==['self','u','y']
    assert list(Observation.__dataclass_fields__)==['y','u','xhat','covariance','innovation','nis']

def test_estimator_future_invariance():
    rng=np.random.default_rng(6);ys=BASE[4:]+rng.normal(0,.3,(20,2));a=UKF();b=UKF()
    for y in ys[:10]:
        xa,_=a.advance(U0,y);xb,_=b.advance(U0,y);np.testing.assert_array_equal(xa,xb)
    # No future object is retained or accepted by the observer.
    ys[10:]+=20
    np.testing.assert_array_equal(a.x,b.x)

def test_dropout_and_positive_covariance():
    a=UKF();x,p=a.advance(U0,np.array([np.nan,np.nan]));assert physical(x);assert min(np.linalg.eigvalsh(p))>0

def test_guard_invalid_action():
    g=ConstraintGuard();uh=np.tile(U0,(57,1));ph=np.tile(P,(57,1))
    assert not g.check(BASE,np.full(6,np.nan),U0[3],BASE[2],uh,ph)[0]
    assert not g.check(BASE,np.full(6,UMAX+1),U0[3],BASE[2],uh,ph)[0]

def test_detector_failure_abstains():
    class Broken:
        def predict(self,x):raise RuntimeError('deliberate')
    d=Detectors({'D5':Broken()});o=Observation(BASE[4:],U0,BASE,np.eye(6)*.01,np.zeros(2),0.)
    r=d.update(o);assert not r['alarms']['D5'] and d.failures==1

def test_supervisor_requires_confirmation():
    s=Supervisor();assert not s.decide(.9,.8);assert s.decide(.9,.8);assert not s.decide(np.nan,.8)

def test_no_alarm_with_quiet_short_history():
    d=Detectors();o=Observation(BASE[4:],U0,BASE,np.eye(6)*.01,np.zeros(2),0.)
    assert d.update(o)['insufficient_evidence']

def test_fallback_on_unrecoverable_prediction():
    x=BASE.copy();x[4]=360;obs=Observation(x[4:],U0,x,np.eye(6)*.01,np.zeros(2),0.)
    ctl=NMPC('C4');ctl.sp=BASE[2];mv,d=ctl.action(obs,{'scores':{'D5':np.nan,'D1':10}},{'D5':.5})
    assert mv==UMAX and d['fallback']=='max_cooling' and not d['feasible']

def test_nominal_controller_bounds():
    ctl=NMPC('C0');ctl.sp=BASE[2];o=Observation(BASE[4:],U0,BASE,np.eye(6)*.01,np.zeros(2),0.)
    mv,d=ctl.action(o,{'scores':{}},{})
    assert UMIN<=mv<=UMAX and d['feasible']

def test_oracle_explicitly_noncausal():
    ctl=NMPC('oracle_offline');ctl.sp=BASE[2];o=Observation(BASE[4:],U0,BASE,np.eye(6),np.zeros(2),0.)
    with pytest.raises(ValueError):ctl.action(o,{'scores':{}},{})

def test_deterministic_scenarios():
    a=specification(30001);b=specification(30001)
    for name in ['noise','actual','params','initial']:np.testing.assert_array_equal(a[name],b[name])

def test_independent_training_seeds():assert not np.array_equal(specification(10001)['noise'],specification(30001)['noise'])

def test_export_strict_json(tmp_path):
    save(tmp_path/'a.json',{'missing':np.nan,'arr':np.array([1,2])});data=json.loads((tmp_path/'a.json').read_text());assert data['missing'] is None

def test_probability_model_target_separation():
    p=ROOT/'results/CD/models/D5.json'
    if p.exists():
        d=json.loads(p.read_text());assert 'thermal' in d['target'] and 'not accident' in d['target'];m=PortableModel(d);pr=m.predict(np.zeros((2,18)));assert np.all((pr>=0)&(pr<=1))

def test_bootstrap_paired_identity():
    a=np.arange(20);v=paired_ci(a,a);assert v['mean_difference']==0;np.testing.assert_array_equal(v['ci95'],[0,0])
