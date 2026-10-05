"""Independent synthetic training/validation; control test seeds are reserved.

State labels and unobserved inputs are used offline only. Two genuine LSTMs
learn causal diagonal Q factors for physical and neural prediction models.
"""
import argparse, copy, time, warnings
import numpy as np
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.exceptions import ConvergenceWarning
from model import *
from networks import NeuralTransition, LSTM

def dataset(seed,n_random,n_trajectories,steps=200):
    rng=np.random.default_rng(seed)
    x=rng.uniform([.0004,2.5,.6,.04,130.],[.30,7.5,3.3,.85,195.],(n_random,5))
    near=n_random//2
    x[:near]=BASE+rng.normal(size=(near,5))*[.017,.6,.4,.13,6.]
    x[:near,:4]=np.maximum(x[:near,:4],.0004)
    u=np.tile(U0,(n_random,1));u[:,:4]*=rng.uniform([.04,.65,.45,.6],[2.,1.55,1.5,1.4],(n_random,4))
    u[:,4:]+=rng.uniform(-5.,5.,(n_random,3));groups=np.full(n_random,-1)
    xx=list(x);uu=list(u);gg=list(groups)
    for j in range(n_trajectories):
        state=BASE+rng.normal(size=5)*[.01,.3,.2,.07,4.];cmd=U0.copy()
        for k in range(steps):
            if k%20==0:
                cmd=U0.copy();cmd[:4]*=rng.uniform([.65,.8,.7,.83],[1.45,1.25,1.15,1.2])
                cmd[4:]+=rng.uniform(-3.,3.,3)
            nxt=transition(state,cmd)
            if not np.all(np.isfinite(nxt)) or not 115.<nxt[4]<205. or np.min(nxt[:4])<=0:
                state=BASE.copy();continue
            xx.append(state.copy());uu.append(cmd.copy());gg.append(j);state=nxt
    x=np.array(xx);u=np.array(uu);groups=np.array(gg)
    target=(transition(x,u,dt=DT/SUBSTEPS,substeps=4)-x)/XS
    valid=np.all(np.isfinite(target),axis=1)
    x=x[valid];u=u[valid];target=target[valid];groups=groups[valid]
    return dict(x=x,u=u,f=np.c_[(x-BASE)/XS,(u-U0)/US],y=target,groups=groups)

def export(model,sx,sy,affine):
    offset=affine[-1]+sy.inverse_transform(model.predict(sx.transform(np.zeros((1,12)))))[0]
    return dict(weights=model.coefs_,biases=model.intercepts_,mean=sx.mean_,scale=sx.scale_,
                target_mean=sy.mean_,target_scale=sy.scale_,affine=affine,offset=offset,
                q_model=np.zeros(5),architecture=[12,*model.hidden_layer_sizes,5],substeps=SUBSTEPS,
                source='offline nominal reconstructed TCC reactor only',dynamic_contract='fully learned substep; no physical residual online')

