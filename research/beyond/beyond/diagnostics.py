"""Local ranks, singular values and explicit prior/quality scaling."""
import numpy as np
import pandas as pd
from scipy.linalg import expm
from scipy.stats import norm
from scipy.linalg import null_space
from beyond.models import get_model
from beyond.common import RESULTS,dump

def run():
    rows=[];spectra=[]
    for kind,variant in [('PG','historical'),('EB','historical'),('EB','hess')]:
        m=get_model(kind,variant);A=np.array(m.fx(m.x0,m.u0,m.p0));scale=m.xscale
        As=A*scale[None,:]/scale[:,None]*m.tau
        C=np.eye(m.n)[m.yidx]*scale[None,:]/m.noise[:,None]
        O=np.vstack([C@np.linalg.matrix_power(As,j) for j in range(m.n)])
        H=np.vstack([C@expm(As*t) for t in np.linspace(0,3,60)])
        for typ,B in [('derivative_stack',O),('finite_record',H)]:
            U,s,V=np.linalg.svd(B,full_matrices=False);spectra.append(dict(kind=kind,variant=variant,type=typ,singular_values=s))
            for tol in [1e-6,1e-9,1e-12]:
                rank=int(np.sum(s>s[0]*tol));null=V[rank:]
                g=np.array(m.qgrad(m.x0)).ravel()*scale
                rows.append(dict(kind=kind,variant=variant,type=typ,relative_tolerance=tol,rank=rank,states=m.n,
                    unobserved_quality_projection=float(np.linalg.norm(null@g)),largest_sv=s[0],smallest_sv=s[-1],
                    scope='local linearization and explicitly scaled numerical rank, not a nonlinear global theorem'))
    pd.DataFrame(rows).to_csv(RESULTS/'observability_ranks.csv',index=False);dump(RESULTS/'observability_spectra.json',spectra)
    a=pd.read_csv(RESULTS/'twins_EB.csv');a['equal_prior_gaussian_testing_error']=norm.cdf(-np.sqrt(a.record_discrimination_squared)/2)
    a.to_csv(RESULTS/'twins_EB.csv',index=False)
    d=pd.read_csv(RESULTS/'spectra.csv');corr=[]
    for kind in ['PG','EB']:
        m=get_model(kind);a=d[d.kind==kind]
        for label,row in [('constant',a[a.wave=='constant'].iloc[0]),('best_target',a.loc[a.common_target_posterior_sd.idxmin()])]:
            z=np.load(RESULTS/f'spectrum_{kind}_{int(row["case"])}.npz');P=z['P'][m.n:,m.n:];s=np.sqrt(np.diag(P));C=P/s[:,None]/s[None,:]
            np.savez_compressed(RESULTS/f'parameter_posterior_{kind}_{label}.npz',covariance=P,correlation=C,names=m.param_names)
            for i,name in enumerate(m.param_names):corr.append(dict(kind=kind,design=label,parameter=name,prior_sd=m.pscale[i],posterior_sd=s[i]*m.pscale[i]))
    pd.DataFrame(corr).to_csv(RESULTS/'parameter_uncertainty.csv',index=False)
    # H26: a reaction-cycle enthalpy defect can add a spurious *local* thermal
    # observability direction. This is not a nonlinear impossibility proof.
    nu=np.array([[-1,-1,0],[-1,0,-1],[1,-1,2],[0,1,-1.]])
    cy=np.array([-1.,1.,1.]);checks=[]
    for variant in ['historical','hess']:
        m=get_model('EB',variant)
        for feed in [.9,1.,1.1]:
            for temp in [150.,155.,160.,162.]:
                x,u=m.operating_point(feed,temp);A=np.array(m.fx(x,u,m.p0))
                K=null_space(A[:4,:4]+m.dilution(u)*np.eye(4))
                coupling=float(np.linalg.norm(A[4,:4]@K))
                scale=m.xscale;As=A*scale[None,:]/scale[:,None]*m.tau
                C=np.eye(5)[[4]]*scale[None,:]/m.noise[:,None]
                H=np.vstack([C@expm(As*t) for t in np.linspace(0,3,60)])
                s=np.linalg.svd(H,compute_uv=False)
                checks.append(dict(variant=variant,feed_ratio=feed,temperature=temp,
                    stoichiometric_kernel_dimension=K.shape[1],thermal_kernel_coupling=coupling,
                    cycle_enthalpy=float(np.array(m.constants['DH'])@cy),finite_record_rank_1e9=int(sum(s>s[0]*1e-9)),
                    fourth_singular_value=s[3],fourth_mode_fisher_eigenvalue=s[3]**2,
                    feasible=m.feasible(x,u),scope='local equilibrium linearization; historical enthalpy defect ablation, not reconciled plant'))
    pd.DataFrame(checks).to_csv(RESULTS/'hess_observability.csv',index=False)
if __name__=='__main__':run()
