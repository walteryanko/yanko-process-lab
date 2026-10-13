"""Adapters reuse archived implementations without altering source equations."""
import importlib.util
import sys
from functools import lru_cache
from pathlib import Path
from dataclasses import asdict
import numpy as np
from .flowsheet import Flowsheet

ROOT = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[2]


@lru_cache(maxsize=2)
def reference(kind):
    path = ROOT/"research"/"beyond"/"vendor"/f"{kind}_reference.py"
    name = f"processlab_archived_{kind}"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class ResearchModel:
    def __init__(self, model_id):
        self.kind = "pg" if model_id == "pg-original" else "eb"
        self.ref = reference(self.kind)
        r = self.ref
        if self.kind == "pg":
            self.x0 = r.steady()["x"].copy(); self.u0 = float(r.U0[1]); self.tidx = 4; self.qidx = 2
            self.names = ["C_A", "C_B", "C_C", "C_M", "T", "T_t"]
            self.state_units = ["kmol/m³"]*4+["K"]*2
            self.measurement_indices = [4,5]; self.scale = np.array([.2, 5., .5, 1., 5., 5.])
            self.bounds = (.05*self.u0, 3*self.u0); self.slew = self.u0/600
            self.input_name = "Vazão de refrigerante"; self.input_unit = "kmol/h"
            self.temperature_limit = (160-32)/1.8+273.15
            self.parameters = asdict(r.Parameters())
            self.provenance = "modeloCT.m (2019), literal SI conversion; native time h, adapted to s. No enthalpy fitting. Jacket asymmetry preserved."
        else:
            self.x0 = r.XSS.copy(); self.u0 = float(r.U0[3]); self.tidx = 4; self.qidx = 2
            self.names = ["C_E", "C_B", "C_EB", "C_DEB", "T1"]
            self.state_units = ["kmol/m³"]*4+["°C"]
            self.measurement_indices = [4]; self.scale = np.array([.01, .5, .3, .05, 5.])
            self.bounds = (.75*self.u0, 1.25*self.u0); self.slew = .5*self.u0/3600
            self.input_name = "Calor retirado"; self.input_unit = "kcal/h"
            self.temperature_limit = 165.
            self.parameters = {"V_m3": r.V, "DH_kcal_kmol": r.DH.tolist(), "Q0_kcal_h": r.Q0, "constant_rhoCp": r.RHOC}
            self.provenance = "Reduced single R1 reconstruction; Q0 calibrated at 160 °C, unreconciled thermal balance. NOT the two-reactor Aspen plant."

    def rhs(self, x, u, disturbance=0.):
        if self.kind == "pg":
            inputs = self.ref.U0.copy(); inputs[1] = u
            from dataclasses import replace
            p = replace(self.ref.Parameters(), T0=self.ref.Parameters().T0+disturbance)
            return self.ref.rhs(0, x, inputs, p)/3600
        inputs = self.ref.U0.copy(); inputs[3] = u; inputs[4:] += disturbance
        return np.asarray(self.ref.F(x, inputs, np.zeros(12))).ravel()/3600

    def quality(self, x):
        return float(x[2]) if self.kind == "pg" else float(x[2]/np.sum(x[:4]))

    def check(self, x):
        x = np.asarray(x)
        lower = 150 if self.kind == "pg" else -20
        upper = 600 if self.kind == "pg" else 350
        if not np.isfinite(x).all() or min(x[:4]) < -1e-9 or not lower <= x[4] <= upper or (self.kind == "pg" and not 150 <= x[5] <= 600):
            raise ValueError("Research model left its numerical domain")


def build_model(project):
    return Flowsheet(project) if project["model"] == "flowsheet" else ResearchModel(project["model"])
