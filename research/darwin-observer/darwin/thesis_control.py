"""SQP reproduction of archived NMPC objective and bounds.

SLSQP is not MATLAB fmincon. CasADi supplies exact objective derivatives; the
optional generated C function changes speed only. The original soft thermal
penalty is switched on/off without changing any other tuning.
"""
import os,time,subprocess
from pathlib import Path
from functools import lru_cache
import numpy as np
import casadi as ca
from scipy.optimize import minimize
from .physics import LEGACY_CP as CP,LEGACY_RHO as RHO,LEGACY_V as V,LEGACY_VT as VT,LEGACY_UA as UA,NP
from .thesis_cases import U_NOM,SP_NOM,T_LIMIT

CACHE=Path(__file__).resolve().parents[1]/'artifacts'/'thesis'/'compiled'

def symbolic_functions():
    x=ca.SX.sym('x',6);u=ca.SX.sym('u',6);p=ca.SX.sym('p',NP)
    v=u[3]/453.6
    basis=ca.vertcat(1,v-1,ca.log(v),(v-1)**2,1/v-1,ca.sqrt(v)-1)
    ua=UA*ca.exp(ca.dot(p[:6],basis));km=ca.exp(p[6]+p[7]*10*(340/x[4]-1))
    fa=u[0]*ca.exp(p[9]);flow=fa/RHO[0]+u[1]/RHO[1]+u[2]/RHO[2]
    rate=16.96e12*ca.exp(-75362.4/((1.987*4.1868)*(x[4]+.1833333333333333)))*km*x[0]
    q=u[3]*CP[1]*(u[5]-x[4])*(1-ca.exp(-ua/(u[3]*CP[1])))
    cap=V*ca.dot(x[:4],ca.DM(CP))*ca.exp(p[13])
    sens=(fa*CP[0]+u[1]*CP[1]+u[2]*CP[3])*(x[4]-u[4]-p[14])
    dx=ca.vertcat((ca.vertcat(fa,u[1],0,u[2])-flow*x[:4])/V+rate*ca.DM([-1,-1,1,0]),
                 (q-sens+83736*ca.exp(p[8])*rate*V)/cap,
                 (u[3]*CP[1]*(u[5]-x[5])-q)/(RHO[1]*VT*CP[1]))
    f=ca.Function('thesis_rhs',[x,u,p],[dx]);h=.015
    a=f(x,u,p);b=f(x+h*a/2,u,p);c=f(x+h*b/2,u,p);d=f(x+h*c,u,p)
    st=ca.Function('thesis_step',[x,u,p],[x+h*(a+2*b+2*c+d)/6])
    moves=ca.MX.sym('moves',6);par=ca.MX.sym('par',87)
    state=par[:6];inputs=par[6:12];sp=par[12];prev=par[13];thermal=par[14];params=par[15:30]
    J=0;pred=[]
    for k in range(57):
        uu=ca.MX(inputs);uu[3]=U_NOM[3]*moves[min(k,5)]
        state=st(state,uu,params);pred.append(state)
        J+=.8*((par[30+k]-state[2])/SP_NOM)**2
        if k<6:J+=.2*(moves[k]-(prev/U_NOM[3] if k==0 else moves[k-1]))**2
        J+=thermal*1000*(ca.fmax(state[4]-T_LIMIT,0)/(160/1.8))**2
    return ca.Function('thesis_cost_grad',[moves,par],[J,ca.gradient(J,moves)]),ca.Function('thesis_prediction',[moves,par],[ca.hcat(pred).T])

@lru_cache(maxsize=1)
def functions():
    cost,pred=symbolic_functions()
    library=CACHE/('thesis_cost.dll' if os.name=='nt' else 'thesis_cost.so')
    if library.exists():
        try:
            compiled=ca.external('thesis_cost_grad',str(library))
            if compiled.size1_in(1)==87:cost=compiled
        except RuntimeError:pass
    return cost,pred

def compile_kernel():
    CACHE.mkdir(parents=True,exist_ok=True);cost,_=symbolic_functions()
    original=Path.cwd()
    try:
        os.chdir(CACHE);cost.generate('thesis_cost.c',{'with_header':True})
        subprocess.run(['gcc','-O3','-fPIC','-shared','thesis_cost.c','-o','thesis_cost.so','-lm'],check=True)
    finally:os.chdir(original)
    functions.cache_clear()

class ThesisNMPC:
    def __init__(self,thermal=False):
        self.sequence=np.ones(6);self.thermal=thermal;self.events=[];self.k=0
        self.cost,self.predict=functions()
    def action(self,x,u,sp,model,future_reference=None):
        self.k+=1;start=time.perf_counter()
        # Archived lastmv = shifted initial sequence[0], not previous applied MV.
        warm=np.r_[self.sequence[1:],self.sequence[-1]]
        refs=np.full(57,sp) if future_reference is None else np.asarray(future_reference,float)
        par=np.r_[x,u,sp,U_NOM[3]*warm[0],float(self.thermal),model.params,refs]
        def evaluate(a):
            j,g=self.cost(a,par);return float(j),np.asarray(g).ravel()
        opt=minimize(evaluate,warm,method='SLSQP',jac=True,bounds=[(.05,3.)]*6,
                     options={'maxiter':100,'ftol':1e-6,'disp':False})
        feasible=np.all(np.isfinite(opt.x)) and np.isfinite(opt.fun) and np.all((opt.x>=.05-1e-8)&(opt.x<=3.+1e-8))
        proposal=np.clip(opt.x,.05,3.) if feasible else warm
        # An unsuccessful SQP never silently substitutes an arbitrary solution.
        fallback=False
        if not opt.success:
            candidates=[warm,np.ones(6),np.full(6,3.)]
            proposal=min(candidates,key=lambda a:evaluate(a)[0]);fallback=True
        self.sequence=proposal
        return float(U_NOM[3]*proposal[0]),dict(solver_success=bool(opt.success),fallback=fallback,
            iterations=int(opt.nit),solver_ms=1000*(time.perf_counter()-start),objective=float(evaluate(proposal)[0]),
            status=int(opt.status))
