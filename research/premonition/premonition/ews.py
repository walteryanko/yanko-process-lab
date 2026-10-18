"""Causal trailing-window EWS; trend removal prevents direct ramp-as-variance claims."""
import numpy as np
from .physics import DT

def indicators(values,dt=DT,min_n=12):
    a=np.asarray(values,float);a=a[np.isfinite(a)]
    if len(a)<min_n:return dict(valid=False,ac1=0.,variance=0.,recovery=0.,trend=0.,skew=0.,low_frequency=0.)
    t=np.arange(len(a))*dt;t=t-t.mean();b=a-a.mean();slope=float(t@b/max(t@t,1e-30));r=b-slope*t
    den=float(r[:-1]@r[:-1]);phi=float(r[:-1]@r[1:]/den) if den>1e-14 else 0.
    phi=float(np.clip(phi,-.99999,.99999));var=float(np.var(r,ddof=1))
    recovery=-np.log(phi)/dt if 0<phi<1 else np.nan
    skew=float(np.mean(r**3)/max(var**1.5,1e-14))
    spec=np.abs(np.fft.rfft(r))**2;lf=float(np.sum(spec[1:max(2,len(spec)//4)])/max(np.sum(spec[1:]),1e-14))
    return dict(valid=True,ac1=phi,variance=var,recovery=recovery,trend=slope,skew=skew,low_frequency=lf)

class EWS:
    def __init__(self,window=32):self.window=window;self.y=[];self.r=[]
    def update(self,y,residual=0.):
        self.y.append(float(y));self.r.append(float(residual));self.y=self.y[-self.window:];self.r=self.r[-self.window:]
        d=indicators(self.y);r=indicators(self.r)
        d['residual_ac1']=r['ac1'];d['residual_variance']=r['variance'];return d
