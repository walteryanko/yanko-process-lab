"""Reproducible train/validation/test experiments on the calibrated CSTR.
Splits are whole trajectories, disjoint seeds. True states/parameters only label
OFFLINE training and score benchmarks; never enter the estimator interface.
"""
from pathlib import Path
from dataclasses import replace
from time import perf_counter
import argparse, csv, json, warnings
import numpy as np
from scipy.integrate import solve_ivp
from scipy.stats import chi2
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.exceptions import ConvergenceWarning
from estimator import *
from cstr import steady, jacobian

ROOT=Path(__file__).resolve().parent
RESULTS=ROOT/'results';WEIGHTS=ROOT/'weights'
REGIMES=['nominal','startup','feed_steps','coolant_steps','UA_mismatch','kinetic_mismatch','variable_noise','sensor_dropout','OOD_combined']


def plant_parameters(ua=1.,k=1.):return replace(P_ADJUSTED,UA=P_ADJUSTED.UA*ua,k0=P_ADJUSTED.k0*k)


def trajectory(seed,regime='train',steps=160,high_accuracy=False):
    rng=np.random.default_rng(seed);inputs=np.tile(U_BASE,(steps,1));std=np.tile([.35,.30],(steps,1))
    masks=np.ones((steps,2),bool);ua=np.ones(steps);ks=np.ones(steps)
    truth=np.zeros((steps+1,6));truth[0]=BASE
    if regime=='train':
        if rng.random()<.25:truth[0]=np.r_[BASE[:4]*rng.uniform(.85,1.15,4),BASE[4:]+rng.uniform(-3,3,2)]
        for start in range(0,steps,40):
            end=min(start+40,steps)
            inputs[start:end]=U_BASE*np.array([rng.uniform(.92,1.05),1,1,rng.uniform(.85,1.15),1,1])
            inputs[start:end,4:]+=rng.uniform(-1.5,1.5,2)
            # Include matched trajectories explicitly; parameter changes not inferable instantly.
            if seed%3:
                ua[start:end]=rng.uniform(.88,1.12);ks[start:end]=rng.uniform(.90,1.10)
            if seed%5==0:std[start:end]*=rng.uniform(.8,2.)
    elif regime=='startup':truth[0]=np.r_[BASE[:4]*np.array([1.3,1.05,.65,1.05]),322.,306.]
    elif regime=='feed_steps':
        inputs[40:85,0]*=.92;inputs[85:125,0]*=1.05;inputs[125:,4]+=1.2
    elif regime=='coolant_steps':
        inputs[40:90,3]*=1.2;inputs[90:,3]*=.85;inputs[115:,5]-=1.5
    elif regime=='UA_mismatch':ua[40:]=.88
    elif regime=='kinetic_mismatch':ks[40:]=1.10
    elif regime=='variable_noise':std[50:110]*=3
    elif regime=='sensor_dropout':masks[50:70,0]=False;masks[90:110,:]=False
    elif regime=='OOD_combined':
        ua[40:]=.80;ks[40:]=1.18;inputs[75:,0]*=.90;std[90:]*=2
    elif regime!='nominal':raise ValueError(regime)
    parameters=[]
    for i in range(steps):
        p=plant_parameters(ua[i],ks[i]);parameters.append(p)
        if high_accuracy:
            sol=solve_ivp(lambda t,x:rhs6(x,inputs[i],p),(0,DT),truth[i],method='DOP853',rtol=2e-10,atol=1e-11,max_step=.003)
            if not sol.success:raise RuntimeError(sol.message)
            truth[i+1]=sol.y[:,-1]
        else:truth[i+1]=transition(truth[i],inputs[i],p,max_step=.001)
    y=truth[1:,4:]+rng.normal(size=(steps,2))*std;y[~masks]=np.nan
    # Same initial estimate error for every compared algorithm on each trajectory.
    x0=truth[0]+rng.normal(size=6)*np.array([.03,.12,.03,.06,.2,.2])
    return dict(seed=seed,regime=regime,u=inputs,y=y,truth=truth,parameters=parameters,x0=x0,ua=ua,ks=ks,std=std)


