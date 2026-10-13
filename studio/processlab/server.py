"""Development/local browser host: loopback only, token and Origin protected API."""
import hmac
import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, unquote
from .models import ROOT


def serve(api,port=0):
    token=secrets.token_urlsafe(32);web=(ROOT/"studio"/"ui"/"dist").resolve()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def send_headers(self,code,mime):
            self.send_response(code);self.send_header("Content-Type",mime)
            self.send_header("X-Content-Type-Options","nosniff");self.send_header("Cache-Control","no-store")
            self.send_header("Content-Security-Policy","default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers()
        def do_GET(self):
            if self.headers.get("Host")!=f"127.0.0.1:{self.server.server_port}":self.send_headers(403,"text/plain");return
            route=unquote(urlparse(self.path).path);path=(web/route.lstrip("/")).resolve()
            if route=="/":path=web/"index.html"
            if not path.is_relative_to(web) or not path.is_file():self.send_headers(404,"text/plain");return
            import mimetypes
            self.send_headers(200,mimetypes.guess_type(path)[0] or "application/octet-stream");self.wfile.write(path.read_bytes())
        def do_POST(self):
            origin=f"http://127.0.0.1:{self.server.server_port}"
            if self.path!="/api" or self.headers.get("Host")!=origin[7:] or self.headers.get("Origin",origin)!=origin or not hmac.compare_digest(self.headers.get("X-ProcessLab-Token",""),token):
                self.send_headers(403,"application/json");self.wfile.write(b'{"ok":false,"error":"Unauthorized local request"}');return
            try:
                size=int(self.headers.get("Content-Length","0"))
                if not 0<size<=2_000_000:raise ValueError("Invalid request size")
                data=json.loads(self.rfile.read(size));response=api.request(data["method"],data.get("payload"))
                body=json.dumps(response,allow_nan=False,ensure_ascii=False).encode()
                self.send_headers(200,"application/json; charset=utf-8");self.wfile.write(body)
            except (ValueError,KeyError,TypeError) as error:
                self.send_headers(400,"application/json");self.wfile.write(json.dumps({"ok":False,"error":str(error)}).encode())
    httpd=ThreadingHTTPServer(("127.0.0.1",port),Handler);httpd.daemon_threads=True
    thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
    return httpd,f"http://127.0.0.1:{httpd.server_port}/#token={token}"
