"""Evaluator-only scenarios: hidden parameters never enter operational Observation."""
import numpy as np
from .physics import *
KINDS=['quiet','heat_ramp','cooling_loss','feed_pulse','feed_step','UA_loss','colored','drift','setpoint','temporary_saturation','oscillation','kinetics']

def specification(seed,steps=160,adversarial=False):
    rng=np.random.default_rng(seed);kind=KINDS[seed%len(KINDS)];known=np.tile(U0,(steps,1));actual=known.copy();params=np.tile(P,(steps,1));sp=np.full(steps,BASE[2]);on=int(rng.integers(50,65));amp=float(rng.uniform(.8,1.2));z=np.arange(steps);ramp=np.clip((z-on)/45,0,1)
    if kind=='heat_ramp':actual[:,4]+=amp*20*ramp
    if kind=='cooling_loss':actual[:,3]=np.maximum(55,U0[3]*(1-.82*amp*ramp))
    if kind=='feed_pulse':actual[:,4]+=amp*17*((z>=on)&(z<on+22))
    if kind=='feed_step':actual[:,0]*=1+.26*amp*(z>=on)
    if kind=='UA_loss':params[:,13]*=1-.65*amp*ramp
    if kind=='setpoint':sp+=.32*ramp
    if kind=='temporary_saturation':actual[:,3]=np.where((z>=on)&(z<on+16),90.,U0[3])
    if kind=='oscillation':actual[:,3]=np.clip(U0[3]+amp*180*np.sin(z*.33),UMIN,UMAX)
    if kind=='kinetics':params[:,9]*=1+.30*amp*ramp
    # Most feeds are known through their commands, but hidden offsets and UA are not.
    if kind in ['feed_step','feed_pulse']:known[:,[0,4]]=actual[:,[0,4]]
    if kind in ['cooling_loss','temporary_saturation','oscillation']:known[:,3]=actual[:,3]  # measured applied flow
    if kind=='setpoint':actual[:,3]=known[:,3]=np.clip(U0[3]-180*ramp,UMIN,UMAX)
    params[:,13]*=rng.uniform(.97,1.03);actual[:,4]+=rng.normal(0,.3)
    noise=rng.normal(0,[1.385/1.8,1.062/1.8],(steps,2))
    if kind=='colored' or adversarial:
        rho=.88 if kind=='colored' else .55
        for k in range(1,steps):noise[k]=rho*noise[k-1]+np.sqrt(1-rho*rho)*noise[k]
    bias=np.zeros((steps,2))
    if kind=='drift':bias[:,0]=amp*6*ramp;bias[:,1]=-amp*1.5*ramp
    if adversarial:noise*=1.5
    x=BASE.copy();x[:4]+=rng.normal(0,[.05,.15,.08,.04]);x[4:]+=rng.normal(0,.25,2)
    return dict(seed=seed,kind=kind,known=known,actual=actual,params=params,noise=noise,bias=bias,initial=x,sp=sp,onset=on)

def open_loop(spec):
    x=spec['initial'].copy();states=[]
    for u,p in zip(spec['actual'],spec['params']):
        x=step(x,u,p,n=6)
        if not physical(x):raise ValueError('Plant integration outside domain')
        states.append(x.copy())
    states=np.array(states);return states,states[:,4:]+spec['noise']+spec['bias']
