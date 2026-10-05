"""Reconstructed PI + EKF baseline on the identical new test plant.

Historical gains, covariances, sampling and initial conditions are unavailable.
They are not claimed recovered. EKF Q is selected on independent validation;
PI follows the TFC's relay / Ziegler-Nichols recipe on a separate nominal run.
No control test score selects either tuning.
"""
import argparse,hashlib,json,time,multiprocessing as mp
import numpy as np
import casadi as ca
from model import *
from observer import Q_BASE,R_MEAS,spd,Observer
from compiled import Models,symbolic_steps,compile_models
from networks import NeuralTransition
from tuning import validation_data,FACTORS
import experiment as exp
from protocol import CASES,SEEDS,specification

BASE_DIR=RESULTS/'historical_baseline'
BASE_DIR.mkdir(exist_ok=True)

class EKF:
    def __init__(self,x0,models,q=None):
        self.x=np.array(x0,copy=True);self.models=models
        self.p=np.diag((np.array([.015,.35,.18,.06,2.])/XS)**2)
        self.qbase=np.array(q if q is not None else Q_BASE,copy=True)
        self.last_q=self.qbase.copy();self.repairs=self.projections=0
        physical=symbolic_steps(NeuralTransition.load())['physical']
        xx=ca.SX.sym('x',5);uu=ca.SX.sym('u',7)
        self.jac=ca.Function('ekf_jacobian',[xx,uu],[ca.densify(ca.jacobian(physical(xx,uu),xx))])
    def update(self,u,y):
        f=np.array(self.jac(self.x,u));a=f*XS[None,:]/XS[:,None]
        xp=self.models.transition('physical',self.x,u)
        pp=a@self.p@a.T+np.diag(self.qbase/XS**2);pp,fixed=spd(pp);self.repairs+=int(fixed)
        mean=(xp-BASE)/XS;nis=None
        if np.isfinite(y):
            h=np.array([0.,0.,0.,0.,XS[4]]);ss=float(h@pp@h+R_MEAS);gain=pp@h/ss
            innovation=float(y-xp[4]);mean+=gain*innovation
            b=np.eye(5)-np.outer(gain,h);post=b@pp@b.T+np.outer(gain,gain)*R_MEAS
            nis=innovation**2/ss
        else:post=pp
        self.x=BASE+mean*XS;self.p,fixed=spd(post);self.repairs+=int(fixed)
        if np.any(self.x[:4]<1e-7):
            self.projections+=int(np.sum(self.x[:4]<1e-7));self.x[:4]=np.maximum(self.x[:4],1e-7)
        if not np.all(np.isfinite(self.x)) or not 0.<self.x[4]<300.:raise ValueError('EKF divergence')
        return self.x.copy(),self.p*XS[:,None]*XS[None,:],nis

class PI:
    def __init__(self,gains=None):
        d=gains or json.loads((RESULTS/'baseline_tuning.json').read_text())['relay']
        self.kp=d['Kp'];self.ti=d['Ti_h'];self.integral=0.;self.previous=1.
        self.s0=1-np.log(2)/np.log(50) # consistent with common 0.04..2 flow bounds
    def step(self,estimate,u,reference,tref=TNOM):
        begin=time.perf_counter();error=float(reference-fraction(estimate))
        self.integral+=self.kp*DT/self.ti*error
        signal=self.s0+self.kp*error+self.integral
        raw=2*np.exp(np.log(50)*(np.clip(signal,0,1)-1))
        flow=float(np.clip(raw,max(.04,self.previous-.12),min(2.,self.previous+.12)))
        # Back-calculation uses the issued command, including the common slew limit.
        issued=1+np.log(flow/2)/np.log(50)
        self.integral+=issued-signal;self.previous=flow
        return np.array([flow,1.]),dict(solver_success=True,status=0,feasible=True,fallback=False,
                iterations=0,predicted_Tmax_C=None,latency_ms=1000*(time.perf_counter()-begin))

