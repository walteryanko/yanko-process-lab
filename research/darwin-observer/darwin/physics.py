"""Six-state PG model, literal ProcessLab f4444d4. Hours, kmol, m³, K, kJ.

No hidden truth mechanisms are part of Model. The historical thermal asymmetry
is intentional: q depends on T and inlet Ta, not on the dynamic state Tt.
"""
from dataclasses import dataclass, field
import numpy as np
from scipy.optimize import brentq
try:
    from numba import njit
except ImportError:
    def njit(*a, **kw):
        return a[0] if a and callable(a[0]) else lambda f: f

CP=np.array([146.5,75.4,192.6,81.6]); RHO=np.array([14.8,55.3,24.7])
U0=np.array([36.3,453.6,45.4,453.6,297.,289.])
E=75362.4; RG=8.314; K0=16.96e12; HEAT=91556.9
V=1.89; VT=1.1; UA=30385.6; DT=.015; NP=15
STATE_NAMES=['CA','CB','CC','CM','T','Tt']
CUNIT=.45359237/.028316846592
LEGACY_CP=np.array([35.,18.,46.,19.5])*4.1868
LEGACY_RHO=np.array([.923,3.45,1.54])*CUNIT
LEGACY_V=500/7.484*.028316846592
LEGACY_VT=38.85*.028316846592
LEGACY_UA=16000*1.05505585262*1.8
LEGACY_U0=np.array([80*.45359237,1000*.45359237,100*.45359237,1000*.45359237,(75-32)/1.8+273.15,(60-32)/1.8+273.15])
# p: UA exp(intercept + dictionary); kinetics exp(a+b*10*(340/T-1));
# heat exp; feed-A exp; sensor offsets/drift; heat capacity exp; feed-T offset.
PARAM_NAMES=['log_UA','UA_linear','UA_log','UA_quadratic','UA_reciprocal',
 'UA_sqrt','log_k','activation','log_heat','log_FA','bias_T','bias_Tt',
 'drift_Tt','log_capacity','bias_Tfeed']

@njit(cache=True)
def basis(v):
    return np.array([1.,v-1.,np.log(v),(v-1.)**2,1./v-1.,np.sqrt(v)-1.])

@njit(cache=True)
def correction(x,u,p):
    v=u[3]/453.6
    a=np.dot(p[:6],basis(v))
    b=p[6]+p[7]*10.*(340./x[4]-1.)
    return np.exp(a),np.exp(b)

@njit(cache=True)
def rhs_factors(x,u,p,ua_factor,k_factor,heat=HEAT,rg=RG,toffset=0.):
    fa=u[0]*np.exp(p[9]);fb=u[1];fm=u[2];mw=u[3]
    flow=fa/RHO[0]+fb/RHO[1]+fm/RHO[2]
    r=K0*np.exp(-E/(rg*(x[4]+toffset)))*k_factor*x[0]
    q=mw*CP[1]*(u[5]-x[4])*(-np.expm1(-UA*ua_factor/(mw*CP[1])))
    cap=V*np.dot(x[:4],CP)*np.exp(p[13])
    sens=(fa*CP[0]+fb*CP[1]+fm*CP[3])*(x[4]-u[4]-p[14])
    out=np.empty(6)
    out[0]=(fa-flow*x[0])/V-r
    out[1]=(fb-flow*x[1])/V-r
    out[2]=r-flow*x[2]/V
    out[3]=(fm-flow*x[3])/V
    out[4]=(q-sens+heat*np.exp(p[8])*r*V)/cap
    out[5]=(mw*CP[1]*(u[5]-x[5])-q)/(RHO[1]*VT*CP[1])
    return out

@njit(cache=True)
def legacy_rhs_factors(x,u,p,ua,k):
    cp=LEGACY_CP;rho=LEGACY_RHO;vol=LEGACY_V
    fa=u[0]*np.exp(p[9]);flow=fa/rho[0]+u[1]/rho[1]+u[2]/rho[2]
    r=K0*np.exp(-(32400*2.326)/((1.987*4.1868)*(x[4]+.183333333333333)))*k*x[0]
    q=u[3]*cp[1]*(u[5]-x[4])*(-np.expm1(-LEGACY_UA*ua/(u[3]*cp[1])))
    cap=vol*np.dot(x[:4],cp)*np.exp(p[13])
    sens=(fa*cp[0]+u[1]*cp[1]+u[2]*cp[3])*(x[4]-u[4]-p[14])
    return np.array([(fa-flow*x[0])/vol-r,(u[1]-flow*x[1])/vol-r,r-flow*x[2]/vol,(u[2]-flow*x[3])/vol,
        (q-sens+83736.*np.exp(p[8])*r*vol)/cap,(u[3]*cp[1]*(u[5]-x[5])-q)/(rho[1]*LEGACY_VT*cp[1])])

