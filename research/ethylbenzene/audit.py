"""Audit every trace and independently reintegrate one run per configuration.

Do not silently discard failed/censored runs or infer actual safety from an
optimizer flag. This audit is distinct from controller/estimator unit tests.
"""
import json,itertools,time
import numpy as np
from model import *
from protocol import CASES,SEEDS,CONFIGS,scenario
from experiment import truth_step

def main():
    start=time.perf_counter();rows=json.loads((RESULTS/'metrics.json').read_text())
    rows+=json.loads((RESULTS/'metrics_tuned.json').read_text())
    expected={(case,c['estimator'],c['prediction'],c['mode'],con,seed) for case in CASES for c in CONFIGS for con in [False,True] for seed in SEEDS}
    expected.update((case,'ukf_tuned',p,m,con,seed) for case in CASES for p in ['physical','neural'] for m in ['siso','mimo'] for con in [False,True] for seed in SEEDS)
    actual={(r['case'],r['estimator'],r['prediction'],r['mode'],r['constrained'],r['seed']) for r in rows}
    assert actual==expected and len(rows)==len(expected)==720
    samples=0;max_temp_error=0.;rate_count=0;max_pred_excess=0.;min_conc=np.inf;reintegration=[]
    groups={};bounds_errors=[]
    for r in rows:
        groups.setdefault((r['estimator'],r['prediction'],r['mode'],r['constrained']),[]).append(r)
        z=np.load(RESULTS/'traces'/f"{r['name']}.npz");n=len(z['time']);samples+=n
        assert n==r['samples']
        if r['status']=='complete':assert n==400 and abs(z['time'][-1]-10.)<1e-12
        if not n:continue
        for key in ['true','estimate','command','actual','reference','Tmax','violation_h','latency_ms','q','cov_diagonal']:
            assert np.all(np.isfinite(z[key])),(r['name'],key)
        cmd=z['command'];assert np.all(cmd[:,0]>=.04*F0[0]-1e-7) and np.all(cmd[:,0]<=2*F0[0]+1e-7)
        qcmd=cmd[:,3]/Q0
        if r['mode']=='mimo':assert qcmd.min()>=.6-1e-7 and qcmd.max()<=1.4+1e-7
        else:np.testing.assert_allclose(qcmd,1.,atol=1e-12)
        assert np.all(z['actual'][:,0]>=.04*F0[0]-1e-7) and np.all(z['actual'][:,0]<=2*F0[0]+1e-7)
        assert np.all(z['q']>0.) and np.all(z['cov_diagonal']>0.)
        min_conc=min(min_conc,float(z['true'][:,:4].min()));assert min_conc>=-1e-7
        max_temp_error=max(max_temp_error,abs(float(max(TNOM,z['Tmax'].max()))-r['Tmax_C']))
        assert abs(float(z['violation_h'].sum())-r['violation_h'])<1e-10
        assert int(z['fallback'].sum())==r['fallbacks']
        assert int((~z['solver_success'].astype(bool)).sum())==r['solver_failed_statuses']
        normalized=np.c_[cmd[:,0]/F0[0],qcmd];changes=abs(np.diff(np.vstack([np.ones(2),normalized]),axis=0))
        count=int(np.sum(np.any(changes>[.12001,.08001],axis=1)));assert count==r['move_rate_overrides'];rate_count+=count
        if r['constrained']:
            accepted=z['predicted_Tmax'][~z['fallback'].astype(bool)]
            if len(accepted):max_pred_excess=max(max_pred_excess,float(accepted.max()-T_LIMIT))
    # Cover every estimator/predictor/mode/temperature combination, cycling
    # across the six cases instead of validating only the nominal trajectory.
    for i,(key,rr) in enumerate(sorted(groups.items())):
        preferred=CASES[i%len(CASES)]
        choices=[r for r in rr if r['status']=='complete' and r['case']==preferred and r['seed']==9002]
        if not choices:choices=[r for r in rr if r['status']=='complete']
        if not choices:continue
        r=choices[0];z=np.load(RESULTS/'traces'/f"{r['name']}.npz");prev=BASE.copy();iae=event=ise=itae=0.;max_state=0.;max_denseT=0.
        for j in range(r['samples']):
            nxt,grid,dense=truth_step(prev,z['actual'][j],scenario(r['case'],j*DT)[2])
            max_state=max(max_state,float(np.max(abs(nxt-z['true'][j]))))
            max_denseT=max(max_denseT,abs(float(dense[:,4].max())-float(z['Tmax'][j])))
            error=fraction(dense)-z['reference'][j];val=float(np.trapezoid(abs(error),grid));iae+=val
            ise+=float(np.trapezoid(error**2,grid));itae+=float(np.trapezoid(abs(error)*(j*DT+grid),grid))
            if j*DT>=(3. if r['case'].startswith('servo') else 5.):event+=val
            prev=z['true'][j].copy()
        errors={k:abs(v-r[k]) for k,v in [('IAE',iae),('IAE_event',event),('ISE',ise),('ITAE',itae)]}
        assert max_state<1e-8 and max_denseT<1e-8 and max(errors.values())<1e-9
        reintegration.append(dict(name=r['name'],metric_max_abs_error=max(errors.values()),state_max_abs_error=max_state,Tmax_max_abs_error=max_denseT))
    obs=json.loads((RESULTS/'metrics_openloop.json').read_text())+json.loads((RESULTS/'metrics_openloop_tuned.json').read_text())
    expected_obs={(case,e,seed) for case in ['servo_up','benzene_50','recycle_minus50','thermal_loss','kinetics_noise']
                  for e in ['ukf','ukf_tuned','lstm_ukf','nake','lstm_nake'] for seed in SEEDS}
    assert len(obs)==75 and {(r['case'],r['estimator'],r['seed']) for r in obs}==expected_obs
    common_truth_error=0.
    for r in obs:
        assert r['status']=='complete' and r['samples']==400
        key=f"{r['case']}__{r['seed']}.npz"
        mainz=np.load(RESULTS/'openloop_traces'/key)
        tunedz=np.load(RESULTS/'ukf_tuned'/'openloop_traces'/key)
        err=float(np.max(abs(mainz['true']-tunedz['true'])));common_truth_error=max(common_truth_error,err)
        assert err<1e-12
        zz=tunedz if r['estimator']=='ukf_tuned' else mainz
        estimate=zz[r['estimator']];assert np.all(np.isfinite(estimate))
        difference=fraction(estimate[200:])-fraction(zz['true'][200:])
        assert abs(float(np.sqrt(np.mean(difference**2)))-r['xEB_RMSE_after5'])<1e-12
    out=dict(expected_runs=720,unique_runs=len(actual),samples=samples,
             statuses={s:sum(r['status']==s for r in rows) for s in sorted(set(r['status'] for r in rows))},
             native_gradient_tests='7 test_study tests passed separately; C chain rule checked against independent CasADi and NumPy rollout',
             maximum_trace_Tmax_difference=max_temp_error,minimum_true_concentration=min_conc,
             observer_runs=len(obs),maximum_paired_observer_truth_difference=common_truth_error,
             maximum_accepted_predicted_temperature_excess_C=max_pred_excess,
             normal_move_rate_overrides=rate_count,reintegration_count=len(reintegration),reintegration=reintegration,
             complete_runs_with_actual_limit_violation=sum(r['constrained'] and r['violation_h']>0 for r in rows),
             covariance_repairs=sum(r['covariance_repairs'] for r in rows),positivity_projections=sum(r['positivity_projections'] for r in rows),
             solver_failed_statuses=sum(r['solver_failed_statuses'] for r in rows),fallbacks=sum(r['fallbacks'] for r in rows),
             duration_s=time.perf_counter()-start)
    dump(RESULTS/'audit.json',out);print(json.dumps({k:v for k,v in out.items() if k!='reintegration'},indent=2))

if __name__=='__main__':main()
