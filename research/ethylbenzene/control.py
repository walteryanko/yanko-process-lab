"""Receding-horizon NMPC. Estimated states are the only plant-state input."""
from time import perf_counter
import numpy as np
from scipy.optimize import minimize
from model import *
from compiled import MOVES,HORIZON

class NMPC:
    def __init__(self,models,prediction='physical',mode='siso',constrained=False):
        self.mode=mode;self.prediction=prediction;self.constrained=constrained
        self.nmv=1 if mode=='siso' else 2;self.previous=np.ones(2)
        self.warm=np.ones(MOVES*self.nmv);self.evaluate=models.evaluators[prediction,mode,constrained]
        self.bounds=[(.04,2.)] if self.nmv==1 else [(.04,2.),(.6,1.4)]
        self.bounds*=MOVES
    def step(self,estimate,u,reference,tref=TNOM):
        theta=np.r_[estimate,u,reference,tref,self.previous];cache={}
        def calc(q):
            if 'q' not in cache or not np.array_equal(q,cache['q']):
                cache['q']=np.array(q,copy=True);cache['v']=self.evaluate(q,theta)
            return cache['v']
        start=perf_counter()
        cons=[dict(type='ineq',fun=lambda q:calc(q)[2],jac=lambda q:calc(q)[3])]
        sol=minimize(lambda q:float(calc(q)[0][0]),self.warm.copy(),jac=lambda q:calc(q)[1],
                     method='SLSQP',bounds=self.bounds,constraints=cons,
                     options={'ftol':1e-7,'maxiter':45,'disp':False})
        result=calc(sol.x);finite=bool(np.all(np.isfinite(result[0])) and np.all(np.isfinite(result[2])))
        feasible=finite and bool(np.min(result[2])>=-1e-5)
        fallback=not feasible
        if fallback:
            # Transparent emergency valve closure + full heat removal. This can override
            # the normal move-rate bound and is logged as a separate control action.
            first=[.04] if self.nmv==1 else [.04,1.4]
            if not self.constrained:first=list(self.previous[:self.nmv])
            self.warm=np.tile(first,MOVES);result=calc(self.warm)
        else:self.warm=sol.x.copy()
        first=self.warm[:self.nmv];self.previous=np.r_[first,1.] if self.nmv==1 else first.copy()
        tempmax=float(T_LIMIT-5*np.min(result[2][:HORIZON])) if self.constrained else None
        return self.previous.copy(),dict(solver_success=bool(sol.success),status=int(sol.status),
              feasible=bool(feasible),fallback=bool(fallback),iterations=int(sol.nit),
              predicted_Tmax_C=tempmax,latency_ms=1000*(perf_counter()-start))
