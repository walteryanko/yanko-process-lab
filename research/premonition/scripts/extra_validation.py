"""Post-campaign diagnostics; does not retrain models or change thresholds."""
from pathlib import Path
import json,sys,argparse,csv
import numpy as np
from scipy.stats import spearmanr,beta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from premonition.io import save,csv_write
from premonition.evaluation import alarm_metrics,paired_ci,aggregate
from premonition.physics import *
from premonition.bifurcation_campaign import trajectory
from premonition.stability import refine_fold
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--results',default=str(ROOT/'results'));args=parser.parse_args();res=Path(args.results)
def run():
    thresholds=json.loads((res/'CD/thresholds.json').read_text());output={};metrics=[]
    for split in ['test','falsification']:
        z=np.load(res/'CD'/f'{split}.npz');names=list(z['detector_names']);pairs=[];unc=[]
        for j,seed in enumerate(z['seed']):
            error=z['truth'][j,:,2]-z['xhat'][j,:,2];sigma=z['features'][j,:,8]
            ev=np.flatnonzero(z['truth'][j,:,4]>344);ev=int(ev[0]) if len(ev) else None
            row=dict(seed=int(seed),rmse_CC=float(np.sqrt(np.mean(error**2))),coverage95_CC=float(np.mean(np.abs(error)<=1.96*sigma)),mean_sigma_CC=float(np.mean(sigma)))
            for detector in ['D0','D5','D5_noEWS']:
                row[detector]=alarm_metrics(z['scores'][j,names.index(detector)],ev,z['valid'][j],thresholds[detector])
            unc.append(row)
        q=np.median([r['rmse_CC'] for r in unc]);groups={}
        for label,rr in [('lower_CC_error',[r for r in unc if r['rmse_CC']<=q]),('higher_CC_error',[r for r in unc if r['rmse_CC']>q])]:
            groups[label]=dict(n=len(rr),mean_RMSE_CC=np.mean([r['rmse_CC'] for r in rr]),D5=aggregate([r['D5'] for r in rr]))
        joint=[r for r in unc if r['D0']['lead_min'] is not None and r['D5']['lead_min'] is not None]
        event_rows=[r for r in unc if r['D0']['event']]
        output[split]=dict(n=len(unc),coverage95_mean=np.mean([r['coverage95_CC'] for r in unc]),mean_RMSE_CC=np.mean([r['rmse_CC'] for r in unc]),error_strata=groups,
            paired_recall_D5_minus_D0=paired_ci([r['D0']['detected'] for r in event_rows],[r['D5']['detected'] for r in event_rows]),
            paired_lead_D5_minus_D0_detected_by_both=paired_ci([r['D0']['lead_min'] for r in joint],[r['D5']['lead_min'] for r in joint]) if joint else None,
            false_alarm_D5_minus_noEWS=paired_ci([r['D5_noEWS']['false_onsets'] for r in unc],[r['D5']['false_onsets'] for r in unc]),note='Lead comparison conditional on both detectors detecting; not a population time-to-event estimate.')
        save(res/'CD'/f'{split}_uncertainty_rows.json',unc)
    save(res/'CD/uncertainty_and_pairs.json',output)
    # Potential outcomes are paired by seed; no unobserved real-world counterfactual is claimed.
    controls=list(csv.DictReader((res/'EF/metrics.csv').open()))
    baseline={int(r['seed']):r for r in controls if r['controller']=='C0'};pairs=[]
    for mode in sorted({r['controller'] for r in controls}-{'C0'}):
        rr=[r for r in controls if r['controller']==mode]
        avoided=sum(int(baseline[int(r['seed'])]['thermal_event']) and not int(r['thermal_event']) for r in rr)
        caused=sum(not int(baseline[int(r['seed'])]['thermal_event']) and int(r['thermal_event']) for r in rr)
        no_event=[r for r in rr if not int(baseline[int(r['seed'])]['thermal_event'])]
        pairs.append(dict(controller=mode,n=len(rr),avoided=int(avoided),caused=int(caused),discordant=int(avoided+caused),discordance_exact_ci=[float(beta.ppf(.025,avoided+caused,len(rr)-avoided-caused+1)) if avoided+caused else 0.,float(beta.ppf(.975,avoided+caused+1,len(rr)-avoided-caused)) if avoided+caused<len(rr) else 1.],nominal_no_event_pairs=len(no_event),potentially_unnecessary_actions=sum(int(r['interventions']) for r in no_event),economic_delta_on_nominal_no_event=float(np.mean([float(r['economic_proxy'])-float(baseline[int(r['seed'])]['economic_proxy']) for r in no_event]))))
    save(res/'EF/counterfactual.json',pairs);csv_write(res/'EF/counterfactual.csv',pairs)
    # Deliberate causality trap: hidden kinetics changes truth without changing available past.
    # Contract and future invariance are also exercised in pytest.
    save(res/'CAUSALITY_CONTRACT.json',{'operational_inputs':['past/current T,Tt','commanded feed and cooling','measured applied cooling','causal UKF mean/covariance/innovation'], 'forbidden':['future measurements','future disturbances','hidden UA/kinetics','plant concentrations'], 'truth_access':'scenario generator, labels, evaluator, plots and explicitly offline oracle only','probability_training':'future labels allowed offline; features do not accept episode or truth arguments'})
if __name__=='__main__':run()
