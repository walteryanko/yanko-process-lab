"""Verify campaign completeness; explicitly recover missing JSONL rows from evidence.

The initial delivery audit found three JSONL omissions, while all 1,200 CSV rows
and traces existed. No cause is asserted. Recovery checks deterministic replay
against the original trace and CSV; original latency columns are retained.
"""
import csv, gzip, hashlib, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from schrodinger_lab.experiments import generate, run, serial, write_json
from schrodinger_lab.filters import FilterConfig

def audit(folder, recover=False):
    p=Path(folder); raw=(p/'runs.jsonl').read_bytes()
    rows=[json.loads(x) for x in raw.decode().splitlines() if x.strip()]
    cfg=json.loads((p/'manifest.json').read_text())['config']
    keys=lambda r:(r['scenario'],int(r['seed']),r['method'])
    indexed={keys(r):r for r in rows}
    assert len(indexed)==len(rows),'Duplicate experiment keys'
    expected=[(s,k,m) for s in cfg['scenarios'] for k in range(cfg['start_seed'],cfg['start_seed']+cfg['trials']) for m in cfg['methods']]
    missing=[key for key in expected if key not in indexed]
    if missing and recover:
        evidence={keys(r):r for r in csv.DictReader((p/'episodes.csv').open())}
        assert set(evidence)==set(expected),'Original CSV itself is incomplete'
        archive=p/'integrity';archive.mkdir(exist_ok=True)
        (archive/'runs_before_recovery.jsonl.gz').write_bytes(gzip.compress(raw))
        changes=[]
        for s,k,m in missing:
            demo=p/f'demo_{s}_{m}.json'
            if k==cfg['start_seed'] and demo.exists():
                r=json.loads(demo.read_text())['result'];source='original demo JSON'
                replay_latency=None
            else:
                reference=next(r for r in rows if r['scenario']==s and r['method']==m)
                fc=reference['config'].copy();fc['threshold']=float('inf') if fc['threshold'] is None else fc['threshold']
                r,tr=run(generate(k,s,cfg['steps']),m,FilterConfig(**fc))
                original=np.load(p/'traces'/f'{s}_{k}_{m}.npz')
                for name in ['estimates','lower90','upper90','covariance']:
                    np.testing.assert_allclose(tr[name],original[name],rtol=0,atol=1e-12)
                source='deterministic replay; original trace verified at absolute tolerance 1e-12'
                replay_latency={name:r[name] for name in ['latency_mean_ms','latency_p95_ms','latency_p99_ms']}
            old=evidence[(s,k,m)]
            for field,metric in [('rmse_CC',r['rmse'][2]),('mae_CC',r['mae'][2]),('crps_CC',r['crps'][2]),('coverage90_CC',r['coverage']['0.9'][2]),('energy',r['energy'])]:
                np.testing.assert_allclose(metric,float(old[field]),rtol=0,atol=1e-12)
            for name in ['latency_mean_ms','latency_p95_ms','latency_p99_ms']:r[name]=float(old[name])
            indexed[(s,k,m)]=r
            changes.append(dict(scenario=s,seed=k,method=m,source=source,original_latency_source='original episodes.csv',replay_latency_ms=replay_latency))
        (p/'runs.jsonl').write_text(''.join(json.dumps(serial(indexed[key]))+'\n' for key in expected),encoding='utf-8')
        write_json(archive/'recovery.json',dict(reason='Three JSONL records absent at final audit; complete original CSV and traces retained. Cause unknown.',original_sha256=hashlib.sha256(raw).hexdigest(),expected=len(expected),original_count=len(rows),recovered=changes))
        rows=[indexed[key] for key in expected];missing=[]
    assert not missing,f'Missing runs: {missing}'
    assert set(indexed)==set(expected),'Unexpected run keys'
    for r in rows:
        assert (p/'traces'/f"{r['scenario']}_{r['seed']}_{r['method']}.npz").exists()
        assert r['failure'] is not None or r['steps_completed']==cfg['steps']
    return dict(folder=p.name,expected=len(expected),present=len(rows),failures=sum(r['failure'] is not None for r in rows),jsonl_sha256=hashlib.sha256((p/'runs.jsonl').read_bytes()).hexdigest())

if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]/'results'
    report=[audit(root/name,recover='--recover' in sys.argv) for name in ['main','hostile','hostile_naive','physics_fixed','physics_joint']]
    write_json(root/'integrity_audit.json',report)
    print(json.dumps(report,indent=2))
