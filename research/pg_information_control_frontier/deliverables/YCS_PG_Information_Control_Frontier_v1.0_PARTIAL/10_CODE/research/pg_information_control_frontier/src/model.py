"""PG kernels. M0 is the recovered MATLAB model; alternatives are hypotheses.
Units: h, kmol, m3, K, kJ. No clipping of the simulated plant.
"""
import numpy as np
from numba import njit
from scipy.integrate import solve_ivp
from scipy.optimize import root
CP=np.array([35.,18.,46.,19.5])*4.1868
RHO=np.array([.923,3.45,1.54])*.45359237/.028316846592
V=500/7.484*.028316846592; VT=38.85*.028316846592
UA=16000*1.05505585262*1.8
U0=np.array([80.,1000.,100.,1000.])*.45359237
U0=np.r_[U0,(75-32)/1.8+273.15,(60-32)/1.8+273.15]
DT=.015; TLIMIT=(160-32)/1.8+273.15
TREF=332.333618020
SLOPE=np.array([.0015,.0002,.0025,.001])
CURVE=np.array([.00001,.000002,.000016,-.000003])
NU=np.array([-1.,-1.,1.,0.])
SCALE=np.array([.2,1.,.4,.5,1.,1.])
VARIANTS=['M0_historical','M1H_Kirchhoff_hypothesis','M1J_mixed_jacket_hypothesis',
          'M2L_linear_cp_hypothesis','M2Q_quadratic_cp_hypothesis']

@njit(cache=True)
def props(t,p,variant):
    a=CP*np.exp(p[2])
    b=a*SLOPE if variant>=3 else np.zeros(4)
    c=a*CURVE if variant>=4 else np.zeros(4)
    d=t-TREF
    cp=a+b*d+c*d*d
    hi=a*d+b*d*d/2+c*d*d*d/3
    dh=-83736.
    if variant>=1: dh+=np.dot(NU,hi)
    return cp,hi,dh

@njit(cache=True)
def energy_terms(x,u,p,variant):
    cp,hi,dh=props(x[4],p,variant)
    _,hfeed,_=props(u[4],p,variant)
    cf=CP[1]*np.exp(p[2])
    if variant>=2:
        g=U0[3]*CP[1]*np.expm1(UA/(U0[3]*CP[1]))*np.exp(p[1])
        q=g*(x[5]-x[4])
    else:
        q=u[3]*cf*(u[5]-x[4])*(-np.expm1(-UA*np.exp(p[1])/(u[3]*cf)))
    sensible=u[0]*(hfeed[0]-hi[0])+u[1]*(hfeed[1]-hi[1])+u[2]*(hfeed[3]-hi[3])
    cap=V*np.dot(x[:4],cp)
    return q,sensible,cap,dh,cf

@njit(cache=True)
def rhs(x,u,p,variant=0):
    flow=u[0]/RHO[0]+u[1]/RHO[1]+u[2]/RHO[2]
    rate=16.96e12*np.exp(-75362.4/((1.987*4.1868)*(x[4]+.1833333333333333))+p[0])*x[0]
    q,sens,cap,dh,cf=energy_terms(x,u,p,variant)
    return np.array([(u[0]-flow*x[0])/V-rate,(u[1]-flow*x[1])/V-rate,
        rate-flow*x[2]/V,(u[2]-flow*x[3])/V,(q+sens-dh*rate*V)/cap,
        (u[3]*cf*(u[5]-x[5])-q)/(RHO[1]*VT*cf)])

@njit(cache=True)
def step(x,u,p,variant=0,nsub=4,dt=DT):
    z=x.copy();h=dt/nsub
    for _ in range(nsub):
        a=rhs(z,u,p,variant);b=rhs(z+h*a/2,u,p,variant)
        c=rhs(z+h*b/2,u,p,variant);d=rhs(z+h*c,u,p,variant)
        z+=h*(a+2*b+2*c+d)/6
    return z

def independent(x,u,p,variant=0,dt=DT):
    s=solve_ivp(lambda t,z:rhs(z,u,p,variant),(0,dt),x,method='DOP853',
                rtol=2e-11,atol=1e-12,max_step=dt/4)
    if not s.success: raise RuntimeError(s.message)
    return s.y[:,-1]

def equilibrium(p=None,variant=0,u=None):
    p=np.zeros(3) if p is None else p;u=U0 if u is None else u
    guess=np.array([.607024732,33.989102107,2.295764605,3.628486671,332.33361802,314.39758533])
    s=root(lambda x:rhs(x,u,p,variant),guess,tol=1e-11)
    if np.max(np.abs(rhs(s.x,u,p,variant)))>1e-7 or min(s.x[:4])<0:
        raise RuntimeError('equilibrium failed')
    return s.x

@njit(cache=True)
def dilution(u): return (u[0]/RHO[0]+u[1]/RHO[1]+u[2]/RHO[2])/V

@njit(cache=True)
def inventory(x): return np.array([x[0]+x[2],x[1]+x[2],x[3]])

@njit(cache=True)
def inventory_step(s,u):
    d=dilution(u);ss=np.array([u[0],u[1],u[2]])/(V*d)
    return ss+(s-ss)*np.exp(-d*DT)

@njit(cache=True)
def reconstruct(z,s):return np.array([s[0]-z[0],s[1]-z[0],z[0],s[2],z[1],z[2]])

@njit(cache=True)
def twin(x,delta):
    out=x.copy();out[2]+=delta;out[1]-=CP[2]/CP[1]*delta
    return out

def jacobian(fun,x,eps=1e-5):
    return np.column_stack([(fun(x+np.eye(len(x))[j]*eps*SCALE[j])
                    -fun(x-np.eye(len(x))[j]*eps*SCALE[j]))/(2*eps*SCALE[j])
                    for j in range(len(x))])

@njit(cache=True)
def rollout(x,inputs,p,variant=0,nsub=4):
    out=np.empty((len(inputs)+1,6));out[0]=x
    for k in range(len(inputs)):out[k+1]=step(out[k],inputs[k],p,variant,nsub)
    return out