def run_filter(data,q=Q_PUBLISHED,network=None,kind='ukf',collect=False):
    f=UKF(data['x0'],q,network,kind);est=[];cov=[];nis=[];dof=[];features=[];targets=[];times=[]
    fail=None
    for i,(u,y) in enumerate(zip(data['u'],data['y'])):
        if collect:
            features.append(f.features(u))
            # One-step teacher error from true states is used ONLY as offline label.
            pred=transition(data['truth'][i],u)
            error=data['truth'][i+1]-pred
            qlabel=np.log1p(error**2/q)
            targets.append(np.r_[np.log(data['ua'][i]),np.log(data['ks'][i]),np.clip(qlabel,0,np.log(1e6))])
        start=perf_counter()
        try:
            x,p,n,d=f.update(u,y)
        except (ValueError,np.linalg.LinAlgError,FloatingPointError) as ex:
            fail=str(ex);break
        times.append((perf_counter()-start)*1e3);est.append(x);cov.append(p);nis.append(n);dof.append(d)
    return dict(est=np.array(est),cov=np.array(cov),nis=np.array(nis),dof=np.array(dof),
                features=features,targets=targets,failed=fail,repairs=f.repairs,times=times)


def score(data,run):
    if run['failed'] is not None:return {'failed':run['failed'],'steps':len(run['est'])}
    e=run['est']-data['truth'][1:];sd=np.sqrt(np.diagonal(run['cov'],axis1=1,axis2=2))
    rmse=np.sqrt(np.mean(e**2,axis=0));mae=np.mean(abs(e),axis=0)
    nees=np.array([err@np.linalg.solve(p,err) for err,p in zip(e,run['cov'])])
    valid=run['dof']>0;d=run['dof'][valid];ns=run['nis'][valid]
    cover=np.mean(abs(e)<=1.96*sd,axis=0)
    return dict(failed=None,steps=len(e),rmse=rmse.tolist(),mae=mae.tolist(),
      cc_rmse=float(rmse[2]),temperature_rmse=float(rmse[4]),
      cc_coverage95=float(cover[2]),coverage95=cover.tolist(),nees_mean=float(nees.mean()),
      nis_mean=float(ns.mean()),nis_in95=float(np.mean((ns>=chi2.ppf(.025,d))&(ns<=chi2.ppf(.975,d)))),
      normalized_rmse=float(np.sqrt(np.mean((e/XS)**2))),
      latency_ms=float(np.median(run['times'])),latency_p95_ms=float(np.percentile(run['times'],95)),
      covariance_repairs=run['repairs'],plant_Tmax=float(data['truth'][:,4].max()),
      plant_above344_samples=int(np.sum(data['truth'][1:,4]>344)))


def portable_network(X,Y,seed=621):
    sx=StandardScaler().fit(X);sy=StandardScaler().fit(Y)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always',ConvergenceWarning)
        model=MLPRegressor(hidden_layer_sizes=(32,24),activation='tanh',solver='adam',alpha=.05,
          learning_rate_init=.002,max_iter=500,random_state=seed,early_stopping=False,tol=2e-5,
          n_iter_no_change=30,batch_size=256).fit(sx.transform(X),sy.transform(Y))
    data=dict(mean=sx.mean_.tolist(),scale=sx.scale_.tolist(),target_mean=sy.mean_.tolist(),target_scale=sy.scale_.tolist(),
      weights=[w.tolist() for w in model.coefs_],biases=[b.tolist() for b in model.intercepts_],
      iterations=int(model.n_iter_),loss=float(model.loss_),convergence_warnings=[str(w.message) for w in caught],
      input_contract='estimated x(k-1), u(k), past innovation statistics; no true state',target_order=['log_UA_scale','log_k0_scale']+[f'log_Q_ratio_{s}' for s in ['CA','CB','CC','CM','T','Tt']])
    net=DenseNetwork(data)
    # Verify exported inference numerically against the training implementation.
    assert np.max(abs(net.predict(X[:20])-sy.inverse_transform(model.predict(sx.transform(X[:20])))))<1e-10
    return net,data


