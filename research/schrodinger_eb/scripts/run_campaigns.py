"""Reproduce all test campaigns into a fresh root; no evidence is overwritten."""
import argparse,subprocess,sys,os
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',default='results/reproduction');p.add_argument('--workers',type=int,default=4)
    p.add_argument('--secondary-only',action='store_true');a=p.parse_args();root=Path(a.out);root.mkdir(parents=True,exist_ok=True)
    env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    jobs=[] if a.secondary_only else [('primary',['--trials','100'])]
    jobs += [('robust',['--trials','12','--start-seed','3000','--scenarios','student','outliers','correlated','missing','bias','feed_step']),
      ('naive',['--trials','12','--start-seed','3000','--scenarios','student','outliers','correlated','bias','--naive']),
      ('physics_fixed',['--trials','20','--start-seed','3500','--scenarios','physics']),
      ('physics_joint',['--trials','20','--start-seed','3500','--scenarios','physics','--joint']),
      ('q64',['--trials','20','--qfactor','64','--methods','M0']),
      ('no_observations',['--trials','100','--no-observations','--methods','M0'])]
    for name,args in jobs:
        if name not in ['primary','q64','no_observations']:args += ['--methods','M0','M1','M2','M3','M4']
        with (root/(name+'.log')).open('w',encoding='utf-8') as log:
            print('Running',name,flush=True)
            subprocess.run([sys.executable,'-m','eblab.experiments','--out',str(root/name),'--workers',str(a.workers)]+args,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    print('Campaigns finished',flush=True)

if __name__=='__main__':main()
