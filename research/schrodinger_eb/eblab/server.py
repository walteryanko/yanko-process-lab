"""Local-only laboratory server; offline replay needs no server."""
import argparse,json,uuid,threading,webbrowser
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse
from dataclasses import replace
from .experiments import generate,run,measurement_spec,serial,SCENARIOS
from .filters import FilterConfig,METHODS

ROOT=Path(__file__).resolve().parents[1]
JOBS={};POOL=ThreadPoolExecutor(max_workers=1)

def validate_config(data):
    scenario=data.get('scenario','gaussian');n=int(data.get('particles',128));steps=int(data.get('steps',60));seed=int(data.get('seed',4242))
    if scenario not in SCENARIOS or n not in [64,128,256,512,1024] or not 8<=steps<=96 or not 0<=seed<2**31:
        raise ValueError('Configuração fora dos limites do laboratório')
    return scenario,n,steps,seed

def compute(job,data):
    try:
        scenario,n,steps,seed=validate_config(data);ep=generate(seed,scenario,steps)
        _,kind=measurement_spec(scenario);cfg=FilterConfig(particles=n,epsilon=.1,bridge_steps=64,likelihood=kind,noise_state=scenario if scenario in ('bias','correlated') else None)
        bundle={}
        for i,method in enumerate(METHODS):
            JOBS[job].update(progress=i/6,message='Executando '+METHODS[method])
            result,trace=run(ep,method,cfg,record_particles=True);bundle[method]=serial(dict(episode=ep,result=result,trace=trace))
        JOBS[job].update(status='done',progress=1,data=bundle)
    except Exception as exc:JOBS[job].update(status='error',error=str(exc))

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT/'web'),**kwargs)
    def log_message(self,*args):pass
    def json(self,value,status=200):
        raw=json.dumps(serial(value),ensure_ascii=False,allow_nan=False).encode('utf-8')
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/api/status':return self.json(dict(online=True,version='1.0.0'))
        if path.startswith('/api/jobs/'):
            return self.json(JOBS.get(path.split('/')[-1],dict(status='missing')))
        return super().do_GET()
    def do_POST(self):
        if self.path!='/api/run':return self.json({'error':'Not found'},404)
        origin=self.headers.get('Origin')
        if origin and urlparse(origin).netloc!=self.headers.get('Host'):return self.json({'error':'Origin rejected'},403)
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<4096:raise ValueError('Invalid request size')
            data=json.loads(self.rfile.read(size));validate_config(data)
            if any(v['status']=='running' for v in JOBS.values()):return self.json({'error':'Já há uma execução em andamento'},409)
            job=uuid.uuid4().hex;JOBS[job]=dict(status='running',progress=0,message='Gerando trajetória')
            # Keep only the last eight jobs to bound application memory.
            while len(JOBS)>8:JOBS.pop(next(iter(JOBS)))
            POOL.submit(compute,job,data);return self.json(dict(job=job))
        except (ValueError,TypeError,json.JSONDecodeError) as exc:return self.json({'error':str(exc)},400)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765);parser.add_argument('--no-browser',action='store_true');args=parser.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(f'YCS Schrödinger-KF: http://127.0.0.1:{args.port}',flush=True)
    if not args.no_browser:threading.Timer(.5,lambda:webbrowser.open(f'http://127.0.0.1:{args.port}')).start()
    try:server.serve_forever()
    except KeyboardInterrupt:server.server_close()

if __name__=='__main__':main()
