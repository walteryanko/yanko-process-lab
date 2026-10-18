"""Campaign B targets disappearance of the low-temperature PG equilibrium.
This is a distinct label from the 344 K thermal crossing used in campaigns C-F.
"""
from pathlib import Path
import json
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import root
from scipy.special import expit
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from .physics import *
from .observer import UKF,Observation
from .ews import EWS,indicators
from .detectors import Features
from .stability import refine_fold,reactive_alpha
from .evaluation import alarm_metrics,aggregate,paired_ci,probability_metrics
from .io import save,csv_write

def trajectory(seed,fold,steps=700,window=64,rate=1.,noise_scale=1.,colored=False,control=False):
    steps=int(np.ceil(steps/max(rate,1e-3))) if rate<1. else steps
    rng=np.random.default_rng(seed);positive=seed%2==0;u0=U0.copy();u0[4]=294.8;x=equilibria(u0)[0].copy();obs=UKF(x=x,mode='historical');ews=EWS(window);rows=[];ev=None;cross=None;tempnoise=np.zeros(2);proc=0.
    end=fold['parameter']+.30 if positive else fold['parameter']-rng.uniform(.05,.2)
    duration=10./rate
    for k in range(steps):
        t=k*DT;uu=U0.copy();uu[4]=294.8+(end-294.8)*min(t/duration,1.)
        if control:uu[3]+=20*np.sin(t*6)  # imposed causal coolant oscillation stress, no future access
        actual=uu.copy();proc=.7*proc+rng.normal(0,.018);actual[4]+=proc
        x=step(x,actual,n=6)
        rho=.85 if colored else 0.;tempnoise=rho*tempnoise+np.sqrt(1-rho*rho)*rng.normal(0,[.2,.15])*noise_scale
        y=x[4:]+tempnoise;xh,Pc=obs.advance(uu,y);d=ews.update(y[0],obs.innov[0])
        critical_feed=refine_fold([fold['T'],fold['parameter']],u=uu)['parameter'] if control else fold['parameter']
        if ev is None and uu[4]>=critical_feed:ev=k # bifurcation of deterministic mean-input frozen family
        if cross is None and x[4]>=fold['T']+3:cross=k
        f=[d['ac1'],np.log(max(d['variance'],1e-9)),d['trend'],reactive_alpha(xh,uu),np.sqrt(Pc[4,4]),obs.nis]
        rows.append(dict(t_h=(k+1)*DT,T=x[4],CC=x[2],T0=uu[4],T0_actual=actual[4],yT=y[0],xhat_T=xh[4],ac1=d['ac1'],variance=d['variance'],recovery=d['recovery'],alpha=reactive_alpha(xh,uu),alpha_truth_frozen=reactive_alpha(x,actual),features=f))
    label=np.zeros(steps,int);H=80;valid=np.arange(steps)+H<steps;valid[:window]=False
    if ev is not None:
        ix=np.arange(steps);label[(ix<ev)&(ix+H>=ev)]=1;valid &= ix<ev
    return dict(seed=seed,positive=positive,event=ev,transition=cross,rows=rows,features=np.array([r['features'] for r in rows]),label=label,valid=valid,
        thermal_event=bool(max(r['T'] for r in rows)>344.),window=window,rate=rate,noise_scale=noise_scale,colored=colored,control=control)

