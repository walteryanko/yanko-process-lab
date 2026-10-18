"""Independent checks of the dissertation reconstruction and causal replay."""
import json
from pathlib import Path
import numpy as np
import pytest
from scipy.integrate import solve_ivp
from darwin.physics import Model, NP, rhs, transition
from darwin.thesis_cases import *
from darwin.thesis_control import symbolic_functions
from darwin.thesis_experiments import commissioning_episode, advance, make_observer
from darwin.observers import observe
from darwin.discovery import GuardedDarwin

ROOT = Path(__file__).resolve().parents[1]

def test_temperature_percentages_use_fahrenheit():
    u, _ = commanded(BY_KEY['REG_TF30'], 4.)
    assert u[4] == pytest.approx((75*.7-32)/1.8+273.15)
    u, _ = commanded(BY_KEY['REG_TC20'], 4.)
    assert u[5] == pytest.approx((60*.8-32)/1.8+273.15)
    assert T_LIMIT == pytest.approx(344.26111111111106)

def test_open_loop_four_events_and_servo_schedule():
    s = BY_KEY['OL_FA']
    assert [commanded(s,t)[0][0]/U_NOM[0] for t in [0,1,5,9,13,17]] == [1,.9,1,1.1,1,1]
    assert commanded(BY_KEY['SERVO_P10'],4)[1] == pytest.approx(SP_NOM*1.1)
    assert commanded(BY_KEY['SERVO_P10'],8)[1] == SP_NOM
    assert time_grid(17)[-1] == 17

def test_complete_historical_operating_point():
    assert X_NOM[2] == pytest.approx(2.29576461,abs=1e-7)
    assert X_NOM[4] == pytest.approx(332.33361802,abs=1e-7)
    assert np.max(abs(rhs(X_NOM,U_NOM,np.zeros(NP),1))) < 1e-8
    assert np.allclose(P_HIST,1e-6*CONVERSION**2)

def test_prediction_and_cost_against_direct_balance_integration():
    cost,predict=symbolic_functions()
    x=X_NOM.copy();x[4]+=8
    u=U_NOM.copy();moves=np.linspace(.7,1.3,6);prev=.93*U_NOM[3]
    refs=np.r_[np.full(20,SP_NOM),np.full(37,SP_NOM*1.1)]
    par=np.r_[x,u,SP_NOM,prev,1.,np.zeros(NP),refs]
    total=0.;states=[]
    for k in range(57):
        uk=u.copy();uk[3]=U_NOM[3]*moves[min(k,5)]
        x=transition(x,uk,np.zeros(NP),.015,1,1);states.append(x)
        total+=.8*((refs[k]-x[2])/SP_NOM)**2
        if k<6:total+=.2*(moves[k]-(prev/U_NOM[3] if k==0 else moves[k-1]))**2
        total+=1000*(max(x[4]-T_LIMIT,0)/(160/1.8))**2
    value,gradient=cost(moves,par)
    assert np.asarray(predict(moves,par)) == pytest.approx(np.array(states),abs=2e-9)
    assert float(value) == pytest.approx(total,rel=1e-9)
    fd=[]
    for j in range(6):
        delta=np.zeros(6);delta[j]=1e-5
        fd.append((float(cost(moves+delta,par)[0])-float(cost(moves-delta,par)[0]))/2e-5)
    assert np.asarray(gradient).ravel() == pytest.approx(fd,rel=2e-5,abs=1e-6)

def test_plant_splits_disturbance_at_actual_event_time():
    s=BY_KEY['REG_FA10'];noise=np.zeros((50,6));x=X_NOM.copy()
    y,_,_,_,_=advance(x,s,3.99,4.005,U_NOM[3],noise)
    ref=x.copy()
    for start,end in [(3.99,4.),(4.,4.005)]:
        u,_=commanded(s,(start+end)/2)
        ref=solve_ivp(lambda t,z:rhs(z,u,np.zeros(NP),1),(start,end),ref,
                      method='DOP853',rtol=1e-11,atol=1e-12).y[:,-1]
    assert np.max(abs(y-ref)) < 2e-7

@pytest.mark.parametrize('integrator',[0,1])
def test_historical_observer_prefix_is_causal(integrator):
    rec,truth=commissioning_episode(888001,steps=60)
    opts=observer_options(X_NOM,integrator)
    a=observe(rec,Model(variant=1),**opts)
    b=observe(rec.prefix(30),Model(variant=1),**opts)
    assert np.array_equal(a['x'][:31],b['x'])
    truth[:]=999
    assert np.array_equal(a['x'],observe(rec,Model(variant=1),**opts)['x'])

def test_rejected_discovery_equals_rk4_and_rollback_keeps_variant():
    a=make_observer('UKF_RK4',X_NOM,{'accepted':False})
    b=make_observer('Darwin',X_NOM,{'accepted':False})
    rec,_=commissioning_episode(888002,steps=30)
    for u,y in zip(rec.inputs,rec.measurements[1:]):
        assert np.array_equal(a.update(u,y)[0],b.update(u,y)[0])
    p=np.zeros(NP);p[0]=-.1
    d=dict(accepted=True,model=Model(p,variant=0).as_dict(),id='test',
           train_seeds=[1],validation_seeds=[2],paired_CI=[1.,2.],relative_gain=.2)
    assert not b.approve(d)
    d['model']=Model(p,variant=1).as_dict()
    assert b.approve(d)
    b.revert('test')
    assert b.active.model.variant==1 and np.all(b.active.model.params==0)

def test_final_seeds_do_not_overlap_commissioning():
    d=json.loads((ROOT/'artifacts/thesis/discovery.json').read_text())
    cal=json.loads((ROOT/'artifacts/thesis/calibration.json').read_text())
    trained=set(d['train_seeds']);validated=set(d['validation_seeds']);calibrated=set(cal['seeds'])
    tested={410000+i*1000+j for i in range(len(SCENARIOS)) for j in range(20)}
    assert not (trained&validated or tested&(trained|validated|calibrated))
    assert d['selected']=='H0' and not d['accepted']
