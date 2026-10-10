"""Exact nominal equations of the recovered benchmarks, with explicit variants.

All time is h, amount kmol, volume m3. PG temperatures K and energy kJ;
EB temperatures degC (Arrhenius K) and energy kcal. The EB historical closure
is intentionally NOT described as reconciled thermodynamics.
"""
from functools import lru_cache
from dataclasses import asdict
from pathlib import Path
import importlib.util
import numpy as np
import casadi as ca
from scipy.optimize import brentq, root

ROOT=Path(__file__).resolve().parents[1]
def reference(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'vendor'/f'{name}_reference.py')
    mod=importlib.util.module_from_spec(spec)
    import sys
    sys.modules[name]=mod;spec.loader.exec_module(mod)
    return mod

class Reactor:
    def __init__(self,kind='PG',variant='historical',dt=None):
        self.kind=kind;self.variant=variant
        if kind=='PG':
            ref=reference('pg');self.constants=asdict(ref.Parameters())
            self.n=6;self.m=6;self.np=4;self.dt=.015 if dt is None else dt
            self.u0=np.r_[ref.U0,[ref.Parameters().FB,ref.Parameters().FM,ref.Parameters().T0]]
            self.x0=ref.steady()['x'];self.tidx=4;self.yidx=[4,5]
            self.noise=np.array([1.385,1.062])/1.8
            self.param_names=['log_k_ref','delta_E_1000_kJ_kmol','log_UA','log_Cp']
            self.pscale=np.array([.15,1.,.15,.05])
            self.xscale=np.r_[np.maximum(.2*self.x0[:4],[.05,.5,.1,.1]),[.3,.3]]
            self.umin=self.u0.copy();self.umax=self.u0.copy()
            self.umin[:3]=[.65*self.u0[0],.05*self.u0[1],self.u0[2]-5]
            self.umax[:3]=[1.35*self.u0[0],3*self.u0[1],self.u0[2]+5]
            self.slew=np.array([.75*self.u0[0],3*self.u0[1],5.,0.,0.,0.]) # per h
            self.tmin=290.;self.tmax=(160-32)/1.8+273.15
            self.cidx=1;self.fidx=0;self.controls=[0,1]
        elif kind=='EB':
            ref=reference('eb');self.n=5;self.m=7;self.np=8;self.dt=.02 if dt is None else dt
            self.u0=ref.U0.copy();self.x0=ref.XSS.copy();self.tidx=4;self.yidx=[4]
            self.noise=np.array([.1]);self.param_names=['log_k1_ref','log_k2_ref','log_k3_ref',
                'delta_E1_1000_cal_mol','delta_E2_1000_cal_mol','delta_E3_1000_cal_mol','log_Cp','log_Q_eff']
            self.pscale=np.array([.15,.15,.15,1.,1.,1.,.05,.02])
            self.xscale=np.r_[.2*self.x0[:4],[.1]]
            self.umin=self.u0.copy();self.umax=self.u0.copy()
            self.umin[[0,3]]=[.65*self.u0[0],.75*self.u0[3]]
            self.umax[[0,3]]=[1.35*self.u0[0],1.25*self.u0[3]]
            self.slew=np.zeros(7);self.slew[[0,3]]=[.4*self.u0[0],.5*self.u0[3]]
            self.tmin=140.85;self.tmax=165.;self.cidx=3;self.fidx=0;self.controls=[0,3]
            self.constants={'V':200.,'K0':[1.528e6*3600,2.778e7*3600,1e3*3600],
                'EA':[17000.,20000.,15000.],'DH':[-27150.,-26950.,-205.5],
                'RHOS':[7.63446,10.8803,10.9014],'CPS':[236.32,265.80,273.50],
                'RHOC':8.09685*73.56,'RECYCLE':[.001198,10.8982,.002015,0.]}
            if variant=='hess':self.constants['DH'][2]=-200.
        else:raise ValueError(kind)
        self.p0=np.zeros(self.np);self._rollout_cache={};self._build()
        if kind=='EB' and variant=='hess':
            self.u0[3]+=float(self.f(self.x0,self.u0,self.p0)[4])*self.constants['RHOC']*200
            self.umin[3]=.75*self.u0[3];self.umax[3]=1.25*self.u0[3]
        self.tau=1/self.dilution(self.u0)
        self.q0=float(self.quality(self.x0));self.prod0=float(self.production(self.x0,self.u0))
        self.duty0=float(self.duty(self.x0,self.u0,self.p0))
    def _build(self):
        x=ca.SX.sym('x',self.n);u=ca.SX.sym('u',self.m);p=ca.SX.sym('p',self.np)
        d=self.constants
        if self.kind=='PG':
            v=u[0]/d['rhoA']+u[3]/d['rhoB']+u[4]/d['rhoM'];D=v/d['V']
            feed=ca.vertcat(u[0],u[3],0,u[4])/v
            temp=x[4]+d['arrhenius_offset'];tref=self.x0[4]+d['arrhenius_offset']
            k=d['k0']*ca.exp(-d['E']/d['R']/temp+p[0]-p[1]*1000/d['R']*(1/temp-1/tref))
            rate=k*x[0];cp=ca.DM([d['cpA'],d['cpB'],d['cpC'],d['cpM']])*ca.exp(p[3])
            duty=u[1]*cp[1]*(u[2]-x[4])*(1-ca.exp(-d['UA']*ca.exp(p[2])/(u[1]*cp[1])))
            cap=d['V']*ca.dot(x[:4],cp);fcp=u[0]*cp[0]+u[3]*cp[1]+u[4]*cp[3]
            rhs=ca.vertcat(D*(feed-x[:4])+ca.DM([-1,-1,1,0])*rate,
                (duty-fcp*(x[4]-u[5])-d['dH']*rate*d['V'])/cap,
                (u[1]*cp[1]*(u[2]-x[5])-duty)/(d['rhoB']*d['Vt']*cp[1]))
            quality=x[2];prod=v*x[2];heat=-duty
            sub=6
        else:
            F=ca.sum1(u[:3]);D=F/d['V'];rho=ca.DM(d['RHOS']);cp=ca.DM(d['CPS'])*ca.exp(p[6])
            temp=x[4]+273.15;tref=433.15
            k=ca.DM(d['K0'])*ca.exp(-ca.DM(d['EA'])/(1.987*temp)+p[:3]-p[3:6]*1000/1.987*(1/temp-1/tref))
            rates=k*ca.vertcat(x[0]*x[1],x[0]*x[2],x[1]*x[3])
            nu=ca.DM([[-1,-1,0],[-1,0,-1],[1,-1,2],[0,1,-1]])
            feed=u[2]*ca.DM(d['RECYCLE'])+ca.vertcat(u[0]*rho[0],u[1]*rho[1],0,0)
            heat=u[3]*ca.exp(p[7]);rhoc=d['RHOC']*ca.exp(p[6])
            energy=ca.dot(u[:3]*rho*cp,u[4:7])-F*rhoc*x[4]-d['V']*ca.dot(ca.DM(d['DH']),rates)-heat
            rhs=ca.vertcat((feed-F*x[:4])/d['V']+nu@rates,energy/(rhoc*d['V']))
            quality=x[2]/ca.sum1(x[:4]);prod=F*x[2]-u[2]*d['RECYCLE'][2]
            sub=12
        self.f=ca.Function('f',[x,u,p],[rhs]);self.fx=ca.Function('fx',[x,u,p],[ca.jacobian(rhs,x)])
        self.fu=ca.Function('fu',[x,u,p],[ca.jacobian(rhs,u)]);self.fp=ca.Function('fp',[x,u,p],[ca.jacobian(rhs,p)])
        self.qfun=ca.Function('quality',[x],[quality]);self.qgrad=ca.Function('qgrad',[x],[ca.jacobian(quality,x)])
        self.prod=ca.Function('prod',[x,u],[prod]);self.heat=ca.Function('heat',[x,u,p],[heat])
        self.dil=ca.Function('dil',[u],[D])
        state=x;h=self.dt/sub
        for _ in range(sub):
            a=self.f(state,u,p);b=self.f(state+h*a/2,u,p);c=self.f(state+h*b/2,u,p);e=self.f(state+h*c,u,p)
            state+=h*(a+2*b+2*c+e)/6
        self.step=ca.Function('step',[x,u,p],[state])
        self.deriv=ca.Function('deriv',[x,u,p],[state,ca.jacobian(state,x),ca.jacobian(state,p)])
    def quality(self,x):
        x=np.asarray(x);return x[...,2] if self.kind=='PG' else x[...,2]/x[...,:4].sum(axis=-1)
    def production(self,x,u):
        return float(self.prod(x,u))
    def duty(self,x,u,p=None):return float(self.heat(x,u,self.p0 if p is None else p))
    def dilution(self,u):return float(self.dil(u))
    def feasible(self,x,u,thermal_limit=None):
        x=np.asarray(x);lim=self.tmax if thermal_limit is None else thermal_limit
        return bool(np.all(np.isfinite(x)) and np.min(x[:4])>=-1e-8 and self.tmin<=x[4]<=lim
                    and np.all(u>=self.umin-1e-7) and np.all(u<=self.umax+1e-7))
    def steady(self,u,p=None,start=None):
        p=self.p0 if p is None else p;start=self.x0 if start is None else start
        sol=root(lambda x:np.array(self.f(x,u,p)).ravel(),start,jac=lambda x:np.array(self.fx(x,u,p)),tol=1e-10)
        err=float(np.max(abs(np.array(self.f(sol.x,u,p)).ravel())))
        if not np.isfinite(err) or err>1e-6 or min(sol.x[:4])<-1e-8:raise ValueError('Nonphysical/failed steady solve')
        return sol.x
    def operating_point(self,feed_ratio,temp):
        u=self.u0.copy();u[0]*=feed_ratio
        if self.kind=='PG':
            d=self.constants;v=u[0]/d['rhoA']+u[3]/d['rhoB']+u[4]/d['rhoM'];D=v/d['V']
            k=d['k0']*np.exp(-d['E']/d['R']/(temp+d['arrhenius_offset']))
            cc=u[0]/v*k/(D+k);x=np.r_[u[0]/v-cc,u[3]/v-cc,cc,u[4]/v,temp,temp]
            def fn(m):
                uu=u.copy();uu[1]=m;return float(self.f(x,uu,self.p0)[4])
            u[1]=brentq(fn,self.umin[1],self.umax[1],xtol=1e-9)
            x[5]=u[2]+(temp-u[2])*(1-np.exp(-d['UA']/(u[1]*d['cpB'])))
        else:
            def fn(c):return np.array(self.f(np.r_[c,temp],u,self.p0))[:4,0]
            s=root(fn,self.x0[:4],tol=1e-11)
            if max(abs(fn(s.x)))>1e-7 or min(s.x)<0:raise ValueError('mass equilibrium')
            x=np.r_[s.x,temp];u[3]+=float(self.f(x,u,self.p0)[4])*self.constants['RHOC']*200
        return x,u
    def rollout(self,x,U,p=None):
        U=np.asarray(U);p=self.p0 if p is None else p
        if len(U)==0:return np.asarray(x)[None]
        if len(U) not in self._rollout_cache:self._rollout_cache[len(U)]=self.step.mapaccum(len(U))
        fn=self._rollout_cache[len(U)]
        X=np.array(fn(x,U.T,np.tile(p,(len(U),1)).T)).T
        return np.vstack([x,X])

@lru_cache(maxsize=16)
def get_model(kind='PG',variant='historical',dt=None):return Reactor(kind,variant,dt)