def supplemental_critical_points(out):
    # Detect all folds by arclength tangent reversal, including unstable-to-unstable folds.
    mapping=json.loads((Path(out).parent/'A/map.json').read_text());critical=[]
    for name,d in mapping.items():
        kind=d['kind'];key=d['key'];rr=d['rows'];sign=np.sign(np.diff([r['parameter'] for r in rr]));idx=np.flatnonzero(sign[:-1]*sign[1:]<0)+1
        def make(v):
            u=U0.copy();p=P.copy()
            if kind=='u':u[key]=v
            else:p[key]=v
            return u,p
        sc=max(abs(rr[0]['parameter']),1.)
        def equations(z,which='fold'):
            T,q=z;u,p=make(q*sc)
            if u[3]<=0:return [1e6,1e6]
            v=heat(T,u,p)
            if which=='fold':w=(heat(T+.001,u,p)-heat(T-.001,u,p))/.002
            else:
                J=jacobian(mass_ss(T,u,p),u,p);w=J[0,0]+J[4,4]
            return [v,w]
        for i in idx:
            r=rr[i];sol=root(equations,[r['T'],r['parameter']/sc],tol=1e-10);T,q=sol.x;u,p=make(q*sc);eig=np.linalg.eigvals(jacobian(mass_ss(T,u,p),u,p))
            h=.001;curvature=(heat(T+h,u,p)-2*heat(T,u,p)+heat(T-h,u,p))/h**2
            eps=1e-5;fparam=(equations([T,q+eps])[0]-equations([T,q-eps])[0])/(2*eps*sc)
            if np.linalg.norm(equations(sol.x))<1e-6:critical.append(dict(axis=name,type='saddle_node',T=T,parameter=q*sc,residual=np.linalg.norm(equations(sol.x)),smallest_eigenvalue=float(min(abs(eig))),second_derivative=curvature,parameter_derivative=fparam,verified=bool(abs(curvature)>1e-6 and abs(fparam*sc)>1e-6),eig_real=eig.real,eig_imag=eig.imag))
        # Pair crossing traced independently of alpha switching to passive Tt mode.
        for c in d['candidates']:
            if c['type']=='hopf_candidate':
                guess=np.mean([c['left'],c['right']],axis=0);sol=root(lambda z:equations(z,'hopf'),[guess[0],guess[1]/sc],tol=1e-10);T,q=sol.x;u,p=make(q*sc);eig=np.linalg.eigvals(jacobian(mass_ss(T,u,p),u,p));complex_eig=eig[np.abs(eig.imag)>.001]
                if len(complex_eig) and np.linalg.norm(equations(sol.x,'hopf'))<1e-6:
                    critical.append(dict(axis=name,type='hopf_linear_candidate',T=T,parameter=q*sc,residual=np.linalg.norm(equations(sol.x,'hopf')),frequency_rad_h=abs(complex_eig[0].imag),eig_real=eig.real,eig_imag=eig.imag,verified=False,limitation='Imaginary pair verified; first Lyapunov coefficient and nonlinear Hopf type not established.'))
    save(Path(out).parent/'A/critical_points.json',critical)
    return critical

