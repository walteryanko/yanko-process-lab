"""Finite candidate NMPC, exact minimax regret within the declared action grid.
A separate continuous two-block SLSQP baseline diagnoses grid artifacts.
"""
import numpy as np
from numba import njit
from scipy.optimize import minimize
from model import step,DT,U0,TLIMIT,twin

def candidates(previous,qmax=3.,n=5):
    vals=[]
    for a in np.linspace(-.4,.4,n):
        u=np.clip(previous+a,.05,qmax)
        for b in np.linspace(-.4,.4,n):
            v=np.clip(u+b,.05,qmax);vals.append([u,v])
    return np.unique(np.array(vals),axis=0)

@njit(cache=True)
def costs(states,plans,u,p,reference,previous,horizon=14,variant=0):
    J=np.empty((len(states),len(plans)));viol=np.empty_like(J)
    for i in range(len(states)):
        for j in range(len(plans)):
            z=states[i].copy();uu=u.copy();vmax=0.;value=0.
            for k in range(horizon):
                uu[3]=U0[3]*plans[j,0 if k<3 else 1]
                z=step(z,uu,p,variant,3)
                value+=.8*((z[2]-reference)/2.295764605)**2
                vmax=max(vmax,z[4]-TLIMIT)
                value+=1000*(max(0.,z[4]-TLIMIT)/(160/1.8))**2
            value+=.2*((plans[j,0]-previous)**2+(plans[j,1]-plans[j,0])**2)
            J[i,j]=value;viol[i,j]=vmax
    return J,viol

def select(J,V,mode):
    feasible=(V<=1e-8)&np.isfinite(J)
    common=np.all(feasible,axis=0)
    minima=np.min(np.where(feasible,J,np.inf),axis=1)
    regret=J-minima[:,None]
    if not np.any(common) or not np.all(np.isfinite(minima)):
        # Explicit fallback: lowest sampled thermal violation, then cost.
        z=np.lexsort((np.max(J,axis=0),np.max(V,axis=0)))[0]
        return int(z),True,float('nan')
    if mode=='regret':score=np.max(regret,axis=0)
    elif mode=='worst':score=np.max(J,axis=0)
    else:score=np.mean(J,axis=0)
    z=int(np.argmin(np.where(common,score,np.inf)))
    return z,False,float(np.max(regret[:,z]))

def decide(x,u,p,ref,prev,mode='nominal',width=0.,qmax=3.,horizon=14,ngrid=5):
    plans=candidates(prev,qmax,ngrid)
    states=np.array([x]) if mode in ['nominal','continuous'] else np.array([twin(x,-width),x,twin(x,width)])
    # Only physically admissible representatives are retained.
    states=states[np.min(states[:,:4],axis=1)>0]
    if len(states)==0:states=np.array([x])
    J,V=costs(states,plans,u,p,ref,prev,horizon)
    z,fall,regret=select(J,V,mode)
    plan=plans[z].copy();success=True
    if mode=='continuous':
        def fun(a):return float(costs(states,a[None,:],u,p,ref,prev,horizon)[0][0,0])
        def con(a):
            _,v=costs(states,a[None,:],u,p,ref,prev,horizon)
            return np.r_[1e-8-v[0],.4-np.abs(a[1]-a[0])]
        op=minimize(fun,plan,method='SLSQP',bounds=[(max(.05,prev-.4),min(qmax,prev+.4)),(.05,qmax)],
            constraints=[{'type':'ineq','fun':con}],options={'maxiter':25,'ftol':1e-7})
        success=bool(op.success and min(con(op.x))>=-1e-6 and np.isfinite(op.fun))
        if success and op.fun<=fun(plan)+1e-8:plan=op.x
        else:fall=True
    independent=np.argmin(np.where(V<=1e-8,J,np.inf),axis=1)
    conflict=float(np.ptp(plans[independent,0])) if len(states)>1 else 0.
    return float(plan[0]),dict(fallback=fall,solver_success=success,regret=regret,conflict=conflict,
                              predicted_violation=float(np.max(V[:,z])),candidates=len(plans))
