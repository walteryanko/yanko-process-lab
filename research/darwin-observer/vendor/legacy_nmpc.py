"""Finite-horizon NMPC: six free moves followed by a held last move, p=57.
B0 faithfully ports NMPC_Fmincon's dimensional scaling and soft 160 F penalty.
MIMO uses point or exact dead-zone costs and analytically eliminated thermal slacks.
"""
import time
from functools import lru_cache
import numpy as np,casadi as ca
from src.plant.model import *
N=57;M=6;S=np.array([.2,2.,2.])
UMIN=U0+np.array([-.2*U0[0],-.5*U0[1],-10.]);UMAX=U0+np.array([.2*U0[0],.5*U0[1],10.])
RATE=np.array([.01*U0[0],.02*U0[1],.5])
@lru_cache(maxsize=8)
def build(mode='mimo',zone=True,preview=False):
 p=Parameters();x=ca.SX.sym('x',6);u=ca.SX.sym('u',3);d=ca.SX.sym('d',3)
 FA,mw,Ta=u[0],u[1],u[2];FB,FM,T0=d[0],d[1],d[2]
 v=FA/p.rhoA+FB/p.rhoB+FM/p.rhoM;r=p.k0*ca.exp(-p.E/(p.R*(x[4]+p.arrhenius_offset)))*x[0]
 duty=mw*p.cpB*(Ta-x[4])*(1-ca.exp(-p.UA/(mw*p.cpB)))
 dx=ca.vertcat(v/p.V*(ca.vertcat(FA,FB,0,FM)/v-x[:4])+ca.vertcat(-r,-r,r,0),
 (duty-(FA*p.cpA+FB*p.cpB+FM*p.cpM)*(x[4]-T0)-p.dH*r*p.V)/(p.V*ca.dot(x[:4],ca.DM([p.cpA,p.cpB,p.cpC,p.cpM]))),
 (mw*p.cpB*(Ta-x[5])-duty)/(p.rhoB*p.Vt*p.cpB))
 f=ca.Function('f',[x,u,d],[dx]);h=DT;k1=f(x,u,d);k2=f(x+h*k1/2,u,d);k3=f(x+h*k2/2,u,d);k4=f(x+h*k3,u,d)
 st=ca.Function('step',[x,u,d],[x+h*(k1+2*k2+2*k3+k4)/6])
 idx=[1] if mode=='siso' else [0,1,2];nu=len(idx);q=ca.MX.sym('q',M*nu);par=ca.MX.sym('par',15+(N if preview else 0))
 xx=par[:6];prev=par[6:9];ref=par[9:12];dis=par[12:15];old=prev;J=0;g=[];U=[];ys=[];slacks=[]
 for j in range(M):
  uu=ca.MX(prev)
  for k,a in enumerate(idx):uu[a]=U0[a]+US[a]*q[j*nu+k]
  U.append(uu)
  du=uu-old
  if mode=='siso':J+=.2*(du[1]/U0[1])**2
  else:
   J+=.2*ca.sumsqr(du/ca.DM(US));g.extend([1-du/ca.DM(RATE),1+du/ca.DM(RATE)])
  old=uu
 for j in range(N):
  xx=st(xx,U[min(j,M-1)],dis);y=xx[[2,4,5]];ys.append(y)
  if mode=='siso':
   J+=.8*((y[0]-(par[15+j] if preview else ref[0]))/(.1433*CUNIT))**2
   excess=ca.fmax(xx[4]-((160-32)/1.8+273.15),0)
   J+=1000*(excess/(160/1.8))**2
  else:
   th=ca.fmax(ca.fabs(y[1:]-ref[1:])-(.5 if zone else 0),0)/2
   J+=.8*(((y[0]-ref[0])/.2)**2+ca.sumsqr(th))
   excess=ca.fmax(xx[4]-344,0);J+=1e4*(excess/2)**2+100*excess/2
   g.append(xx[:4])
  slacks.append(excess)
 G=ca.vertcat(*g) if g else ca.MX.ones(1,1)
 cheap=ca.Function('cost',[q,par],[J,G]);full=ca.Function('derivatives',[q,par],[J,ca.gradient(J,q),G,ca.jacobian(G,q)])
 pred=ca.Function('prediction',[q,par],[ca.hcat(ys).T,ca.vertcat(*slacks)])
 return cheap,full,pred,st
class Problem:
 def __init__(self,x,previous,reference,mode='mimo',zone=True,p=Parameters(),warm=None,future_reference=None):
  self.mode=mode;self.idx=[1] if mode=='siso' else [0,1,2];self.nu=len(self.idx)
  self.par=np.r_[x,previous,reference,[p.FB,p.FM,p.T0]];self.previous=previous.copy()
  
  if mode=='siso' and warm is not None:self.par[7]=U0[1]+US[1]*warm[0] # Exact archived lastmv=mvseq0(1), after prior sequence shift.
  if future_reference is not None:self.par=np.r_[self.par,future_reference]
  self.cheap,self.full,self.predictor,self.step=build(mode,zone,future_reference is not None);self.calls=0;self.deriv_calls=0;self.cache=None
  lo=UMIN.copy();hi=UMAX.copy()
  if mode=='siso':lo[1]=50*.45359237;hi[1]=3000*.45359237
  self.lo=(lo-U0)/US;self.hi=(hi-U0)/US
  self.bounds=[(self.lo[j],self.hi[j]) for _ in range(M) for j in self.idx]
  self.warm=self.project(np.tile((previous-U0)/US,(M,1))[:,self.idx].ravel() if warm is None else warm)
 def project(self,q):
  b=np.array(q).reshape(M,self.nu).copy();old=(self.previous-U0)/US
  for k in range(M):
   for a,j in enumerate(self.idx):
    lo,hi=self.lo[j],self.hi[j]
    if self.mode!='siso':lo=max(lo,old[j]-RATE[j]/US[j]);hi=min(hi,old[j]+RATE[j]/US[j])
    b[k,a]=np.clip(b[k,a],lo,hi);old[j]=b[k,a]
  return b.ravel()
 def value(self,q):
  self.calls+=1;r=self.cheap(q,self.par);return float(r[0]),np.array(r[1]).ravel()
 def evaluate(self,q):
  if self.cache is None or not np.array_equal(self.cache[0],q):
   self.calls+=1;self.deriv_calls+=1;a=self.full(q,self.par)
   self.cache=(q.copy(),float(a[0]),np.array(a[1]).ravel(),np.array(a[2]).ravel(),np.array(a[3]))
  return self.cache[1:]
 def action(self,q):
  u=self.previous.copy()
  for k,j in enumerate(self.idx):u[j]=U0[j]+US[j]*q[k]
  return u
 def shift(self,q):
  b=q.reshape(M,self.nu);return np.vstack([b[1:],b[-1]]).ravel()
