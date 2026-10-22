"""Cross-campaign paired contrasts and independent balance/integrity audit."""
import sys,json,hashlib,platform
from pathlib import Path
import numpy as np
from scipy.stats import wasserstein_distance
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from eblab.experiments import write_json
from eblab.model import *

def read(group):return [json.loads(s) for s in (ROOT/'results'/group/'runs.jsonl').read_text().splitlines()]
def paired(a,b,metric='rmse',index=2):
    refs={(r['scenario'],r['seed'],r['method']):r for r in b if not r['failure']};diff=[]
    for r in a:
        key=(r['scenario'],r['seed'],r['method'])
        if key in refs and not r['failure']:
            x=r[metric];y=refs[key][metric];diff.append((x[index]-y[index]) if index is not None else x-y)
    d=np.array(diff);rng=np.random.default_rng(32155)
    return dict(n=len(d),mean_delta=d.mean(),ci95=np.quantile(rng.choice(d,(5000,len(d))).mean(1),[.025,.975]))

def main():
    groups=['primary','robust','naive','physics_fixed','physics_joint','q64','no_observations'];rows={g:read(g) for g in groups}
    result={}
    for sc in ['gaussian','weak_thermal']:
        nominal=[r for r in rows['primary'] if r['scenario']==sc and r['method']=='M0']
        result['Q64_minus_Q1_'+sc]=paired([r for r in rows['q64'] if r['scenario']==sc],nominal)
        result['no_observation_minus_observed_'+sc]=paired([r for r in rows['no_observations'] if r['scenario']==sc],nominal)
    result['noise_model_contrasts']={}
    for sc in ['bias','correlated','outliers','student']:
        for m in ['M0','M1','M2','M3','M4']:
            result['noise_model_contrasts'][sc+'_'+m]=paired([r for r in rows['robust'] if r['scenario']==sc and r['method']==m],[r for r in rows['naive'] if r['scenario']==sc and r['method']==m])
    result['joint_minus_fixed']={m:paired([r for r in rows['physics_joint'] if r['method']==m],[r for r in rows['physics_fixed'] if r['method']==m]) for m in ['M0','M1','M2','M3','M4']}
    ref=json.loads((ROOT/'results/studies/posterior_reference.json').read_text());dist=[]
    for r in ref['snapshots']:
        if r['n']!=8192:continue
        for m in ['M0','M1','M2','M3','M4','M5']:
            demo=json.loads((ROOT/'results/primary'/f'demo_weak_thermal_{m}.json').read_text());s=demo['trace']['snapshots'][r['step']]
            w1=wasserstein_distance(np.array(s['particles'])[:,2],r['particles'],u_weights=s['weights'],v_weights=r['weights'])
            dist.append(dict(step=r['step'],method=m,w1_CEB=w1,reference='Bootstrap PF N=8192, seed=2000'))
    result['posterior_distances']=dist
    maxbalance=0.;nvalid=0;ndatasets=0;ntraces=0;hashes={};totalfail=0
    for group,rr in rows.items():
        expected={'primary':1200,'robust':360,'naive':240,'physics_fixed':100,'physics_joint':100,'q64':40,'no_observations':200}[group]
        assert len(rr)==expected,(group,len(rr));assert len(set((r['scenario'],r['seed'],r['method']) for r in rr))==expected
        totalfail+=sum(r['failure'] is not None for r in rr)
        for p in (ROOT/'results'/group/'datasets').glob('*.npz'):
            ep=np.load(p);x=ep['true'];u=ep['u'];proc=ep['process'];theta=ep['theta'];assert np.all(valid(x));ndatasets+=1
            z=x[:,:4]@MOIETIES.T;f=u[:,:3];ft=f.sum(1)
            feed=f[:,0,None]*RHO[0]*np.exp(theta[4])*[1,0,0,0]+f[:,1,None]*RHO[1]*[0,1,0,0]+f[:,2,None]*REC
            zeq=(feed@MOIETIES.T)/ft[:,None]
            pred=zeq+(z[:-1]-zeq)*np.exp(-ft[:,None]*DT/V)+proc[:,:4]@MOIETIES.T
            maxbalance=max(maxbalance,float(abs(z[1:]-pred).max()));hashes[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
        for r in rr:
            p=ROOT/'results'/group/'traces'/f"{r['scenario']}_{r['seed']}_{r['method']}.npz";t=np.load(p);ntraces+=1
            assert np.all(valid(t['estimates'][:,:5]));nvalid+=len(t['estimates'])
            ep=np.load(ROOT/'results'/group/'datasets'/f"{r['scenario']}_{r['seed']}.npz")
            rmse=np.sqrt(np.mean((t['estimates'][:,:5]-ep['true'][1:len(t['estimates'])+1])**2,axis=0))
            np.testing.assert_allclose(rmse,r['rmse'],atol=1e-12,rtol=0)
    result['audit']=dict(estimation_runs=sum(map(len,rows.values())),failed=totalfail,datasets=ndatasets,traces=ntraces,
        physical_posterior_means_checked=nvalid,max_moiety_balance_residual=maxbalance,
        balance_definition='Exact linear inventory flow solution plus recorded additive process noise, independent of reaction kinetics.',
        dataset_sha256=hashes,python=sys.version,platform=platform.platform())
    result['primary_domain_events']={}
    for m in ['M0','M1','M2','M3','M4','M5']:
        rr=[r for r in rows['primary'] if r['method']==m]
        result['primary_domain_events'][m]=dict(initial_rejected=sum(r['initial_rejected'] for r in rr),
             analysis_or_process_rejected=sum(r['rejected_count'] for r in rr),fallbacks=sum(r['fallback_count'] for r in rr),
             diagnostic_sample_rejected=sum(r['diagnostic_sample_rejections'] for r in rr))
    write_json(ROOT/'results/analysis.json',result)
    print({k:v for k,v in result['audit'].items() if k!='dataset_sha256'})

if __name__=='__main__':main()
