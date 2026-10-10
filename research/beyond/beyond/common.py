from pathlib import Path
import json,hashlib,platform,sys,time,os
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
RESULTS=Path(os.environ.get('BEYOND_RESULTS',str(ROOT/'results')))
FIGURES=Path(os.environ.get('BEYOND_FIGURES',str(ROOT/'figures')))
RESULTS.mkdir(exist_ok=True,parents=True);FIGURES.mkdir(exist_ok=True,parents=True)
def dump(path,obj):
    def convert(x):
        if isinstance(x,np.ndarray):return x.tolist()
        if isinstance(x,np.generic):return x.item()
        if isinstance(x,Path):return str(x)
        raise TypeError(type(x))
    Path(path).write_text(json.dumps(obj,default=convert,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def frame(path,rows):pd.DataFrame(rows).to_csv(path,index=False)
def paired_ci(a,b,seed=55441,nboot=4000):
    a=np.asarray(a);b=np.asarray(b);diff=a-b;rng=np.random.default_rng(seed)
    vals=diff[rng.integers(0,len(a),(nboot,len(a)))].mean(axis=1)
    rel=100*(a.mean()/b.mean()-1) if abs(b.mean())>1e-12 else np.nan
    return dict(n=len(a),mean_a=a.mean(),mean_b=b.mean(),difference=diff.mean(),
                low=np.quantile(vals,.025),high=np.quantile(vals,.975),relative_percent=rel)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def metrics(model,X,U,reference=None,plant_parameters=None):
    x=X[1:];q=model.quality(x);dt=model.dt;ref=model.q0 if reference is None else reference
    e=q-ref;t=np.arange(1,len(q)+1)*dt
    prod=np.array([model.production(a,b) for a,b in zip(x,U)])
    P=np.tile(model.p0,(len(U),1)) if plant_parameters is None else np.asarray(plant_parameters)
    if P.ndim==1:P=np.tile(P,(len(U),1))
    heat=np.array([model.duty(a,b,p) for a,b,p in zip(x,U,P)])
    vol=np.array([model.dilution(u) for u in U])*model.constants['V']
    pp=dict(IAE=float(np.sum(abs(e))*dt),ISE=float(np.sum(e*e)*dt),ITAE=float(np.sum(t*abs(e))*dt),
        production_mean=float(prod.mean()),production_total=float(prod.sum()*dt),
        quality_mean=float(q.mean()),quality_sd=float(q.std()),Tmax=float(x[:,4].max()),Tmin=float(x[:,4].min()),
        heat_mean=float(heat.mean()),heat_total=float(heat.sum()*dt),feed_mean=float(U[:,0].mean()),
        cooling_mean=float(U[:,model.cidx].mean()),cooling_square_mean=float(np.mean((U[:,model.cidx]/model.u0[model.cidx])**2)),
        actuation_tv=float(np.abs(np.diff(U[:,model.controls]/model.u0[model.controls],axis=0)).sum()),
        violation_steps=int(np.sum((x[:,4]>model.tmax+1e-7)|(x[:,4]<model.tmin-1e-7))),
        thermal_margin=float(model.tmax-x[:,4].max()),min_concentration=float(x[:,:4].min()))
    if model.kind=='PG':
        pp.update(conversion=float(prod.sum()/U[:,0].sum()),selectivity=1.,byproduct_mean=0.)
    else:
        pp.update(conversion=float(1-np.sum(vol*x[:,0])/(np.sum(U[:,0])*model.constants['RHOS'][0]+np.sum(U[:,2])*model.constants['RECYCLE'][0])),
            selectivity=float(prod.sum()/(prod.sum()+np.sum(vol*x[:,3])+1e-30)),
            byproduct_mean=float(np.mean(vol*x[:,3])),byproduct_total=float(np.sum(vol*x[:,3])*dt))
    return pp

def slew_limit(model,U,initial=None):
    U=np.array(U,copy=True);prev=model.u0.copy() if initial is None else np.array(initial,copy=True)
    for i in range(len(U)):
        U[i]=np.clip(U[i],model.umin,model.umax)
        U[i]=prev+np.clip(U[i]-prev,-model.slew*model.dt,model.slew*model.dt)
        prev=U[i].copy()
    return U

def pareto(df,columns):
    a=df[columns].to_numpy();keep=np.ones(len(a),bool)
    for i in range(len(a)):keep[i]=not np.any(np.all(a<=a[i],axis=1)&np.any(a<a[i],axis=1))
    return keep