def transition_training(epochs):
    start=time.perf_counter();tr=dataset(4101,18000,40);va=dataset(4201,2000,8)
    affine=np.linalg.lstsq(np.c_[tr['f'],np.ones(len(tr['f']))],tr['y'],rcond=None)[0]
    residual=tr['y']-np.c_[tr['f'],np.ones(len(tr['f']))]@affine
    sx=StandardScaler().fit(tr['f']);sy=StandardScaler().fit(residual)
    xx=sx.transform(tr['f']);yy=sy.transform(residual)
    model=MLPRegressor(hidden_layer_sizes=(48,48),activation='tanh',alpha=1e-5,batch_size=512,
                      learning_rate_init=.002,random_state=4111,max_iter=1,shuffle=True)
    best=float('inf');selected=None;history=[]
    def score(data):
        net=NeuralTransition(data);errors=(net.substep(va['x'],va['u'])-va['x'])-va['y']*XS
        # Selection by independently seeded trajectories plus full-domain diagnostics.
        rmse=np.sqrt(np.mean(errors[va['groups']>=0]**2,axis=0))
        val=float(np.mean((rmse/np.array([.0001,.001,.001,.0003,.02]))**2))
        return val,rmse
    for epoch in range(epochs):
        model.partial_fit(xx,yy)
        if (epoch+1)%10==0:
            data=export(model,sx,sy,affine);val,rmse=score(data)
            history.append(dict(epoch=epoch+1,score=val,substep_rmse=rmse))
            if val<best:best=val;selected=copy.deepcopy(data);selected['epoch']=epoch+1
            if (epoch+1)%50==0:print('MLP epoch',epoch+1,'substep rmse',np.round(rmse,6),flush=True)
    model.coefs_=[np.array(w).copy() for w in selected['weights']];model.intercepts_=[np.array(b).copy() for b in selected['biases']]
    model.solver='lbfgs';model.max_iter=250;model.max_fun=300;model.warm_start=True;model.tol=1e-8
    with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter('always',ConvergenceWarning);model.fit(xx,yy)
    refined=export(model,sx,sy,affine);val,rmse=score(refined)
    if val<best:selected=refined;selected['epoch']='lbfgs';best=val
    net=NeuralTransition(selected);real=transition(va['x'],va['u'],substeps=24);err=net(va['x'],va['u'])-real
    selected['q_model']=np.mean(err[va['groups']>=0]**2,axis=0)
    dump(WEIGHTS/'transition.json',selected)
    # Held-out multi-step rollout, no control-test parameters select the model.
    rng=np.random.default_rng(4251);ee=[];failed=0
    for j in range(12):
        true=BASE+rng.normal(size=5)*[.008,.2,.1,.05,3.];pred=true.copy();cmd=U0.copy()
        cmd[:4]*=rng.uniform([.8,.85,.75,.88],[1.25,1.2,1.15,1.12]);out=[]
        for _ in range(40):
            true=transition(true,cmd,substeps=24);pred=net(pred,cmd)
            if not np.all(np.isfinite(pred)) or not 0.<pred[4]<300.:
                failed+=1;break
            out.append(np.r_[pred-true,fraction(pred)-fraction(true)])
        ee.extend(out)
    ee=np.asarray(ee)
    protocol=dict(training_seed=4101,validation_seed=4201,rollout_seed=4251,training_samples=len(xx),
                  training_random_points=18000,training_trajectories=40,validation_samples=len(va['x']),
                  selected_epoch=selected['epoch'],one_step_rmse=np.sqrt(np.mean(err**2,axis=0)),
                  trajectory_one_step_rmse=np.sqrt(selected['q_model']),
                  rollout_rmse=np.sqrt(np.mean(ee**2,axis=0)),rollout_max_error=np.max(abs(ee),axis=0),
                  rollout_failures=failed,rollouts=12,rollout_steps=40,history=history,
                  duration_s=time.perf_counter()-start,lbfgs_warnings=[str(w.message) for w in ws],
                  source_domain=dict(T_C=[130,195],fE_factor=[.04,2.],Q_factor=[.6,1.4]),
                  synthetic=True)
    dump(RESULTS/'training_transition.json',protocol);print('Transition trained',protocol['trajectory_one_step_rmse'],'rollout',protocol['rollout_rmse'],flush=True)

