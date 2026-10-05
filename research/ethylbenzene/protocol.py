"""TCC disturbances retained at 5 h; new servo and robustness tests."""
import numpy as np
from model import *
from observer import KINDS
CASES=['servo_up','servo_down','benzene_50','recycle_minus50','thermal_loss','kinetics_noise']
SEEDS=[9001,9002,9003]
CONFIGS=[dict(estimator=e,prediction=p,mode=m) for e in KINDS for p in ['physical','neural'] for m in ['siso','mimo']]

def scenario(case,t):
    u=U0.copy();ref=float(fraction(BASE));kin=np.ones(3);loss=1.;noise=1.;missing=False
    if case=='servo_up' and 3.<=t<7.:ref*=1.1
    if case=='servo_down' and 3.<=t<7.:ref*=.9
    if case=='benzene_50' and t>=5.:u[1]*=1.5
    if case=='recycle_minus50' and t>=5.:u[2]*=.5
    if case=='thermal_loss' and t>=5.:loss=.8
    if case=='kinetics_noise' and t>=5.:
        kin=np.array([1.25,.9,1.1]);noise=3.;missing=5.5<=t<6.
    return u,ref,kin,loss,noise,missing

def specification():
    return dict(calibration=calibration_audit(),cases=CASES,seeds=SEEDS,configurations=CONFIGS,
      runs=len(CASES)*len(SEEDS)*len(CONFIGS)*2,duration_h=10.,sample_h=DT,
      tcc_cases=dict(benzene_50='+50% pure benzene at 5 h',recycle_minus50='-50% recycle at 5 h'),
      new_cases=dict(servo_up='+10% xEB at 3 h, nominal at 7 h',servo_down='-10% xEB at 3 h, nominal at 7 h',
                    thermal_loss='20% unobserved heat-removal efficiency loss at 5 h',
                    kinetics_noise='k1 +25%, k2 -10%, k3 +10%, input noise 3x at 5 h; T sensor missing 5.5-6 h'),
      initial_condition='nominal steady state, common biased estimate; no unrecoverable historical startup included in control score',
      initial_estimate_offset=[.006,.22,-.12,.04,1.5],
      noise=dict(input_relative_std=.01,feed_temperature_std_C=.2,temperature_measurement_std_C=1.5,
                 actuator_clipping=True,pairing='same independent innovations by case/seed/time across every configuration'),
      information='commanded inputs only; future disturbances not previewed; true concentrations are scoring labels only',
      state_prediction=dict(physical='printed balances with documented unit correction/effective Q',neural='12-48-48-5 MLP, fully learned substeps'),
      estimators=dict(ukf='physical prediction, constant diagonal Q',lstm_ukf='physical prediction, genuine LSTM predicts positive Q factors from past',
                      nake='learned dynamics, UKF/Joseph correction, previous NIS EWMA scales positive Q',
                      lstm_nake='learned dynamics, UKF/Joseph correction, separately trained genuine LSTM adapts Q'),
      nake_status='research working name; no KalmanNet reproduction or neural Kalman-gain training',
      controllers=dict(siso='xEB tracking via ethylene flow; Q command fixed',mimo='xEB and T tracking via ethylene flow and Q'),
      cost='0.8*((xEB-ref)/0.02)^2 + MIMO-only 0.2*((T-Tnom)/5)^2 + 0.03*sum(normalized move changes squared)',
      comparison='MIMO adds a thermal objective and actuator; direct xEB ranking is accompanied by temperature/effort metrics',
      horizon=dict(prediction_steps=40,prediction_h=1.,control_moves=4,first_blocks_steps=5,last_move_held=True),
      bounds=dict(fE_factor=[.04,2.],Q_factor=[.6,1.4],move_rate=[.12,.08]),
      constraints=dict(temperature_modes=['off','on: predicted T<=165 C'],actual_monitoring='DOP853 dense output at 21 points/sample',
                       note='prediction feasibility does not guarantee actual noisy plant temperature'),
      solver=dict(name='SciPy SLSQP; physical CasADi C derivatives, neural exact C chain rule checked against CasADi',maxiter=45,ftol=1e-7),
      fallback='constrained infeasible: fE minimum and Q maximum in MIMO; may override normal move-rate bound; unconstrained: previous command',
      stopped_runs='guard at T>220 C, T<0 C, negative concentration or numerical failure; flagged and excluded from full-duration matched rankings',
      training_test_separation='training seeds 4101/4401; validation 4201/4251/4501; test seeds 9001-9003',
      synthetic=True,scope='first reactor; not a full Aspen plantwide study; no experimental plant data')

if __name__=='__main__':dump(RESULTS/'protocol.json',specification())
