"""Audited wrapper of the ProcessLab ethylbenzene first-reactor reconstruction.
Time h, concentrations kmol/m3, temperature Celsius, input Q kcal/h (positive removal).
Source commit 16aaafb63572d62e0e3341e26d8317b0651bdde0, never PG kinetics.
"""
import numpy as np
from scipy.integrate import solve_ivp
from vendor.model import (V,NU,MW,K0,E,RGAS,DH,RHO,CP,RHO_REACTOR,CP_REACTOR,
    CAPACITY,REC,F0,TFEED,BASE,U0,XS,DT,Q0,TNOM,T_LIMIT,STATE_NAMES,calibration_audit)
SCALES=XS.copy()
Q_PUBLISHED=np.array([1e-7,2e-6,2e-6,1e-7,.0036])
MOIETIES=np.array([[0,1,1,1],[1,0,1,2]])
H=np.array([[0.,0.,0.,0.,1.]])
SOURCE_COMMIT='16aaafb63572d62e0e3341e26d8317b0651bdde0'

def valid(x):
    x=np.asarray(x)
    return np.all(np.isfinite(x),axis=-1)&np.all(x[...,:4]>=0,axis=-1)&(x[...,4]>0)&(x[...,4]<220)

def rates(x,theta=None):
    x=np.asarray(x);t=np.zeros(5) if theta is None else np.asarray(theta)
    k=K0*3600*np.exp(t[...,:3]-E/(RGAS*(x[...,4,None]+273.15)))
    return k*np.stack([x[...,0]*x[...,1],x[...,0]*x[...,2],x[...,1]*x[...,3]],axis=-1)

def rhs(x,u,theta=None):
    x=np.asarray(x);u=np.asarray(u);t=np.zeros(5) if theta is None else np.asarray(theta)
    f=u[...,:3];total=f.sum(axis=-1);rr=rates(x,t)
    inflow=f[...,0,None]*RHO[0]*np.exp(t[...,4,None])*np.array([1.,0,0,0])+f[...,1,None]*RHO[1]*np.array([0.,1,0,0])+f[...,2,None]*REC
    dc=(inflow-total[...,None]*x[...,:4])/V+rr@NU.T
    heat=np.sum(f*RHO*CP*u[...,4:7],axis=-1)-total*RHO_REACTOR*CP_REACTOR*x[...,4]-V*(rr@DH)*np.exp(t[...,3])-u[...,3]
    return np.concatenate([dc,(heat/CAPACITY)[...,None]],axis=-1)

def step(x,u,dt=DT,max_step=DT/8,theta=None,method='rk4'):
    a=np.array(x,dtype=float,copy=True)
    if not np.all(valid(a)):raise ValueError('Nonphysical input state')
    if method=='dop853':
        if a.ndim!=1:raise ValueError('DOP853 truth integrator accepts one state')
        sol=solve_ivp(lambda _,xx:rhs(xx,u,theta),(0,dt),a,method='DOP853',rtol=1e-10,atol=1e-12)
        if not sol.success:raise ArithmeticError(sol.message)
        a=sol.y[:,-1]
    elif method=='rk4':
        n=max(1,int(np.ceil(dt/max_step)));h=dt/n
        for _ in range(n):
            k1=rhs(a,u,theta);k2=rhs(a+h*k1/2,u,theta)
            k3=rhs(a+h*k2/2,u,theta);k4=rhs(a+h*k3,u,theta)
            a+=h*(k1+2*k2+2*k3+k4)/6
            if not np.all(valid(a)):raise ValueError('Integrator left physical domain')
    else:raise ValueError('Unknown integrator')
    if not np.all(valid(a)):raise ValueError('Integrator output outside physical domain')
    return a

def fraction(x):
    a=np.asarray(x);return a[...,2]/a[...,:4].sum(axis=-1)

def metadata():
    a=calibration_audit();a.update(source_commit=SOURCE_COMMIT,states=STATE_NAMES,
       measured_states=['T_C'],input_units=['m3/h','m3/h','m3/h','kcal/h','C','C','C'],
       concentrations_unit='kmol/m3',time_unit='h',sample_seconds=90,
       reference_integrator='DOP853 rtol=1e-10 atol=1e-12',filter_integrator='RK4 eight substeps',
       physical_scales=SCALES,process_covariance_diagonal=Q_PUBLISHED,
       moiety_matrix=MOIETIES,stoichiometric_residual=MOIETIES@NU,
       limitations='Reduced printed-ODE reconstruction; inferred effective Q, not Aspen thermodynamics or plant validation.')
    return a
