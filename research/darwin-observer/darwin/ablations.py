"""Predeclared mechanism ablations and independent falsification challenges."""
import json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from .physics import Model,NP,BASE,U0,CP,simulate
from .truth import generate
from .observers import observe
from .detection import diagnose
from .discovery import GuardedDarwin
from .identification import residual_vector,local_observability
from .experiments import savejson,savecsv,save_episode

ROOT=Path(__file__).resolve().parents[1]

def streaming(record,d,threshold,delay=False,monitor=True):
    g=GuardedDarwin(None if delay else d,monitor=monitor);xs=[BASE.copy()];attempted=not delay
    for k,(u,y) in enumerate(zip(record.inputs,record.measurements[1:]),1):
        x,_=g.update(u,y);xs.append(x)
        if delay and not attempted and k>=20:
            if diagnose(observe(record.prefix(k)),threshold)['detected']:
                g.approve(d);attempted=True
    return np.array(xs),g.events,g.fallbacks

def main():
    out=ROOT/'artifacts'/'main';th=json.loads((out/'calibration.json').read_text(encoding='utf-8'))['threshold'];rows=[];events=[]
    # Models already fitted: removing one acceptance criterion does not refit on test.
    for j,s in enumerate(['H0','A_rich','C_bias','B_curvature']):
        d=json.loads((out/'discoveries'/f'{s}.json').read_text(encoding='utf-8'));rank=d['ranking'];nom=next(r for r in rank if r['name']=='H0')
        choices={
          'full':d['model'],
          'no_detector':min([r for r in rank if r['eligible']],key=lambda r:r['score'])['model'],
          'no_holdout_ranking':min(rank,key=lambda r:r['train_mse'])['model'],
          'no_physical_gate':min(rank,key=lambda r:r['score'])['model'],
          'no_symbolic':min([r for r in rank if r['category']!='structure' and r['eligible']],key=lambda r:r['score'])['model'],
          'no_adaptation':nom['model']}
        for i in range(100):
            ep=generate(400000+j*1000+i,s)
            for method,md in choices.items():
                r=observe(ep.operational,Model.from_dict(md));err=np.sqrt(np.mean((r['x'][:,2]-ep.truth[:,2])**2))
                rows.append(dict(scenario=s,seed=ep.operational.seed,method=method,rmse_CC=float(err)))
    for j,s in enumerate(['A_rich','D_feed','X_saturation']):
        d=json.loads((out/'discoveries'/'A_rich.json').read_text(encoding='utf-8'))
        for i in range(100):
            ep=generate(450000+j*1000+i,s)
            for method,delay,monitor in [('online_guarded',True,True),('frozen_guarded',False,True),('no_loss_fallback',False,False)]:
                xs,ev,nf=streaming(ep.operational,d,th,delay,monitor)
                rows.append(dict(scenario=s,seed=ep.operational.seed,method=method,rmse_CC=float(np.sqrt(np.mean((xs[:,2]-ep.truth[:,2])**2))),fallbacks=nf))
                if i<3:events.append(dict(scenario=s,seed=ep.operational.seed,method=method,events=ev))
    savecsv(out/'ablations.csv',rows);savejson(out/'online_events.json',events)
    # Development challenge search only. X_saturation final test seeds are disjoint.
    d=json.loads((out/'discoveries'/'A_rich.json').read_text(encoding='utf-8'));m=Model.from_dict(d['model']);challenges=[];rng=np.random.default_rng(601017)
    for i in range(40):
        dt=float(rng.choice([.0075,.015,.03]));strength=float(rng.uniform(.1,.55));scenario=str(rng.choice(['D_feed','D_flow','D_composition','X_saturation','D_noise']))
        ep=generate(600000+i,scenario,dt=dt,overrides=dict(strength=strength));a=observe(ep.operational,m);b=observe(ep.operational)
        ae=float(np.sqrt(np.mean((a['x'][:,2]-ep.truth[:,2])**2)));be=float(np.sqrt(np.mean((b['x'][:,2]-ep.truth[:,2])**2)))
        challenges.append(dict(seed=600000+i,scenario=scenario,dt=dt,strength=strength,Darwin_rmse=ae,UKF_rmse=be,ratio=ae/max(be,1e-9)))
        save_episode(out/'datasets'/'challenge'/f'{600000+i}.npz',ep)
    challenges.sort(key=lambda r:r['ratio'],reverse=True);savejson(out/'adversarial.json',dict(refitted=False,development_challenges=challenges,final_evaluation='X_saturation; seeds 117000..117099'))
    # Profile activation coefficient with rate and heat as nuisance competitors.
    recs=[generate(10000+5*1000+i,'B_activation').operational for i in range(4)]
    prof=[]
    for activation in np.linspace(-1.2,.3,21):
        def objective(q):
            p=np.zeros(NP);p[7]=activation;p[[0,6,8]]=q
            return residual_vector(recs,p)
        r=least_squares(objective,[0,0,0],bounds=([-.5,-.6,-.15],[.5,.6,.15]),max_nfev=45,loss='soft_l1')
        prof.append(dict(activation=float(activation),mse=float(np.mean(r.fun**2)),nuisance_UA_rate_heat=r.x.tolist(),success=bool(r.success)))
    delta=np.array([0.,-CP[2]/CP[1],1.,0.,0.,0.])*.12
    inp=np.tile(U0,(80,1));a=simulate(BASE,inp,np.zeros(NP));b=simulate(BASE+delta,inp,np.zeros(NP))
    savejson(out/'identifiability.json',dict(local_observability=local_observability(BASE,U0),activation_profile=prof,
        invisible_direction=delta,thermal_separation=float(np.max(abs(a[:,4:]-b[:,4:]))),initial_CC_separation=.12,
        caveat='profile is conditional on operational prefix and finite candidate family; no proof of unique global mechanism'))
    print('Ablations',len(rows),'challenges',len(challenges),flush=True)

if __name__=='__main__':main()
