import time,os
import numpy as np
import casadi as ca
from ethylbenzene_model.model import *

# Literature-inspired operational TEST envelope, NOT a certified process limit.
TMAX=170.85

class PI:
    def __init__(self,kp=1.2,ti=.4,feedforward=False,safety=False):
        self.kp=kp;self.ti=ti;self.ff=feedforward;self.safety=safety;self.integral=0.;self.last=NOMINAL_STROKE
        self.time=[];self.fallbacks=0;self.failures=0
        # Linear steady-state feedforward in valve position; generated from model.
        self.g=np.zeros(2)
        x0,_=steady();yy=molefractions(x0)[2]
        up=U0.copy();up[0]*=1.001;xx,_=steady(up);gu=(molefractions(xx)[2]-yy)/(.001*U0[0])*U0[0]*np.log(50)
        for j in range(2):
            up=U0.copy();up[j+1]*=1.001;xx,_=steady(up);gd=(molefractions(xx)[2]-yy)/(.001*U0[j+1]);self.g[j]=-gd/gu
    def act(self,x,sp,u,p=None,P=None):
        t=time.perf_counter();err=sp-molefractions(x)[2]
        ff=float(self.g@(u[1:3]-U0[1:3])) if self.ff else 0.
        raw=NOMINAL_STROKE+ff+self.kp*err+self.integral
        stroke=float(np.clip(raw,.05,1))
        # Conditional integration anti-windup at static valve saturation.
        if abs(raw-stroke)<1e-10 or np.sign(err)!=np.sign(raw-stroke):self.integral+=self.kp/self.ti*DT*err
        if self.safety:
            stroke,hit=safety_filter(x,stroke,u,p);self.fallbacks+=hit
        self.last=stroke;self.time.append(time.perf_counter()-t)
        return np.array([stroke,1.])

def safety_filter(x,stroke,u,p=None,margin=0.):
    p=np.zeros(12) if p is None else p
    def temp(s):
        uu=u.copy();uu[0]=float(valve_flow(s));return step(x,uu,p)[4]
    if temp(stroke)<=TMAX-margin:return stroke,0
    lo=.05;hi=stroke
    if temp(lo)>TMAX-margin:return lo,1
    for _ in range(20):
        mid=(lo+hi)/2
        if temp(mid)>TMAX-margin:hi=mid
        else:lo=mid
    return lo,1

class NMPC:
    cache={}
    def __init__(self,mimo=False,constrained=True,robust=False,economic=False,adaptive_compute=False,horizon=12):
        self.mimo=mimo;self.constrained=constrained;self.robust=robust;self.economic=economic
        self.adaptive_compute=adaptive_compute;self.horizon=horizon;self.time=[];self.iterations=[];self.failures=0;self.fallbacks=0
        self.last=np.array([NOMINAL_STROKE,1.]);self.guess=None
    def _build(self,n):
        key=(self.mimo,self.constrained,self.robust,self.economic,n)
        if key in self.cache:return self.cache[key]
        # first step is actual sample time; remaining predictions are 6 min apart.
        _,_,_,longstep,_=build(dt=.10,substeps=12)
        nc=4;nm=2 if self.mimo else 1
        v=ca.MX.sym('v',nm*nc);par=ca.MX.sym('par',5+7+12+1+2+1)
        x=par[:5];u=par[5:12];p=par[12:24];sp=par[24];last=par[25:27];margin=par[27]
        cost=0;g=[];ws=[]
        scenarios=[0.] if not self.robust else [-.07,0.,.07]
        for sc in scenarios:
            xx=x;pp=ca.MX(p);pp[0]+=sc;prev=last
            for j in range(n):
                block=min(nc-1,j*nc//n);s=v[block*nm];cool=v[block*nm+1] if self.mimo else 1.
                uu=ca.MX(u);uu[0]=FMAX*50**(s-1);uu[3]=Q0*cool
                xx=STEP(xx,uu,pp) if j==0 else longstep(xx,uu,pp)
                y=xx[2]/ca.sum1(xx[:4]);debf=xx[3]/ca.sum1(xx[:4])
                weight=DT if j==0 else .10
                cost+=weight*((y-sp)/.025)**2/len(scenarios)
                cost+=weight*.025*((s-NOMINAL_STROKE)/.2)**2/len(scenarios)
                if self.mimo:cost+=weight*.003*((cool-1)/.2)**2/len(scenarios)
                if self.economic:cost+=weight*.06*(debf/.05)**2/len(scenarios)
                if self.constrained:g.append(xx[4]+margin);ws.append(0)
                if j==0:
                    g.append(s-last[0]);ws.append(1)
                    cost+=.003*((s-last[0])/.025)**2
                    if self.mimo:g.append(cool-last[1]);ws.append(2);cost+=.001*((cool-last[1])/.025)**2
            cost+=2*((xx[2]/ca.sum1(xx[:4])-sp)/.025)**2/len(scenarios)
        opts={'ipopt.print_level':0,'print_time':False,'ipopt.sb':'yes','ipopt.max_iter':55,'ipopt.tol':1e-5,'ipopt.acceptable_tol':1e-3,'ipopt.max_cpu_time':.7}
        if os.environ.get('EB_JIT')=='1':opts.update({'jit':True,'compiler':'shell','jit_options':{'flags':['-O0']}})
        solver=ca.nlpsol('mpc','ipopt',{'x':v,'p':par,'f':cost,'g':ca.vertcat(*g)},opts)
        lb=np.tile([.05,.75] if self.mimo else [.05],nc);ub=np.tile([1.,1.25] if self.mimo else [1.],nc)
        lbg=np.array([-np.inf if w==0 else -.045 if w==1 else -.035 for w in ws]);ubg=np.array([TMAX if w==0 else .045 if w==1 else .035 for w in ws])
        self.cache[key]=(solver,lb,ub,lbg,ubg)
        return self.cache[key]
    def act(self,x,sp,u,p=None,P=None):
        t=time.perf_counter();p=np.zeros(12) if p is None else p
        n=self.horizon
        if self.adaptive_compute:n=8 if x[4]<TMAX-5 and (P is None or P[4,4]<.001) else 16
        solver,lb,ub,lbg,ubg=self._build(n)
        margin=0.
        if self.robust and P is not None:margin=min(2.,1.645*np.sqrt(max(P[4,4],0))*SCALE[4])
        par=np.r_[x,u,p,sp,self.last,margin]
        if self.guess is None or len(self.guess)!=len(lb):self.guess=np.tile(self.last if self.mimo else self.last[:1],4)
        try:
            sol=solver(x0=self.guess,p=par,lbx=lb,ubx=ub,lbg=lbg,ubg=ubg)
            stats=solver.stats();z=np.array(sol['x']).ravel();gg=np.array(sol['g']).ravel()
            feasible=np.all(gg<=ubg+1e-3) and np.all(gg>=lbg-1e-3) and np.all(np.isfinite(z))
            if not stats['success'] or not feasible:raise ValueError('infeasible/failed NLP')
            self.guess=z;self.last=np.array([z[0],z[1] if self.mimo else 1.]);self.iterations.append(stats['iter_count'])
        except (ValueError,RuntimeError):
            self.failures+=1;self.fallbacks+=1
            s,_=safety_filter(x,self.last[0],u,p)
            self.last=np.array([s,min(1.25,self.last[1]+.035) if self.mimo else 1.])
        self.time.append(time.perf_counter()-t)
        return self.last.copy()
