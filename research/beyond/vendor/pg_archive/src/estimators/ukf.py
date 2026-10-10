"""Scaled UKF. Linear measurement update includes the additive process Q.
Covariances and state means are stored in SI; sigma-point arithmetic is centered.
"""
import numpy as np
from src.plant.model import *
H=np.eye(6)[[4,5]]
class UKF:
 def __init__(self,x,P=P0,R=RBASE,method='euler',alpha=1e-3):
  self.x=x.copy();self.P=P.copy();self.R=R.copy();self.method=method;self.alpha=alpha;self.repairs=0
  self.nu=np.zeros(2);self.S=self.R.copy();self.nis=0.
 def predict(self,u,p=Parameters()):
  n=6;c=self.alpha**2*n;w=np.full(13,1/(2*c));w[0]=(c-n)/c;wc=w.copy();wc[0]+=3-self.alpha**2
  pn=self.P/XS[:,None]/XS[None,:];pn=(pn+pn.T)/2
  try:L=np.linalg.cholesky(c*pn)
  except np.linalg.LinAlgError:
   e,v=np.linalg.eigh(pn);pn=(v*np.maximum(e,1e-14))@v.T;L=np.linalg.cholesky(c*pn);self.repairs+=1
  sigma=self.x+np.vstack([np.zeros(6),L.T,-L.T])*XS
  pred=step(sigma,u,p,method=self.method);base=pred[0];mu=base+np.einsum('i,ij->j',w,pred-base)
  d=(pred-mu)/XS;P=(d.T*wc)@d;P=P*XS[:,None]*XS[None,:]
  return mu,(P+P.T)/2
 def update_prediction(self,mu,P,z,q=QFIX):
  P=P+np.diag(q);S=P[4:6,4:6]+self.R;K=np.linalg.solve(S,P[:,4:6].T).T;nu=z-mu[4:6]
  self.x=mu+K@nu;A=np.eye(6)-K@H
  self.P=A@P@A.T+K@self.R@K.T;self.P=(self.P+self.P.T)/2
  self.nu=nu;self.S=S;self.nis=float(nu@np.linalg.solve(S,nu));return self.x
 def cycle(self,u,z,q=QFIX,p=Parameters()):return self.update_prediction(*self.predict(u,p),z,q)
