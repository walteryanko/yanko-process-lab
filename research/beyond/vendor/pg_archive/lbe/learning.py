"""Small learned corrections to reaction rate and UA, preserving stoichiometry."""
import json
import numpy as np
import casadi as ca
from lbe.config import ROOT
from src.plant.model import U0

def features(x,u):
    x=np.asarray(x);u=np.asarray(u)
    return np.stack([(x[...,4]-332)/18,(x[...,0]-.6)/.65,np.broadcast_to(u[...,1]/U0[1]-1,x.shape[:-1])],axis=-1)

class Residual:
    def __init__(self,path=None):
        d=json.loads((path or ROOT/'models/selected.json').read_text());self.data=d;self.kind=d['kind']
        self.weights=[np.array(w) for w in d['weights']];self.biases=[np.array(w) for w in d['biases']]
        self.mean=np.array(d['mean']);self.scale=np.array(d['scale'])
    def __call__(self,x,u):
        z=features(x,u)
        if self.kind=='ridge':z=np.concatenate([z,z*z,z[...,0:1]*z[...,1:2],z[...,0:1]*z[...,2:3],z[...,1:2]*z[...,2:3]],axis=-1)
        for i,(w,b) in enumerate(zip(self.weights,self.biases)):
            z=z@w+b
            if i<len(self.weights)-1:z=np.tanh(z)
        return np.clip(z*self.scale+self.mean,-.30,.30)
    def symbolic(self,x,u):
        z=ca.vertcat((x[4]-332)/18,(x[0]-.6)/.65,u[1]/U0[1]-1)
        if self.kind=='ridge':z=ca.vertcat(z,z*z,z[0]*z[1],z[0]*z[2],z[1]*z[2])
        for i,(w,b) in enumerate(zip(self.weights,self.biases)):
            z=ca.DM(w.T)@z+ca.DM(b)
            if i<len(self.weights)-1:z=ca.tanh(z)
        return ca.fmin(.30,ca.fmax(-.30,z*ca.DM(self.scale)+ca.DM(self.mean)))

def build_step(learned=False,euler=False):
    from src.plant.model import Parameters
    from lbe.config import DT
    p=Parameters();x=ca.SX.sym('x',6);u=ca.SX.sym('u',3);d=ca.SX.sym('d',3);b=ca.SX.sym('b',2)
    rr=Residual() if learned else None
    corr=rr.symbolic(x,u) if learned else ca.SX.zeros(2)
    corr=ca.fmin(.60,ca.fmax(-.50,corr+b))
    v=u[0]/p.rhoA+d[0]/p.rhoB+d[1]/p.rhoM
    r=p.k0*ca.exp(-p.E/(p.R*(x[4]+p.arrhenius_offset)))*(1+corr[0])*x[0]
    duty=u[1]*p.cpB*(u[2]-x[4])*(1-ca.exp(-p.UA*(1+corr[1])/(u[1]*p.cpB)))
    f=ca.vertcat(v/p.V*(ca.vertcat(u[0],d[0],0,d[1])/v-x[:4])+ca.vertcat(-r,-r,r,0),
      (duty-(u[0]*p.cpA+d[0]*p.cpB+d[1]*p.cpM)*(x[4]-d[2])-p.dH*r*p.V)/(p.V*ca.dot(x[:4],ca.DM([p.cpA,p.cpB,p.cpC,p.cpM]))),
      (u[1]*p.cpB*(u[2]-x[5])-duty)/(p.rhoB*p.Vt*p.cpB))
    ff=ca.Function('rhs',[x,u,d,b],[f]);z=x
    if euler:z=x+DT*f
    else:
        h=DT/2
        for _ in range(2):
            a=ff(z,u,d,b);bb=ff(z+h*a/2,u,d,b);c=ff(z+h*bb/2,u,d,b);dd=ff(z+h*c,u,d,b)
            z=z+h*(a+2*bb+2*c+dd)/6
    fstep=ca.Function('step',[x,u,d,b],[z])
    if not euler:
        from lbe.compiled import maybe_compiled
        return maybe_compiled(fstep,f'step_{int(learned)}')
    return fstep
