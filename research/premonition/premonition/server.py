"""Local, loopback-only scientific server; no hardware interface or remote service."""
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
import json,urllib.parse,threading
import numpy as np
from .physics import *
from .stability import spectrum,observability
from .io import clean
ROOT=Path(__file__).resolve().parents[1]
LOCK=threading.Lock()
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)
    def send_json(self,data,status=200):
        b=json.dumps(clean(data),allow_nan=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
    def do_GET(self):
        if self.path=='/api/health':return self.send_json({'ok':True,'mode':'local CPU science','version':'1.0.0'})
        if self.path=='/':self.path='/PREMONITION_LAB.html'
        return super().do_GET()
    def do_POST(self):
        if self.path not in ['/api/equilibria','/api/simulate']:return self.send_json({'error':'unknown endpoint'},404)
        try:
            n=int(self.headers.get('Content-Length','0'))
            if n>4096:raise ValueError('request too large')
            args=json.loads(self.rfile.read(n));u=U0.copy()
            if self.path=='/api/equilibria':
                mw=float(args.get('mw',U0[3]));t0=float(args.get('T0',U0[4]))
                if not UMIN<=mw<=UMAX or not 275<=t0<=325:raise ValueError('Parameters outside study domain')
                u[3]=mw;u[4]=t0;xx=equilibria(u)
                return self.send_json({'inputs':u,'equilibria':[dict(x=x,eig=spectrum(x,u),observability=observability(x,u)) for x in xx]})
            seed=int(args.get('seed',50000));mode=args.get('mode','C4')
            if mode not in ['C0','C1','C2','C3','C4','conservative','C4_noEWS']:raise ValueError('Choose an operational controller')
            if not 0<=seed<2**31:raise ValueError('Seed outside range')
            from .detectors import load_models
            from .control_campaign import rollout
            if not LOCK.acquire(False):return self.send_json({'error':'A simulation is running. Retry after completion.'},409)
            try:
                models=load_models(ROOT/'results/CD/models');thresholds=json.loads((ROOT/'results/CD/thresholds.json').read_text());m,r=rollout(seed,mode,models,thresholds);return self.send_json(dict(metrics=m,rows=r))
            finally:LOCK.release()
        except Exception as e:self.send_json({'error':str(e)},400)

def serve(port=8765,open_browser=True):
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    print(f'YCS Premonition-MPC http://127.0.0.1:{port} (Ctrl+C to stop)',flush=True)
    if open_browser:
        import webbrowser
        webbrowser.open(f'http://127.0.0.1:{port}')
    server.serve_forever()
