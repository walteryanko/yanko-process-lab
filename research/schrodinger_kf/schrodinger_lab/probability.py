"""Numerically stable probabilistic primitives; no truth-state dependency."""
import numpy as np
from scipy.special import logsumexp, gammaln
from scipy.spatial.distance import cdist

def normalize(logw):
    logw=np.asarray(logw,float)
    z=logsumexp(logw)
    if not np.isfinite(z): raise FloatingPointError('All posterior weights invalid')
    w=np.exp(logw-z);return w/w.sum()

def ess(w):
    w=np.asarray(w,float)
    if np.any(w<0) or not np.isclose(w.sum(),1): raise ValueError('Weights must sum to one')
    return float(1/np.sum(w*w))

def systematic(w,rng,n=None):
    n=len(w) if n is None else int(n)
    ess(w)
    return np.minimum(np.searchsorted(np.cumsum(w),(rng.random()+np.arange(n))/n),len(w)-1)

def moments(x,w):
    mean=w@x;d=x-mean
    return mean,(d*w[:,None]).T@d

def spd(a,floor=1e-12):
    a=(a+a.T)/2;v,q=np.linalg.eigh(a)
    return (q*np.maximum(v,floor))@q.T

def weighted_quantile(x,w,qs):
    order=np.argsort(x);s=np.cumsum(w[order]);
    return np.interp(qs,s,x[order],left=x[order[0]],right=x[order[-1]])

def gaussian_logpdf(res,R):
    inv=np.linalg.inv(R);d=R.shape[0]
    return -.5*(np.einsum('...i,ij,...j->...',res,inv,res)+np.linalg.slogdet(R)[1]+d*np.log(2*np.pi))

def loglik(x,y,R,kind='gaussian'):
    mask=np.isfinite(y)
    if not np.any(mask):return np.zeros(len(x))
    res=x[:,4:6][:,mask]-np.asarray(y)[mask];cov=R[np.ix_(mask,mask)]
    if kind=='student':
        nu=3.;d=mask.sum();q=np.einsum('ni,ij,nj->n',res,np.linalg.inv(cov),res)
        return gammaln((nu+d)/2)-gammaln(nu/2)-.5*(d*np.log(nu*np.pi)+np.linalg.slogdet(cov)[1])-(nu+d)/2*np.log1p(q/nu)
    if kind=='mixture':
        return np.logaddexp(np.log(.94)+gaussian_logpdf(res,cov),np.log(.06)+gaussian_logpdf(res,100*cov))
    return gaussian_logpdf(res,cov)

def robust_cov(res,cov,pred_cov,kind):
    """One-step covariance-matched robust Gaussian approximation, shared UKF/EnKF.
    Student t uses an innovation scale mixture approximation, not exact Bayes.
    """
    q=float(res@np.linalg.solve(pred_cov+cov,res));d=len(res)
    if kind=='student': return cov*max(1.,(3+q)/(3+d))
    if kind=='mixture':
        l0=np.log(.94)+gaussian_logpdf(res,pred_cov+cov)
        l1=np.log(.06)+gaussian_logpdf(res,pred_cov+100*cov)
        p=float(np.exp(l1-np.logaddexp(l0,l1)))
        return cov*(1+99*p)
    return cov

def crps_ensemble(x,w,y):
    order=np.argsort(x);xx=x[order];ww=w[order]
    cum=np.cumsum(ww)-ww;cx=np.cumsum(ww*xx)-ww*xx
    half_pair=np.sum(ww*(xx*cum-cx))
    return float(np.sum(w*np.abs(x-y))-half_pair)

def energy_score(x,w,y,scales):
    z=x/scales;truth=y/scales
    return float(w@np.linalg.norm(z-truth,axis=1)-.5*w@cdist(z,z)@w)

def non_gaussianity(x,w):
    m,p=moments(x,w);d=x-m;v=np.maximum(np.diag(p),1e-14)
    kurt=np.sum(w[:,None]*d**4,axis=0)/v**2
    skew=np.sum(w[:,None]*d**3,axis=0)/v**1.5
    return float(max(np.max(np.abs(kurt-3)),np.max(np.abs(skew))))
