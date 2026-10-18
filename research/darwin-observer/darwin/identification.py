"""Constrained output-error fits using operational data only.

Unmeasured initial concentrations use a shared prior, never true states.
Discarding the first 0.30 h reduces dependence on that prior. This does NOT
establish global structural identifiability; singular values are local evidence.
"""
from dataclasses import dataclass
import numpy as np
from scipy.optimize import least_squares
from .physics import Model,BASE,NP,PARAM_NAMES,simulate
from .observers import run_numeric,observe

@dataclass(frozen=True)
class Hypothesis:
    name: str
    indices: tuple
    category: str
    statement: str
    conditions: str

HYPOTHESES=[
 Hypothesis('H0',(),'null','nominal physics and unbiased sensors','nominal noise model adequate'),
 Hypothesis('UA_constant',(0,),'parameter','constant UA differs','thermal transient'),
 Hypothesis('UA_linear',(0,1),'structure','log UA depends linearly on normalized coolant flow','persistent mw excitation'),
 Hypothesis('UA_power',(0,2),'structure','UA is a power of normalized coolant flow','wide mw excitation'),
 Hypothesis('UA_quadratic',(0,1,3),'structure','curvature in log UA versus flow','at least three separated flow levels'),
 Hypothesis('UA_reciprocal',(0,4),'structure','inverse-flow dependence','broad mw domain'),
 Hypothesis('UA_sqrt',(0,5),'structure','square-root flow dependence','broad mw domain'),
 Hypothesis('kinetic_rate',(6,),'kinetic','constant rate multiplier','known heat and feed; chemistry observable aggregate'),
 Hypothesis('kinetic_activation',(6,7),'kinetic','centered Arrhenius correction','broad reactor temperature range'),
 Hypothesis('reaction_heat',(8,),'thermal','reaction heat differs','independence from kinetic effects'),
 Hypothesis('feed_composition',(9,),'feed','FA calibration differs','known other flows'),
 Hypothesis('sensor_bias',(10,11),'sensor','constant temperature sensor bias','transient and independent thermal balance'),
 Hypothesis('sensor_drift',(10,11,12),'sensor','linear Tt sensor drift','long observation period'),
 Hypothesis('thermal_capacity',(13,),'thermal','effective heat capacity differs','thermal transient'),
 Hypothesis('feed_temperature',(14,),'feed','feed temperature bias','independent input calibration'),
 Hypothesis('joint_UA_kinetic',(0,6,7),'joint','competing UA and Arrhenius errors','joint sensitivity rank required'),
]
LOW=np.array([-.55,-.7,-.8,-.6,-.7,-1.,-.6,-1.2,-.15,-.2,-3.,-3.,-3.,-.25,-5.])
HIGH=-LOW

def prediction(record,params,variant=0,observer_options=None):
    # Initialization from a causal 0.30 h commissioning prefix. No validation
    # targets after this prefix are used to initialize or update the forecast.
    n=min(20,len(record.inputs))
    init=observe(record.prefix(n),Model(params,variant=variant),**(observer_options or {}))['x']
    tail=simulate(init[-1],record.inputs[n:],params,record.dt,3,variant)
    states=np.vstack([init[:-1],tail])
    out=states[:,4:]+params[10:12]
    out[:,1]+=params[12]*np.arange(len(out))*record.dt
    return out

def residual_vector(records,params,burn=20,start=None,end=None,variant=0,observer_options=None):
    out=[]
    for rec in records:
        yp=prediction(rec,params,variant,observer_options);z=rec.measurements
        a=burn if start is None else start;b=len(z) if end is None else end
        sigma=np.sqrt((observer_options or {}).get('measurement_variance',np.array([.04,.04])))
        d=(yp[a:b]-z[a:b])/sigma;mask=np.isfinite(z[a:b]);d=d[mask]
        if not np.all(np.isfinite(d)):d=np.full(len(d),1e6)
        out.append(d)
    return np.concatenate(out)

def fit(hyp,records,max_nfev=70,burn=20,initial=None,variant=0,observer_options=None):
    idx=list(hyp.indices);p=np.zeros(NP)
    if not idx:return dict(model=Model(p,hyp.name,variant),hypothesis=hyp,train_mse=float(np.mean(residual_vector(records,p,burn,variant=variant,observer_options=observer_options)**2)),success=True,nfev=0,identifiability=dict(rank=0,condition=1.,std=[],singular_values=[]))
    def fn(a):
        pp=np.zeros(NP);pp[idx]=a
        return residual_vector(records,pp,burn,variant=variant,observer_options=observer_options)
    x0=np.zeros(len(idx)) if initial is None else np.clip(np.asarray(initial)[idx],LOW[idx]+1e-6,HIGH[idx]-1e-6)
    opt=least_squares(fn,x0,bounds=(LOW[idx],HIGH[idx]),max_nfev=max_nfev,loss='soft_l1',f_scale=2.,diff_step=2e-4,ftol=2e-6,xtol=2e-6,gtol=2e-5)
    p[idx]=opt.x
    # Whitened sensitivity/Fisher diagnostic; numerical rank is scale-relative.
    J=opt.jac;s=np.linalg.svd(J,compute_uv=False);rank=int(np.sum(s>max(s[0]*1e-4,1e-8)))
    sigma2=float(np.sum(opt.fun**2)/max(len(opt.fun)-len(idx),1))
    cov=np.linalg.pinv(J.T@J,rcond=1e-8)*sigma2
    se=np.sqrt(np.maximum(np.diag(cov),0.))
    info=dict(rank=rank,condition=float(s[0]/max(s[-1],1e-12)),std=se.tolist(),singular_values=s.tolist(),
              parameters=[PARAM_NAMES[i] for i in idx],correlation=(cov/np.maximum(np.outer(se,se),1e-15)).tolist(),
              caveat='local, conditional on initial-state prior and model; not global uniqueness')
    return dict(model=Model(p,hyp.name,variant),hypothesis=hyp,train_mse=float(np.mean(opt.fun**2)),success=bool(opt.success),nfev=int(opt.nfev),identifiability=info)

def local_observability(x,u,steps=20,dt=.015):
    scale=np.array([.1,1.,.1,.1,1.,1.]);cols=[]
    inp=np.tile(u,(steps,1));p=np.zeros(NP)
    for j in range(6):
        e=scale[j]*1e-3;a=x.copy();b=x.copy();a[j]+=e;b[j]-=e
        cols.append(((simulate(a,inp,p,dt)[:,4:]-simulate(b,inp,p,dt)[:,4:])/(2*e)*scale[j]).ravel())
    S=np.column_stack(cols);sv=np.linalg.svd(S,compute_uv=False)
    return dict(singular_values=sv.tolist(),rank=int(np.sum(sv>sv[0]*1e-7)),scales=scale.tolist())
