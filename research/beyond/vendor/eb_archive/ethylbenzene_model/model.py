"""TFC R1 reconstruction. Time h; concentration kmol/m3; T degC; Q kcal/h.

Literal TFC constant-property energy balance, not a validated safety model.
Kinetic pre-exponent units corrected against original Luyben (2011): per s.
Q0 below is explicitly a reconstruction calibration, replace if recovered.
"""
import numpy as np
import casadi as ca
from scipy.optimize import least_squares

V = 200.0
R = 1.987
K0 = np.array([1.528e6,2.778e7,1e3])*3600
EA = np.array([17000.,20000.,15000.])
DH = np.array([-27150.,-26950.,-205.5])
NU = np.array([[-1.,-1,0],[-1,0,-1],[1,-1,2],[0,1,-1]])
MOIETY = np.array([[0,1,1,1],[1,0,1,2.]])
RHOS = np.array([7.63446,10.8803,10.9014])
CPS = np.array([236.32,265.80,273.50])
RHOC = 8.09685*73.56
RECYCLE = np.array([.001198,10.8982,.002015,0.])
FLOWS = np.array([82.59918,57.95784,88.92402])
FEEDT = np.array([46.85,46.85,45.22])
SCALE = np.array([.1,7.,3.,.6,50.])
NOMINAL_STROKE = .785175
FMAX = FLOWS[0] / 50**(NOMINAL_STROKE-1)
DT = .02

def stationary_concentrations(T=160.0, flows=FLOWS, p=None):
    p=np.zeros(12) if p is None else np.asarray(p)
    k=K0*np.exp(p[:3]-(EA+1000*p[3:6])/(R*(T+273.15)))
    feed=flows[2]*RECYCLE.copy();feed[1]*=np.exp(p[10])
    feed[0]+=flows[0]*RHOS[0]*np.exp(p[8]); feed[1]+=flows[1]*RHOS[1]*np.exp(p[9])
    def fun(c):
        rates=k*np.array([c[0]*c[1],c[0]*c[2],c[1]*c[3]])
        return (feed-flows.sum()*c)/V+NU@rates
    sol=least_squares(fun,[.04,4.63,1.97,.37],bounds=(0,np.inf),xtol=1e-13,ftol=1e-13,gtol=1e-13)
    if np.linalg.norm(fun(sol.x))>1e-7: raise RuntimeError('stationary concentration solve failed')
    return sol.x

XSS = np.r_[stationary_concentrations(),160.]
rates0=K0*np.exp(-EA/(R*(XSS[4]+273.15)))*np.array([XSS[0]*XSS[1],XSS[0]*XSS[2],XSS[1]*XSS[3]])
Q0=float(np.dot(FLOWS*RHOS*CPS,FEEDT)-FLOWS.sum()*RHOC*XSS[4]+V*np.dot(-DH,rates0))
U0=np.r_[FLOWS,Q0,FEEDT]

def valve_flow(stroke):
    return np.where(np.asarray(stroke)<=0,0.,FMAX*50**(np.asarray(stroke)-1))

def valve_stroke(flow):
    return np.clip(1+np.log(np.maximum(flow,1e-12)/FMAX)/np.log(50),0,1)

def molefractions(x):
    return np.asarray(x)[...,:4]/np.maximum(np.sum(np.asarray(x)[...,:4],axis=-1,keepdims=True),1e-12)

def build(dt=DT,substeps=8):
    x=ca.SX.sym('x',5); u=ca.SX.sym('u',7); p=ca.SX.sym('p',12)
    kval=ca.DM(K0)*ca.exp(p[:3]-(ca.DM(EA)+1000*p[3:6])/(R*(x[4]+273.15)))
    rates=kval*ca.vertcat(x[0]*x[1],x[0]*x[2],x[1]*x[3])
    feed=u[2]*ca.vertcat(RECYCLE[0],RECYCLE[1]*ca.exp(p[10]),RECYCLE[2],0)
    feed+=ca.vertcat(u[0]*RHOS[0]*ca.exp(p[8]),u[1]*RHOS[1]*ca.exp(p[9]),0,0)
    fout=u[0]+u[1]+u[2]
    dc=(feed-fout*x[:4])/V+ca.DM(NU)@rates
    energy=ca.dot(u[:3]*ca.DM(RHOS*CPS),u[4:7])-fout*RHOC*x[4]+V*ca.dot(ca.DM(-DH),rates)*ca.exp(p[6])-u[3]
    dtemp=energy/(RHOC*V*ca.exp(p[7]))+p[11]
    rhs=ca.vertcat(dc,dtemp)
    f=ca.Function('rhs',[x,u,p],[rhs])
    a=ca.Function('rhs_jac',[x,u,p],[ca.jacobian(rhs,x)])
    b=ca.Function('input_jac',[x,u,p],[ca.jacobian(rhs,u)])
    state=x; h=dt/substeps
    for _ in range(substeps):
        k1=f(state,u,p);k2=f(state+h*k1/2,u,p);k3=f(state+h*k2/2,u,p);k4=f(state+h*k3,u,p)
        state=state+h/6*(k1+2*k2+2*k3+k4)
    step=ca.Function('rk4',[x,u,p],[state])
    A=ca.Function('step_jac',[x,u,p],[ca.jacobian(state,x)])
    return f,a,b,step,A

F,JAC,BJAC,STEP,AJAC=build()

def step(x,u=U0,p=None):
    return np.array(STEP(x,u,np.zeros(12) if p is None else p)).ravel()

def steady(u=U0,p=None,start=XSS):
    p=np.zeros(12) if p is None else p
    sol=least_squares(lambda x: np.array(F(x,u,p)).ravel()/SCALE,start,bounds=([0,0,0,0,-20],[15,20,15,10,350]),xtol=1e-12,ftol=1e-12,gtol=1e-12)
    return sol.x, np.linalg.norm(sol.fun)

if __name__=='__main__':
    print('XSS',XSS,'fractions',molefractions(XSS),'Q0',Q0,'FMAX',FMAX)
    print('steady residual',np.array(F(XSS,U0,np.zeros(12))).ravel())
    print('eigenvalues',np.linalg.eigvals(np.array(JAC(XSS,U0,np.zeros(12)))))