def tune():
    models=Models();data=validation_data();scores=[]
    for factor in FACTORS:
        errors=[];te=[]
        for commands,states,measurements in data:
            o=EKF(BASE+np.array([.006,.22,-.12,.04,1.5]),models,Q_BASE*factor)
            for j,(u,x,y) in enumerate(zip(commands,states,measurements)):
                estimate,cov,nis=o.update(u,y)
                if j>=40:errors.append(float(fraction(estimate)-fraction(x)));te.append(float(estimate[4]-x[4]))
        rmse=float(np.sqrt(np.mean(np.array(errors)**2)));tr=float(np.sqrt(np.mean(np.array(te)**2)))
        scores.append(dict(factor=factor,xEB_RMSE=rmse,T_RMSE_C=tr,score=(rmse/.001)**2+(tr/1.5)**2))
        print('EKF validation',scores[-1],flush=True)
    best=min(scores,key=lambda r:r['score']);q=Q_BASE*best['factor']
    obs=EKF(BASE,models,q);state=BASE.copy();relay=[];switch=[];previous_sign=1
    signal0=1-np.log(2)/np.log(50);d=.02;hysteresis=.00015
    for j in range(600):
        error=float(fraction(BASE)-fraction(obs.x));sgn=previous_sign
        if error>hysteresis:sgn=1
        if error<-hysteresis:sgn=-1
        if sgn!=previous_sign:switch.append(j*DT)
        previous_sign=sgn;flow=2*np.exp(np.log(50)*(signal0+d*sgn-1))
        u=U0.copy();u[0]*=flow
        state,grid,dense=exp.truth_step(state,u,np.ones(3));obs.update(u,state[4])
        relay.append([j*DT,float(fraction(obs.x)),flow,float(state[4])])
    sw=np.array(switch);rr=np.array(relay)
    if len(sw)<12:raise RuntimeError('No sustained relay cycle; do not invent PI gains')
    periods=sw[2:]-sw[:-2];tu=float(np.median(periods[-10:]))
    amps=[]
    for a,b in zip(sw[-12:-2],sw[-10:]):
        values=rr[(rr[:,0]>=a)&(rr[:,0]<b),1]
        if len(values):amps.append(.5*float(values.max()-values.min()))
    amp=float(np.median(amps));kcu=4*d/(np.pi*amp)
    result=dict(status='reconstructed, not recovered historical gains',validation_seed=4601,
       validation_trajectories=16,EKF_Q_factor=best['factor'],constant_Q=q,candidates=scores,
       relay=dict(duration_h=15.,measurement_noise=False,nominal_only=True,signal_amplitude=d,
          hysteresis_xEB=hysteresis,switches=len(sw),period_h=tu,xEB_amplitude=amp,Kcu=kcu,
          Kp=kcu/2.2,Ti_h=tu/1.2,recipe='TFC Table 3.5: Kc=Kcu/2.2; Ti=Tu/1.2'),
       common_bounds=dict(fE_factor=[.04,2.],maximum_move=.12,Q_fixed=1.),
       caveat='Same new plant/noise/initial conditions; original unknown Q/P/R/dt/PI gains and startup not reproduced. New antiwindup/slew limits declared.',
       no_test_tuning=True)
    dump(RESULTS/'baseline_tuning.json',result)
    np.savez_compressed(BASE_DIR/'relay.npz',trace=rr,switches=sw)
    print('RELAY',result['relay'],flush=True);return result

def observer_factory(x0,models,kind='ukf',lstm=None,network=None):
    if kind=='ekf_reconstructed':
        q=np.array(json.loads((RESULTS/'baseline_tuning.json').read_text())['constant_Q'])
        return EKF(x0,models,q)
    return Observer(x0,models,kind,lstm,network)

def pi_factory(models,prediction='physical',mode='siso',constrained=False):
    if prediction!='physical' or mode!='siso' or constrained:raise ValueError('Historical architecture is PI SISO without new thermal constraint')
    return PI()

def init(lib,signature):
    exp.init_worker(lib,signature);exp.Observer=observer_factory;exp.NMPC=pi_factory
    exp.RESULTS=BASE_DIR;exp.KINDS=['ekf_reconstructed']

def run(workers=3):
    config=json.loads((RESULTS/'baseline_tuning.json').read_text())
    sig=hashlib.sha256((json.dumps(config,sort_keys=True)+Path(__file__).read_text()+json.dumps(specification(),default=lambda x:x.tolist() if isinstance(x,np.ndarray) else x)).encode()).hexdigest()
    jobs=[(case,'ekf_reconstructed','physical','siso',False,seed) for case in CASES for seed in SEEDS]
    lib=compile_models();rows=[]
    with mp.get_context('fork').Pool(workers,initializer=init,initargs=(lib,sig)) as pool:
        for row in pool.imap_unordered(exp.run,jobs):
            rows.append(row);print('PI + EKF',len(rows),'/',len(jobs),row['status'],flush=True)
    rows.sort(key=lambda r:r['name']);exp.save_metrics(rows,RESULTS/'metrics_pi_ekf')
    oj=[(case,seed) for case in ['servo_up','benzene_50','recycle_minus50','thermal_loss','kinetics_noise'] for seed in SEEDS]
    obs=[]
    with mp.get_context('fork').Pool(workers,initializer=init,initargs=(lib,sig)) as pool:
        for rr in pool.starmap(exp.openloop,oj):obs.extend(rr)
    exp.save_metrics(obs,RESULTS/'metrics_openloop_ekf')
    assert all(r['status']=='complete' and r['samples']==400 for r in rows+obs)
    print('Finished 18 PI + EKF control runs and 15 EKF observer runs',flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--tune-only',action='store_true');ap.add_argument('--run-only',action='store_true');ap.add_argument('--workers',type=int,default=3);args=ap.parse_args()
    if not args.run_only:tune()
    if not args.tune_only:run(args.workers)
