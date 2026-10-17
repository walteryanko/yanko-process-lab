"""Non-symbolic thermal residual baselines trained ONLY from jacket balance.

RBF ridge and a small MLP predict log UA from the same operational records.
No hidden concentrations, rates or plant parameters are training labels.
"""
import warnings
import numpy as np
from sklearn.neural_network import MLPRegressor
from sklearn.exceptions import ConvergenceWarning
from .physics import CP,RHO,VT,UA,U0,NP,BASE,njit
from .observers import filter_step,P6

def weak_targets(records,block=10):
    X=[];Y=[]
    for rec in records:
        y=rec.measurements;u=rec.inputs
        for a in range(0,len(u)-block+1,block):
            b=a+block;w=u[a,3]
            if not np.all(np.isfinite(y[a:b+1])) or np.ptp(u[a:b,3])>1e-4:continue
            T=(y[a:b,0]+y[a+1:b+1,0])/2;Tt=(y[a:b,1]+y[a+1:b+1,1])/2;Ta=u[a:b,5]
            value=RHO[1]*VT*CP[1]*(y[b,1]-y[a,1])-rec.dt*np.sum(w*CP[1]*(Ta-Tt))
            den=rec.dt*np.sum(T-Ta);G=value/max(den,1e-8)
            ratio=G/(w*CP[1])
            if .02<ratio<.98:
                ua=-w*CP[1]*np.log1p(-ratio);target=np.log(ua/UA)
                if abs(target)<1.:X.append([np.log(w/U0[3])]);Y.append(target)
    return np.array(X),np.array(Y)

def rbf_features(x,centers,width=.4):
    return np.c_[np.ones(len(x)),np.exp(-((x-centers[None,:])/width)**2)]

def fit_baselines(records):
    X,Y=weak_targets(records)
    if len(X)<15:return dict(available=False,reason='insufficient integral balance labels')
    centers=np.linspace(-1.,1.,10);A=rbf_features(X,centers)
    w=np.linalg.solve(A.T@A+.8*np.eye(A.shape[1]),A.T@Y)
    mlp=MLPRegressor(hidden_layer_sizes=(12,8),activation='tanh',solver='lbfgs',alpha=.5,max_iter=350,random_state=971)
    with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter('always',ConvergenceWarning);mlp.fit(X,Y)
    return dict(available=True,labels=len(Y),centers=centers.tolist(),weights=w.tolist(),
        mlp_weights=[a.tolist() for a in mlp.coefs_],mlp_biases=[a.tolist() for a in mlp.intercepts_],
        convergence_warnings=[str(x.message) for x in ws],training_source='weak jacket integral; operational measurements only')

def parameters(inputs,artifact,kind):
    X=np.log(inputs[:,3:4]/U0[3]);P=np.zeros((len(inputs),NP))
    if not artifact.get('available'):return P
    if kind=='rbf':out=rbf_features(X,np.array(artifact['centers']))@np.array(artifact['weights'])
    else:
        out=X
        for j,(w,b) in enumerate(zip(artifact['mlp_weights'],artifact['mlp_biases'])):
            out=out@np.array(w)+np.array(b)
            if j<len(artifact['mlp_weights'])-1:out=np.tanh(out)
        out=out.ravel()
    P[:,0]=np.clip(out,-.65,.65)
    return P

@njit(cache=True)
def run_residual(inputs,y,params,dt):
    x=BASE.copy();p=np.diag(P6);n=len(y)
    for j in range(2):
        if np.isfinite(y[0,j]):
            gain=p[4+j,4+j]/(p[4+j,4+j]+.04);x[4+j]+=gain*(y[0,j]-x[4+j]);p[4+j,4+j]*=(1-gain)
    xs=np.empty((n,6));ps=np.empty((n,6,6));r=np.full((n,2),np.nan);S=np.full((n,2,2),np.nan);nis=np.zeros(n);pred=np.empty((n,6))
    xs[0]=x;ps[0]=p;pred[0]=x
    for k in range(1,n):
        x,p,r[k],S[k],nis[k],pred[k]=filter_step(x,p,inputs[k-1],y[k],params[k-1],dt,k*dt)
        xs[k]=x;ps[k]=p
    return xs,ps,r,S,nis,pred

def observe_residual(record,artifact,kind='rbf'):
    import time
    t=time.perf_counter();P=parameters(record.inputs,artifact,kind)
    xs,p,r,S,nis,pred=run_residual(record.inputs,record.measurements,P,record.dt)
    return dict(x=xs,cov=p,innovation=r,S=S,nis=nis,pred=pred,seconds=time.perf_counter()-t)
