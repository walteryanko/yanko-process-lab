"""CSTR reconstructed from Brandao (2019), equations 33--55, Table 1 P.O.2.
Units: kmol, m^3, K, kJ, h. m_dot_w is MOLAR coolant flow, not kg/h.
The published heat duty depends on T, not Tt. This is preserved deliberately.
"""
from dataclasses import dataclass, asdict, replace
import numpy as np
from scipy.optimize import brentq
from scipy.integrate import solve_ivp

STATE_NAMES = ['C_A','C_B','C_C','C_M','T','T_t']
MV_NAMES = ['F_A0','m_dot_w','T_a1']
CV_NAMES = ['C_C','T','T_t']
U0 = np.array([36.3,453.6,289.0])
XS = np.array([1.,40.,2.,4.,10.,10.])
# Design spans, explicitly chosen for screening, not measured actuator limits.
US = np.array([.20*36.3,.50*453.6,10.])
YS = np.array([.20,10.,10.])

@dataclass(frozen=True)
class Parameters:
    cpA: float=146.5
    cpB: float=75.4
    cpC: float=192.6
    cpM: float=81.6
    rhoA: float=14.8
    rhoB: float=55.3
    rhoM: float=24.7
    E: float=75362.40
    R: float=8.314
    k0: float=16.96e12
    dH: float=-91556.90
    V: float=1.89
    Vt: float=1.1
    UA: float=30385.60
    FB: float=453.6
    FM: float=45.4
    T0: float=297.

def feed(u,p):
    FA,mw,Ta=u
    v=FA/p.rhoA+p.FB/p.rhoB+p.FM/p.rhoM
    return v,np.array([FA,p.FB,0.,p.FM])/v

def rhs(t,x,u,p=Parameters()):
    FA,mw,Ta=u
    v,c0=feed(u,p)
    r=p.k0*np.exp(-p.E/(p.R*x[4]))*x[0]
    dc=v/p.V*(c0-x[:4])+np.array([-r,-r,r,0.])
    eff=-np.expm1(-p.UA/(mw*p.cpB))
    duty=mw*p.cpB*(Ta-x[4])*eff
    cp=np.array([p.cpA,p.cpB,p.cpC,p.cpM])
    capacity=p.V*np.dot(x[:4],cp)
    feed_capacity=FA*p.cpA+p.FB*p.cpB+p.FM*p.cpM
    dT=(duty-feed_capacity*(x[4]-p.T0)-p.dH*r*p.V)/capacity
    dTt=(mw*p.cpB*(Ta-x[5])-duty)/(p.rhoB*p.Vt*p.cpB)
    return np.r_[dc,dT,dTt]

def mass_ss(T,u,p):
    v,c0=feed(u,p); D=v/p.V
    k=p.k0*np.exp(-p.E/(p.R*T))
    ca=D*c0[0]/(D+k); cc=k*ca/D
    cb=c0[1]-cc; cm=c0[3]
    a=np.exp(-p.UA/(u[1]*p.cpB))
    tt=u[2]+(T-u[2])*(1-a)
    return np.array([ca,cb,cc,cm,T,tt])

def heat_residual(T,u,p):
    return rhs(0,mass_ss(T,u,p),u,p)[4]

def jacobian(x,u,p):
    A=np.empty((6,6));B=np.empty((6,3))
    for j in range(6):
        h=1e-5*max(abs(x[j]),XS[j]); dx=np.eye(6)[j]*h
        A[:,j]=(rhs(0,x+dx,u,p)-rhs(0,x-dx,u,p))/(2*h)
    for j in range(3):
        h=1e-5*max(abs(u[j]),US[j]); du=np.eye(3)[j]*h
        B[:,j]=(rhs(0,x,u+du,p)-rhs(0,x,u-du,p))/(2*h)
    C=np.eye(6)[[2,4,5]]
    return A,B,C

def equilibria(u,p=Parameters()):
    grid=np.linspace(260,430,1701)
    f=np.array([heat_residual(T,u,p) for T in grid])
    roots=[]
    for i in range(len(grid)-1):
        if f[i]*f[i+1]<0:
            T=brentq(heat_residual,grid[i],grid[i+1],args=(u,p),xtol=1e-11)
            x=mass_ss(T,u,p); A,_,_=jacobian(x,u,p)
            eig=np.linalg.eigvals(A)
            roots.append(dict(x=x,stable=bool(max(eig.real)<0),eig=eig))
    return roots

def steady(u,p=Parameters(),hint=332.3):
    roots=equilibria(u,p)
    if not roots: raise ValueError('No equilibrium in 260--430 K')
    return min(roots,key=lambda z:abs(z['x'][4]-hint))

def gain(u,p,x,rel=.01,physical_temperature=False):
    G=np.empty((3,3)); details=[]
    for j in range(3):
        h=rel*(10. if (physical_temperature and j==2) else abs(u[j]))
        du=np.eye(3)[j]*h
        xp=steady(u+du,p,x[4]);xm=steady(u-du,p,x[4])
        G[:,j]=(xp['x'][[2,4,5]]-xm['x'][[2,4,5]])/(2*h)
        details.append(dict(mv=MV_NAMES[j],delta=h,xplus=xp['x'],xminus=xm['x'],
            plus_stable=xp['stable'],minus_stable=xm['stable'],
            plus_jump_K=float(xp['x'][4]-x[4]),minus_jump_K=float(xm['x'][4]-x[4])))
    return G,details

def simulate(x,u,p,tend=4.,n=2001):
    tt=np.linspace(0,tend,n)
    sol=solve_ivp(lambda t,z:rhs(t,z,u,p),(0,tend),x,method='DOP853',
        rtol=2e-10,atol=1e-11,t_eval=tt,max_step=.015)
    if not sol.success: raise RuntimeError(sol.message)
    return sol.t,sol.y.T
