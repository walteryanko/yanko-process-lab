"""Exact ProcessLab TABLED equations, kmol, m3, h, K, kJ.

Source commit f4444d4c238291b8633743930249ee387ad94541, model.ts.
No historical/calibrated coefficients are mixed into this variant.
"""
from dataclasses import dataclass, asdict
import numpy as np
from scipy.optimize import brentq

CP = np.array([146.5, 75.4, 192.6, 81.6])
RHO = np.array([14.8, 55.3, 24.7])
U0 = np.array([36.3, 453.6, 45.4, 453.6, 297., 289.])
DT = .015
SCALES = np.array([1., 40., 3., 4., 10., 10.])
NAMES = ['CA', 'CB', 'CC', 'CM', 'T', 'Tt']
UNITS = ['kmol/m³'] * 4 + ['K'] * 2
Q_PUBLISHED = np.array([5.616e-8,5.616e-5,5.616e-8,2.4246e-13,.0346356,.00666123])
H = np.eye(6)[4:6]
MIN_MW, MAX_MW, STUDY_T, STOP_T = 22.7, 1366.2, 344., 355.4

@dataclass(frozen=True)
class Parameters:
    E: float = 75362.4
    R: float = 8.314
    k0: float = 16.96e12
    heat: float = 91556.9  # positive -DeltaH, kJ/kmol
    V: float = 1.89
    Vt: float = 1.1
    UA: float = 30385.6  # kJ/(h K)

P = Parameters()

def valid(x):
    x = np.asarray(x)
    return (np.all(np.isfinite(x), axis=-1) & np.all(x[..., :4] >= 0, axis=-1)
            & np.all((x[..., 4:6] >= 150) & (x[..., 4:6] <= 600), axis=-1)
            & (np.sum(x[..., :4] * CP, axis=-1) > 0))

def check(x):
    if not np.all(valid(x)):
        raise ValueError('State outside physical domain; no silent clipping.')

def flow(u):
    return u[...,0]/RHO[0] + u[...,1]/RHO[1] + u[...,2]/RHO[2]

def rhs(x, u=U0, p=P, theta=None):
    """theta: log multipliers [UA,k0,FA,heat]; never read truth in filters."""
    x=np.asarray(x, float); u=np.asarray(u,float)
    if np.any(u[...,3]<=0) or not np.all(np.isfinite(u)):
        raise ValueError('Invalid input')
    if theta is None:
        ua,kin,fa,heat = p.UA,1.,u[...,0],p.heat
    else:
        m=np.exp(np.asarray(theta)); ua=p.UA*m[...,0];kin=m[...,1]
        fa=u[...,0]*m[...,2];heat=p.heat*m[...,3]
    v=fa/RHO[0]+u[...,1]/RHO[1]+u[...,2]/RHO[2]
    r=p.k0*kin*np.exp(-p.E/(p.R*x[...,4]))*x[...,0]
    q=u[...,3]*CP[1]*(u[...,5]-x[...,4])*(-np.expm1(-ua/(u[...,3]*CP[1])))
    cap=p.V*np.sum(x[...,:4]*CP,axis=-1)
    if np.any(cap<=0) or np.any(x[...,4]<=0):
        raise ValueError('Invalid heat capacity or temperature')
    sens=(fa*CP[0]+u[...,1]*CP[1]+u[...,2]*CP[3])*(x[...,4]-u[...,4])
    out=np.empty_like(x)
    out[...,0]=(fa-v*x[...,0])/p.V-r
    out[...,1]=(u[...,1]-v*x[...,1])/p.V-r
    out[...,2]=r-v*x[...,2]/p.V
    out[...,3]=(u[...,2]-v*x[...,3])/p.V
    out[...,4]=(q-sens+heat*r*p.V)/cap
    # Deliberately asymmetric: Tt does NOT feed back into reactor heat duty.
    out[...,5]=(u[...,3]*CP[1]*(u[...,5]-x[...,5])-q)/(RHO[1]*p.Vt*CP[1])
    return out

def step(x,u=U0,dt=DT,max_step=.001,p=P,theta=None,method='rk4'):
    x=np.array(x,float,copy=True);u=np.asarray(u,float);check(x)
    if dt<0 or max_step<=0: raise ValueError('Invalid time step')
    if method=='euler':
        out=x+dt*rhs(x,u,p,theta);check(out);return out
    if method!='rk4': raise ValueError('Unknown integrator')
    n=max(1,int(np.ceil(dt/max_step)));h=dt/n
    for _ in range(n):
        a=rhs(x,u,p,theta);b=rhs(x+h*a/2,u,p,theta)
        c=rhs(x+h*b/2,u,p,theta);d=rhs(x+h*c,u,p,theta)
        x+=h*(a+2*b+2*c+d)/6
        check(x)
    return x

def equilibria(u=U0,p=P):
    u=np.asarray(u,float);v=flow(u)
    def state(t):
        k=p.k0*np.exp(-p.E/(p.R*t));ca=u[0]/(v+p.V*k);cc=p.V*k*ca/v
        q=u[3]*CP[1]*(u[5]-t)*(-np.expm1(-p.UA/(u[3]*CP[1])))
        return np.array([ca,u[1]/v-cc,cc,u[2]/v,t,u[5]-q/(u[3]*CP[1])])
    grid=np.arange(250,400.25,.25);f=lambda t:rhs(state(t),u,p)[4];out=[]
    for a,b in zip(grid[:-1],grid[1:]):
        if f(a)*f(b)<=0:
            t=brentq(f,a,b,xtol=1e-12)
            if not out or abs(t-out[-1][4])>1e-7: out.append(state(t))
    return out

BASE=equilibria()[-1]
# Exact thermally invisible composition direction (not stoichiometric conversion).
NULL_CC=np.array([0.,-CP[2]/CP[1],1.,0.,0.,0.])
NULL_CM=np.array([0.,-CP[3]/CP[1],0.,1.,0.,0.])

def metadata():
    return dict(variant='ProcessLab main / literal TABLED',
                commit='f4444d4c238291b8633743930249ee387ad94541',
                parameters=asdict(P),cp=CP.tolist(),rho=RHO.tolist(),
                input=U0.tolist(),equilibria=[x.tolist() for x in equilibria()],
                dt_h=DT,dt_s=DT*3600,scales=SCALES.tolist(),
                residual=rhs(BASE).tolist(),historical_equilibrium_K=332.3336,
                historical_heat_kJ_per_kmol=36000*2.326,
                historical_source_commit='88c40e65204fa6aa5bed02cc64fb15be79a53bb1')
