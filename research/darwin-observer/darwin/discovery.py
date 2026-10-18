"""Auditable state machine with explicit null, holdout and reversal."""
from dataclasses import asdict
import hashlib,json,time
import numpy as np
from .physics import Model,NP
from .data import assert_disjoint
from .observers import observe,OnlineUKF
from .detection import diagnose
from .identification import HYPOTHESES,Hypothesis,fit,residual_vector
from .symbolic import weak_jacket,equations,physical_check

def paired_interval(values,seed=61017,draws=2000):
    a=np.asarray(values,float);rng=np.random.default_rng(seed)
    if not len(a):return [None,None]
    b=np.mean(a[rng.integers(0,len(a),(draws,len(a)))],axis=1)
    return np.quantile(b,[.025,.975]).tolist()

def discover(train,validation,threshold=12.,allowed=None,gate=True,physical=True,holdout=True,variant=0,observer_options=None):
    assert_disjoint(train,validation);events=[];start=time.perf_counter()
    def event(state,details):events.append(dict(order=len(events),state=state,details=details,elapsed_seconds=time.perf_counter()-start))
    event('OBSERVE',dict(episodes=len(train),fingerprints=[r.fingerprint() for r in train]))
    ds=[diagnose(observe(r,Model(variant=variant),**(observer_options or {})),threshold) for r in train]
    evidence=sum(d['detected'] for d in ds)>=max(1,len(ds)//3)
    event('DETECT',dict(persistent=evidence,diagnostics=ds))
    weak=weak_jacket(train,variant=variant);hypotheses=HYPOTHESES if allowed is None else [h for h in HYPOTHESES if h.name in allowed]
    if allowed is None and 0<len(weak['terms'])<=4:
        inds=tuple(sorted(set([0]+weak['terms'])))
        hypotheses=hypotheses+[Hypothesis('UA_sparse',inds,'structure','sparse weak-balance proposal','term independence and holdout prediction')]
    event('HYPOTHESIZE',dict(names=[h.name for h in hypotheses],unfitted_alternative='H8 extra dynamics remain possible; not uniquely diagnosed',weak_proposal=weak))
    ranking=[];fits={};nobs=sum(np.isfinite(r.measurements[20:]).sum() for r in validation)
    scoring=validation if holdout else train
    for h in hypotheses:
        f=fit(h,train,initial=weak['coefficients']+[0.]*(NP-6) if h.name=='UA_sparse' else None,variant=variant,observer_options=observer_options);m=f['model'];fits[h.name]=f
        errors=[float(np.mean(residual_vector([r],m.params,variant=variant,observer_options=observer_options)**2)) for r in scoring]
        phys=physical_check(m)
        rank_ok=f['identifiability']['rank']==len(h.indices) and f['identifiability']['condition']<1e5
        penalty=.025*len(h.indices)+np.log(max(nobs,2))*len(h.indices)/max(nobs,1)
        score=float(np.mean(errors))+penalty
        ranking.append(dict(name=h.name,category=h.category,statement=h.statement,conditions=h.conditions,indices=list(h.indices),
            train_mse=f['train_mse'],validation_mse=float(np.mean(errors)),validation_episodes=errors,score=score,complexity=len(h.indices),
            model=m.as_dict(),identifiability=f['identifiability'],physical=phys,optimization_success=f['success'],nfev=f['nfev'],
            eligible=(phys['valid'] or not physical) and rank_ok and f['success'],equations=equations(m),equation_export_version=2))
    event('DISCOVER',dict(candidates=len(ranking),training_only=True))
    ranking.sort(key=lambda a:a['score']);nom=next(r for r in ranking if r['name']=='H0')
    eligible=[r for r in ranking if r['eligible']];best=eligible[0] if eligible else nom
    gain=(nom['validation_mse']-best['validation_mse'])/max(nom['validation_mse'],1e-12)
    diff=np.array(nom['validation_episodes'])-best['validation_episodes'];ci=paired_interval(diff)
    accepted=best['name']!='H0' and gain>=.10 and ci[0]>0 and (evidence or not gate)
    plausible=[r['name'] for r in eligible if r['score']<=best['score']+max(.05,.03*best['validation_mse'])]
    reason='validated predictive correction; physical uniqueness not established' if accepted else 'insufficient independent evidence; retain null'
    event('CHALLENGE',dict(physical_checks=True,prolonged_integration_hours=6.,plausible_hypotheses=plausible))
    event('VALIDATE',dict(relative_gain=gain,paired_CI=ci,min_gain=.10,gate=evidence,independent=holdout))
    selected=best if accepted else nom
    for r in ranking:
        r['status']='accepted' if r['name']==selected['name'] and accepted else ('retained_null' if r['name']=='H0' and not accepted else 'rejected_or_ambiguous')
        r['reason']=reason if r['name']==selected['name'] else ('physical or rank gate failed' if not r['eligible'] else 'lower validation evidence or competing equivalent explanation')
    event('ACCEPT' if accepted else 'REJECT',dict(selected=selected['name'],reason=reason));event('MONITOR',dict(fallback='nominal',rolling_window=20,loss_ratio=1.2))
    ident=hashlib.sha256('|'.join(r.fingerprint() for r in train+validation).encode()).hexdigest()[:16]
    return dict(id=ident,version='1.1.0' if variant else '1.0.0',model_variant='historical-SI-complete' if variant else 'ProcessLab-tabulated-f4444d4',accepted=accepted,selected=selected['name'],
                category=selected['category'],reason=reason,model=selected['model'],best_unrestricted=best['name'],
                plausible=plausible,ranking=ranking,events=events,weak_proposal=weak,relative_gain=gain,paired_CI=ci,
                train_seeds=[r.seed for r in train],validation_seeds=[r.seed for r in validation],execution_seconds=time.perf_counter()-start)

class GuardedDarwin:
    """Online causal shadow-model monitoring. Current sample can trigger rollback;
    it cannot improve its own prior prediction. A new equation is accepted only
    through approve() with independently validated past completed episodes.
    """
    def __init__(self,discovery=None,monitor=True,nominal_model=None,observer_options=None):
        self.base_model=nominal_model or Model()
        self.nominal=OnlineUKF(self.base_model,**(observer_options or {}));self.active=OnlineUKF(self.base_model,**(observer_options or {}));self.accepted=False;self.monitor=monitor
        self.nom_losses=[];self.active_losses=[];self.events=[];self.k=0;self.fallbacks=0
        if discovery:self.approve(discovery)
    def approve(self,discovery):
        if not discovery.get('accepted'):return False
        if not discovery.get('paired_CI') or discovery['paired_CI'][0]<=0:return False
        if discovery.get('relative_gain',0)<.10:return False
        if not discovery.get('train_seeds') or not discovery.get('validation_seeds'):return False
        if set(discovery['train_seeds'])&set(discovery['validation_seeds']):return False
        m=Model.from_dict(discovery['model'])
        if m.variant!=self.base_model.variant:return False
        if not physical_check(m)['valid']:return False
        # Preserve current state/covariance when updating a running observer.
        self.active.model=m;self.accepted=True;self.events.append(dict(step=self.k,state='ACCEPT',id=discovery['id']))
        return True
    def revert(self,reason):
        self.accepted=False;self.active.model=self.base_model;self.active.x=self.nominal.x.copy();self.active.P=self.nominal.P.copy()
        self.fallbacks+=1;self.events.append(dict(step=self.k,state='REVERT',reason=reason))
    def update(self,u,y,dt=.015):
        self.k+=1;xn,dn=self.nominal.update(u,y,dt)
        if self.accepted and not self.active.model.supports(self.active.x,u):self.revert('outside validated envelope')
        if not self.accepted:
            self.active.x=self.nominal.x.copy();self.active.P=self.nominal.P.copy();self.active.t=self.nominal.t
            return xn,dn
        try:xa,da=self.active.update(u,y,dt)
        except (ValueError,FloatingPointError,np.linalg.LinAlgError):self.revert('numeric failure');return xn,dn
        self.nom_losses.append(float(np.nanmean(dn['innovation']**2)));self.active_losses.append(float(np.nanmean(da['innovation']**2)))
        if self.monitor and len(self.active_losses)>=20:
            n=np.nanmean(self.nom_losses[-20:]);a=np.nanmean(self.active_losses[-20:])
            if a>1.2*n+.01:self.revert('rolling prediction loss worse than nominal');return xn,dn
        return xa,da
