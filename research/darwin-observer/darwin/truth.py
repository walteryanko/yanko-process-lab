"""Evaluator-only virtual plants. Never imported by discovery or observers."""
from dataclasses import dataclass
import numpy as np
from .physics import (njit,rhs_factors,legacy_rhs_factors,U0,LEGACY_U0,BASE,NP,DT,equilibrium)
from .data import Record

@njit(cache=True)
def hidden_rhs(x,u,law,strength,variant=0):
    p=np.zeros(NP);v=u[3]/453.6;ua=1.;kin=1.
    if law==1:ua=v**strength
    elif law==2:kin=np.exp(strength)
    elif law==3:kin=np.exp(strength*10.*(340./x[4]-1.))
    elif law==4:ua=np.exp(strength)
    elif law==5:kin=np.exp(strength*((x[4]-335.)/12.)**2)
    elif law==6:ua=1.+strength*np.tanh(1.6*np.log(v))
    if variant==1:return legacy_rhs_factors(x,u,p,ua,kin)
    return rhs_factors(x,u,p,ua,kin)

@njit(cache=True)
def hidden_step(x,u,law=0,strength=0.,dt=DT,variant=0):
    z=x.copy();h=dt/6
    for j in range(6):
        a=hidden_rhs(z,u,law,strength,variant);b=hidden_rhs(z+h*a/2,u,law,strength,variant)
        c=hidden_rhs(z+h*b/2,u,law,strength,variant);d=hidden_rhs(z+h*c,u,law,strength,variant)
        z+=h*(a+2*b+2*c+d)/6
    return z

@dataclass
class Episode:
    operational: Record
    truth: np.ndarray
    metadata: dict

SCENARIOS={
 'H0':dict(law=0,strength=0.),
 'A_mild':dict(law=1,strength=.15),
 'A_rich':dict(law=1,strength=.4),
 'A_weak':dict(law=1,strength=.4,excitation='weak'),
 'B_rate':dict(law=2,strength=.25),
 'B_activation':dict(law=3,strength=-.6),
 'B_curvature':dict(law=5,strength=.30),
 'C_bias':dict(law=0,strength=0.,sensor='bias'),
 'C_drift':dict(law=0,strength=0.,sensor='drift'),
 'C_noise':dict(law=0,strength=0.,sensor='noise'),
 'C_dropout':dict(law=0,strength=0.,sensor='dropout'),
 'C_UA':dict(law=4,strength=-.25),
 'D_feed':dict(law=1,strength=.4,regime='feed'),
 'D_flow':dict(law=1,strength=.4,regime='flow'),
 'D_composition':dict(law=1,strength=.4,regime='composition'),
 'D_noise':dict(law=1,strength=.4,sensor='noise'),
 'D_legacy':dict(law=1,strength=.4,variant=1),
 'X_saturation':dict(law=6,strength=.35,regime='flow'),
}

def generate(seed,scenario='H0',steps=120,dt=DT,overrides=None):
    cfg=dict(SCENARIOS[scenario]);cfg.update(overrides or {})
    variant=cfg.get('variant',0)
    rng=np.random.default_rng(seed);u=np.tile(LEGACY_U0 if variant else U0,(steps,1))
    for k in range(0,steps,10):
        lo,hi=(400,510) if cfg.get('excitation')=='weak' else (220,1050)
        if cfg.get('regime')=='flow':lo,hi=160,1230
        u[k:k+10,3]=rng.uniform(lo,hi)
        u[k:k+10,4]+=rng.uniform(-2.5,2.5)
        u[k:k+10,0]*=rng.uniform(.96,1.04)
    if cfg.get('regime')=='feed':u[:,4]+=4.
    if cfg.get('regime')=='composition':u[:,0]*=1.08;u[:,1]*=.95
    x=np.empty((steps+1,6));x[0]=equilibrium(LEGACY_U0 if variant else U0,variant=variant)
    x[0,:4]+=rng.normal(0,[.05,.4,.08,.06]);x[0,4:]+=rng.normal(0,.4,2)
    for k in range(steps):
        x[k+1]=hidden_step(x[k],u[k],cfg['law'],cfg['strength'],dt,variant)
    sd=.2 if cfg.get('sensor')!='noise' else .8
    z=x[:,4:]+rng.normal(0,sd,(steps+1,2))
    if cfg.get('sensor')=='bias':z[:,0]+=1.5
    if cfg.get('sensor')=='drift':z[:,1]+=1.8*np.arange(steps+1)*dt
    if cfg.get('sensor')=='dropout':z[rng.random(z.shape)<.22]=np.nan
    return Episode(Record(seed,u,z,dt),x,dict(scenario=scenario,noise_std=sd,synthetic=True,**cfg))
