"""Six-state PG. Literal SI transform of archived modeloCT.m, not table fitting.
Units: kmol/m3, K, kmol/h, kJ, hours. Tt does not feed back into reactor heat duty.
"""
from dataclasses import dataclass, asdict
import numpy as np
from scipy.optimize import brentq
try:
    from numba import njit
except ImportError:
    def njit(*args, **kwargs):
        if args and callable(args[0]): return args[0]
        return lambda f: f
CUNIT=.45359237/.028316846592
DT=.015
SCALE=np.array([1.,40.,2.,4.,10.,10.])
U0=np.array([80*.45359237,1000*.45359237,100*.45359237,1000*.45359237,(75-32)/1.8+273.15,(60-32)/1.8+273.15])
UMIN=22.7; UMAX=1366.2; T_LIMIT=344.; T_HISTORICAL=355.4
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
    heat:float=36000*2.326
    V:float=500/7.484*.028316846592
    Vt:float=38.85*.028316846592
    UA:float=16000*1.05505585262*1.8
    offset:float=(460-459.67)/1.8
    def array(self): return np.array(list(asdict(self).values()),dtype=float)
P=Parameters().array()
TABLE=Parameters(146.5,75.4,192.6,81.6,14.8,55.3,24.7,75362.4,8.314,16.96e12,91556.9,1.89,1.1,30385.6,0.).array()
TABLE_U=np.array([36.3,453.6,45.4,453.6,297.,289.])
@njit(cache=True)
def flow(u,p=P): return u[0]/p[4]+u[1]/p[5]+u[2]/p[6]
@njit(cache=True)
def rhs(x,u,p=P):
    v=flow(u,p);D=v/p[11];k=p[9]*np.exp(-p[7]/p[8]/(x[4]+p[14]));r=k*x[0]
    c=u[3]*p[1]*(-np.expm1(-p[13]/(u[3]*p[1])))
    q=c*(u[5]-x[4]);cap=p[11]*np.dot(x[:4],p[:4]);feedcp=u[0]*p[0]+u[1]*p[1]+u[2]*p[3]
    return np.array([(u[0]-v*x[0])/p[11]-r,(u[1]-v*x[1])/p[11]-r,r-D*x[2],(u[2]-v*x[3])/p[11],(q-feedcp*(x[4]-u[4])+p[10]*r*p[11])/cap,(u[3]*p[1]*(u[5]-x[5])-q)/(p[5]*p[12]*p[1])])
@njit(cache=True)
def step(x,u,p=P,dt=DT,n=3):
    z=x.copy();h=dt/n
    for _ in range(n):
        a=rhs(z,u,p);b=rhs(z+h*a/2,u,p);c=rhs(z+h*b/2,u,p);d=rhs(z+h*c,u,p)
        z+=h*(a+2*b+2*c+d)/6
    return z
@njit(cache=True)
def physical(x): return np.all(np.isfinite(x)) and np.min(x[:4])>=-1e-8 and 200<x[4]<500 and 200<x[5]<500
@njit(cache=True)
def jacobian(x,u,p=P):
    """Analytic Jacobian of all six balances, including changing heat capacity."""
    J=np.zeros((6,6));D=flow(u,p)/p[11];k=p[9]*np.exp(-p[7]/p[8]/(x[4]+p[14]));rt=k*x[0]*p[7]/p[8]/(x[4]+p[14])**2
    for j in range(4):J[j,j]=-D
    J[0,0]-=k;J[1,0]=-k;J[2,0]=k
    J[0,4]=-rt;J[1,4]=-rt;J[2,4]=rt
    cap=p[11]*np.dot(x[:4],p[:4]);dT=rhs(x,u,p)[4]
    c=u[3]*p[1]*(-np.expm1(-p[13]/(u[3]*p[1])))
    feedcp=u[0]*p[0]+u[1]*p[1]+u[2]*p[3]
    for j in range(4):J[4,j]=-dT*p[11]*p[j]/cap
    J[4,0]+=p[10]*p[11]*k/cap
    J[4,4]=(-c-feedcp+p[10]*p[11]*rt)/cap
    J[5,4]=c/(p[5]*p[12]*p[1]);J[5,5]=-u[3]/(p[5]*p[12])
    return J
@njit(cache=True)
def spectral_abscissa(x,u,p=P):
    J=jacobian(x,u,p)
    a=J[0,0];b=J[0,4];c=J[4,0]+J[4,1]-J[4,2];d=J[4,4]
    disc=(a-d)**2+4*b*c
    ar=(a+d+np.sqrt(max(0.,disc)))/2
    return max(ar,J[3,3],J[5,5])
@njit(cache=True)
def mass_ss(T,u,p=P):
    v=flow(u,p);k=p[9]*np.exp(-p[7]/p[8]/(T+p[14]));ca=u[0]/(v+p[11]*k);cc=p[11]*k*ca/v
    return np.array([ca,u[1]/v-cc,cc,u[2]/v,T,u[5]+(T-u[5])*(-np.expm1(-p[13]/(u[3]*p[1])))])
@njit(cache=True)
def heat(T,u,p=P): return rhs(mass_ss(T,u,p),u,p)[4]
def equilibria(u=U0,p=P,bounds=(250.,430.),spacing=.25):
    grid=np.arange(bounds[0],bounds[1]+spacing/2,spacing);v=np.array([heat(t,u,p) for t in grid]);rr=[]
    for i in range(len(grid)-1):
        if v[i]*v[i+1]<0:rr.append(brentq(lambda t:heat(t,u,p),grid[i],grid[i+1],xtol=1e-11))
        if abs(v[i])<1e-10:rr.append(grid[i])
    return [mass_ss(t,u,p) for t in sorted(set(round(r,9) for r in rr))]
BASE=equilibria()[0]
def require_valid(x,u):
    if not physical(x) or not np.all(np.isfinite(u)) or u[3]<=0:raise ValueError('Outside physical/numerical domain')
