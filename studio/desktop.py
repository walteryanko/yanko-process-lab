"""Native Windows host; CLI and smoke mode use the same API and numerical engine."""
import os
os.environ.setdefault("OPENBLAS_NUM_THREADS","1")
os.environ.setdefault("OMP_NUM_THREADS","1")
import argparse
import json
import logging
import sys
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--browser",action="store_true");parser.add_argument("--port",type=int,default=0)
    parser.add_argument("--data-dir");parser.add_argument("--smoke",action="store_true")
    parser.add_argument("--smoke-output");parser.add_argument("--run");parser.add_argument("--replay");parser.add_argument("--output")
    parser.add_argument("--gui-smoke-output")
    args=parser.parse_args()
    from processlab.api import API
    from processlab.models import ROOT
    from processlab.storage import atomic_json
    api=API(args.data_dir)
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
        lab_evidence={}
        for kind in ("comparison","tuning"):
            payload={"project":boot["data"]["scenarios"][1],"kind":kind,"options":{"steps":4,"budget":3,"time_budget_s":30},"variants":[{"label":"PID","experiment":{}},{"label":"Manual","experiment":{"controller":"manual"}}]}
            job=api.request("lab_start",payload);assert job["ok"],job
            api.laboratory.worker.join(40)
            status=api.request("lab_status");assert status["data"]["status"]=="completed",status
            record=api.request("lab_read",{"id":job["data"]["id"]});assert record["ok"],record
            lab_evidence[kind]={"runs":len(record["data"]["runs"]),"candidates":len(record["data"]["candidates"]),"status":record["data"]["status"]}
        out={"ok":True,"frozen":bool(getattr(sys,"frozen",False)),"time":result["time"],"platform":sys.platform,"ui_exists":(ROOT/"studio/ui/dist/index.html").is_file(),"cases":cases,"laboratory":lab_evidence}
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
                        window.evaluate_js("Array.from(document.querySelectorAll('.tabs button')).find(b => b.textContent === 'Laboratório').click()")
                        time.sleep(.2)
                        lab_ready=window.evaluate_js("document.querySelector('.laboratory-page').getBoundingClientRect().height > 0")
                        window.evaluate_js("window.dispatchEvent(new KeyboardEvent('keydown', {key:'F1',bubbles:true}))")
                        time.sleep(.2)
                        help_ready=window.evaluate_js("document.querySelector('[role=dialog]') !== null")
                        atomic_json(args.gui_smoke_output,{"ok":bool(lab_ready and help_ready),"renderer":"edgechromium","frozen":bool(getattr(sys,"frozen",False)),"ui_rendered":True,"laboratory_rendered":bool(lab_ready),"help_rendered":bool(help_ready)})
                        window.destroy();return
                except Exception:pass
                time.sleep(.25)
            atomic_json(args.gui_smoke_output,{"ok":False,"error":"UI not ready within 45 seconds"});window.destroy()
        webview.start(smoke,gui="edgechromium" if sys.platform=="win32" else None)
    else:webview.start(gui="edgechromium" if sys.platform=="win32" else None)


if __name__=="__main__":
    try:main()
    except Exception as error:
        import traceback
        diagnostic={"ok":False,"error":str(error),"type":type(error).__name__,"traceback":traceback.format_exc()}
        folder=Path(os.environ.get("APPDATA",Path.home()))/"YCS ProcessLab Studio"
        outputs=[folder/"startup-error.json"]
        for flag in ("--smoke-output","--gui-smoke-output"):
            if flag in sys.argv and sys.argv.index(flag)+1<len(sys.argv):
                outputs.append(Path(sys.argv[sys.argv.index(flag)+1]))
        for target in outputs:
            try:
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_text(json.dumps(diagnostic,indent=2),encoding="utf-8")
            except OSError:pass
        if sys.stderr is not None:traceback.print_exc()
        if sys.platform=="win32" and not any(flag in sys.argv for flag in ("--smoke","--gui-smoke-output","--run","--replay")):
            import ctypes
            ctypes.windll.user32.MessageBoxW(None,f"Não foi possível iniciar o ProcessLab Studio.\n\n{error}\n\nDetalhes: {outputs[0]}","YCS ProcessLab Studio",16)
        raise SystemExit(1)
