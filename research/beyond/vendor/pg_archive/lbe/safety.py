"""Interval thermal-inventory filter and analytically invariant shutdown backup.

Conditional on known conserved inventories/feeds, fixed Cp/dH, rate/UA bounds,
bounded sensor error and immediate feed isolation. See reports/safety_proof.md.
No learned predictor or UKF covariance is used as a deterministic certificate.
"""
import numpy as np
from math import exp,expm1,log1p
from lbe.physics import inventory_potential,Parameters,U0,feed
from lbe.config import *

class I:
    __slots__=('l','h')
    def __init__(self,l,h=None):self.l=float(l);self.h=float(l if h is None else h)
    def __add__(self,o):
        if not isinstance(o,I):o=I(o)
        return I(self.l+o.l,self.h+o.h)
    __radd__=__add__
    def __neg__(self):return I(-self.h,-self.l)
    def __sub__(self,o):return self+-o if isinstance(o,I) else self+(-o)
    def __rsub__(self,o):return -self+o
    def __mul__(self,o):
        if not isinstance(o,I):o=I(o)
        z=(self.l*o.l,self.l*o.h,self.h*o.l,self.h*o.h);return I(min(z),max(z))
    __rmul__=__mul__
    def __truediv__(self,o):
        if not isinstance(o,I):o=I(o)
        if o.l<=0<=o.h:raise ValueError('interval division across zero')
        return self*I(1/o.h,1/o.l)
    def log1p(self):return I(log1p(self.l),log1p(self.h))

def inventory(x):
    p=Parameters();w=np.dot(x[:4],[p.cpA,p.cpB,p.cpC,p.cpM]);return w-CP_DELTA*x[0]

def _ca_end(a,k,source,D,h):
    z=D+k;e=exp(-z*h);return a*e+source*(-expm1(-z*h))/z

def bound_step(tlo,thi,blo,bhi,q,u,p,dt=DT,ua_low=UA_BOUNDS[0],n=12,t0_error=0.):
    """Correlated thermal-inventory coordinates (T,B); Picard flow tubes.

    Reaction cancels exactly from Bdot. For fixed T,q,G, Bdot=A*exp(-c*B)-const
    has a negative derivative. Face bounds avoid the interval wrapping of CA,B.
    """
    H=-p.dH;delta=CP_DELTA;c=delta/H;v,_=feed(u,p);D=v/p.V
    F=u[0]*p.cpA+p.FB*p.cpB+p.FM*p.cpM;fq=F-delta*u[0];qeq=fq/v
    gl=u[1]*p.cpB*(-expm1(-p.UA*ua_low/(u[1]*p.cpB)));gh=u[1]*p.cpB*(-expm1(-p.UA*UA_BOUNDS[1]/(u[1]*p.cpB)))
    h=dt/n;peak=bhi;pad=2e-9
    def BF(B,T,G,qq,T0):
        ee=exp(c*(B-T));A=G*(u[2]-T)+F*(T0-T)+H*u[0]+H*fq/delta
        return A/(p.V*qq*ee)-H*fq/(delta*p.V*qq),c*A/(p.V*qq*ee)
    for _ in range(n):
        qn=qeq+(q-qeq)*exp(-D*h);ql,qh=min(q,qn),max(q,qn)
        # Monotone B and T face bounds. Derivatives signs are checked throughout.
        tl=tlo-.2;th=thi+.2;bl=blo-.2;bh=bhi+.2;found=False
        for _it in range(20):
            vals=[];aa=[];valid=True
            for B,T,G,qq,T0 in [(B,T,G,qq,T0) for B in [bl,bh] for T in [tl,th] for G in [gl,gh] for qq in [ql,qh] for T0 in [p.T0-t0_error,p.T0+t0_error]]:
                val,a=BF(B,T,G,qq,T0);vals.append(val);aa.append(a)
                # d(Bdot)/dT=[-G*(1+c*(T-Ta))-c*F*(T-T0)]/(V*q*exp(...))
                valid=valid and a>0 and -G*(1+c*(T-u[2]))-c*F*(T-T0)<=0
            if not valid:return (tlo,thi,blo,bhi,q),np.inf,False
            gmin=max(0,bl-th);gmax=max(0,bh-tl)
            ai=I(ql/delta*expm1(c*gmin),qh/delta*expm1(c*gmax));wi=I(ql,qh)+delta*ai
            ki=I(RATE_BOUNDS[0]*p.k0*exp(-p.E/(p.R*(max(tl,260)+p.arrhenius_offset))),RATE_BOUNDS[1]*p.k0*exp(-p.E/(p.R*(min(th,395)+p.arrhenius_offset))))
            ti=I(tl,th);GG=I(gl,gh)
            ft=(GG*(u[2]-ti)+F*(I(p.T0-t0_error,p.T0+t0_error)-ti)+H*p.V*ki*ai)/(p.V*wi)
            needed=[tlo+h*min(0,ft.l),thi+h*max(0,ft.h),blo+h*min(0,min(vals)),bhi+h*max(0,max(vals))]
            if tl<=needed[0] and th>=needed[1] and bl<=needed[2] and bh>=needed[3]:found=True;break
            tl=min(tl,needed[0]-.02);th=max(th,needed[1]+.02);bl=min(bl,needed[2]-.02);bh=max(bh,needed[3]+.02)
        if not found:return (tlo,thi,blo,bhi,q),np.inf,False
        fl=min(BF(blo,T,G,qq,T0)[0] for T in [tl,th] for G in [gl,gh] for qq in [ql,qh] for T0 in [p.T0-t0_error,p.T0+t0_error])
        fh=max(BF(bhi,T,G,qq,T0)[0] for T in [tl,th] for G in [gl,gh] for qq in [ql,qh] for T0 in [p.T0-t0_error,p.T0+t0_error])
        amin,amax=min(aa),max(aa);al=amax if fl>=0 else amin;ah=amin if fh>=0 else amax
        bn=blo+fl*(-expm1(-al*h))/al-pad;Bn=bhi+fh*(-expm1(-ah*h))/ah+pad
        if u[0]==0:
            # T >= 280 is invariant. This threshold also covers T < coolant inlet.
            backup_threshold=p.T0+t0_error+gh/F*max(u[2]-280.,0.)
            Bn=min(Bn,max(bhi,backup_threshold)+pad)
        peak=max(peak,bhi,Bn);tlo=max(280,tlo+h*ft.l-pad);thi=min(Bn,thi+h*ft.h+pad);blo,bhi,q=bn,Bn,qn
        if peak>T_LIMIT+.01:return (tlo,thi,blo,bhi,q),peak,False
    return (tlo,thi,blo,bhi,q),peak,peak<=T_LIMIT-1e-7

