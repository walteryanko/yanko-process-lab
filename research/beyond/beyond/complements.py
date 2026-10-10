"""Exact forgetting, invariant coordinates, delayed samples and thermal falsifiers."""
import numpy as np
import pandas as pd
import casadi as ca
from scipy.linalg import null_space
from beyond.models import get_model,ROOT
from beyond.common import RESULTS,dump,frame,metrics,slew_limit
from beyond.spectra import schedule,information

def twins_and_forgetting():
    m=get_model('PG');cp=np.array([m.constants[k] for k in ['cpA','cpB','cpC','cpM']])
    delta=np.array([0.,-.5*cp[2]/cp[1],.5,0.,0.,0.]);rows=[]
    for wave in ['constant','step','impulse','prbs','chirp','sin','multisine']:
        U=schedule(m,wave,4*m.tau,'joint',.025,horizon=.9)
        xa=m.x0-delta/2;xb=m.x0+delta/2;A=m.rollout(xa,U);B=m.rollout(xb,U)
        analytic=delta[2]*np.exp(-np.r_[0,np.cumsum([m.dilution(u)*m.dt for u in U])])
        rows.append(dict(wave=wave,temperature_difference=float(abs(A[:,m.yidx]-B[:,m.yidx]).max()),
            analytic_error=float(abs(B[:,2]-A[:,2]-analytic).max()),initial_separation=delta[2],final_separation=float(B[-1,2]-A[-1,2]),
            information_about_invisible_coordinate=0.,min_concentration=min(A[:,:4].min(),B[:,:4].min())))
        np.savez_compressed(RESULTS/f'twins_PG_{wave}.npz',A=A,B=B,U=U,analytic=analytic)
    frame(RESULTS/'twins.csv',rows)
    # Autonomous H13: matching cumulative throughput fixes terminal forgetting.
    # Smooth, zero-mean shapes respect the FIRST actuator move as well as
    # internal increments. Recentring a clipped square had violated startup slew.
    n=40;raw=.06*np.sin(2*np.pi*(np.arange(n)+.5)/n);forget=[]
    for name,w in [('constant',np.zeros(n)),('frontloaded',raw),('backloaded',-raw)]:
        U=np.tile(m.u0,(n,1));U[:,0]*=1+w
        assert np.all(abs(np.diff(np.vstack([m.u0,U]),axis=0))<=m.slew*m.dt+1e-7)
        A=m.rollout(m.x0-delta/2,U);B=m.rollout(m.x0+delta/2,U)
        sep=abs(B[:,2]-A[:,2]);Dsum=sum(m.dilution(u)*m.dt for u in U)
        r=metrics(m,A,U);r.update(schedule=name,cumulative_dilution=Dsum,final_separation=float(sep[-1]),
            integrated_ambiguity=float(np.trapezoid(sep,dx=m.dt)),mean_feed=float(U[:,0].mean()),
            max_slew_ratio=float(np.max(np.abs(np.diff(np.r_[m.u0[0],U[:,0]]))/(m.slew[0]*m.dt))))
        forget.append(r);np.savez_compressed(RESULTS/f'forgetting_{name}.npz',A=A,B=B,U=U)
    frame(RESULTS/'forgetting.csv',forget)
    eps=.02*m.q0
    dump(RESULTS/'forgetting_bound.json',dict(initial_width=.5,quality_halfband=eps,
       minimum_nominal_time_h=float(np.log(.5/(2*eps))/m.dilution(m.u0)),
       statement='necessary lower bound only; terminal width determined by cumulative dilution for exact PG twins'))

def coordinates():
    m=get_model('PG');d=m.constants;cp=np.array([d[k] for k in ['cpA','cpB','cpC','cpM']])
    L=np.zeros((5,6));L[0,0]=1;L[1,:4]=cp;L[2,[0,2]]=1;L[3,4]=1;L[4,5]=1
    # Five closed coordinates preserve the decision output without reconstructing
    # chemically irrelevant invisible directions. Initial covariance is projected.
    z=ca.SX.sym('z',5);u=ca.SX.sym('u',6);p=ca.SX.sym('p',4)
    # Fixed pseudoinverse is only a representative of a quotient class.
    representative=ca.DM(np.linalg.pinv(L))@z
    # Absolute positivity of this representative is not required by quotient
    # dynamics: rate uses CA and thermal capacity uses the preserved Cp sum.
    f=ca.Function('quotient_f',[z,u,p],[ca.DM(L)@m.f(representative,u,p)])
    state=z;h=m.dt/6
    for _ in range(6):
        a=f(state,u,p);b=f(state+h*a/2,u,p);c=f(state+h*b/2,u,p);dd=f(state+h*c,u,p);state+=h*(a+2*b+2*c+dd)/6
    st=ca.Function('quotient_step',[z,u,p],[state]);U=schedule(m,'chirp',2*m.tau,'joint',.03,horizon=1.2)
    X=m.rollout(m.x0,U);Z=[L@m.x0]
    for uu in U:Z.append(np.array(st(Z[-1],uu,m.p0)).ravel())
    Z=np.array(Z)
    Nu=np.array([[-1,-1,0],[-1,0,-1],[1,-1,2],[0,1,-1.]])
    M=np.array([[0,1,1,1],[1,0,1,2.]])
    dump(RESULTS/'coordinates.json',dict(PG_projection=L,PG_state_dimension=6,PG_decision_quotient_dimension=5,
       trajectory_projection_error=float(np.max(abs(Z-X@L.T))),quality_error=float(np.max(abs(Z[:,2]-Z[:,0]-X[:,2]))),
       EB_stoichiometric_rank=int(np.linalg.matrix_rank(Nu)),EB_invariants=M,EB_invariant_residual=float(abs(M@Nu).max()),
       prior_covariance_projected=L@np.diag(m.xscale**2)@L.T,
       conclusion='exact reduced dynamics, not additional information or a validated reduced controller'))
    np.savez_compressed(RESULTS/'coordinates.npz',X=X,Z=Z,U=U,L=L)

