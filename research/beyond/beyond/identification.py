"""Nonlinear holdout check of spectroscopy and prospective decision value.

MAP fits use ONLY input/temperature records and a common stated prior. A future
stationary quality decision has the same target and candidate set for all probes.
Decision regret is evaluated offline on the true parameter realization; it is
not a closed-loop or global optimum claim.
"""
import time
import numpy as np
import pandas as pd
import casadi as ca
from scipy.optimize import least_squares
from beyond.models import get_model
from beyond.common import RESULTS,metrics,dump
from beyond.spectra import schedule

class Fit:
    def __init__(self,m,U):
        self.m=m;self.U=U;n=len(U);d=m.n+m.np
        a=ca.MX.sym('a',d);data=ca.MX.sym('data',len(m.yidx)*n)
        # Positive chemical inventories; identical .2 relative prior in every probe.
        x=ca.vertcat(ca.DM(m.x0[:4])*ca.exp(.2*a[:4]),ca.DM(m.x0[4:])+ca.DM(m.xscale[4:])*a[4:m.n])
        p=a[m.n:]*ca.DM(m.pscale)
        X=m.step.mapaccum(n)(x,ca.DM(U.T),ca.repmat(p,1,n))
        obs=X[m.yidx,:]/ca.repmat(ca.DM(m.noise),1,n)
        rr=ca.vertcat(ca.vec(obs)-data,a)
        self.f=ca.Function('map_res',[a,data],[rr]);self.j=ca.Function('map_jac',[a,data],[ca.jacobian(rr,a)])
        self.out=ca.Function('map_out',[a],[X[:,-1]])
    def solve(self,Y):
        m=self.m;data=(Y/m.noise).ravel();start=time.perf_counter()
        cache=[None,None,None]
        def ev(a):
            if cache[0] is None or not np.array_equal(a,cache[0]):
                cache[:]=[a.copy(),np.array(self.f(a,data)).ravel(),np.array(self.j(a,data))]
            return cache[1:]
        r=least_squares(lambda a:ev(a)[0],np.zeros(m.n+m.np),jac=lambda a:ev(a)[1],
            bounds=(-3*np.ones(m.n+m.np),3*np.ones(m.n+m.np)),max_nfev=55,ftol=1e-7,gtol=1e-7,xtol=1e-7)
        P=np.linalg.pinv(r.jac.T@r.jac)
        return r.x[m.n:]*m.pscale,P,r,float(time.perf_counter()-start)

def candidate_costs(m,p,uncertainty=None):
    rows=[]
    for ratio in np.linspace(.8,1.2,17):
        u=m.u0.copy();u[m.cidx]*=ratio
        try:
            x=m.steady(u,p);q=float(m.quality(x));feasible=m.feasible(x,u)
            c=((q-m.q0)/(.02*m.q0))**2+.02*(ratio-1)**2
            violation=max(0,x[4]-m.tmax,m.tmin-x[4]);c+=1000*violation**2
            if uncertainty is not None:
                A=np.array(m.fx(x,u,p));G=np.array(m.fp(x,u,p));g=np.array(m.qgrad(x)).ravel()@(-np.linalg.solve(A,G))*m.pscale
                c+=max(float(g@uncertainty@g),0)/(.02*m.q0)**2
            rows.append((c,q,x[4],feasible))
        except (ValueError,np.linalg.LinAlgError):rows.append((1e8,np.nan,np.nan,False))
    return np.array(rows,dtype=float)

def run():
    rows=pd.read_csv(RESULTS/'identification.csv').to_dict('records') if (RESULTS/'identification.csv').exists() else []
    for kind in ['PG','EB']:
        m=get_model(kind);waves=['constant','step','prbs','sin']
        fitters={w:Fit(m,schedule(m,w,(4 if kind=='PG' else 1)*m.tau,'feed',.025)) for w in waves}
        for s in range(24):
            rng=np.random.default_rng(65000+s);p=rng.normal(size=m.np)*m.pscale*.65
            p=np.clip(p,-2*m.pscale,2*m.pscale);x=m.x0.copy();x[:4]*=np.exp(rng.normal(0,.12,4))
            n=len(fitters['constant'].U);noise=rng.normal(size=(n,len(m.yidx)))*m.noise
            case='correct_family' if s<16 else 'sensor_bias_unmodelled'
            if s>=16:noise+=m.noise*.7
            true=candidate_costs(m,p);oracle=int(np.argmin(true[:,0]));prior=candidate_costs(m,m.p0);prioridx=int(np.argmin(prior[:,0]))
            for w,fit in fitters.items():
                if any(v['kind']==kind and v['wave']==w and v['seed']==65000+s for v in rows):continue
                X=m.rollout(x,fit.U,p);Y=X[1:,m.yidx]+noise
                phat,P,r,seconds=fit.solve(Y);estimated=candidate_costs(m,phat);robust=candidate_costs(m,phat,P[m.n:,m.n:])
                a=int(np.argmin(estimated[:,0]));b=int(np.argmin(robust[:,0]));met=metrics(m,X,fit.U,plant_parameters=p)
                future_solve_success=True
                try:qtrue=float(m.quality(m.steady(m.u0,p)));qpred=float(m.quality(m.steady(m.u0,phat)))
                except ValueError:
                    qtrue=qpred=np.nan;future_solve_success=False
                rows.append(dict(kind=kind,wave=w,seed=65000+s,case=case,fit_success=bool(r.success),evaluations=r.nfev,seconds=seconds,
                    parameter_scaled_rmse=float(np.sqrt(np.mean(((phat-p)/m.pscale)**2))),
                    future_quality_error=qpred-qtrue,future_steady_solve_success=future_solve_success,
                    decision_grid_has_feasible=bool(np.any(true[:,3])),decision_regret=true[a,0]-true[oracle,0],
                    robust_decision_regret=true[b,0]-true[oracle,0],prior_regret=true[prioridx,0]-true[oracle,0],
                    decision_feasible=bool(true[a,3]),robust_decision_feasible=bool(true[b,3]),
                    oracle_ratio=.8+.025*oracle,selected_ratio=.8+.025*a,robust_ratio=.8+.025*b,
                    probe_violation_steps=met['violation_steps'],probe_feed_mean=met['feed_mean'],probe_heat=met['heat_total']))
                np.savez_compressed(RESULTS/f'identification_{kind}_{w}_{65000+s}.npz',X=X,U=fit.U,Y=Y,p=p,phat=phat,P=P,
                    true_decision_cost=true,predicted_decision_cost=estimated,robust_predicted_cost=robust)
            pd.DataFrame(rows).to_csv(RESULTS/'identification.csv',index=False)
            print(kind,65000+s,'MAP holdout complete',flush=True)
    dump(RESULTS/'identification_scope.json',dict(n=24,seeds='65000..65023',selection='frequency chosen using nominal local design only',
        decision='17 common prospective stationary cooling decisions; current true composition never used for fit or selection',
        uncertainty='Laplace posterior, approximate; sensor-bias cases deliberately outside fitted family',
        warning='Prospective steady regret does not certify transient feasibility or closed-loop economic value'))
if __name__=='__main__':run()
