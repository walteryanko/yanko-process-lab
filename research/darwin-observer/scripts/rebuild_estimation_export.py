"""Regenerate the v1.0 CSV export from frozen models, without refitting.

The pre-existing repository gzip failed its CRC/decompression check. This repair
re-executes the original 100-seed evaluations and does not infer rows from means.
"""
import csv,gzip,json,sys,shutil
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from darwin import experiments as ex
from darwin.metrics import summary

def task(arg):
    ex.save_episode=lambda *a,**k:None
    return ex.eval_scenario(arg)

def main():
    out=ROOT/'artifacts'/'export_repair';out.mkdir(exist_ok=True)
    source=ROOT/'artifacts'/'main'
    shutil.copytree(source/'models',out/'models',dirs_exist_ok=True)
    shutil.copyfile(source/'calibration.json',out/'calibration.json')
    rows=[];errors=[]
    with ProcessPoolExecutor(2) as pool:
        futures=[pool.submit(task,(s,i,str(out),100)) for i,s in enumerate(ex.TEST_SCENARIOS)]
        for f in as_completed(futures):
            s,r,e=f.result();rows+=r;errors+=e;print(s,len(r),len(e),flush=True)
    if errors:raise RuntimeError(errors)
    rows.sort(key=lambda r:(r['scenario'],r['seed'],r['method']))
    ex.savecsv(out/'estimation.csv',rows)
    old=json.loads((source/'estimation_summary.json').read_text())
    new=summary(rows)
    # Preserve the original report, but retain a complete new summary for audit.
    ex.savejson(out/'estimation_summary.json',new)
    raw=(out/'estimation.csv').read_bytes()
    packed=gzip.compress(raw,mtime=0)
    assert gzip.decompress(packed)==raw
    (source/'estimation.csv.gz').write_bytes(packed)
    print(json.dumps(dict(rows=len(rows),gzip_bytes=len(packed),old_summary_equal=old==new)))

if __name__=='__main__':main()
