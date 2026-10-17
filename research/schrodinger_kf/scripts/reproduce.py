"""Fresh timestamped output directory; never overwrite delivered evidence."""
import os,sys,subprocess,datetime
from pathlib import Path
root=Path(__file__).resolve().parents[1];os.chdir(root)
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
out=Path('reproductions')/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');out.mkdir(parents=True)
commands=[['-m','unittest','discover','-s','tests','-v'],
 ['-m','schrodinger_lab.studies','development','--out',str(out/'development')],
 ['-m','schrodinger_lab.studies','synthetic','--out',str(out/'studies')],
 ['-m','schrodinger_lab.studies','observability','--out',str(out/'studies')],
 ['-m','schrodinger_lab.experiments','--out',str(out/'main'),'--trials','100','--steps','48','--epsilon','.02'],
 ['-m','schrodinger_lab.experiments','--out',str(out/'hostile'),'--trials','12','--steps','32','--epsilon','.02','--scenarios','student','outliers','correlated','missing','bias'],
 ['-m','schrodinger_lab.experiments','--out',str(out/'hostile_naive'),'--trials','12','--steps','32','--epsilon','.02','--naive','--scenarios','student','outliers','correlated'],
 ['-m','schrodinger_lab.experiments','--out',str(out/'physics_fixed'),'--trials','20','--steps','32','--epsilon','.02','--scenarios','physics'],
 ['-m','schrodinger_lab.experiments','--out',str(out/'physics_joint'),'--trials','20','--steps','32','--epsilon','.02','--scenarios','physics','--joint'],
 ['-m','schrodinger_lab.control','--out',str(out/'control'),'--trials','20','--steps','32'],
 ['-m','schrodinger_lab.studies','scaling','--out',str(out/'studies')]]
for cmd in commands:
    print('Running:',*cmd,flush=True);subprocess.run([sys.executable,*cmd],check=True)
print('Completed:',out.resolve())