def calibrate_and_verify():
    residual=rhs6(BASE,U_BASE);a,_,_=jacobian(BASE,U0,P_ADJUSTED);eig=np.linalg.eigvals(a)
    drift=transition(BASE,U_BASE,dt=4,max_step=.001)-BASE
    disturbed=BASE*np.array([1.05,1.01,.96,1.02,1.,1.]);disturbed[4]+=1.5
    a1=transition(disturbed,U_BASE,dt=.6,max_step=.001)
    b1=transition(disturbed,U_BASE,dt=.6,max_step=.0005)
    hi=solve_ivp(lambda t,x:rhs6(x,U_BASE),(0,.6),disturbed,method='DOP853',rtol=1e-11,atol=1e-12).y[:,-1]
    assert max(abs(residual))<1e-8 and max(abs(drift))<1e-8
    assert max(eig.real)<0 and max(abs(a1-b1))<1e-7 and max(abs(a1-hi))<1e-7
    # Cross-language parity check generated by the Node core.
    return dict(target_T_K=TARGET_T,adjusted_dH_kJ_kmol=P_ADJUSTED.dH,tabled_dH=P_TABLE.dH,
      relative_change=float(P_ADJUSTED.dH/P_TABLE.dH-1),adjusted_state=BASE.tolist(),
      residual=residual.tolist(),max_hold_drift=float(max(abs(drift))),eigenvalues=[[float(v.real),float(v.imag)] for v in eig],
      step_halving_error=float(max(abs(a1-b1))),DOP853_error=float(max(abs(a1-hi))),
      note='Single-point effective-enthalpy calibration; not identified physical parameter or reproduction of all historical cases')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--seeds',type=int,default=8);parser.add_argument('--steps',type=int,default=160)
    args=parser.parse_args();RESULTS.mkdir(exist_ok=True);WEIGHTS.mkdir(exist_ok=True)
    calibration=calibrate_and_verify();(RESULTS/'calibration.json').write_text(json.dumps(calibration,indent=2))
    train_seeds=list(range(100,136));val_seeds=list(range(500,506));test_seeds=list(range(900,900+args.seeds))
    train=[trajectory(seed,steps=args.steps) for seed in train_seeds]
    val=[trajectory(seed,steps=args.steps) for seed in val_seeds]
    # Retune using ONLY training trajectories (subset chosen before results).
    subset=train[::6];choices=[]
    for qc in [1.,100.,10000.]:
        for qt in [.25,1.,4.]:
            q=Q_PUBLISHED*np.r_[np.full(3,qc),1.,qt,qt]
            values=[score(d,run_filter(d,q)) for d in subset]
            loss=np.mean([v.get('normalized_rmse',1e6) for v in values])
            choices.append(dict(qc=qc,qt=qt,q=q.tolist(),training_loss=float(loss)))
            print('tuning',qc,qt,round(loss,6),flush=True)
    selected=min(choices,key=lambda z:z['training_loss']);q=np.array(selected['q'])
    print('collecting teacher labels',flush=True)
    runs=[run_filter(d,q,collect=True) for d in train]
    assert not any(r['failed'] for r in runs)
    X=np.vstack([r['features'] for r in runs]);Y=np.vstack([r['targets'] for r in runs])
    net,weights=portable_network(X,Y)
    (WEIGHTS/'nake_mlp.json').write_text(json.dumps(weights))
    validation={kind:[score(d,run_filter(d,q,net if kind!='ukf_tuned' else None,kind)) for d in val]
        for kind in ['ukf_tuned','nake_q','nake_dynamics','nake_hybrid']}
    # Validation is reported; no test-driven selection, no test weights update.
    metadata=dict(train_seeds=train_seeds,validation_seeds=val_seeds,test_seeds=test_seeds,steps=args.steps,dt=DT,
      q_published=Q_PUBLISHED.tolist(),q_tuned=q.tolist(),tuning_candidates=choices,selected=selected,
      training_samples=len(X),validation=validation,network_iterations=weights['iterations'],
      convergence_warnings=weights['convergence_warnings'],R=R_BASE.tolist(),
      training_parameter_ranges={'UA':[.88,1.12],'k0':[.9,1.1]},
      test_truth='DOP853 rtol=2e-10; independent simulator from filter RK4')
    (RESULTS/'protocol.json').write_text(json.dumps(metadata,indent=2))
    metrics=[]
    for regime in REGIMES:
        for seed in test_seeds:
            d=trajectory(seed,regime,args.steps,high_accuracy=True)
            trace={'truth':d['truth'],'u':d['u'],'y':d['y']}
            for kind in ['ukf_published','ukf_tuned','nake_q','nake_dynamics','nake_hybrid']:
                qr=Q_PUBLISHED if kind=='ukf_published' else q
                nr=None if kind.startswith('ukf') else net
                r=run_filter(d,qr,nr,kind);s=score(d,r);s.update(regime=regime,seed=seed,estimator=kind)
                metrics.append(s);trace[kind]=r['est'];trace[kind+'_sd']=np.sqrt(np.diagonal(r['cov'],axis1=1,axis2=2))
                print('test',regime,seed,kind,round(s.get('cc_rmse',np.nan),6),s.get('failed'),flush=True)
            if seed==test_seeds[0]:np.savez_compressed(RESULTS/f'trace_{regime}.npz',**trace)
    (RESULTS/'metrics.json').write_text(json.dumps(metrics,indent=2,allow_nan=False))
    keys=['regime','seed','estimator','failed','cc_rmse','temperature_rmse','cc_coverage95','normalized_rmse','nees_mean','nis_mean','latency_ms','latency_p95_ms','covariance_repairs','plant_Tmax','plant_above344_samples']
    with (RESULTS/'metrics.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,keys,extrasaction='ignore',lineterminator='\n');w.writeheader();w.writerows(metrics)
    print('finished',len(metrics),'runs',flush=True)

if __name__=='__main__':main()