@njit(cache=True)
def rhs(x,u,p,variant=0):
    ua,k=correction(x,u,p)
    if variant==1: # literal legacy conversion, separate complete thermal convention
        return legacy_rhs_factors(x,u,p,ua,k)
    return rhs_factors(x,u,p,ua,k)

@njit(cache=True)
def transition(x,u,p,dt=DT,nsub=3,variant=0):
    z=x.copy();h=dt/nsub
    for j in range(nsub):
        a=rhs(z,u,p,variant);b=rhs(z+h*a/2,u,p,variant)
        c=rhs(z+h*b/2,u,p,variant);d=rhs(z+h*c,u,p,variant)
        z+=h*(a+2*b+2*c+d)/6
    return z

@njit(cache=True)
def batch_transition(xs,u,p,dt=DT,nsub=3,variant=0):
    out=np.empty_like(xs)
    for j in range(len(xs)):out[j]=transition(xs[j],u,p,dt,nsub,variant)
    return out

@njit(cache=True)
def simulate(x0,inputs,p,dt=DT,nsub=3,variant=0):
    out=np.empty((len(inputs)+1,6));out[0]=x0
    for j in range(len(inputs)):out[j+1]=transition(out[j],inputs[j],p,dt,nsub,variant)
    return out

def in_domain(x):
    a=np.asarray(x)
    return bool(np.all(np.isfinite(a)) and np.all(a[...,:4]>=0) and
                np.all((a[...,4:]>=250)&(a[...,4:]<=400)))

def equilibrium(u=U0,p=None,variant=0):
    p=np.zeros(NP) if p is None else np.asarray(p,float)
    rho=LEGACY_RHO if variant else RHO;cp=LEGACY_CP if variant else CP
    vol=LEGACY_V if variant else V;ua0=LEGACY_UA if variant else UA
    fa=u[0]*np.exp(p[9]);fl=fa/rho[0]+u[1]/rho[1]+u[2]/rho[2]
    def xof(t):
        rg,toff=(1.987*4.1868,.1833333333333333) if variant else (RG,0.)
        ua,km=correction(np.array([1.,30.,2.,3.,t,310.]),u,p)
        k=K0*np.exp(-E/(rg*(t+toff)))*km;ca=fa/(fl+vol*k);cc=vol*k*ca/fl
        q=u[3]*cp[1]*(u[5]-t)*(-np.expm1(-ua0*ua/(u[3]*cp[1])))
        return np.array([ca,u[1]/fl-cc,cc,u[2]/fl,t,u[5]-q/(u[3]*cp[1])])
    roots=[]
    for t in np.arange(270.,381.,.5):
        if rhs(xof(t),u,p,variant)[4]*rhs(xof(t+.5),u,p,variant)[4]<0:
            roots.append(brentq(lambda z:rhs(xof(z),u,p,variant)[4],t,t+.5))
    if not roots:raise ValueError('No equilibrium in [270,381.5] K')
    return xof(max(roots))

BASE=equilibrium()

@dataclass
class Model:
    params: np.ndarray=field(default_factory=lambda:np.zeros(NP))
    name: str='nominal'
    variant: int=0
    envelope: tuple=(150.,1250.,295.,350.)
    def step(self,x,u,dt=DT):
        z=transition(np.asarray(x,float),np.asarray(u,float),self.params,dt,3,self.variant)
        if not in_domain(z):raise FloatingPointError('Physical domain exceeded')
        return z
    def measurement(self,x,t=0.):
        return np.asarray(x)[...,4:6]+self.params[10:12]+np.array([0.,self.params[12]*t])
    def supports(self,x,u):
        lo,hi,tlo,thi=self.envelope
        return lo<=u[3]<=hi and tlo<=x[4]<=thi
    def as_dict(self):
        return dict(name=self.name,params=self.params.tolist(),variant=self.variant,envelope=list(self.envelope))
    @classmethod
    def from_dict(cls,d):
        return cls(np.array(d['params']),d['name'],d.get('variant',0),tuple(d.get('envelope',(150,1250,295,350))))
