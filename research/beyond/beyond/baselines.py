"""Recovered baseline code, adapted ONLY to a common plant/actuator wrapper.

Historical reproduction is separate from this matched comparison. PG C0 retains
its archived Euler UKF and soft thermal cost. C2/C3 use recovered joint filters.
The C3 invariant prior is not promoted as valid knowledge of unknown inventory.
EB FKE+PI is the documented reconstruction, not certified original TFC tuning.
"""
import os,sys,time,argparse
import numpy as np
import pandas as pd
from beyond.models import get_model,ROOT
from beyond.common import RESULTS,metrics,dump
from beyond.control import EKF,FixedPolicy
from beyond.closedloop import scenario
os.environ['LBE_NO_COMPILED']='1'

def pg_factory(name,x):
    sys.path.insert(0,str(ROOT/'vendor/pg_archive'))
    from src.plant.model import Parameters
    from src.estimators.ukf import UKF
    from src.controllers.nmpc import Problem
    from src.optimizers.solvers import solve
    from lbe.estimation import HybridUKF
    from discovery.reduced import ReducedUKF
    import lbe.control as ctl
    ctl.T_LIMIT=get_model('PG').tmax
    p=Parameters();warm=None
    if name=='C0_archived':est=UKF(x,P=np.diag(get_model('PG').xscale**2),method='euler');controller=None
    else:
        est=HybridUKF(x,augmented=True) if name=='C2_joint' else ReducedUKF(x,augmented=True)
        if name=='C2_joint':est.P[:6,:6]=np.diag(get_model('PG').xscale**2)
        controller=ctl.Controller({})
    def update(u,y):
        return est.cycle(u[:3],y,p=p) if name=='C0_archived' else est.cycle(u[:3],p,y)
    def act(xhat,u,ref):
        nonlocal warm
        if name=='C0_archived':
            pr=Problem(xhat,u[:3],np.array([ref,x[4],x[5]]),mode='siso',p=p,warm=warm)
            info=solve(pr,'SQP',maxiter=60);v=pr.action(info['x']);warm=pr.shift(info['x'])
        else:v,info=controller.solve(xhat,u[:3],p,np.full(57,ref),bias=est.bias)
        out=u.copy();out[:3]=v
        return out,info
    return update,act,est

def eb_factory(name,x):
    sys.path.insert(0,str(ROOT/'vendor/eb_archive'))
    from estimators.filters import Filter
    from controllers.cascade import CascadePI
    import controllers.control as ctl
    import controllers.nmpc_envelope as en
    from ethylbenzene_model.model import valve_flow,SCALE
    ctl.TMAX=get_model('EB').tmax;en.TMAX=get_model('EB').tmax
    est=Filter(x,kind='ekf',sigma=.1);est.P=np.diag((get_model('EB').xscale/SCALE)**2)
    controller=ctl.PI() if name=='B0R_FKE_PI' else CascadePI() if name=='cascade_FF' else en.EnvelopeNMPC()
    def update(u,y):return est.update(u,float(y[0]))
    def act(xhat,u,ref):
        before=controller.failures;v=controller.act(xhat,ref,u,P=est.P)
        out=u.copy();out[0]=float(valve_flow(v[0]));out[3]=get_model('EB').u0[3]*v[1]
        return out,dict(success=controller.failures==before,feasible=controller.failures==before)
    return update,act,est

def run(kind):
    m=get_model(kind);rows=[]
    names=['C0_archived','C2_joint','C3_reduced','direct','inferential'] if kind=='PG' else ['B0R_FKE_PI','cascade_FF','envelope_NMPC','direct','inferential']
    regions={'nominal':(m.x0,m.u0)}
    if kind=='PG':regions['fixed_feed_340K']=m.operating_point(1.,340.)
    n=80 if kind=='PG' else 160
    for region,(xo,uo) in regions.items():
        for case in ['known_nominal','unknown_combined']:
            for seed in range(67000,67006):
                p,rng=scenario(m,seed,'combined' if 'unknown' in case else 'nominal')
                initial=xo.copy()
                if 'unknown' in case:initial[:4]*=np.exp(rng.normal(0,.12,4))
                noise=rng.normal(size=(n,len(m.yidx)))*m.noise
                for name in names:
                    x=initial.copy();u=uo.copy();X=[x.copy()];E=[];U=[];Y=[];times=[];fail=0;guard=0;Tfiltered=xo[4]
                    if name in ['direct','inferential']:
                        est=EKF(m,xo);pol=FixedPolicy(m,xo,uo,name,1.)
                    else:update,act,est=(pg_factory if kind=='PG' else eb_factory)(name,xo)
                    for j in range(n):
                        y=x[m.yidx]+noise[j];start=time.perf_counter()
                        if name in ['direct','inferential']:
                            xhat=est.cycle(u,y) if j else xo.copy()
                            desired=pol.act(y,xhat,est.P);info={'success':True}
                        else:
                            xhat=update(u,y) if j else xo.copy();desired,info=act(xhat,u,float(m.quality(xo)))
                        fail+=not info['success'];times.append(time.perf_counter()-start)
                        Tfiltered=.55*Tfiltered+.45*y[0]
                        if Tfiltered>m.tmax-.75:desired[m.cidx]=m.umax[m.cidx];guard+=1
                        desired=np.clip(desired,m.umin,m.umax)
                        u=u+np.clip(desired-u,-m.slew*m.dt,m.slew*m.dt)
                        E.append(xhat.copy());Y.append(y);U.append(u.copy());x=np.array(m.step(x,u,p)).ravel();X.append(x.copy())
                    X=np.array(X);U=np.array(U);E=np.array(E);met=metrics(m,X,U,float(m.quality(xo)),plant_parameters=p)
                    met.update(kind=kind,baseline=name,region=region,case=case,seed=seed,
                        normalized_IAE=met['IAE']/(n*m.dt*m.q0),solver_failures=fail,guard_hits=guard,
                        estimation_RMSE=float(np.sqrt(np.mean((m.quality(E)-m.quality(X[:-1]))**2))),
                        average_ms=1000*np.mean(times),p99_ms=1000*np.quantile(times,.99),
                        initial_information='known exact mean' if case=='known_nominal' else 'common nominal mean, unknown inventories; C3 does not represent invariant uncertainty')
                    rows.append(met);np.savez_compressed(RESULTS/f'baseline_{kind}_{region}_{name}_{case}_{seed}.npz',X=X,U=U,E=E,Y=Y,p=p,timing=times)
                pd.DataFrame(rows).to_csv(RESULTS/f'baselines_{kind}.csv',index=False)
                print(kind,region,case,seed,'baselines complete',flush=True)
    dump(RESULTS/f'baselines_{kind}_scope.json',dict(recovered=True,common_dt=m.dt,common_temperature_limit=m.tmax,
        wrapper='All receive the same external amplitude/slew limits and measured-temperature guard; this changes historical unrestricted actions.',
        historical_reproduction=False,tuning='Recovered gains for previous baselines; frozen gain=1 for new simple policies; no superiority claim from unequal tuning.',
        limitation='C0 original soft thermal penalty; C3 known-inventory premise tested separately; EB B0R is a reconstruction.'))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('kind',choices=['PG','EB']);run(ap.parse_args().kind)
