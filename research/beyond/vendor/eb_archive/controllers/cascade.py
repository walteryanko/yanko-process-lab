"""Low-complexity co-designed composition/temperature loops.

Same hypothetical cooling actuator limits as MIMO NMPC. No online composition.
Feedforward is computed only from the nominal model and measured flow inputs.
"""
import time
import numpy as np
from scipy.optimize import brentq
from ethylbenzene_model.model import *

class CascadePI:
    def __init__(self,feedforward=True):
        self.ff=feedforward;self.integral=0.;self.thermal_int=0.;self.last=np.array([NOMINAL_STROKE,1.]);self.cache={}
        self.time=[];self.failures=0;self.fallbacks=0
    def feedforward(self,u,sp):
        key=(round(u[1],6),round(u[2],6),round(sp,7))
        if key in self.cache:return self.cache[key]
        def objective(fe):
            c=stationary_concentrations(160.,np.array([fe,u[1],u[2]]))
            return c[2]/c.sum()-sp
        # Selectivity makes xEB(fe) nonmonotone. Search every sign-changing
        # bracket; the old endpoint-only bracket missed both recycle roots.
        grid=np.linspace(5.,FMAX,41);values=[objective(f) for f in grid];roots=[]
        for a,b,va,vb in zip(grid[:-1],grid[1:],values[:-1],values[1:]):
            if va*vb<0:roots.append(brentq(objective,a,b,xtol=1e-7))
        if roots:
            # Minimum-feed branch, closest to ordinary operating region.
            fe=min(roots,key=lambda f:abs(f-FLOWS[0]))
        else:
            fe=float(grid[np.argmin(abs(np.array(values)))]);self.failures+=1
        s=float(valve_stroke(fe));self.cache[key]=s;return s
    def act(self,x,sp,u,p=None,P=None):
        t=time.perf_counter();error=sp-molefractions(x)[2]
        sff=self.feedforward(u,sp) if self.ff else NOMINAL_STROKE
        raw=sff+3.*error+self.integral
        stroke=float(np.clip(raw,max(.05,self.last[0]-.045),min(1.,self.last[0]+.045)))
        if abs(raw-stroke)<1e-10 or np.sign(error)!=np.sign(raw-stroke):self.integral+=3/.35*DT*error
        fe=float(valve_flow(stroke));flow=np.array([fe,u[1],u[2]])
        rates=K0*np.exp(-EA/(R*(x[4]+273.15)))*np.array([x[0]*x[1],x[0]*x[2],x[1]*x[3]])
        qff=float(np.dot(flow*RHOS*CPS,u[4:])-flow.sum()*RHOC*160+V*np.dot(-DH,rates))
        et=x[4]-160
        qr=(qff+RHOC*V*(5*et+self.thermal_int))/Q0
        cool=float(np.clip(qr,max(.75,self.last[1]-.035),min(1.25,self.last[1]+.035)))
        if abs(qr-cool)<1e-10 or np.sign(et)!=np.sign(qr-cool):self.thermal_int+=8*DT*et
        self.last=np.array([stroke,cool]);self.time.append(time.perf_counter()-t);return self.last.copy()
