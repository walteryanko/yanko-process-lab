"""Innovation diagnostics; a discrepancy is NOT a diagnosis of faulty physics."""
import numpy as np
from scipy.stats import chi2

def diagnose(result,threshold=12.,window=20):
    r=result['innovation'];S=result['S'];z=np.full_like(r,np.nan)
    for j in range(2):z[:,j]=r[:,j]/np.sqrt(np.maximum(S[:,j,j],1e-12))
    stats=[];first=None;cusum=0.
    for k in range(1,len(z)):
        a=z[max(1,k-window+1):k+1];nn=np.sum(np.isfinite(a),axis=0)
        if np.min(nn)<window*.6:continue
        mu=np.nansum(a,axis=0)/np.maximum(nn,1)
        stat=float(np.sum(mu**2*nn))
        if np.any(np.isfinite(z[k])):cusum=max(0.,cusum+float(np.nanmean(z[k]**2))-1.5)
        stats.append((k,stat,cusum))
        if first is None and stat>threshold:first=k
    ac=[];pvals=[]
    for j in range(2):
        v=z[1:,j];v=v[np.isfinite(v)];v=v-v.mean() if len(v) else v
        rho=[]
        for lag in range(1,6):
            rho.append(float(np.dot(v[:-lag],v[lag:])/max(np.dot(v,v),1e-15)) if len(v)>lag else 0.)
        n=len(v);q=n*(n+2)*sum(a*a/max(n-k-1,1) for k,a in enumerate(rho))
        ac.append(rho);pvals.append(float(chi2.sf(q,5)))
    return dict(detected=first is not None,first_step=first,threshold=threshold,
                max_stat=max([s[1] for s in stats],default=0.),cusum_max=max([s[2] for s in stats],default=0.),
                autocorrelation=ac,ljung_box_p=pvals,
                missing_fraction=float(np.mean(~np.isfinite(r[1:]))),
                mean_nis=float(np.mean(result['nis'][1:])),
                interpretation='discrepancy only; noise, sensor and physical causes compete')

def calibrate_threshold(nominal_results,quantile=.99):
    values=[diagnose(r,threshold=float('inf'))['max_stat'] for r in nominal_results]
    # Independent episodes calibrate the maximum-over-time statistic.
    return float(max(12.,np.quantile(values,quantile))),values