class SafetyFilter:
    def __init__(self,x):
        self.box=(float(x[4]),float(x[4]),float(inventory_potential(x)),float(inventory_potential(x)),float(inventory(x)))
        self.valid=True;self.interventions=0;self.fallbacks=0;self.uncovered=0
    def correct(self,z,error_bound):
        if z is None or not np.isfinite(z):return
        a,A,b,B,q=self.box
        an=max(a,z-error_bound);An=min(A,z+error_bound)
        if an>An+1e-8:
            self.valid=False;return
        self.box=(an,An,max(b,an),B,q)
    def choose(self,u,p,force=False,ua_low=UA_BOUNDS[0],t0_error=0.,cooling_max=3000*.45359237):
        original=u.copy();cert=None;peak=np.inf;reason='accepted';fallback=False
        def check(a):return bound_step(*self.box,a,p,ua_low=ua_low,t0_error=t0_error)
        if not force and self.valid:
            cert,peak,ok=check(u)
            if ok:self.box=cert;return u,False,False,True,peak,reason
            high=u.copy();high[1]=cooling_max
            cert,peak,ok=check(high)
            if ok:
                low=u[1];hi=high[1]
                for _ in range(9):
                    mid=(low+hi)/2;trial=u.copy();trial[1]=mid;ss,pk,good=check(trial)
                    if good:hi=mid;cert=ss;peak=pk
                    else:low=mid
                u=high;u[1]=hi;cert,peak,ok=check(u);reason='cooling_filter'
            else:fallback=True
        else:fallback=True
        if fallback:
            u=u.copy();u[0]=0;u[1]=cooling_max
            cert,peak,propagated=check(u);reason='feed_isolation_backup'
            # The invariant potential proof covers indefinite backup, even after a sensor dropout.
            F=p.FB*p.cpB+p.FM*p.cpM
            gh=u[1]*p.cpB*(-expm1(-p.UA*UA_BOUNDS[1]/(u[1]*p.cpB)))
            threshold=p.T0+t0_error+gh/F*max(u[2]-280.,0.)
            ok=bool(self.valid and self.box[3]<=T_LIMIT and threshold<=T_LIMIT and min(p.T0-t0_error,u[2])>=280.)
            if not propagated:
                # A rejected Picard enclosure may be partial in time. Never use it
                # as the next observer state. The invariant backup gives a valid
                # full-sample enclosure, independent of the reaction rate.
                v,_=feed(u,p);D=v/p.V;qeq=F/v
                qnext=qeq+(self.box[4]-qeq)*exp(-D*DT)
                upper=max(self.box[3],threshold)+2e-9
                cert=(280.,upper,280.,upper,qnext)
                peak=upper

            self.fallbacks+=1
        self.box=cert;intervention=not np.allclose(u,original,rtol=0,atol=1e-7)
        self.interventions+=int(intervention)
        return u,intervention,fallback,ok,peak,reason

