import numpy as np
from scipy.stats import wilcoxon
from .physics import Model,transition
from .discovery import paired_interval
from .detection import diagnose

def estimate_metrics(ep,result,model=None,threshold=12.):
    x=result['x'];truth=ep.truth;err=x-truth
    rmse=np.sqrt(np.mean(err**2,axis=0));late=np.sqrt(np.mean(err[20:]**2,axis=0))
    sd=np.sqrt(np.maximum(np.diagonal(result['cov'],axis1=1,axis2=2),0))
    coverage=np.mean(abs(err)<=1.96*sd,axis=0)
    d=diagnose(result,threshold);model=model or Model();forecast=[]
    for a in range(20,len(x)-10,20):
        z=x[a].copy()
        for j in range(10):z=transition(z,ep.operational.inputs[a+j],model.params,ep.operational.dt,3,model.variant)
        forecast.append(z[4:]-ep.operational.measurements[a+10])
    multi=float(np.sqrt(np.nanmean(np.array(forecast)**2))) if forecast else None
    return dict(**{'rmse_'+n:float(v) for n,v in zip(['CA','CB','CC','CM','T','Tt'],rmse)},
        rmse_CC_after_20=float(late[2]),coverage_CC=float(coverage[2]),coverage_T=float(coverage[4]),
        nis=d['mean_nis'],detected=d['detected'],detection_step=d['first_step'],
        ljung_box_p_T=d['ljung_box_p'][0],ljung_box_p_Tt=d['ljung_box_p'][1],
        forecast10_K=multi,ms_per_step=1000*result['seconds']/max(len(x)-1,1))

def summary(rows,primary='rmse_CC',baseline='UKF'):
    groups={};all_scenarios=sorted(set(r['scenario'] for r in rows))
    for s in all_scenarios:
        sub=[r for r in rows if r['scenario']==s];base={r['seed']:r[primary] for r in sub if r['method']==baseline}
        methods={}
        for m in sorted(set(r['method'] for r in sub)):
            a=[r for r in sub if r['method']==m];v=np.array([r[primary] for r in a]);b=np.array([base[r['seed']] for r in a]);delta=b-v
            ci=paired_interval(delta);gain=float(100*np.mean(delta)/max(np.mean(b),1e-15))
            p=float(wilcoxon(delta,zero_method='pratt').pvalue) if np.any(abs(delta)>1e-12) else 1.
            methods[m]=dict(n=len(a),mean=float(v.mean()),std=float(v.std(ddof=1)) if len(v)>1 else 0.,mean_CI=paired_interval(v),
                gain_percent=gain,paired_difference=float(delta.mean()),paired_CI=ci,p_value=p,
                wins=int(np.sum(delta>1e-12)),coverage_CC=float(np.mean([r.get('coverage_CC',np.nan) for r in a])),
                detection_rate=float(np.mean([r.get('detected',False) for r in a])))
        groups[s]=methods
    # Holm controls comparisons of the predeclared Darwin method vs UKF across scenarios.
    entries=sorted([(v['Darwin']['p_value'],s) for s,v in groups.items() if 'Darwin' in v]);running=0.
    for i,(p,s) in enumerate(entries):
        running=max(running,min(1.,p*(len(entries)-i)));groups[s]['Darwin']['p_holm']=running
    return groups
