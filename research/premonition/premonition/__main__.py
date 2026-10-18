import argparse,subprocess,sys
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description='YCS Premonition-MPC scientific laboratory')
    p.add_argument('command',choices=['audit','A','B','CD','EF','all','reports','dashboard','serve']);p.add_argument('--out',default='results');p.add_argument('--n',type=int,default=100);p.add_argument('--pilot',action='store_true');p.add_argument('--port',type=int,default=8765);p.add_argument('--no-browser',action='store_true');p.add_argument('--report-out');a=p.parse_args();root=Path(a.out)
    if a.command in ['audit','all']:
        from .audit import physical_audit
        physical_audit(root/'physical_audit.json')
    if a.command in ['A','all']:
        from .stability import campaign_A
        campaign_A(root/'A')
    if a.command in ['B','all']:
        from .bifurcation_campaign import campaign_B
        campaign_B(root/'B',n=a.n)
    if a.command in ['CD','all']:
        from .detection_campaign import campaign_CD
        campaign_CD(root/'CD',pilot=a.pilot)
    if a.command in ['EF','all']:
        from .control_campaign import campaign_EF
        campaign_EF(root/'EF',root/'CD/models',root/'CD/thresholds.json',n=a.n,pilot=a.pilot)
    if a.command in ['reports','all']:
        project=Path(__file__).resolve().parents[1]
        reports=Path(a.report_out) if a.report_out else root.with_name('reports' if root.name=='results' else 'reports_'+root.name)
        subprocess.run([sys.executable,str(project/'scripts/extra_validation.py'),'--results',str(root.resolve())],check=True)
        subprocess.run([sys.executable,str(project/'scripts/make_reports.py'),'--results',str(root.resolve()),'--reports',str(reports.resolve())],check=True)
    if a.command in ['dashboard','all']:
        from .dashboard import build
        build(root)
    if a.command=='serve':
        from .server import serve
        serve(a.port,not a.no_browser)
if __name__=='__main__':main()
