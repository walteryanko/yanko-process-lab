import numpy as np
from sklearn.metrics import average_precision_score,brier_score_loss,precision_recall_curve
from scipy.stats import beta
from .physics import DT

def event_index(T,limit=344.):
    ix=np.flatnonzero(np.asarray(T)>limit);return int(ix[0]) if len(ix) else None

def future_labels(T,H=20):
    T=np.asarray(T);e=event_index(T);valid=np.arange(len(T))+H<len(T)
    if e is not None:valid &= np.arange(len(T))<e
    label=np.zeros(len(T),int)
    if e is not None:label[(np.arange(len(T))<e)&(np.arange(len(T))+H>=e)]=1
    return label,valid,e

def alarm_metrics(score,e,valid,threshold,H=20):
    score=np.asarray(score);valid=np.array(valid,bool);alarm=np.isfinite(score)&(score>=threshold)&valid
    onset=alarm&~np.r_[False,alarm[:-1]]
    # Persistent alarm started too early is false; no retrospective credit at horizon entry.
    onset_ix=np.flatnonzero(onset)
    true_onsets=[int(k) for k in onset_ix if e is not None and 0<e-k<=H]
    false_onsets=len(onset_ix)-len(true_onsets)
    detected=bool(true_onsets)
    return dict(event=int(e is not None),detected=int(detected),missed=int(e is not None and not detected),false_onsets=false_onsets,true_onsets=len(true_onsets),
        exposure_h=float(valid.sum()*DT),lead_min=(e-min(true_onsets))*DT*60 if detected else None,redundant=max(0,len(true_onsets)-1))

def aggregate(rows):
    events=sum(r['event'] for r in rows);hits=sum(r['detected'] for r in rows);fp=sum(r['false_onsets'] for r in rows);tp=sum(r['true_onsets'] for r in rows);exposure=sum(r['exposure_h'] for r in rows);leads=[r['lead_min'] for r in rows if r['lead_min'] is not None]
    return dict(n_trajectories=len(rows),events=events,detected=hits,missed=events-hits,recall=hits/events if events else None,precision=tp/(tp+fp) if tp+fp else None,false_alarms_per_h=fp/exposure if exposure else None,false_onsets=fp,exposure_h=exposure,lead_median_min=float(np.median(leads)) if leads else None,lead_min=leads,redundant=sum(r['redundant'] for r in rows),
        recall_exact_ci=[float(beta.ppf(.025,hits,events-hits+1)) if hits else 0.,float(beta.ppf(.975,hits+1,events-hits)) if hits<events else 1.] if events else None)

def probability_metrics(y,p):
    y=np.asarray(y);p=np.clip(p,1e-8,1-1e-8);pr,rc,th=precision_recall_curve(y,p);bins=[]
    for a in np.linspace(0,.9,10):
        m=(p>=a)&(p<a+.1000001)
        if m.any():bins.append(dict(n=int(m.sum()),pred=float(p[m].mean()),observed=float(y[m].mean()),lo=float(a)))
    return dict(n=int(len(y)),prevalence=float(y.mean()),brier=float(brier_score_loss(y,p)),brier_constant=float(np.mean((y-y.mean())**2)),average_precision=float(average_precision_score(y,p)) if y.sum() else None,
        ece=float(sum(b['n']*abs(b['pred']-b['observed']) for b in bins)/len(y)),reliability=bins,pr_precision=pr[::max(1,len(pr)//150)],pr_recall=rc[::max(1,len(rc)//150)])

def paired_ci(a,b,seed=713,n=2000):
    d=np.asarray(b)-np.asarray(a);rng=np.random.default_rng(seed);means=np.mean(d[rng.integers(0,len(d),(n,len(d)))],axis=1)
    return dict(n=len(d),mean_difference=float(d.mean()),ci95=np.quantile(means,[.025,.975]),median_difference=float(np.median(d)),fraction_negative=float(np.mean(d<0)),direction='B minus A; negative is favorable only for metrics to be minimized')

def choose_threshold(episodes,key,max_far=.5):
    scores=np.concatenate([e['scores'][key][e['valid']] for e in episodes]);scores=scores[np.isfinite(scores)]
    candidates=np.unique(np.r_[np.quantile(scores,np.linspace(0,1,61)),scores.max()+1e-6])
    choices=[]
    for th in candidates:
        rows=[alarm_metrics(e['scores'][key],e['event'],e['valid'],th) for e in episodes];agg=aggregate(rows)
        if agg['false_alarms_per_h']<=max_far:choices.append(((agg['recall'] or 0,-agg['false_alarms_per_h'],-th),float(th),agg))
    if not choices:return float('inf'),{'abstained':True}
    _,th,agg=max(choices,key=lambda a:a[0]);return th,agg
