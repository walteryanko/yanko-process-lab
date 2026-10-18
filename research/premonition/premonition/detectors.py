import json
from pathlib import Path
import numpy as np
from scipy.special import expit
from .physics import *
from .ews import EWS
from .stability import reactive_alpha
from .observer import Observation
from .io import save
FEATURES=['T','Tt','trend','predicted_peak','alpha_reactive','alpha_full','quasisteady_residual','sigma_T','sigma_CC','nis','ac1','log_variance','residual_ac1','log_residual_variance','low_frequency','mw_fraction','cooling_headroom','recovery']
NOEWS=[0,1,2,3,4,5,6,7,8,9,15,16]

@njit(cache=True)
def prediction(x,u,n=20):
    z=x.copy();peak=x[4]
    for _ in range(n):
        z=step(z,u);peak=max(peak,z[4])
        if not physical(z):return 500.
    return peak

class Features:
    def __init__(self,window=32):self.ews=EWS(window)
    def update(self,obs:Observation):
        d=self.ews.update(obs.y[0],obs.innovation[0]);x=obs.xhat;u=obs.u
        ar=reactive_alpha(x,u);af=spectral_abscissa(x,u);peak=prediction(x,u)
        res=float(np.linalg.norm(rhs(x,u)/SCALE));std=np.sqrt(np.maximum(np.diag(obs.covariance),0))
        f=np.array([obs.y[0],obs.y[1],d['trend'],peak,ar,af,res,std[4],std[2],obs.nis,d['ac1'],np.log(max(d['variance'],1e-9)),d['residual_ac1'],np.log(max(d['residual_variance'],1e-9)),d['low_frequency'],u[3]/UMAX,(UMAX-u[3])/UMAX,d['recovery']])
        return np.nan_to_num(f,nan=0.,posinf=500.,neginf=-500.),d

class PortableModel:
    """JSON-only inference: histogram gradient boosting distilled to explicit tree arrays.
    No pickle loading, no hidden state access. Platt scaling is calibration-set only.
    """
    def __init__(self,data):self.d=data
    def score(self,X):
        X=np.atleast_2d(X)[:,self.d['features']]
        if self.d['type']=='logistic':return (X-np.array(self.d['mean']))/np.array(self.d['scale'])@np.array(self.d['coef'])+self.d['intercept']
        pred=np.full(len(X),self.d['base'])
        for tree in self.d['trees']:
            for i,row in enumerate(X):
                k=0
                while tree['left'][k]!=-1:
                    k=tree['left'][k] if row[tree['feature'][k]]<=tree['threshold'][k] else tree['right'][k]
                pred[i]+=self.d['learning_rate']*tree['value'][k]
        return pred
    def predict(self,X):return expit(self.d.get('cal_a',1)*self.score(X)+self.d.get('cal_b',0))

def train_model(X,y,Xcal,ycal,kind='boost',indices=None):
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.ensemble import GradientBoostingClassifier
    indices=list(range(X.shape[1])) if indices is None else list(indices)
    a=X[:,indices]
    if len(np.unique(y))<2:raise ValueError('Both event classes required')
    if kind=='logistic':
        scaler=StandardScaler().fit(a);m=LogisticRegression(C=.2,max_iter=500,random_state=13).fit(scaler.transform(a),y)
        d=dict(type='logistic',features=indices,mean=scaler.mean_,scale=scaler.scale_,coef=m.coef_[0],intercept=m.intercept_[0])
    else:
        m=GradientBoostingClassifier(n_estimators=55,max_depth=2,min_samples_leaf=60,learning_rate=.06,random_state=13).fit(a,y)
        trees=[]
        for tr in m.estimators_[:,0]:
            t=tr.tree_;trees.append(dict(left=t.children_left,right=t.children_right,feature=t.feature,threshold=t.threshold,value=t.value[:,0,0]))
        prior=float(m.init_.class_prior_[1]);d=dict(type='boost',features=indices,base=float(np.log(prior/(1-prior))),learning_rate=.06,trees=trees)
    from .io import clean
    d=clean(d);model=PortableModel(d)
    raw=model.score(Xcal)
    if len(np.unique(ycal))>=2:
        cal=LogisticRegression(C=1e3,max_iter=500,random_state=13).fit(raw[:,None],ycal);d.update(cal_a=float(cal.coef_[0,0]),cal_b=float(cal.intercept_[0]))
    d['feature_names']=[FEATURES[i] for i in indices];d['target']='first thermal crossing T>344K within 20 future samples under generating policy; not accident probability'
    return PortableModel(d)

class Detectors:
    def __init__(self,models=None,thresholds=None):self.features=Features();self.models=models or {};self.thresholds=thresholds or {};self.failures=0
    def update(self,obs):
        f,d=self.features.update(obs)
        # D0: thermal threshold plus short (3.6 min) trend extrapolation.
        scores={'D0':max(f[0]-342.,f[0]+.06*max(f[2],0)-344.),'D1':f[3]-344.,'D2':f[10]+.12*f[11],
                'D3':f[4] if f[6]<1. else -100.}
        for name,m in self.models.items():
            try:
                v=float(m.predict(f)[0]);scores[name]=v if np.isfinite(v) else np.nan
            except Exception:scores[name]=np.nan;self.failures+=1
        alarms={name:bool(np.isfinite(v) and v>=self.thresholds.get(name,0. if name in ['D0','D1'] else -.8 if name=='D3' else .5)) for name,v in scores.items()}
        if not d['valid']:alarms['D2']=False
        return dict(features=f,ews=d,scores=scores,alarms=alarms,insufficient_evidence=not any(alarms.values()))

def load_models(path):
    path=Path(path);return {name:PortableModel(json.loads((path/f'{name}.json').read_text())) for name in ['D4','D5','D5_noEWS']}
