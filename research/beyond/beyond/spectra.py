"""Local Bayesian information with explicit initial-state and thermal nuisances.

Fisher matrices are whitened by sensor SD and by a FIXED physical prior scale.
They concern a deterministic simulator with iid measurement noise, not a
guaranteed covariance under process noise or structural mismatch.
"""
import time
import numpy as np
from scipy.signal import chirp
from beyond.models import get_model
from beyond.common import RESULTS,dump,frame,metrics,slew_limit

def information(model,x,U,p=None,keep=False):
    p=model.p0 if p is None else p;n=model.n;d=n+model.np
    S=np.zeros((n,d));S[:,:n]=np.diag(model.xscale)
    F=np.zeros((d,d));z=x.copy();hist=[z.copy()];SS=[];HH=[]
    for u in U:
        zz,A,G=model.deriv(z,u,p);z=np.array(zz).ravel();A=np.array(A);G=np.array(G)
        S=A@S;S[:,n:]+=G*model.pscale
        H=S[model.yidx]/model.noise[:,None];F+=H.T@H
        hist.append(z.copy())
        if keep:SS.append(S.copy());HH.append(H.copy())
    P=np.linalg.solve(np.eye(d)+F,np.eye(d));P=(P+P.T)/2
    g=np.array(model.qgrad(z)).ravel()@S
    prior_var=float(g@g);post_var=float(g@P@g)
    sv=np.linalg.svd(F,compute_uv=False)
    eig=np.linalg.eigvalsh(F);positive=eig[eig>max(eig[-1]*1e-10,1e-12)]
    result=dict(logdet_information=float(np.linalg.slogdet(np.eye(d)+F)[1]),
        effective_rank=int(np.sum(sv>max(sv[0]*1e-9,1e-10))),
        condition_nonzero=float(positive[-1]/positive[0]) if len(positive) else 1.,
        current_quality_prior_sd=np.sqrt(max(prior_var,0)),current_quality_posterior_sd=np.sqrt(max(post_var,0)),
        current_quality_information_reduction=1-np.sqrt(max(post_var,0)/max(prior_var,1e-30)),
        param_prior_rms=1.,param_posterior_rms=float(np.sqrt(np.diag(P)[n:].mean())),
        param_variance_reduction=float(1-np.diag(P)[n:].mean()))
    # A common prospective decision target eliminates terminal-state/phase bias.
    A0=np.array(model.fx(model.x0,model.u0,model.p0));G0=np.array(model.fp(model.x0,model.u0,model.p0))
    target=np.array(model.qgrad(model.x0)).ravel()@(-np.linalg.solve(A0,G0))*model.pscale
    result['common_target_prior_sd']=float(np.linalg.norm(target))
    result['common_target_posterior_sd']=float(np.sqrt(max(target@P[n:,n:]@target,0)))
    for j,name in enumerate(model.param_names):result['posterior_sd_'+name]=float(np.sqrt(max(P[n+j,n+j],0))*model.pscale[j])
    return result,np.array(hist),dict(F=F,P=P,S=S,SS=np.array(SS),H=np.array(HH))

def waveform(t,wave,period,seed=62201,phase=0):
    a=2*np.pi*t/period+phase
    if wave=='constant':y=np.zeros_like(t)
    elif wave=='sin':y=np.sin(a)
    elif wave=='square':y=np.tanh(4*np.sin(a))
    elif wave=='step':y=np.where(t<t[-1]/2,-1.,1.)
    elif wave=='impulse':y=np.where((t>t[-1]*.2)&(t<t[-1]*.3),1.,-1/9)
    elif wave=='prbs':
        rng=np.random.default_rng(seed);bits=rng.choice([-1.,1.],int(t[-1]/period*4)+3)
        y=bits[np.minimum((t/(period/4)).astype(int),len(bits)-1)]
    elif wave=='chirp':y=chirp(t,f0=.2/period,t1=t[-1],f1=5/period,method='logarithmic')
    elif wave=='multisine':y=(np.sin(a)+np.sin(3*a+1.3)+np.sin(7*a+2.2))/np.sqrt(3)
    else:raise ValueError(wave)
    y=y-y.mean();s=np.sqrt(np.mean(y*y))
    return y/s if s>1e-12 else y

def schedule(model,wave,period,mode='feed',amp=.025,phase=0,horizon=None):
    horizon=(2 if model.kind=='PG' else 8) if horizon is None else horizon
    n=round(horizon/model.dt);t=np.arange(n)*model.dt;U=np.tile(model.u0,(n,1))
    if mode in ['feed','joint']:U[:,0]*=1+amp*waveform(t,wave,period)
    if mode in ['cool','joint']:U[:,model.cidx]*=1+amp*waveform(t,wave,period,phase=phase)
    return slew_limit(model,U)

def run():
    allrows=[];start=time.perf_counter()
    for kind in ['PG','EB']:
        m=get_model(kind);cases=[('constant',m.tau,'feed',0.,0.)]
        for wave in ['step','impulse','prbs','chirp','multisine']:cases.append((wave,2*m.tau,'feed',.025,0.))
        for period in [.25,.5,1,2,4,8]:
            for mode in ['feed','cool']:cases.append(('sin',period*m.tau,mode,.025,0.))
        for phase in [0,np.pi/2,np.pi,3*np.pi/2]:cases.append(('sin',2*m.tau,'joint',.025/np.sqrt(2),phase))
        for idx,(wave,period,mode,amp,phase) in enumerate(cases):
            U=schedule(m,wave,period,mode,amp,phase)
            info,X,data=information(m,m.x0,U)
            row=dict(kind=kind,case=idx,wave=wave,period=period,period_tau=period/m.tau,mode=mode,amp=amp,phase=phase)
            row.update(info);row.update(metrics(m,X,U));row['input_rms']=float(np.sqrt(np.mean(((U[:,m.controls]-m.u0[m.controls])/m.u0[m.controls])**2)))
            if wave=='sin':
                t=np.arange(len(U))*m.dt;ii=t>t[-1]/2
                Z=np.c_[np.ones(ii.sum()),np.sin(2*np.pi*t[ii]/period),np.cos(2*np.pi*t[ii]/period),
                    np.sin(4*np.pi*t[ii]/period),np.cos(4*np.pi*t[ii]/period)]
                beta=np.linalg.lstsq(Z,X[1:,4][ii],rcond=None)[0]
                row.update(temp_fundamental=float(np.hypot(beta[1],beta[2])),phase_rad=float(np.arctan2(beta[2],beta[1])),
                    second_harmonic=float(np.hypot(beta[3],beta[4])))
            np.savez_compressed(RESULTS/f'spectrum_{kind}_{idx}.npz',X=X,U=U,F=data['F'],P=data['P'],S=data['S'])
            allrows.append(row)
        print(kind,'spectra complete',flush=True)
    frame(RESULTS/'spectra.csv',allrows);dump(RESULTS/'spectra_runtime.json',{'seconds':time.perf_counter()-start})
if __name__=='__main__':run()
