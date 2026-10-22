"""M3 is a barycentric entropic particle transform, NOT a diffusion bridge."""
import numpy as np
from scipy.special import logsumexp
from scipy.spatial.distance import cdist
from .probability import moments

def sinkhorn(cost,a,b,epsilon=.05,tol=1e-8,max_iter=1000):
    cost=np.asarray(cost,float);a=np.asarray(a,float);b=np.asarray(b,float)
    if epsilon<=0 or np.any(a<0) or np.any(b<0) or not np.isclose(a.sum(),1) or not np.isclose(b.sum(),1):
        raise ValueError('Invalid transport marginals/epsilon')
    if cost.shape!=(len(a),len(b)) or not np.all(np.isfinite(cost)): raise ValueError('Invalid cost')
    ia=a>0;ib=b>0;c=cost[np.ix_(ia,ib)];aa=a[ia];bb=b[ib]
    k=-c/epsilon;lv=np.zeros(len(bb));la=np.log(aa);lb=np.log(bb)
    err=np.inf
    for it in range(1,max_iter+1):
        lu=la-logsumexp(k+lv[None,:],axis=1)
        lv=lb-logsumexp(k+lu[:,None],axis=0)
        if it%5==0 or it==max_iter:
            plan=np.exp(lu[:,None]+k+lv[None,:]);err=max(np.max(np.abs(plan.sum(1)-aa)),np.max(np.abs(plan.sum(0)-bb)))
            if err<tol:break
    out=np.zeros_like(cost);out[np.ix_(ia,ib)]=plan
    return out,dict(iterations=it,marginal_error=float(err),converged=bool(err<tol),
                    mass=float(out.sum()),cost=float(np.sum(out*cost)),epsilon=float(epsilon))

def transform(x,w,scales,epsilon=.05,tol=1e-8,max_iter=1000):
    n=len(x);cost=cdist(x/scales,x/scales,'sqeuclidean')
    plan,diag=sinkhorn(cost,w,np.full(n,1/n),epsilon,tol,max_iter)
    if not diag['converged']: raise ArithmeticError('Sinkhorn marginal tolerance not reached')
    # Rows are weighted source atoms, columns uniform target labels.
    new=n*plan.T@x
    m,c=moments(x,w);mn,cn=moments(new,np.full(n,1/n))
    diag.update(mean_error=float(np.max(np.abs(mn-m))),
                variance_ratio=float(np.trace(cn/np.outer(scales,scales))/max(np.trace(c/np.outer(scales,scales)),1e-20)))
    return new,plan,diag
