import time
from functools import lru_cache
import numpy as np
import casadi as ca
from scipy.optimize import minimize
from src.plant.model import *
from lbe.config import N,M,T_LIMIT,DT,CP_DELTA
from lbe.learning import build_step

METHODS={
 'C0_original':dict(legacy=True),
 'C1_classic':dict(),
 'C2_economic':dict(economic=True),
 'C3_hybrid_estimator':dict(estimator=True),
 'C4_hybrid_model':dict(model=True),
 'C5_no_safety':dict(model=True,estimator=True,economic=True,uncertainty=True),
 'C6_full':dict(model=True,estimator=True,economic=True,uncertainty=True,safety=True),
 'A_no_residual':dict(estimator=True,economic=True,uncertainty=True,safety=True,no_residual=True),
 'A_no_QR':dict(model=True,estimator=True,economic=True,uncertainty=True,safety=True,no_QR=True),
 'A_no_economics':dict(model=True,estimator=True,uncertainty=True,safety=True),
 'A_no_uncertainty':dict(model=True,estimator=True,economic=True,safety=True),
 'C1_classic_SG':dict(uncertainty=True,safety=True),
 'C2_chance':dict(economic=True,chance=True)
}

@lru_cache(maxsize=16)
def build(learned=False,economic=False,legacy=False,safety=False):
    # Use symbolic transition while constructing derivatives; external functions
    # need not expose higher derivatives. Compilation occurs after graph creation.
    import os
    previous_flag=os.environ.get('LBE_NO_COMPILED');os.environ['LBE_NO_COMPILED']='1'
    st=build_step(learned)
    if previous_flag is None:os.environ.pop('LBE_NO_COMPILED',None)
    else:os.environ['LBE_NO_COMPILED']=previous_flag
    p=Parameters();q=ca.MX.sym('q',M);par=ca.MX.sym('par',6+3+3+2+N+3)
    x=par[:6];u0=par[6:9];d=par[9:12];bias=par[12:14];refs=par[14:14+N];limit=par[-3];economic_scale=par[-2];barrier_margin=par[-1]
    J=0;G=[];X=[];old=u0[1]/U0[1];v0,_=feed(U0,p);c0=.1433*CUNIT
    for j in range(M):J+=.2*(q[j]-old)**2;old=q[j]
    for j in range(N):
        u=ca.vertcat(u0[0],q[min(j,M-1)]*U0[1],u0[2]);x=st(x,u,d,bias);X.append(x)
        e=(x[2]-refs[j])/c0
        if legacy:
            J+=.8*e**2+1000*(ca.fmax(x[4]-((160-32)/1.8+273.15),0)/(160/1.8))**2
        else:
            quality=30*e**2+200*ca.fmax(ca.fabs(e)-.01,0)**2;J+=quality
            if economic:
                v=u[0]/p.rhoA+d[0]/p.rhoB+d[1]/p.rhoM
                duty=u[1]*p.cpB*(x[4]-u[2])*(1-ca.exp(-p.UA/(u[1]*p.cpB)))
                J+=economic_scale*(u[0]/U0[0]+.04*q[min(j,M-1)]**2+.02*duty/1e6-1.2*v*x[2]/(v0*c0))
            G.append(limit-x[4]);G.append(x[0])
            if safety:
                w=ca.dot(x[:4],ca.DM([p.cpA,p.cpB,p.cpC,p.cpM]));qq=w-CP_DELTA*x[0]
                B=x[4]+(-p.dH)/CP_DELTA*ca.log(1+CP_DELTA*x[0]/qq)
                G.append(T_LIMIT-barrier_margin-B)
    g=ca.vertcat(*G) if G else ca.MX.ones(1,1)
    fun=ca.Function('nmpc',[q,par],[J,ca.gradient(J,q),g,ca.jacobian(g,q)])
    pred=ca.Function('prediction',[q,par],[ca.hcat(X).T])
    if not legacy:
        from lbe.compiled import maybe_compiled
        fun=maybe_compiled(fun,f'mpc_{int(learned)}_{int(economic)}_{int(safety)}')
    return fun,pred

class Controller:
    def __init__(self,options):
        self.options=options;self.fun,self.pred=build(options.get('model',False),options.get('economic',False),options.get('legacy',False),options.get('safety',False));self.warm=np.ones(M)
    def solve(self,x,u,p,refs,bias=np.zeros(2),sigmaT=0.,eco_scale=1.,force_failure=False,barrier_margin=0.):
        opt=self.options;limit=T_LIMIT
        if opt.get('uncertainty'):limit-=2.
        if opt.get('chance'):limit-=2.326347874*min(sigmaT,3.)
        par=np.r_[x,u,[p.FB,p.FM,p.T0],bias,refs,limit,eco_scale,barrier_margin];cache=[None,None]
        def evaluate(q):
            if cache[0] is None or not np.array_equal(cache[0],q):
                a=self.fun(q,par);cache[:]=[q.copy(),(float(a[0]),np.array(a[1]).ravel(),np.array(a[2]).ravel(),np.array(a[3]))]
            return cache[1]
        timer=time.perf_counter()
        try:
            if force_failure:raise RuntimeError('injected solver failure')
            r=minimize(lambda q:evaluate(q)[0],self.warm,jac=lambda q:evaluate(q)[1],method='SLSQP',bounds=[(.05,3.)]*M,
              constraints=[dict(type='ineq',fun=lambda q:evaluate(q)[2],jac=lambda q:evaluate(q)[3])],options=dict(maxiter=60,ftol=1e-6,disp=False))
            good=bool(np.isfinite(r.fun) and np.min(evaluate(r.x)[2])>=-1e-5)
            success=bool(r.success);iters=r.nit;qq=r.x if good else self.warm
        except Exception:
            good=success=False;iters=0;qq=self.warm
        if not good:qq=np.full(M,3.)
        self.warm=np.r_[qq[1:],qq[-1]];a=u.copy();a[1]=float(np.clip(qq[0],.05,3))*U0[1]
        return a,dict(success=success,feasible=good,iterations=iters,seconds=time.perf_counter()-timer,predicted_limit=limit)
