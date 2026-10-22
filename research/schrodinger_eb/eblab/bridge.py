"""Schrödinger–Föllmer diffusion, distinct from Sinkhorn transforms.

Bao & Sun arXiv:2512.18928v1 eqs (3.9),(3.12),(3.13); Sun v4 retains
the same core. bandwidth=0 is the published empirical drift. bandwidth>0
implements the EXACT drift for a continuous Gaussian-kernel target. The SDE
integration and empirical posterior approximation remain approximate.
"""
import numpy as np
from scipy.special import softmax

def drift(x,t,z,logw,bandwidth=0.,block=128):
    """Reference dV=dW, V0=0. Target sum_j wj N(zj,h² I).
    D=1-t+t*h²; logits=logw + (x.z - t*||z||²/2)/D.
    alpha=(E[z|x,t]-(1-h²)*x)/D. h=0 recovers eq (3.9).
    """
    if not 0<=t<1 or bandwidth<0: raise ValueError('Invalid bridge time/bandwidth')
    den=1-t+t*bandwidth**2;zz=np.sum(z*z,axis=1);out=np.empty_like(x)
    for a in range(0,len(x),block):
        xx=x[a:a+block];logits=logw+(xx@z.T-.5*t*zz)/den
        weights=softmax(logits,axis=1)
        out[a:a+block]=(weights@z-(1-bandwidth**2)*xx)/den
    return out

def generate(x,w,rng,steps=64,bandwidth=.05,grid='quadratic',save_path=False):
    """Affine coordinates fixed from FORECAST particles, never true states.
    Physical diagonal prior std makes Brownian reference anisotropic in SI.
    Path time tau is auxiliary, NOT future observation time.
    """
    if steps<2 or len(x)<2:raise ValueError('Insufficient bridge discretization')
    center=np.mean(x,axis=0);scale=np.maximum(np.std(x,axis=0),1e-7)
    z=(x-center)/scale
    logw=np.full(len(w),-np.inf);positive=w>0;logw[positive]=np.log(w[positive])
    ts=np.linspace(0,1,steps+1)
    if grid=='quadratic': ts=1-(1-ts)**2
    elif grid!='uniform':raise ValueError('Unknown diffusion grid')
    v=np.zeros_like(x);path=[v.copy()] if save_path else []
    for t,tn in zip(ts[:-1],ts[1:]):
        dt=tn-t;v+=drift(v,t,z,logw,bandwidth)*dt+np.sqrt(dt)*rng.normal(size=v.shape)
        if save_path:path.append(v.copy())
    result=center+scale*v
    diag=dict(steps=steps,bandwidth=bandwidth,grid=grid,
              target='weighted Gaussian KDE' if bandwidth else 'empirical approximation',
              start=center.tolist(),diffusion_scale=scale.tolist(),
              mean_shift=float(np.linalg.norm((result.mean(0)-w@x)/scale)),
              target_trace=float(np.sum(w[:,None]*(z-w@z)**2)+len(scale)*bandwidth**2),
              generated_trace=float(np.var(v,axis=0).sum()))
    return result,diag,(center+scale*np.array(path) if save_path else None)