def q_dataset(seed,count,models,network):
    from observer import Observer,Q_BASE,WINDOW
    rng=np.random.default_rng(seed);out={k:[[],[]] for k in ['physical','neural']}
    for j in range(count):
        true=BASE+rng.normal(size=5)*[.01,.3,.15,.05,2.]
        initial=BASE+rng.normal(size=5)*[.01,.25,.12,.04,1.]
        obs={k:Observer(initial,models,'ukf' if k=='physical' else 'nake',network=network) for k in out}
        histories={k:[] for k in out};targets={k:Q_BASE.copy() for k in out};cmd=U0.copy()
        multipliers=np.ones(3);noise=1.;loss=1.
        for step in range(160):
            if step%25==0:
                cmd=U0.copy();cmd[:4]*=rng.uniform([.8,.8,.75,.9],[1.2,1.25,1.1,1.1]);cmd[4:]+=rng.uniform(-2,2,3)
            if step%40==0:
                multipliers=rng.uniform(.87,1.13,3);noise=rng.uniform(.5,2.);loss=rng.uniform(.93,1.07)
            actual=cmd.copy();actual[:4]*=1+rng.normal(0,.01*noise,4);actual[3]*=loss;actual[4:]+=rng.normal(0,.2,3)
            actual[0]=np.clip(actual[0],.04*F0[0],2*F0[0]);actual[3]=max(0.,actual[3])
            nxt=transition(true,actual,multiplier=multipliers,substeps=16)
            if not np.all(np.isfinite(nxt)) or not 95.<nxt[4]<215.:
                true=BASE.copy();continue
            y=float(nxt[4]+rng.normal(0,1.5))
            for k,o in obs.items():
                histories[k].append(o.feature(cmd));histories[k]=histories[k][-WINDOW:]
                pred=models.transition(k,true,cmd);res=(nxt-pred)**2
                targets[k]=.85*targets[k]+.15*res
                desired=np.log(np.clip((targets[k]+.25*Q_BASE)/o.qbase,.25,100.))
                if step>=WINDOW:
                    out[k][0].append(np.array(histories[k]));out[k][1].append(desired)
                o.update(cmd,y)
            true=nxt
        if (j+1)%16==0:print('Q data trajectories',j+1,'/',count,flush=True)
    return {k:(np.asarray(a),np.asarray(b)) for k,(a,b) in out.items()}

def lstm_training(epochs):
    from compiled import Models
    start=time.perf_counter();network=NeuralTransition.load();models=Models()
    tr=q_dataset(4401,64,models,network);va=q_dataset(4501,16,models,network);summary={}
    for k in ['physical','neural']:
        lstm=LSTM(seed=4301+(k=='neural'));history=lstm.fit(*tr[k],*va[k],epochs=epochs)
        predictions=lstm.predict(va[k][0]);rmse=np.sqrt(np.mean((predictions-va[k][1])**2,axis=0))
        # Portable JSON inference parity, recurrent weights trained, held-out split selected.
        filename=WEIGHTS/f'lstm_q_{k}.json';dump(filename,lstm.export())
        restored=LSTM.load(filename);parity=float(np.max(abs(restored.predict(va[k][0][:20])-predictions[:20])))
        summary[k]=dict(samples=len(tr[k][0]),validation_samples=len(va[k][0]),
                        epoch=lstm.epoch,log_factor_validation_rmse=rmse,export_max_error=parity,history=history)
        print('LSTM',k,'trained, validation log-Q RMSE',rmse,flush=True)
    dump(RESULTS/'training_lstm.json',dict(models=summary,training_seed=4401,validation_seed=4501,
      training_trajectories=64,validation_trajectories=16,steps=160,window=12,hidden=16,
      features=17,outputs=5,optimizer='NumPy BPTT/Adam, gradient-norm clipping at 5',
      targets='offline EWMA of squared one-step model error; previous innovations and commanded inputs only online',
      sequence_split='whole separately seeded trajectories, no overlapping windows across splits',
      duration_s=time.perf_counter()-start,synthetic=True))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--stage',choices=['all','transition','lstm'],default='all')
    ap.add_argument('--epochs',type=int,default=350);ap.add_argument('--lstm-epochs',type=int,default=150);args=ap.parse_args()
    WEIGHTS.mkdir(parents=True,exist_ok=True);RESULTS.mkdir(parents=True,exist_ok=True)
    dump(RESULTS/'calibration.json',calibration_audit())
    if args.stage in ['all','transition']:transition_training(args.epochs)
    if args.stage in ['all','lstm']:lstm_training(args.lstm_epochs)
