import csv
import io
import threading
from .schema import canonical,CATALOG
from .models import build_model
from .scenarios import scenarios
from .simulation import Simulation
from .storage import Storage,atomic_json,atomic_bytes


class API:
    def __init__(self,directory=None):
        self.storage=Storage(directory);self.sim=None;self.lock=threading.RLock()

    def request(self,method,payload=None):
        payload={} if payload is None else payload
        with self.lock:
            try:return {"ok":True,"data":self._request(method,payload)}
            except Exception as e:
                import logging
                logging.getLogger("processlab").exception("Request failed: %s",method)
                return {"ok":False,"error":str(e),"type":type(e).__name__}

    def _request(self,method,p):
        if method=="bootstrap":return {"scenarios":scenarios(),"catalog":CATALOG,"saved":self.storage.list(),"storage":str(self.storage.root)}
        if method=="save":return self.storage.save(p)
        if method=="open":return self.storage.load(p["id"])
        if method=="validate":
            project=canonical(p);m=build_model(project)
            m.check(m.x0)
            return {"valid":True,"states":len(m.x0),"provenance":m.provenance}
        if method=="steady":
            project=canonical(p);m=build_model(project)
            if hasattr(m,"steady"):
                x,result=m.steady(project["experiment"]["manual"]);result.pop("derivative",None)
            else:
                from scipy.optimize import root
                import numpy as np
                sol=root(lambda x:m.rhs(x,project["experiment"]["manual"]),m.x0)
                if not sol.success or max(abs(sol.fun))>1e-8:raise ValueError("Steady-state solver did not converge")
                m.check(sol.x);x=sol.x;result={"derivative_max":float(np.max(abs(sol.fun)))}
            return {"state":x.tolist(),"names":m.names,"result":result}
        if method=="reset":
            candidate=Simulation(p);self.sim=candidate;return candidate.snapshot()
        if method=="advance":
            if self.sim is None:raise ValueError("Initialize a simulation first")
            return self.sim.advance(p.get("count",1))
        if method=="inspect":
            if self.sim is None:return None
            return self.sim.snapshot()
        if method=="setpoint":
            if self.sim is None:raise ValueError("Initialize first")
            config={**self.sim.project,"experiment":{**self.sim.c,"setpoint":p["setpoint"]}}
            cfg=canonical(config)["experiment"];self.sim.c["setpoint"]=cfg["setpoint"]
            self.sim.manifest.setdefault("setpoint_events",[]).append({"at_step":self.sim.step_number,"value":cfg["setpoint"]})
            return {"setpoint":cfg["setpoint"]}
        if method=="observability":
            if self.sim is None or self.sim.observer is None:raise ValueError("Initialize a virtual sensor first")
            return self.sim.observer.observability(self.sim.controller.last)
        if method=="export":
            if self.sim is None:raise ValueError("No experiment to export")
            result=self.sim.snapshot();path=self.storage.root/"experiments"/(self.sim.project["id"]+"-last.json")
            atomic_json(path,result);return {"path":str(path),"result":result}
        if method=="export_project":
            project=canonical(p);path=self.storage.root/"exports"/(project["id"]+".processlab.json")
            atomic_json(path,project);return {"path":str(path),"project":project}
        if method=="export_csv":
            if self.sim is None:raise ValueError("No experiment to export")
            out=io.StringIO(newline="");writer=csv.writer(out);names=self.sim.model.names
            writer.writerow(["time_s"]+[f"truth_{n}" for n in names]+[f"estimated_{n}" for n in names]+["input","setpoint"])
            for row in self.sim.rows:
                writer.writerow([row["t"]]+row["truth"]+(row["estimate"] or [""]*len(names))+[row["input"],row["setpoint"]])
            path=self.storage.root/"exports"/(self.sim.project["id"]+".csv");content=out.getvalue()
            atomic_bytes(path,content.encode("utf-8"));return {"path":str(path),"csv":content}
        raise ValueError("Unsupported API operation")