def sparse_sampling():
    rows=[]
    for kind in ['PG','EB']:
        m=get_model(kind);horizon=1.5 if kind=='PG' else 6.
        U=schedule(m,'sin',4*m.tau,'feed',.02,horizon=horizon)
        _,X,a=information(m,m.x0,U,keep=True);S=a['SS'];H=a['H'];n=len(U);d=m.n+m.np
        Fs=np.cumsum(np.einsum('nij,nik->njk',H,H),axis=0);G=np.array([np.array(m.qgrad(x)).ravel()@s for x,s in zip(X[1:],S)])
        base=np.array([g@np.linalg.solve(np.eye(d)+ff,g) for g,ff in zip(G,Fs)])
        total=float(base.sum()*m.dt)
        for delaytau in [0,.5,1,2]:
            delay=int(round(delaytau*m.tau/m.dt))
            for species in range(4):
                sigma=max(.02*m.x0[species],.002)
                for j in np.unique(np.linspace(0,n-2,21).astype(int)):
                    arrival=j+delay
                    if arrival>=n:continue
                    h=S[j,species]/sigma;add=np.outer(h,h)
                    vals=base.copy()
                    for t in range(arrival,n):vals[t]=G[t]@np.linalg.solve(np.eye(d)+Fs[t]+add,G[t])
                    gain=float((base-vals).sum()*m.dt)
                    rows.append(dict(kind=kind,delay_tau=delaytau,species=species,sample_h=(j+1)*m.dt,arrival_h=(arrival+1)*m.dt,
                        lab_sigma=sigma,integrated_variance_without=total,integrated_variance_with=total-gain,
                        variance_value=gain,reduction_percent=100*gain/total,cost_break_even_quality_variance_hours=gain,
                        scope='local Gaussian causal variance, not measured economic or closed-loop benefit'))
        print(kind,'sparse sampling complete',flush=True)
    frame(RESULTS/'sparse_sampling.csv',rows)

def thermal_falsifiers():
    m=get_model('EB');h=get_model('EB','hess');rows=[]
    for variant,mod in [('historical',m),('hess',h)]:
        for mode in ['feed','cool','joint']:
            for period in [.5,1,2,4]:
                U=schedule(mod,'sin',period*mod.tau,mode,.025,horizon=8.)
                inf,X,_=information(mod,mod.x0,U);inf.update(variant=variant,mode=mode,period_tau=period);rows.append(inf)
    frame(RESULTS/'hess_spectra.csv',rows)
    rho=np.array(m.constants['RHOS']);cp=np.array(m.constants['CPS']);rhoc=m.constants['RHOC'];F=m.u0[:3]
    # Counterfactual literal Celsius->Kelvin use, followed by nominal Q refit.
    # This deliberately INVALID change exposes the reference-dependent closure.
    C=273.15;offset=C*(np.dot(F,rho*cp)-F.sum()*rhoc)
    derivative_artifact=C*(rho*cp-rhoc)/(rhoc*200)
    B=np.array(m.fu(m.x0,m.u0,m.p0));A=np.array(m.fx(m.x0,m.u0,m.p0))
    Bbad=B.copy();Bbad[4,:3]+=derivative_artifact
    tempslope=(-np.linalg.solve(A,B))[4,0];badslope=(-np.linalg.solve(A,Bbad))[4,0]
    dump(RESULTS/'thermal_falsifiers.json',dict(Hess_cycle_residual_kcal_kmol=-27150-(-26950)-(-205.5),
       nominal_reference_shift_Q_MW=offset*4184/3.6e9,temperature_input_jacobian_artifact=derivative_artifact,
       historical_dTdfE=float(tempslope),invalid_reference_shift_dTdfE=float(badslope),
       warning='Counterfactual bad unit/reference handling, not a physical alternative plant; refitting nominal Q does not cure dynamic slope error',
       historical_Q_MW=m.duty0*4184/3.6e9,archived_Aspen_Q_MW=9.087923,
       confounding='A heat-loss offset, duty bias, feed-enthalpy error and kinetic heat mismatch can share a scalar residual.'))

def run():
    twins_and_forgetting();coordinates();sparse_sampling();thermal_falsifiers()
if __name__=='__main__':run()
