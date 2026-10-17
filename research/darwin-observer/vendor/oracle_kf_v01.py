"""ORACLE-KF Lab v0.1 | causal student distilled from offline UKF/RTS teacher.

Six-state propylene-glycol CSTR. Model coefficients from
walteryanko/yanko-process-lab main/lib/simulation/model.ts (read 2026-10-16).
Uses only T and Tt as online observations. All results synthetic, research use only.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, time
from pathlib import Path
import numpy as np
from scipy.optimize import brentq
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor

CP=np.array([146.5,75.4,192.6,81.6]); RHO=np.array([14.8,55.3,24.7]); E=75362.4; RG=8.314; K0=16.96e12
HEAT=91556.9; V=1.89; VT=1.1; UA=30385.6
U0=np.array([36.3,453.6,45.4,453.6,297.,289.]); DT=.015
Q=np.array([5.616e-8,5.616e-5,5.616e-8,2.4246e-13,.0346356,.00666123])
NOISE_STD=.35 # kelvin; experiment selection, not historical ProcessLab 1%
P0=np.diag([.19**2,.19**2,.19**2,.08**2,.9**2,.9**2]); R=np.diag([NOISE_STD**2]*2)
H=np.zeros((2,6)); H[0,4]=H[1,5]=1.
AXIS=np.array([1.,1.,-1.,0.,0.,0.]); WIN=6

def deriv(x,u,ua=UA,heat=HEAT):
    flow=u[...,0]/RHO[0]+u[...,1]/RHO[1]+u[...,2]/RHO[2]
    r=K0*np.exp(-E/(RG*x[...,4]))*x[...,0]
    q=u[...,3]*CP[1]*(u[...,5]-x[...,4])*(-np.expm1(-ua/(u[...,3]*CP[1])))
    cap=V*np.sum(x[...,:4]*CP,axis=-1)
    sens=(u[...,0]*CP[0]+u[...,1]*CP[1]+u[...,2]*CP[3])*(x[...,4]-u[...,4])
    out=np.empty_like(x)
    out[...,0]=(u[...,0]-flow*x[...,0])/V-r
    out[...,1]=(u[...,1]-flow*x[...,1])/V-r
    out[...,2]=r-flow*x[...,2]/V
    out[...,3]=(u[...,2]-flow*x[...,3])/V
    out[...,4]=(q-sens+heat*r*V)/cap
    out[...,5]=(u[...,3]*CP[1]*(u[...,5]-x[...,5])-q)/(RHO[1]*VT*CP[1])
    return out

def step(x,u,dt=DT,substep=.0025,ua=UA,heat=HEAT):
    """Vectorized nonlinear RK4. Substep adjustable; fidelity test vs 0.001 h."""
    x=np.asarray(x,float).copy();u=np.asarray(u,float)
    n=max(1,int(np.ceil(dt/substep))); h=dt/n
    for _ in range(n):
        k1=deriv(x,u,ua,heat);k2=deriv(x+.5*h*k1,u,ua,heat)
        k3=deriv(x+.5*h*k2,u,ua,heat);k4=deriv(x+h*k3,u,ua,heat)
        x=x+h*(k1+2*k2+2*k3+k4)/6
    return x

def equilibrium():
    u=U0;v=u[0]/RHO[0]+u[1]/RHO[1]+u[2]/RHO[2]
    def xof(t):
        k=K0*np.exp(-E/(RG*t));ca=u[0]/(v+V*k);cc=V*k*ca/v
        q=u[3]*CP[1]*(u[5]-t)*(-np.expm1(-UA/(u[3]*CP[1])))
        return np.array([ca,u[1]/v-cc,cc,u[2]/v,t,u[5]-q/(u[3]*CP[1])])
    roots=[]
    for a in np.arange(260,400,.5):
        fa=deriv(xof(a),u)[4];fb=deriv(xof(a+.5),u)[4]
        if fa*fb<0:roots.append(brentq(lambda t:deriv(xof(t),u)[4],a,a+.5))
    if not roots: raise RuntimeError('No PG equilibrium')
    return xof(max(roots))
BASE=equilibrium()

def sigma_points(x,p,alpha=.5):
    n=6;lam=alpha*alpha*n-n;c=n+lam
    l=np.linalg.cholesky(c*((p+p.T)/2+np.eye(n)*1e-11))
    s=np.concatenate((x[None,:],x[None,:]+l.T,x[None,:]-l.T))
    wm=np.full(13,1/(2*c));wc=wm.copy()
    wm[0]=lam/c;wc[0]=wm[0]+1-alpha*alpha+2
    return s,wm,wc

def assimilate_initial(x,p,z):
    S=H@p@H.T+R
    K=np.linalg.solve(S,(p@H.T).T).T
    out=x+K@(z-H@x);A=np.eye(6)-K@H
    return out,(A@p@A.T+K@R@K.T)

def ukf_transition(x,p,u,z):
    """One step causal UKF, plus cross-cov for legitimate offline RTS smoothing."""
    sig,w,wc=sigma_points(x,p)
    pr=step(sig,np.broadcast_to(u,sig.shape))
    xp=np.sum(pr*w[:,None],axis=0)
    d=pr-xp
    pp=np.einsum('i,ij,ik->jk',wc,d,d)+np.diag(Q)
    cross=np.einsum('i,ij,ik->jk',wc,sig-x,pr-xp)
    S=H@pp@H.T+R
    K=np.linalg.solve(S,(pp@H.T).T).T
    innov=z-H@xp
    xf=xp+K@innov
    A=np.eye(6)-K@H
    pf=A@pp@A.T+K@R@K.T
    pf=(pf+pf.T)/2
    return xf,pf,xp,pp,cross,innov

def oracle_smoother(xf,xpred,pp,cross):
    """UKF-RTS teacher. Uses future x[k+1:] measurements; NEVER used in online features."""
    xs=xf.copy()
    for k in range(len(xs)-2,-1,-1):
        gain=np.linalg.solve(pp[k+1]+1e-10*np.eye(6),cross[k+1].T).T
        xs[k]=xf[k]+gain@(xs[k+1]-xpred[k+1])
    return xs

def generate(seed:int,steps=48,stress=False,matched=False):
    rng=np.random.default_rng(int(seed))
    true=np.empty((steps+1,6)); z=np.empty((steps+1,2)); u=np.empty((steps,6))
    true[0]=BASE.copy()
    delta=rng.normal(0,.14 if not stress else .21)
    delta=np.clip(delta,-.27,.31)
    true[0]+=delta*AXIS
    true[0,3]+=rng.normal(0,.045)
    true[0,4:6]+=rng.normal(0,.4 if not stress else .7,2)
    ua_rel=0. if matched else rng.normal(0,.07 if not stress else .16)
    true_heat=HEAT if matched else HEAT*(1+rng.normal(0,.012 if not stress else .035))
    unknown_t0_bias=0. if matched else rng.normal(0,1.25 if not stress else 3.3)
    block=0.; pulse=0. if matched else rng.choice([-1,1])*rng.uniform(0,1.5 if not stress else 4.0)
    for k in range(steps):
        if k%5==0: block=.58*block+.42*rng.normal(0,280 if not stress else 400)
        mw=float(np.clip(453.6+block,135,1160))
        obs_u=U0.copy();obs_u[3]=mw
        if k>=steps//3 and k<steps//3+8: obs_u[0]*=1.04 if not stress else 1.08
        if k>=steps//2: obs_u[4]+= (1.0 if not stress else 2.5)
        # FA and commanded Tfeed are available to estimators.  Unknown Tfeed bias isn't.
        u[k]=obs_u
        actual_u=obs_u.copy();actual_u[4]+=unknown_t0_bias+pulse*(k>=steps//2)
        true[k+1]=step(true[k],actual_u,ua=UA*(1+ua_rel),heat=true_heat)
    z=true[:,4:6]+rng.normal(0,NOISE_STD,(steps+1,2))
    return {'seed':seed,'true':true,'z':z,'u':u,'ua_error':ua_rel,'unknown_T0':unknown_t0_bias,'stress':stress,'heat_error':true_heat/HEAT-1.,'matched':matched}

def observe(ep):
    n=len(ep['z']);xf=np.empty((n,6));cov=np.empty((n,6,6))
    xpred=np.empty_like(xf);pp=np.empty_like(cov);cross=np.zeros_like(cov);innov=np.zeros((n,2))
    xf[0],cov[0]=assimilate_initial(BASE.copy(),P0.copy(),ep['z'][0]);xpred[0]=BASE;pp[0]=P0
    for k in range(1,n):
        xf[k],cov[k],xpred[k],pp[k],cross[k],innov[k]=ukf_transition(xf[k-1],cov[k-1],ep['u'][k-1],ep['z'][k])
    xs=oracle_smoother(xf,xpred,pp,cross)
    ep.update({'filtered':xf,'smooth':xs,'cov':cov,'innovation':innov})
    return ep

def features(ep):
    """Only current/past measurements, prior controls, current causal UKF and its diagnostics."""
    xf=ep['filtered'];z=ep['z'];U=ep['u'];r=ep['innovation'];p=ep['cov'];n=len(z)
    feats=[]
    for k in range(n):
        f=list(xf[k])+list(z[k])+list(np.log10(np.maximum(np.diag(p[k]),1e-15)))+[k*DT]
        for j in range(WIN):
            h=max(k-j,0)
            f+=list(r[h] if k>=j else np.zeros(2))
            f+=list(z[h]-BASE[4:6])
            f+=[float(U[h-1,3]) if h>0 else U0[3]]
        # history indicators and action history; these are available by time k.
        f.append(min(k,WIN)/WIN)
        feats.append(f)
    return np.array(feats)

def build(ntrain=70,nval=24,ntest=28,steps=48,seed=4701):
    rng=np.random.default_rng(seed)
    split={}
    for name,n in [('train',ntrain),('val',nval),('test',ntest)]:
        # genuine held-out episodes; stress mix only in test, not for teacher selection
        split[name]=[observe(generate(int(s),steps,stress=(name=='test' and i>=n//2),matched=(name!='test' or i<n//2))) for i,s in enumerate(rng.integers(1,2**31-1,size=n))]
    return split

def pack(episodes):
    X=np.concatenate([features(e) for e in episodes]);y=np.concatenate([(e['smooth']-e['filtered'])[:,2] for e in episodes])
    return X,y

def train_models(episodes,validation):
    X,y=pack(episodes);Xv,yv=pack(validation);scaler=StandardScaler();Xt=scaler.fit_transform(X);Xvt=scaler.transform(Xv)
    models={
        'Ridge':Ridge(alpha=100),
        'ExtraTrees':ExtraTreesRegressor(n_estimators=70,max_depth=11,min_samples_leaf=8,max_features=.8,n_jobs=1,random_state=43),
        'HistGB':HistGradientBoostingRegressor(max_iter=140,max_leaf_nodes=15,l2_regularization=5.0,learning_rate=.055,min_samples_leaf=35,random_state=43),
    }
    selection=[]; best=(float('inf'),None,None,None)
    for name,model in models.items():
        model.fit(Xt,y);v=model.predict(Xvt)
        for shrink in (.25,.5,.75,1.):
            score=float(np.sqrt(np.mean((yv-shrink*v)**2)))
            selection.append({'model':name,'shrink':shrink,'validation_teacher_RMSE':score})
            if score<best[0]:best=(score,name,shrink,model)
    return scaler,best[3],best[1],best[2],selection

def evaluate(splits,scaler,model,shrink,store=6):
    per=[];traces=[]
    for group,eps in splits.items():
        for ix,ep in enumerate(eps):
            y=ep['true'][:,2];ukf=ep['filtered'][:,2];teacher=ep['smooth'][:,2]
            predict=model.predict(scaler.transform(features(ep)))
            student=np.maximum(1e-7,ukf+shrink*predict)
            ep['student_cc']=student
            vals={'split':group,'trial':ix,'seed':int(ep['seed']),'stress':bool(ep['stress']),
                  'ukf_rmse':float(np.sqrt(np.mean((ukf-y)**2))),
                  'teacher_rmse':float(np.sqrt(np.mean((teacher-y)**2))),
                  'student_rmse':float(np.sqrt(np.mean((student-y)**2))),
                  'ukf_mae':float(np.mean(np.abs(ukf-y))),
                  'teacher_mae':float(np.mean(np.abs(teacher-y))),
                  'student_mae':float(np.mean(np.abs(student-y))),
                  'ua_error':float(ep['ua_error']),'unknown_T0':float(ep['unknown_T0']),'heat_error':float(ep['heat_error']),'matched':bool(ep['matched']),
                  'max_T':float(np.max(ep['true'][:,4]))}
            per.append(vals)
            if group=='test' and ix<store:
                traces.append({'trial':ix,'stress':ep['stress'],'seed':int(ep['seed']),
                    't_hours':(np.arange(len(y))*DT).round(6).tolist(),
                    'true_cc':y.round(7).tolist(),'ukf_cc':ukf.round(7).tolist(),
                    'oracle_cc':teacher.round(7).tolist(),'student_cc':student.round(7).tolist(),
                    'true_T':ep['true'][:,4].round(6).tolist(),
                    'measured_T':ep['z'][:,0].round(6).tolist(),
                    'mw':ep['u'][:,3].round(3).tolist()})
    return per,traces

def summarise(per,split='test'):
    a=[r for r in per if r['split']==split]
    ans={'n_episodes':len(a),'n_normal':sum(not v['stress'] for v in a),'n_stress':sum(v['stress'] for v in a)}
    for m in ('ukf','teacher','student'):
        ans[m+'_RMSE_mean']=float(np.mean([v[m+'_rmse'] for v in a]))
        ans[m+'_MAE_mean']=float(np.mean([v[m+'_mae'] for v in a]))
    gain=[(r['ukf_rmse']-r['student_rmse']) for r in a]
    ans.update({'student_gain_pct_mean_rmse':100*(ans['ukf_RMSE_mean']-ans['student_RMSE_mean'])/ans['ukf_RMSE_mean'],
                'student_wins':sum(x>1e-10 for x in gain),'student_losses':sum(x<-1e-10 for x in gain),
                'teacher_gain_pct_mean_rmse':100*(ans['ukf_RMSE_mean']-ans['teacher_RMSE_mean'])/ans['ukf_RMSE_mean']})
    # Bootstrap episode-level (paired) and group error, not claiming CI for independent time points.
    if len(a):
        rg=np.random.default_rng(891);ab=np.array([r['ukf_rmse'] for r in a]);st=np.array([r['student_rmse'] for r in a]);b=[]
        for i in range(2000):
            ids=rg.integers(0,len(a),len(a));b.append(100*(1-np.mean(st[ids])/np.mean(ab[ids])))
        ans['paired_bootstrap_gain_pct_CI95']=[float(i) for i in np.percentile(b,[2.5,97.5])]
    return ans

def subgroup_summary(per,group):
    a=[r for r in per if r['split']=='test' and bool(r['stress'])==bool(group)]
    return {'n':len(a),'ukf_rmse':float(np.mean([r['ukf_rmse'] for r in a])),'teacher_rmse':float(np.mean([r['teacher_rmse'] for r in a])),'student_rmse':float(np.mean([r['student_rmse'] for r in a])),'student_wins':sum(r['student_rmse']<r['ukf_rmse'] for r in a)}

def run(args):
    start=time.perf_counter();splits=build(args.train,args.val,args.test,args.steps,args.seed)
    print('Simulação e suavização concluídas',round(time.perf_counter()-start,1),'s',flush=True)
    scaler,model,name,shrink,selection=train_models(splits['train'],splits['val'])
    print('Aluno escolhido por pseudo-rótulos de validação:',name,'shrink',shrink,flush=True)
    per,traces=evaluate(splits,scaler,model,shrink,store=args.test)
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    with open(out/'episodes.csv','w',newline='') as fh:
        writer=csv.DictWriter(fh,per[0].keys());writer.writeheader();writer.writerows(per)
    report={'protocol':'Offline RTS teacher → causal student (UKF features + past observations and actions)',
            'model':'Six-state Yanko ProcessLab tabulated variant, not historical PG variant',
            'n_train':args.train,'n_val':args.val,'n_test':args.test,'samples_per_episode':args.steps+1,
            'measurements':'T,Tt only','sensor_sigma_K':NOISE_STD,'split_seed':args.seed,
            'teacher':'unscented Rauch–Tung–Striebel smoother using future observations offline',
            'student':{'model':name,'shrink':shrink,'selection_metric':'validation RMSE to SMOOTHED teacher residual, NOT true concentrations'},
            'results':{s:summarise(per,s) for s in splits},'test_subgroups':{'matched':subgroup_summary(per,False),'shift':subgroup_summary(per,True)},
            'limitations':['Unmodeled UA and feed temperature disturbances; same parametric process family',
                           'Teacher sees future only offline; test truth is used ONLY for evaluation',
                           'Matched model in train/validation, test includes matched and out-of-distribution UA/heat/feed uncertainty; historical model coefficients not replicated',
                           'Synthetic episodes, short horizon, no physical validation'],
            'elapsed_seconds':round(time.perf_counter()-start,2)}
    (out/'summary.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
    (out/'traces.json').write_text(json.dumps(traces,ensure_ascii=False))
    (out/'model_selection.json').write_text(json.dumps(selection,indent=2,ensure_ascii=False))
    import joblib
    joblib.dump({'scaler':scaler,'model':model,'shrink':shrink,'model_name':name,'feature_window':WIN},out/'student_model.joblib')
    print(json.dumps(report,indent=2,ensure_ascii=False),flush=True)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--train',type=int,default=70);p.add_argument('--val',type=int,default=24);p.add_argument('--test',type=int,default=28);p.add_argument('--steps',type=int,default=48);p.add_argument('--seed',type=int,default=4701);p.add_argument('--out',default='results')
    run(p.parse_args())