def campaign_B(out,n=100):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);critical=supplemental_critical_points(out);fold=refine_fold([309,295.5])
    # Train/cal/test independent episodes; probability target is mean-input fold crossing, not thermal event.
    sets=[]
    for label,base,count in [('train',60000,80),('calibration',61000,40),('test',62000,n)]:
        eps=[]
        for i in range(count):eps.append(trajectory(base+i,fold))
        sets.append(eps);print(json.dumps(dict(stage='B',split=label,n=count)),flush=True)
    train,cal,test=sets
    X=np.vstack([e['features'][e['valid']] for e in train]);y=np.concatenate([e['label'][e['valid']] for e in train]);scaler=StandardScaler().fit(X)
    m=LogisticRegression(C=.2,max_iter=500,random_state=13).fit(scaler.transform(X),y)
    Xc=np.vstack([e['features'][e['valid']] for e in cal]);yc=np.concatenate([e['label'][e['valid']] for e in cal]);raw=m.decision_function(scaler.transform(Xc))
    calibrator=LogisticRegression(C=1000,max_iter=500).fit(raw[:,None],yc)
    model=dict(target='mean-input loss of low-temperature equilibrium within 80 samples (72 min); not thermal exceedance',features=['ac1','log_variance','trend','reactive_alpha_estimated','sigma_T','nis'],mean=scaler.mean_,scale=scaler.scale_,coef=m.coef_[0],intercept=m.intercept_[0],cal_a=calibrator.coef_[0,0],cal_b=calibrator.intercept_[0])
    save(out/'bifurcation_probability.json',model)
    def probabilities(e):return calibrator.predict_proba(m.decision_function(scaler.transform(e['features']))[:,None])[:,1]
    def scores(e):
        f=e['features'];return {'thermal_342':np.array([r['yT']-342 for r in e['rows']]),'EWS':f[:,0]+.12*f[:,1],'spectral':f[:,3],'hybrid_probability':probabilities(e)}
    th={'thermal_342':0.};selection={}
    for name in ['EWS','spectral','hybrid_probability']:
        allscores=np.concatenate([scores(e)[name][e['valid']] for e in cal]);candidates=np.unique(np.r_[np.quantile(allscores,np.linspace(0,1,51)),allscores.max()+1e-6]);possible=[]
        for v in candidates:
            a=aggregate([alarm_metrics(scores(e)[name],e['event'],e['valid'],v,H=80) for e in cal])
            if a['false_alarms_per_h']<=.2:possible.append(((a['recall'] or 0,-a['false_alarms_per_h'],-v),v,a))
        _,v,a=max(possible,key=lambda z:z[0]);th[name]=v;selection[name]=a
    rows=[];summary={}
    for name in th:
        rr=[dict(seed=e['seed'],detector=name,**alarm_metrics(scores(e)[name],e['event'],e['valid'],th[name],H=80)) for e in test];rows+=rr;summary[name]=aggregate(rr)
    prob=probability_metrics(np.concatenate([e['label'][e['valid']] for e in test]),np.concatenate([probabilities(e)[e['valid']] for e in test]))
    # Predetermined sensitivity combinations, no threshold re-tuning on test.
    sensitivity=[];stress_traces=[]
    settings=[(24,1.,1.,False,False),(128,1.,1.,False,False),(64,2.,1.,False,False),(64,.5,1.,False,False),(64,1.,2.,False,False),(64,1.,1.,True,False),(64,1.,1.,False,True)]
    for j,(window,rate,noise,colored,control) in enumerate(settings):
        eps=[trajectory(63000+j*100+i,fold,window=window,rate=rate,noise_scale=noise,colored=colored,control=control) for i in range(12)]
        for name in th:
            a=aggregate([alarm_metrics(scores(e)[name],e['event'],e['valid'],th[name],H=80) for e in eps]);sensitivity.append(dict(setting=j,window=window,rate=rate,noise=noise,colored=colored,control=control,detector=name,**a))
        stress_traces.append(eps[0]);print(json.dumps(dict(stage='B_sensitivity',setting=j)),flush=True)
    # Measured return rate from an infinitesimal slow eigenmode perturbation at static equilibria.
    recovery=[]
    for feed in np.linspace(294.8,fold['parameter']-.0005,24):
        u=U0.copy();u[4]=feed;x=equilibria(u)[0];A=jacobian(x,u);e,V=np.linalg.eig(A);i=np.argmax(e.real);delta=V[:,i].real;delta*=.001/np.linalg.norm(delta/SCALE)
        sol=solve_ivp(lambda t,z:rhs(z,u),[0,2],x+delta,t_eval=np.linspace(0,2,101),rtol=1e-10,atol=1e-11);dist=np.linalg.norm((sol.y.T-x)/SCALE,axis=1);rate_fit=-np.polyfit(sol.t[:50],np.log(np.maximum(dist[:50],1e-14)),1)[0]
        recovery.append(dict(T0=feed,T=x[4],alpha=e.real.max(),expected_recovery=-e.real.max(),fitted_recovery=rate_fit))
    csv_write(out/'recovery.csv',recovery);csv_write(out/'metrics.csv',rows);csv_write(out/'sensitivity.csv',sensitivity);save(out/'sensitivity.json',sensitivity);save(out/'summary.json',summary);save(out/'probability.json',prob);save(out/'thresholds.json',th);save(out/'traces.json',test[:4]+stress_traces)
    save(out/'execution.json',dict(train=80,calibration=40,test=n,sensitivity=84,steps=700,fold=fold,thermal_events_in_test=sum(e['thermal_event'] for e in test),fold_events=sum(e['event'] is not None for e in test),observed_transitions=sum(e['transition'] is not None for e in test),target_limitation='Event is frozen deterministic mean-input fold; noisy plant can tip earlier or later. Oscillatory coolant sensitivity recomputes the instantaneous mean-input fold. Slow ramps run longer to reach the same endpoint.'))
    return summary
