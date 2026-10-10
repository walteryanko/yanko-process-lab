"""Common, budgeted SQP / PSO / DE / hybrid interfaces. No unbounded search."""
import numpy as np,time
from scipy.optimize import minimize

def solve(problem,method='SQP',seed=0,population=12,generations=4,maxiter=60,deadline=50.):
 start=time.perf_counter();rng=np.random.default_rng(seed);p=problem;nit=0;global_evals=0;timed_out=False
 def score(q):
  nonlocal global_evals
  v,c=p.value(q);global_evals+=1
  return v+1e7*np.sum(np.minimum(c,0)**2) if np.isfinite(v) else 1e30
 best=p.warm.copy();baseJ,bc=p.value(best);bestJ=baseJ+1e7*np.sum(np.minimum(bc,0)**2)
 if method!='SQP':
  n=len(best);bounds=np.array(p.bounds);width=bounds[:,1]-bounds[:,0]
  candidates=[best]
  for i in range(population-1):
   raw=best+rng.normal(size=n)*width*(.08 if i<population//2 else .6)
   candidates.append(p.project(raw))
  X=np.array(candidates);scores=np.array([score(a) for a in X]);pb=X.copy();ps=scores.copy();velocity=np.zeros_like(X)
  for it in range(generations):
   if time.perf_counter()-start>deadline:timed_out=True;break
   ib=int(np.argmin(scores));best=X[ib].copy();bestJ=scores[ib]
   for i in range(population):
    if method.startswith('PSO'):
     velocity[i]=.7*velocity[i]+1.4*rng.random(n)*(pb[i]-X[i])+1.4*rng.random(n)*(best-X[i]);trial=p.project(X[i]+velocity[i])
    else:
     pool=np.delete(np.arange(population),i);a,b,c=rng.choice(pool,3,replace=False);mut=X[a]+.7*(X[b]-X[c]);mask=rng.random(n)<.8;mask[rng.integers(n)]=True;trial=p.project(np.where(mask,mut,X[i]))
    val=score(trial)
    if method.startswith('PSO') or val<scores[i]:X[i]=trial;scores[i]=val
    if val<ps[i]:pb[i]=trial;ps[i]=val
   nit+=1
  i=int(np.argmin(ps));best=pb[i].copy();bestJ=ps[i]
 success=True;message='global budget completed'
 if method=='SQP' or method.endswith('SQP'):
  def callback(q):
   if time.perf_counter()-start>deadline:raise TimeoutError('solver wall-clock budget')
  try:
   s=minimize(lambda q:p.evaluate(q)[0],best,jac=lambda q:p.evaluate(q)[1],method='SLSQP',bounds=p.bounds,
    constraints=[dict(type='ineq',fun=lambda q:p.evaluate(q)[2],jac=lambda q:p.evaluate(q)[3])],callback=callback,
    options=dict(maxiter=maxiter,ftol=1e-7,disp=False))
   q=p.project(s.x);value,cons=p.value(q);success=bool(s.success);message=str(s.message);nit+=s.nit
   # Retain the better feasible result; solver success is still separately logged.
   v0,c0=p.value(best)
   if np.min(cons)>=-1e-6 and (value<=v0 or np.min(c0)<-1e-6):best=q
  except TimeoutError:timed_out=True;success=False;message='deadline exceeded'
 value,con=p.value(best);feasible=bool(np.min(con)>=-1e-6 and np.isfinite(value))
 return dict(x=best,J=value,success=success,feasible=feasible,message=message,iterations=nit,evaluations=p.calls,
  model_steps=p.calls*57,derivative_evaluations=p.deriv_calls,global_evaluations=global_evals,seconds=time.perf_counter()-start,timed_out=timed_out,
  minimum_constraint=float(np.min(con)))
