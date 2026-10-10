"""Causal output feedback. No plant state/parameter truth enters these classes.

The direct policy stores only filtered temperatures and an integral. It never
constructs chemical states. The inferential comparator has a temperature-only
EKF with nominal parameters. Both policies use identical measured actuators.
"""
import numpy as np
from beyond.models import get_model

class EKF:
    def __init__(self,m,x):
        self.m=m;self.x=x.copy();self.P=np.diag(m.xscale**2);self.nis=0.
    def cycle(self,u,y):
        m=self.m;z,A,_=m.deriv(self.x,u,m.p0);self.x=np.array(z).ravel();A=np.array(A)
        Q=np.diag((m.xscale*.015)**2);self.P=A@self.P@A.T+Q
        ok=np.isfinite(y);idx=np.array(m.yidx)[ok]
        if len(idx):
            H=np.eye(m.n)[idx];R=np.diag(m.noise[ok]**2);S=H@self.P@H.T+R
            K=np.linalg.solve(S,(self.P@H.T).T).T;nu=np.array(y)[ok]-self.x[idx]
            self.x+=K@nu;C=np.eye(m.n)-K@H;self.P=C@self.P@C.T+K@R@K.T
            self.nis=float(nu@np.linalg.solve(S,nu))
        self.x[:4]=np.maximum(self.x[:4],1e-7);self.x[4:]=np.clip(self.x[4:],m.tmin-20,m.tmax+20)
        self.P=(self.P+self.P.T)/2
        return self.x.copy()

class FixedPolicy:
    """One set of gains per reactor, fixed across all operating regions."""
    def __init__(self,m,xop,uop,mode='direct',gain=1.):
        self.m=m;self.xop=xop.copy();self.uop=uop.copy();self.mode=mode;self.gain=gain
        self.last=uop.copy();self.integral=0.;self.thermal_integral=0.;self.yfiltered=xop[4]
        self.last_quality=float(m.quality(xop));self.wait=0.;self.time=0.;self.shield_hits=0
        A=np.array(m.fx(m.x0,m.u0,m.p0));B=np.array(m.fu(m.x0,m.u0,m.p0));
        Xu=-np.linalg.solve(A,B);g=np.array(m.qgrad(m.x0)).ravel()
        self.gainq=float(g@Xu[:,m.cidx if m.kind=='PG' else 0])*m.u0[m.cidx if m.kind=='PG' else 0]/m.q0
        self.gaint=float(Xu[4,m.cidx]*m.u0[m.cidx])
    def act(self,measurement,estimate=None,cov=None,reference=None,thermal_target=None,uop=None):
        m=self.m;u0=self.uop if uop is None else uop;ref=float(m.quality(self.xop)) if reference is None else reference
        Tref=self.xop[4] if thermal_target is None else thermal_target
        y=float(measurement[0])
        if np.isfinite(y):self.yfiltered=.55*self.yfiltered+.45*y
        y=self.yfiltered;u=u0.copy();self.time+=m.dt
        et=y-Tref
        # Thermal output control uses only sensor history, feedforward and inputs.
        thermal_raw=u0[m.cidx]/m.u0[m.cidx]+self.gain*(-et/self.gaint)*1.5+self.thermal_integral
        if self.mode=='direct' or m.kind=='EB':
            u[m.cidx]=thermal_raw*m.u0[m.cidx]
            self.thermal_integral+=self.gain*(-et/self.gaint)*m.dt/max(m.tau,.1)
        if self.mode!='direct':
            eq=(ref-float(m.quality(estimate)))/m.q0
            active=True
            if self.mode=='deadband':eq=np.sign(eq)*max(abs(eq)-.02,0)
            if self.mode=='wait' and self.time<3*m.tau:active=False
            if self.mode=='gated' and cov is not None:
                g=np.array(m.qgrad(estimate)).ravel();sd=np.sqrt(max(float(g@cov@g),0))/m.q0
                if abs(eq)<max(.02,1.5*sd):active=False
            idx=m.cidx if m.kind=='PG' else 0
            if active:
                raw=u0[idx]/m.u0[idx]+self.gain*eq/self.gainq+self.integral
                u[idx]=raw*m.u0[idx]
                if m.umin[idx]<u[idx]<m.umax[idx]:self.integral+=self.gain*eq/self.gainq*m.dt/(2*m.tau)
            elif m.kind=='PG':u[m.cidx]=thermal_raw*m.u0[m.cidx]
        # Fixed measured-temperature override. This is a heuristic, not a safety certificate.
        if y>m.tmax-.75:
            u[m.cidx]=m.umax[m.cidx];self.shield_hits+=1
            self.thermal_integral=min(self.thermal_integral,0.)
        if y<m.tmin+1:u[m.cidx]=m.umin[m.cidx]
        u=np.clip(u,m.umin,m.umax)
        u=self.last+np.clip(u-self.last,-m.slew*m.dt,m.slew*m.dt)
        # Back-calculation prevents windup of thermal integral after saturation.
        if self.mode=='direct' or m.kind=='EB':
            self.thermal_integral+=.2*(u[m.cidx]/m.u0[m.cidx]-thermal_raw)
        self.last=u.copy();return u
