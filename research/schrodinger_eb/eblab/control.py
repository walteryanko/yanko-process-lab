"""Simulation-only constrained NMPC; estimation and controller effects separated.
CasADi derivatives, SciPy SLSQP, same limits/objective for all four arms.
"""
import argparse,time,csv
from functools import lru_cache
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from .model import *
from .filters import FilterConfig,make_filter
from .experiments import initial,write_json,serial
HORIZON=20;BLOCK=5;MOVES=4
BOUNDS=[(.04,2.),(.6,1.4)]*MOVES
MOVE_LIMIT=np.array([.12,.08])

@lru_cache(None)
def evaluator(nsc):
    import casadi as ca
    x=ca.SX.sym('x',5);u=ca.SX.sym('u',7)
    k=ca.DM(K0*3600)*ca.exp(-ca.DM(E)/(RGAS*(x[4]+273.15)))
    rr=k*ca.vertcat(x[0]*x[1],x[0]*x[2],x[1]*x[3])
    total=ca.sum1(u[:3]);feed=u[0]*RHO[0]*ca.DM([1,0,0,0])+u[1]*RHO[1]*ca.DM([0,1,0,0])+u[2]*ca.DM(REC)
    dc=(feed-total*x[:4])/V+ca.DM(NU)@rr
    heat=ca.dot(u[:3]*ca.DM(RHO*CP),u[4:7])-total*RHO_REACTOR*CP_REACTOR*x[4]-V*ca.dot(rr,ca.DM(DH))-u[3]
    fun=ca.Function('ode',[x,u],[ca.vertcat(dc,heat/CAPACITY)])
    xx=x;h=DT/8
    for _ in range(8):
        a=fun(xx,u);b=fun(xx+h*a/2,u);c=fun(xx+h*b/2,u);d=fun(xx+h*c,u);xx+=h*(a+2*b+2*c+d)/6
    transition=ca.Function('transition',[x,u],[xx])
    q=ca.MX.sym('q',MOVES*2);param=ca.MX.sym('param',5*nsc+7+1+2)
    states=[param[5*i:5*(i+1)] for i in range(nsc)]
    baseu=param[5*nsc:5*nsc+7];target=param[5*nsc+7];prev=param[-2:]
    loss=0;constraints=[]
    for k in range(HORIZON):
        move=q[2*(k//BLOCK):2*(k//BLOCK)+2]
        uu=ca.vertcat(baseu[0]*move[0],baseu[1:3],baseu[3]*move[1],baseu[4:7])
        for j in range(nsc):
            states[j]=transition(states[j],uu);z=states[j];frac=z[2]/ca.sum1(z[:4])
            loss+=(.8*((frac-target)/.02)**2+.2*((z[4]-TNOM)/5)**2)/nsc
            constraints += [(T_LIMIT-z[4])/5,z[0]/.1]
    for i in range(MOVES):
        move=q[2*i:2*i+2];delta=move-(prev if i==0 else q[2*i-2:2*i])
        loss+=.03*ca.dot(delta,delta)
        constraints.extend([ca.DM(MOVE_LIMIT)-delta,ca.DM(MOVE_LIMIT)+delta])
    con=ca.vertcat(*constraints)
    return ca.Function('nmpc',[q,param],[loss,ca.gradient(loss,q),con,ca.jacobian(con,q)])

def representatives(mean,particles,w,policy):
    if policy=='nominal':return np.array(mean[:5])[None,:]
    if policy!='risk':raise ValueError('Unknown policy')
    rows=[np.array(mean[:5])]
    for value in [fraction(particles[:,:5]),particles[:,4]]:
        order=np.argsort(value);cdf=np.cumsum(w[order])
        for q in [.1,.9]:rows.append(particles[order[min(np.searchsorted(cdf,q),len(order)-1)],:5])
    return np.array(rows)

def nominal_fallback(mean,target,previous):
    action=np.array([1+8*(target-fraction(mean[:5])),1+.03*(mean[4]-TNOM)])
    action=np.clip(action,previous-MOVE_LIMIT,previous+MOVE_LIMIT)
    return np.clip(action,[.04,.6],[2.,1.4])

class NMPC:
    def __init__(self,policy='nominal'):
        self.policy=policy;self.previous=np.ones(2);self.warm=np.ones(8)
    def choose(self,mean,particles,w,u,target,force_fallback=False):
        states=representatives(mean,particles,w,self.policy);fun=evaluator(len(states))
        param=np.r_[states.ravel(),u,target,self.previous];cache={};start=time.perf_counter()
        def calc(q):
            if 'q' not in cache or not np.array_equal(q,cache['q']):
                v=fun(q,param);cache.update(q=q.copy(),v=[np.asarray(t).squeeze() for t in v])
            return cache['v']
        if not force_fallback:
            sol=minimize(lambda q:float(calc(q)[0]),self.warm,jac=lambda q:calc(q)[1],method='SLSQP',bounds=BOUNDS,
                constraints=[dict(type='ineq',fun=lambda q:calc(q)[2],jac=lambda q:calc(q)[3])],
                options={'ftol':1e-7,'maxiter':35,'disp':False})
            v=calc(sol.x);feasible=bool(np.isfinite(v[0]) and np.all(np.isfinite(v[2])) and np.min(v[2])>=-1e-6)
            success=bool(sol.success);iterations=int(sol.nit)
        else:feasible=False;success=False;iterations=0
        if feasible:self.warm=sol.x.copy();action=self.warm[:2].copy()
        else:action=nominal_fallback(mean,target,self.previous);self.warm=np.tile(action,MOVES)
        self.previous=action.copy()
        return action,dict(fallback=int(not feasible),solver_success=success,iterations=iterations,
            control_ms=1000*(time.perf_counter()-start),feasible=feasible)

def episode(job):
    seed,method,policy,steps,forced=job;rng=np.random.default_rng(np.random.SeedSequence([seed,77123]))
    mean,cov=initial('gaussian');x=rng.multivariate_normal(mean,cov*.25)
    process=rng.normal(size=(steps,5))*np.sqrt(Q_PUBLISHED);noise=rng.normal(0,1.5,steps)
    f=make_filter(method,mean,cov,np.array([[2.25]]),FilterConfig(),seed+8888)
    ctl=NMPC(policy);m=mean.copy();hist=[];failure=None;target0=fraction(BASE)
    for k in range(steps):
        try:
            target=target0*(1.04 if 20<=k<40 else 1.)
            pts,w,_=f.posterior(seed=seed+k);action,diag=ctl.choose(m,pts,w,U0,target,forced)
            u=U0.copy();u[0]*=action[0];u[3]*=action[1]
            x=step(x,u,method='dop853')+process[k]
            if not valid(x):raise ValueError('Closed-loop truth outside domain')
            y=np.array([x[4]+noise[k]]);m,p=f.advance(u,y)
            hist.append(dict(k=k,x=x,estimate=m[:5],y=y,reference=target,commands=action,
                fE=u[0],Q_MW=u[3]*4184/3.6e9,sigma_T=np.sqrt(p[4,4]),filter=f.last.copy(),**diag))
        except Exception as ex:failure=dict(step=k,type=type(ex).__name__,message=str(ex));break
    metrics=dict(seed=seed,method=method,policy=policy,steps=len(hist),failure=failure,forced=forced)
    if hist:
        metrics.update(iae_xEB=float(DT*sum(abs(fraction(r['x'])-r['reference']) for r in hist)),
            rmse_CEB=float(np.sqrt(np.mean([(r['x'][2]-r['estimate'][2])**2 for r in hist]))),
            peak_T=max(r['x'][4] for r in hist),violations=sum(r['x'][4]>T_LIMIT for r in hist),
            fallbacks=sum(r['fallback'] for r in hist),solver_failures=sum(not r['solver_success'] for r in hist),
            control_ms=np.mean([r['control_ms'] for r in hist]),heat_removed_Gcal=DT*sum(r['Q_MW']*3.6e9/4184/1e6 for r in hist),
            ethylene_m3=DT*sum(r['fE'] for r in hist),
            production_kmol=DT*sum((r['fE']+U0[1]+U0[2])*r['x'][2] for r in hist))
    return metrics,dict(seed=seed,method=method,policy=policy,history=hist)

def experiment(trials=10,steps=60,out='results/control',workers=4,forced=False):
    from concurrent.futures import ProcessPoolExecutor,as_completed
    path=Path(out);path.mkdir(parents=True,exist_ok=True);rows=[];traces=[]
    arms=[('M0','nominal')] if forced else [('M0','nominal'),('M1','nominal'),('M4','nominal'),('M4','risk')]
    jobs=[(seed,m,p,steps,forced) for seed in range(1550 if forced else 4000,(1550 if forced else 4000)+trials) for m,p in arms]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for fut in as_completed([pool.submit(episode,j) for j in jobs]):
            r,t=fut.result();rows.append(r);traces.append(t);print('control',r['seed'],r['method'],r['policy'],r['failure'],flush=True)
    rows.sort(key=lambda r:(r['seed'],r['method'],r['policy']));groups={};rng=np.random.default_rng(19)
    refs={r['seed']:r['iae_xEB'] for r in rows if r['method']=='M0' and not r['failure']}
    sbrefs={r['seed']:r['iae_xEB'] for r in rows if r['method']=='M4' and r['policy']=='nominal' and not r['failure']}
    for m,p in arms:
        rr=[r for r in rows if r['method']==m and r['policy']==p];good=[r for r in rr if not r['failure']]
        g=dict(n=len(rr),completed=len(good),failed=len(rr)-len(good))
        if good:
            for key in ['iae_xEB','rmse_CEB','peak_T','violations','fallbacks','solver_failures','control_ms','heat_removed_Gcal','ethylene_m3','production_kmol']:g[key]=np.mean([r[key] for r in good])
            for name,ref in [('vs_UKF',refs),('vs_M4_nominal',sbrefs)]:
                d=np.array([r['iae_xEB']-ref[r['seed']] for r in good if r['seed'] in ref])
                if len(d):g[name]=dict(mean_delta=d.mean(),ci95=np.quantile(rng.choice(d,(2000,len(d))).mean(1),[.025,.975]))
        groups[m+'_'+p]=g
    write_json(path/'control.json',dict(rows=rows,summary=groups,traces=traces,horizon=HORIZON,steps=steps,
       constraints=dict(T_max_C=165,fE_relative=[.04,2],Q_relative=[.6,1.4],move_limits=MOVE_LIMIT),
       limitation='Ideal heat-removal actuator; local solver, five representative scenarios; not a safety guarantee or industrial validation. No Multiverse module claimed.'))
    with (path/'control.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(serial(rows))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--trials',type=int,default=10);p.add_argument('--steps',type=int,default=60)
    p.add_argument('--out',default='results/control');p.add_argument('--workers',type=int,default=4);p.add_argument('--forced',action='store_true')
    a=p.parse_args();experiment(a.trials,a.steps,a.out,a.workers,a.forced)
