"""Faithful SI transform of the recovered 2019 modeloCT.m; hours are time units.
The archived T_F+460 convention is retained as T_K+0.183333333333 K.
"""
from dataclasses import dataclass,asdict,replace
from functools import lru_cache
import numpy as np
from scipy.optimize import brentq
from scipy.integrate import solve_ivp
CUNIT=.45359237/.028316846592
TEMP_OFFSET=(460-459.67)/1.8
STATE_NAMES=['C_A','C_B','C_C','C_M','T','T_t']
MV_NAMES=['F_A0','m_dot_w','T_a1'];CV_NAMES=['C_C','T','T_t']
XS=np.array([1.,40.,2.,4.,10.,10.]);YS=np.array([.2,10.,10.])
U0=np.array([80*.45359237,1000*.45359237,(60-32)/1.8+273.15])
US=np.array([.2*U0[0],.5*U0[1],10.]);DT=.015
CONVERSION=np.array([CUNIT]*4+[1/1.8]*2)
QFIX_IMPERIAL=np.array([5.616e-8]*3+[2.4246e-13,.0346356,.0066123])
QFIX=QFIX_IMPERIAL*CONVERSION**2
RBASE=np.diag((np.array([1.385,1.062])/1.8)**2)
P0=np.diag(1e-6*CONVERSION**2)
QMIN=np.maximum(QFIX*1e-4,1e-12)
QMAX=np.array([.02,.2,.02,.01,4.,4.])
@dataclass(frozen=True)
class Parameters:
 cpA:float=35*4.1868
 cpB:float=18*4.1868
 cpC:float=46*4.1868
 cpM:float=19.5*4.1868
 rhoA:float=.923*CUNIT
 rhoB:float=3.45*CUNIT
 rhoM:float=1.54*CUNIT
 E:float=32400*2.326
 R:float=1.987*4.1868
 k0:float=16.96e12
 dH:float=-36000*2.326
 V:float=500/7.484*.028316846592
 Vt:float=38.85*.028316846592
 UA:float=16000*1.05505585262*1.8
 FB:float=1000*.45359237
 FM:float=100*.45359237
 T0:float=(75-32)/1.8+273.15
 arrhenius_offset:float=TEMP_OFFSET

def feed(u,p):
 v=u[0]/p.rhoA+p.FB/p.rhoB+p.FM/p.rhoM
 return v,np.array([u[0],p.FB,0.,p.FM])/v

def rhs(t,x,u,p=Parameters()):
 x=np.asarray(x);FA,mw,Ta=u;v,c0=feed(u,p)
 r=p.k0*np.exp(-p.E/(p.R*(x[...,4]+p.arrhenius_offset)))*x[...,0]
 dc=v/p.V*(c0-x[...,:4])+r[...,None]*np.array([-1.,-1.,1.,0.])
 duty=mw*p.cpB*(Ta-x[...,4])*(-np.expm1(-p.UA/(mw*p.cpB)))
 cap=p.V*(x[...,:4]@np.array([p.cpA,p.cpB,p.cpC,p.cpM]))
 feedcp=FA*p.cpA+p.FB*p.cpB+p.FM*p.cpM
 dT=(duty-feedcp*(x[...,4]-p.T0)-p.dH*r*p.V)/cap
 dTt=(mw*p.cpB*(Ta-x[...,5])-duty)/(p.rhoB*p.Vt*p.cpB)
 return np.concatenate([dc,dT[...,None],dTt[...,None]],axis=-1)

def step(x,u,p=Parameters(),method='rk4',substeps=2,dt=DT):
 if method=='euler':return x+dt*rhs(0,x,u,p)
 h=dt/substeps;x=np.array(x,copy=True)
 for _ in range(substeps):
  a=rhs(0,x,u,p);b=rhs(0,x+h*a/2,u,p);c=rhs(0,x+h*b/2,u,p);d=rhs(0,x+h*c,u,p)
  x=x+h*(a+2*b+2*c+d)/6
 return x

def mass_ss(T,u,p):
 v,c0=feed(u,p);D=v/p.V;k=p.k0*np.exp(-p.E/(p.R*(T+p.arrhenius_offset)))
 ca=D*c0[0]/(D+k);cc=k*ca/D
 return np.array([ca,c0[1]-cc,cc,c0[3],T,u[2]+(T-u[2])*(-np.expm1(-p.UA/(u[1]*p.cpB)))])
def heat_residual(T,u,p):return rhs(0,mass_ss(T,u,p),u,p)[4]
def jacobian(x,u,p):
 A=np.empty((6,6));B=np.empty((6,3))
 for j in range(6):
  h=1e-5*max(abs(x[j]),XS[j]);d=np.eye(6)[j]*h;A[:,j]=(rhs(0,x+d,u,p)-rhs(0,x-d,u,p))/(2*h)
 for j in range(3):
  h=1e-5*max(abs(u[j]),US[j]);d=np.eye(3)[j]*h;B[:,j]=(rhs(0,x,u+d,p)-rhs(0,x,u-d,p))/(2*h)
 return A,B,np.eye(6)[[2,4,5]]
def equilibria(u,p=Parameters()):
 grid=np.linspace(260,430,1701);f=np.array([heat_residual(t,u,p) for t in grid]);out=[]
 roots=[brentq(heat_residual,grid[i],grid[i+1],args=(u,p),xtol=1e-11) for i in np.flatnonzero(f[:-1]*f[1:]<0)]
 roots+=list(grid[np.abs(f)<1e-10]);unique=[]
 for t in sorted(roots):
  if unique and abs(t-unique[-1])<1e-7:continue
  unique.append(t);x=mass_ss(t,u,p);A,_,_=jacobian(x,u,p);e=np.linalg.eigvals(A)
  out.append(dict(x=x,stable=bool(max(e.real)<0),eig=e))
 return out
@lru_cache(maxsize=256)
def _steady(ut,p,hint):
 a=equilibria(np.array(ut),p)
 if not a:raise ValueError('No equilibrium in scanned interval')
 return min(a,key=lambda d:abs(d['x'][4]-hint))
def steady(u=U0,p=Parameters(),hint=332.3):return _steady(tuple(u),p,float(hint))
def gain(u,p,x,rel=.01,physical_temperature=False):
 G=np.empty((3,3));details=[]
 for j in range(3):
  h=rel*(10 if physical_temperature and j==2 else abs(u[j]));d=np.eye(3)[j]*h
  xp=steady(u+d,p,x[4]);xm=steady(u-d,p,x[4]);G[:,j]=(xp['x'][[2,4,5]]-xm['x'][[2,4,5]])/(2*h)
  details.append(dict(mv=MV_NAMES[j],delta=h,xplus=xp['x'],xminus=xm['x'],plus_stable=xp['stable'],minus_stable=xm['stable'],plus_jump_K=float(xp['x'][4]-x[4]),minus_jump_K=float(xm['x'][4]-x[4])))
 return G,details
def simulate(x,u,p,tend=4.,n=2001):
 sol=solve_ivp(lambda t,z:rhs(t,z,u,p),(0,tend),x,method='DOP853',rtol=2e-10,atol=1e-11,t_eval=np.linspace(0,tend,n),max_step=.015)
 if not sol.success:raise RuntimeError(sol.message)
 return sol.t,sol.y.T

def startup():return np.array([0.,3.45*CUNIT,0.,0.,(75-32)/1.8+273.15,(60-32)/1.8+273.15])

