"""Full reproduction in an isolated timestamped copy (Windows-safe)."""
import sys,subprocess,shutil,os,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

if __name__=='__main__':
    dest=ROOT/'reproductions'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    dest.mkdir(parents=True,exist_ok=False)
    for name in ['eblab','vendor','scripts','tests','web','configs']:
        shutil.copytree(ROOT/name,dest/name,ignore=shutil.ignore_patterns('__pycache__','data.js'))
    (dest/'results').mkdir();env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    commands=[['-m','unittest','discover','-s','tests','-v']]
    commands += [['-m','eblab.studies',s] for s in ['development','synthetic','observability','reference']]
    commands += [['scripts/run_campaigns.py','--out','results'],['-m','eblab.studies','scaling'],
       ['-m','eblab.control'],['-m','eblab.control','--forced','--trials','3','--out','results/fallback_validation'],
       ['scripts/analyze.py'],['scripts/build_dashboard.py']]
    for cmd in commands:
        print('Running:',*cmd,flush=True);subprocess.run([sys.executable]+cmd,cwd=dest,env=env,check=True)
    print('Reproduction complete:',dest)
