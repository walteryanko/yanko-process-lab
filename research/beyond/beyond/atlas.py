"""Finite scenario/action atlas plus separately labelled exact impossibility bounds."""
import numpy as np
import pandas as pd
from scipy.optimize import least_squares
from beyond.models import get_model
from beyond.common import RESULTS,dump
from beyond.spectra import information,schedule

def eb_twins():
    m=get_model('EB');U=np.tile(m.u0,(round(1./m.dt),1));_,X,a=information(m,m.x0,U,keep=True)
    H=a['H'][:,:,:m.n].reshape(-1,m.n);g=np.array(m.qgrad(m.x0)).ravel()*m.xscale
    P=np.linalg.solve(np.eye(m.n)+H.T@H,np.eye(m.n));d=P@g;d/=max(np.max(abs(d)),1e-12)
    rows=[]
    for amp in [.1,.25,.5,1.]:
        delta=d*m.xscale*amp;A=m.rollout(m.x0-delta,U);B=m.rollout(m.x0+delta,U)
        # Approximate twins, explicitly no structural impossibility assertion.
        rows.append(dict(amplitude=amp,initial_quality_gap=float(m.quality(B[0])-m.quality(A[0])),
            final_quality_gap=float(m.quality(B[-1])-m.quality(A[-1])),
            max_temperature_gap=float(abs(B[:,4]-A[:,4]).max()),
            record_discrimination_squared=float(np.sum(((B[1:,4]-A[1:,4])/m.noise[0])**2)),
            plausible=bool(min(A[:,:4].min(),B[:,:4].min())>=0),scope='numerical nearly-indistinguishable pair; whitened whole-record distance, not only peak temperature'))
        np.savez_compressed(RESULTS/f'twins_EB_{amp}.npz',A=A,B=B,U=U)
    pd.DataFrame(rows).to_csv(RESULTS/'twins_EB.csv',index=False)

def action_atlas():
    rows=[]
    for kind in ['PG','EB']:
        m=get_model(kind);delta=np.zeros(m.n)
        if kind=='PG':delta[2]=.25;delta[1]=-.25*m.constants['cpC']/m.constants['cpB']
        else:
            data=np.load(RESULTS/'twins_EB_0.5.npz');delta=(data['B'][0]-data['A'][0])/2
        states=[m.x0-delta,m.x0+delta]
        for horizon in [.05,.1,.2,.4,.8] if kind=='PG' else [.1,.5,1.,2.]:
            n=max(1,round(horizon/m.dt));candidates=[]
            for q in np.linspace(.75,1.25,51):
                U=np.tile(m.u0,(n,1));desired=m.u0[m.cidx]*q;last=m.u0[m.cidx]
                for j in range(n):last+=np.clip(desired-last,-m.slew[m.cidx]*m.dt,m.slew[m.cidx]*m.dt);U[j,m.cidx]=last
                outcomes=[];safe=[]
                for state in states:
                    X=m.rollout(state,U);outcomes.append(float(m.quality(X[-1])));safe.append(bool(np.all((X[:,4]<=m.tmax)&(X[:,4]>=m.tmin))))
                candidates.append((q,*outcomes,*safe))
            ar=np.array(candidates);np.savez_compressed(RESULTS/f'action_atlas_{kind}_{horizon}.npz',candidates=ar,states=states)
            for ratio in [.98,1.,1.02,1.1]:
                ref=m.q0*ratio;eps=.02*m.q0;err=abs(ar[:,1:3]-ref)
                feasible=(err<=eps)&ar[:,3:5].astype(bool)
                individual=feasible.any(axis=0);common=feasible.all(axis=1).any()
                category='A_local' if common else 'B_local' if individual.all() else 'C_candidate_family_only'
                rows.append(dict(kind=kind,horizon_h=n*m.dt,reference=ref,halfband=eps,classification=category,
                    feasible_twin1=bool(individual[0]),feasible_twin2=bool(individual[1]),common_policy=bool(common),
                    minimax_terminal_error=float(np.min(err.max(axis=1))),
                    scope='51 causal constant-target cooling ramps, not a global viability kernel; C here only rejects this candidate family'))
    pd.DataFrame(rows).to_csv(RESULTS/'action_atlas.csv',index=False)
    m=get_model('PG');U=m.u0.copy();U[0]=m.umax[0];Dmax=m.dilution(U);imax=U[0]/(Dmax*m.constants['V'])
    dump(RESULTS/'exact_bounds.json',dict(
        PG_quality_width_initial=.5,PG_halfband=.02*m.q0,
        PG_impossible_common_guarantee_before_h=float(np.log(.5/(.04*m.q0))/Dmax),
        PG_maximum_invariant_feed=imax,PG_infeasible_reference_example=imax+.2,
        assumptions='Fixed FB/FM and stated FA bounds, initial CA+CC <= maximum feed invariant, nonnegative CA; then CC <= CA+CC <= max(FA/v) for every admissible input. These exact inequalities are distinct from numerical C-candidate classifications.',
        EB_element_invariant_bound='For fixed feeds, B+EB+DEB and E+EB+2DEB each obey dilution balances. For nonnegative states, EB <= min(I_benzene,I_ethyl); this bounds concentration, not directly mole fraction.',
        decision_principle='An observation-equivalence class is controllable for a specification only if its admissible successful policy sets have nonempty intersection. This is a necessary condition, not a newly established universal sufficient theorem.'))

def prices():
    d=pd.read_csv(RESULTS/'landscape.csv');rows=[]
    for kind,a in d.groupby('kind'):
        m=get_model(kind);a=a[(a.production>=.9*m.prod0)&(a.thermal_margin>=2)].copy()
        for feed_price in [.2,.4,.6,.8,1.]:
            for deb_price in [0,.2,1.]:
                score=a.production/m.prod0-feed_price*a.feed_ratio-.02*(a.cooling_ratio**2 if kind=='PG' else a.cooling_ratio)-deb_price*a.byproduct/m.prod0
                r=a.loc[score.idxmax()]
                rows.append(dict(kind=kind,feed_weight=feed_price,byproduct_weight=deb_price,selected_index=int(r['index']),
                    feed_ratio=r.feed_ratio,temperature=r.temperature,production=r.production,sensitivity_relative=r.sensitivity_relative))
    pd.DataFrame(rows).to_csv(RESULTS/'economic_weights.csv',index=False)

def run():eb_twins();action_atlas();prices()
if __name__=='__main__':run()
