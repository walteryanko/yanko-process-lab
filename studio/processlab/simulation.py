import copy
import hashlib
import json
import platform
import time
from datetime import datetime, timezone
from importlib.metadata import version, PackageNotFoundError
import numpy as np
from . import __version__
from .schema import canonical
from .models import build_model, ROOT
from .numerics import integrate
from .sensors import Sensors
from .estimation import Observer
from .control import Controller


def manifest(project):
    deps={}
    for name in ("numpy","scipy","pint","casadi","pywebview"):
        try:deps[name]=version(name)
        except PackageNotFoundError:deps[name]="not installed"
    revision="unknown";dirty=None
    if (ROOT/"studio"/"build-info.json").exists():
        revision=json.loads((ROOT/"studio"/"build-info.json").read_text())["commit"]
    else:
        import subprocess
        try:
            revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,stderr=subprocess.DEVNULL,text=True,timeout=2).strip()
            dirty=bool(subprocess.check_output(["git","status","--porcelain"],cwd=ROOT,stderr=subprocess.DEVNULL,text=True,timeout=2).strip())
        except (OSError,subprocess.SubprocessError):pass
    content=json.dumps(project,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    engine_files=sorted((ROOT/"studio/processlab").glob("*.py"))
    engine_hash=hashlib.sha256(b"".join(p.name.encode()+b"\0"+p.read_bytes() for p in engine_files)).hexdigest() if engine_files else None
    return {"application_version":__version__,"git_commit":revision,"working_tree_dirty":dirty,"engine_source_sha256":engine_hash,"project_sha256":hashlib.sha256(content).hexdigest(),"created_utc":datetime.now(timezone.utc).isoformat(),"python":platform.python_version(),"platform":platform.platform(),"dependencies":deps,"project":copy.deepcopy(project),"truth_used_for":"physical simulation, emulated sensors and retrospective scoring only","uncertainty":"Uncalibrated approximate covariance; MHE uses EKF companion covariance","hardware_validation":"Runtime host only; not a measurement on the user's laptop"}


class Simulation:
    def __init__(self,project):
        self.project=canonical(project);self.c=self.project["experiment"];self.model=build_model(self.project)
        if not len(self.model.x0):raise ValueError("Dynamic simulation requires a tank or CSTR; use steady-state solve for algebraic flowsheets")
        self.truth=self.model.x0.copy();self.sensors=Sensors(self.model,self.c)
        self.observer=None if self.c["observer"]=="none" else Observer(self.model,self.c)
        self.controller=Controller(self.model,self.c);self.step_number=0
        self.status="ready";self.error=None;self.rows=[];self.events=[];self.wall_seconds=0.
        self.stats={"nfev":0,"integration_calls":0,"max_step_wall_seconds":0.}
        self.manifest=manifest(self.project)
        events=self.sensors.sample(0,self.truth);self.events.extend(events)
        if self.observer:self.observer.assimilate(0,events)
        self._record(self.controller.last)

    def disturbance(self,step):
        return self.c["disturbance_value"] if step*self.c["dt"]>=self.c["disturbance_time"] else 0.

    def advance(self,count=1):
        if self.status in ("completed","failed","constraint_stop"):return self.snapshot()
        for _ in range(min(max(int(count),1),20)):
            if (self.step_number+1)*self.c["dt"]>self.c["duration"]+1e-8:
                self.status="completed";break
            tick=time.perf_counter()
            try:
                d=self.disturbance(self.step_number)
                u=self.controller.act(None if self.observer is None else self.observer.x.copy(),self.sensors.last_values,d)
                nxt=integrate(self.model,self.truth,u,d,self.c["dt"],self.c,self.stats)
                if self.observer:self.observer.advance(u,d)
                events=self.sensors.sample(self.step_number+1,nxt)
                if self.observer:self.observer.assimilate(self.step_number+1,events)
                self.truth=nxt;self.step_number+=1;self.events.extend(events);self._record(u)
                self.status="paused"
                if self.truth[self.model.tidx]>self.model.temperature_limit:
                    self.status="constraint_stop";self.error="Configured thermal study limit crossed; simulation stopped. This is detection, not a safety guarantee."
                    break
            except (ValueError,OverflowError,np.linalg.LinAlgError,FloatingPointError) as e:
                self.status="failed";self.error=str(e);break
            finally:
                elapsed=time.perf_counter()-tick;self.wall_seconds+=elapsed
                self.stats["max_step_wall_seconds"]=max(self.stats["max_step_wall_seconds"],elapsed)
        return self.snapshot()

    def _record(self,u):
        o=self.observer
        q_est=None if o is None else self.model.quality(o.x)
        cv=self.model.quality(self.truth) if self.c["control_target"]=="quality" else self.truth[self.model.tidx]
        age=None if self.sensors.last_sample is None else (self.step_number-self.sensors.last_sample)*self.c["dt"]
        self.rows.append({"t":self.step_number*self.c["dt"],"truth":self.truth.tolist(),"estimate":None if o is None else o.x.tolist(),"sd":None if o is None else np.sqrt(np.diag(o.P)).tolist(),"measured":self.sensors.last_values,"measurement_age_s":age,"input":float(u),"setpoint":self.c["setpoint"],"quality_truth":self.model.quality(self.truth),"quality_estimate":q_est,"control_error":float(cv-self.c["setpoint"]),"temperature_violation":max(0.,float(self.truth[self.model.tidx]-self.model.temperature_limit))})

    def snapshot(self):
        m=self.model;o=self.observer
        metrics={"wall_seconds":self.wall_seconds,"samples":len(self.rows),"sensor_samples":self.sensors.acquired,"sensor_drops":self.sensors.dropped}
        if len(self.rows)>1:
            errors=np.array([r["control_error"] for r in self.rows]);t=np.array([r["t"] for r in self.rows])
            metrics.update(iae=float(np.trapezoid(abs(errors),t)),itae=float(np.trapezoid(t*abs(errors),t)),max_temperature_violation=max(r["temperature_violation"] for r in self.rows),control_effort=float(np.sum(np.diff([r["input"] for r in self.rows])**2)))
            if o is not None:
                delta=np.array([r["estimate"] for r in self.rows])-np.array([r["truth"] for r in self.rows])
                metrics["state_rmse"]=np.sqrt(np.mean(delta**2,axis=0)).tolist()
                metrics["quality_rmse"]=float(np.sqrt(np.mean([(r["quality_estimate"]-r["quality_truth"])**2 for r in self.rows])))
                sd=np.array([r["sd"] for r in self.rows]);metrics["empirical_2sd_coverage"]=np.mean(abs(delta)<=2*sd,axis=0).tolist()
        stream_result=None
        if hasattr(m,"evaluate"):
            stream_result=m.evaluate(self.truth,self.rows[-1]["input"],self.disturbance(max(0,self.step_number-1)))
            stream_result.pop("derivative")
        return {"status":self.status,"error":self.error,"time":self.step_number*self.c["dt"],"rows":self.rows,"events":self.events,"metrics":metrics,"solver":self.stats,"controller":self.controller.diagnostics,"observer":None if o is None else o.diagnostics,"streams":stream_result,"metadata":{"names":m.names,"units":m.state_units,"temperature_index":m.tidx,"quality_index":m.qidx,"measurement_indices":m.measurement_indices,"input_name":m.input_name,"input_unit":m.input_unit,"input_bounds":m.bounds,"temperature_limit":m.temperature_limit,"parameters":getattr(m,"parameters",{}),"provenance":m.provenance},"manifest":self.manifest}

    def run(self):
        while self.status not in ("completed","failed","constraint_stop"):
            self.advance(20)
        return self.snapshot()

    @classmethod
    def replay(cls,record):
        simulation=cls(record["manifest"]["project"])
        events=record["manifest"].get("setpoint_events",[])
        target=len(record["rows"])-1
        for k in range(target):
            for e in events:
                if e["at_step"]==k:simulation.c["setpoint"]=float(e["value"])
            simulation.advance(1)
            if simulation.status in ("failed","constraint_stop"):break
        simulation.manifest["setpoint_events"]=copy.deepcopy(events)
        return simulation.snapshot()
