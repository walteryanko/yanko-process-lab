"""Generate independent fixtures from the archived scientific implementations.
Run explicitly when recovering models. Fixtures are test expectations, never UI outputs.
"""
import importlib.util,sys,json,pathlib
import numpy as np
from scipy.integrate import solve_ivp
ROOT=pathlib.Path(__file__).resolve().parents[3]
cases=[]
for kind in ('pg','eb'):
 path=ROOT/'research/beyond/vendor'/f'{kind}_reference.py'
 spec=importlib.util.spec_from_file_location(kind,path);mod=importlib.util.module_from_spec(spec);sys.modules[kind]=mod;spec.loader.exec_module(mod)
 x=mod.steady()['x'] if kind=='pg' else mod.XSS
 u=mod.U0.copy();u[1 if kind=='pg' else 3]*=.97
 if kind=='pg':
  from dataclasses import replace
  params=replace(mod.Parameters(),T0=mod.Parameters().T0+1)
  fun=lambda t,z:mod.rhs(t,z,u,params)/3600
 else:
  u[4:]+=1
  fun=lambda t,z:np.asarray(mod.F(z,u,np.zeros(12))).ravel()/3600
 dt=54 if kind=='pg' else 72;ts=np.arange(9)*dt
 sol=solve_ivp(fun,(0,ts[-1]),x,method='DOP853',rtol=1e-12,atol=1e-13,t_eval=ts,max_step=1)
 assert sol.success
 cases.append(dict(model='pg-original' if kind=='pg' else 'eb-reduced',dt=dt,u=float(u[1 if kind=='pg' else 3]),disturbance=1,x0=x.tolist(),rhs=fun(0,x).tolist(),times=ts.tolist(),trajectory=sol.y.T.tolist(),source=str(path.relative_to(ROOT)),solver='SciPy DOP853 rtol=1e-12 atol=1e-13',tolerance=2e-6))
dest=ROOT/'packages/scientific-core/fixtures/reference.json';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps({'sourceCommit':'42a85b820740774729f3c28c4e402a3ddeeea52a','cases':cases},indent=2)+'\n')
print(dest)
