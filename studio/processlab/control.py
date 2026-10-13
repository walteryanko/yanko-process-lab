"""Controllers see observations/estimates only. Bound/rate constraints are explicit."""
import numpy as np
from scipy.optimize import minimize
from .numerics import integrate


class Controller:
    def __init__(self,model,config):
        self.model,self.c=model,config;self.last=float(np.clip(config["manual"],*model.bounds));self.integral=0.;self.previous=None
        self.warm=np.full(config["horizon"],self.last)
        self.diagnostics={"optimizer_failures":0,"last_status":"manual","iterations":0}

    def act(self,estimate,measurement,disturbance):
        c,m=self.c,self.model;dt=c["dt"];low,high=m.bounds
        lower=max(low,self.last-m.slew*dt);upper=min(high,self.last+m.slew*dt)
        if c["controller"] == "manual":
            action=float(np.clip(c["manual"],lower,upper))
        elif c["controller"] == "pid":
            if measurement is None:
                self.diagnostics["last_status"]="hold: no available measurement";return self.last
            pos=m.measurement_indices.index(m.tidx);error=c["setpoint"]-measurement[pos]
            sign=1 if hasattr(m,"units") else -1
            de=0 if self.previous is None else (error-self.previous)/dt
            trial=self.integral+error*dt
            raw=c["manual"]+sign*(c["kp"]*error+c["ki"]*trial+c["kd"]*de)
            action=float(np.clip(raw,lower,upper))
            if raw==action or sign*error*(raw-action)<0:self.integral=trial
            self.previous=error;self.diagnostics["last_status"]="PID, conditional integration anti-windup"
        else:
            if estimate is None:raise ValueError("NMPC cannot access simulator ground truth")
            span=high-low;n=c["horizon"];last=self.last
            # Optimize normalized moves to avoid incompatible watt/flow scales.
            def unpack(z):return low+np.asarray(z)*span
            def path(z):
                x=estimate.copy();out=[]
                for u in unpack(z):
                    x=integrate(m,x,u,disturbance,dt,c);out.append(x.copy())
                return np.array(out)
            def objective(z):
                try:
                    states=path(z);y=np.array([m.quality(x) for x in states]) if c["control_target"]=="quality" else states[:,m.tidx]
                    norm=max(.05,abs(c["setpoint"])*.05) if c["control_target"]=="quality" else 5.
                    return float(np.sum(((y-c["setpoint"])/norm)**2)+c["move_weight"]*np.sum(np.diff(np.r_[(last-low)/span,z])**2))
                except (ValueError,FloatingPointError):return 1e20
            def constraints(z):
                U=unpack(z);rate=m.slew*dt-np.abs(np.diff(np.r_[last,U]))
                try:thermal=m.temperature_limit-path(z)[:,m.tidx]
                except (ValueError,FloatingPointError):thermal=np.full(n,-1e6)
                return np.r_[rate/span,thermal/10]
            guess=np.clip((self.warm-low)/span,0,1)
            sol=minimize(objective,guess,method="SLSQP",bounds=[(0,1)]*n,constraints={"type":"ineq","fun":constraints},options={"maxiter":25,"ftol":1e-5})
            self.diagnostics.update(last_status=str(sol.message),iterations=int(sol.nit))
            if sol.success and np.isfinite(sol.fun) and min(constraints(sol.x))>=-1e-7:
                U=unpack(sol.x);action=float(np.clip(U[0],lower,upper));self.warm=np.r_[U[1:],U[-1]]
            else:
                self.diagnostics["optimizer_failures"]+=1;action=last
                self.diagnostics["last_status"]="bounded hold fallback: "+str(sol.message)
        self.last=action;return action
