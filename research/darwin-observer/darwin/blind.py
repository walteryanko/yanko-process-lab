"""Per-episode blinded diagnosis: fit <=60, validate 61..90, act >90.

The classifier receives a Record without a scenario name, failure label or truth.
Its episode-local holdout is predeclared; no refitting on final 91..120 outcomes.
"""
import numpy as np
from .identification import HYPOTHESES,fit,prediction
from .physics import Model
from .symbolic import physical_check
from .observers import observe,filter_step
from .detection import diagnose

def classify(record,threshold=12.,gate=True,physical=True,validate=True):
    prefix=record.prefix(60);nom=observe(record.prefix(90));diag=diagnose(nom,threshold)
    missing=float(np.mean(~np.isfinite(record.measurements[:91])))
    if missing>.12:return dict(label='sensor_availability',accepted=False,model=Model().as_dict(),ranking=[],diagnostic=diag)
    if diag['mean_nis']>7 and not diag['detected']:
        return dict(label='sensor_noise',accepted=False,model=Model().as_dict(),ranking=[],diagnostic=diag)
    names=['H0','UA_constant','UA_power','kinetic_rate','kinetic_activation','reaction_heat','sensor_bias','sensor_drift','feed_composition']
    ranking=[]
    for h in HYPOTHESES:
        if h.name not in names:continue
        f=fit(h,[prefix],max_nfev=45);m=f['model']
        pred=prediction(record.prefix(90),m.params)
        a,b=(61,91) if validate else (21,61)
        errors=(pred[a:b]-record.measurements[a:b])/.2
        loss=float(np.nanmean(errors**2));phys=physical_check(m,stress=False)
        eligible=(phys['valid'] or not physical) and f['success'] and f['identifiability']['rank']==len(h.indices)
        score=loss+.08*len(h.indices)
        ranking.append(dict(name=h.name,category=h.category,loss=loss,score=score,model=m.as_dict(),eligible=eligible))
    ranking.sort(key=lambda a:a['score']);null=next(x for x in ranking if x['name']=='H0')
    valid=[r for r in ranking if r['eligible']];best=valid[0] if valid else null
    gain=1-best['loss']/max(null['loss'],1e-12)
    accepted=best['name']!='H0' and gain>.20 and (diag['detected'] or not gate)
    # Preserve explanations from distinct families if out-of-sample scores tie.
    near=[r for r in valid if r['score']<=best['score']+max(.10,.05*best['score'])]
    categories={r['category'] for r in near}
    ambiguous=('sensor' in categories and len(categories)>1)
    if ambiguous:accepted=False
    if accepted:label='sensor' if best['category']=='sensor' else 'physics'
    elif ambiguous:label='ambiguous'
    elif diag['mean_nis']>7:label='sensor_noise'
    else:label='insufficient_evidence' if diag['detected'] else 'nominal'
    return dict(label=label,accepted=bool(accepted),model=(best if accepted else null)['model'],ranking=ranking,
                diagnostic=diag,gain=gain,ambiguous=ambiguous,activation_step=91)

def apply_after_validation(record,diagnosis):
    out=observe(record);m=Model.from_dict(diagnosis['model'])
    if not diagnosis['accepted']:return out
    x=out['x'][90].copy();p=out['cov'][90].copy()
    for k in range(91,len(record.measurements)):
        x,p,r,S,nis,xp=filter_step(x,p,record.inputs[k-1],record.measurements[k],m.params,record.dt,k*record.dt)
        out['x'][k]=x;out['cov'][k]=p;out['innovation'][k]=r;out['S'][k]=S;out['nis'][k]=nis;out['pred'][k]=xp
    return out
