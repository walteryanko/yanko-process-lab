"""Native Windows host; CLI and smoke mode use the same API and numerical engine."""
import os
os.environ.setdefault("OPENBLAS_NUM_THREADS","1")
os.environ.setdefault("OMP_NUM_THREADS","1")
import argparse
import json
import logging
import sys
from pathlib import Path
from processlab.api import API
from processlab.models import ROOT
from processlab.storage import atomic_json


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--browser",action="store_true");parser.add_argument("--port",type=int,default=0)
    parser.add_argument("--data-dir");parser.add_argument("--smoke",action="store_true")
    parser.add_argument("--smoke-output");parser.add_argument("--run");parser.add_argument("--replay");parser.add_argument("--output")
    parser.add_argument("--gui-smoke-output")
    args=parser.parse_args();api=API(args.data_dir)
    logging.basicConfig(filename=api.storage.root/"processlab.log",level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")
    if args.smoke:
        boot=api.request("bootstrap");assert boot["ok"],boot
        cases=[]
        for p in boot["data"]["scenarios"]:
            for method,payload in [("save",p),("open",{"id":p["id"]}),("reset",p),("advance",{"count":3})]:
                response=api.request(method,payload);assert response["ok"],response
            result=response["data"]
            assert result["status"] not in ("failed","constraint_stop"),response
            if getattr(sys,"frozen",False):
                assert result["manifest"]["engine_source_sha256"],"Bundled engine source provenance missing"
                assert "not installed" not in result["manifest"]["dependencies"].values(),"Dependency metadata missing"
            cases.append({"id":p["id"],"model":p["model"],"time":result["time"],"status":result["status"],"manifest":result["manifest"]})
        out={"ok":True,"frozen":bool(getattr(sys,"frozen",False)),"time":result["time"],"platform":sys.platform,"ui_exists":(ROOT/"studio/ui/dist/index.html").is_file(),"cases":cases}
        if args.smoke_output:atomic_json(args.smoke_output,out)
        print(json.dumps(out));return
    if args.run or args.replay:
        from processlab.simulation import Simulation
        if args.replay:
            result=Simulation.replay(json.loads(Path(args.replay).read_text("utf-8")))
        else:
            p=json.loads(Path(args.run).read_text("utf-8"));sim=Simulation(p);result=sim.run()
        atomic_json(args.output or "experiment-result.json",result)
        if result["status"] in ("failed","constraint_stop"):raise SystemExit(1)
        return
    if args.browser:
        from processlab.server import serve
        server,url=serve(api,args.port);print(url,flush=True)
        try:
            import threading
            threading.Event().wait()
        except KeyboardInterrupt:server.shutdown()
        return
    import webview
    index=ROOT/"studio/ui/dist/index.html"
    if not index.exists():raise RuntimeError("Frontend bundle missing: run npm run build in studio/ui")
    window=webview.create_window("YCS ProcessLab Studio",str(index),js_api=api,width=1360,height=850,min_size=(1000,680),background_color="#10161f")
    if args.gui_smoke_output:
        import time
        def smoke():
            deadline=time.monotonic()+45
            while time.monotonic()<deadline:
                try:
                    ready=window.evaluate_js("document.querySelector('[data-testid=\"studio-ready\"]') !== null")
                    if ready:
                        atomic_json(args.gui_smoke_output,{"ok":True,"renderer":"edgechromium","frozen":bool(getattr(sys,"frozen",False)),"ui_rendered":True})
                        window.destroy();return
                except Exception:pass
                time.sleep(.25)
            atomic_json(args.gui_smoke_output,{"ok":False,"error":"UI not ready within 45 seconds"});window.destroy()
        webview.start(smoke,gui="edgechromium" if sys.platform=="win32" else None)
    else:webview.start(gui="edgechromium" if sys.platform=="win32" else None)


if __name__=="__main__":main()
