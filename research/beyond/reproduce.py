#!/usr/bin/env python3
"""Reproduction without modifying delivered reference results."""
import argparse,os,sys,subprocess,datetime,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def run(command,env):
    print('+',' '.join(command),flush=True);subprocess.run(command,cwd=ROOT,env=env,check=True)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--full',action='store_true');ap.add_argument('--figures',action='store_true');ap.add_argument('--output');a=ap.parse_args()
    env=os.environ.copy();env['OPENBLAS_NUM_THREADS']='1';env['OMP_NUM_THREADS']='1';env['LBE_NO_COMPILED']='1'
    if a.figures:
        run([sys.executable,'-m','beyond.reporting'],env);return
    target=Path(a.output).resolve() if a.output else ROOT/'reproduced'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    if target.exists() and any(target.iterdir()):raise SystemExit('Choose an empty output directory; delivered evidence is never erased.')
    target.mkdir(parents=True,exist_ok=True);env['BEYOND_RESULTS']=str(target/'results');env['BEYOND_FIGURES']=str(target/'figures')
    run([sys.executable,'-m','unittest','discover','-s','tests','-v'],env)
    modules=['spectra','landscape','periodic','closedloop','complements','identification','sampling_control','adaptive','atlas','same_quality'] if a.full else ['complements']
    for module in modules:run([sys.executable,'-m','beyond.'+module],env)
    if a.full:
        for kind in ['PG','EB']:run([sys.executable,'-m','beyond.baselines',kind],env)
        for module in ['verification','diagnostics','reporting']:run([sys.executable,'-m','beyond.'+module],env)
    (target/'reproduction_status.json').write_text(json.dumps(dict(success=True,full=a.full,python=sys.version),indent=2))
    print('Results:',target,flush=True)
if __name__=='__main__':main()
