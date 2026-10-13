"""Executable acyclic, constant-density liquid networks in SI.

The tracer A and product B share molecular mass; x is A mass fraction.
The pressure calculation is forward-specified, not a hydraulic network solve.
"""
import copy
from dataclasses import dataclass, asdict
import numpy as np
from scipy.optimize import root
from .schema import CATALOG

CP, RHO = 4180., 1000.


@dataclass
class Stream:
    flow: float
    temperature: float
    fraction: float
    pressure: float

    def check(self):
        if not np.isfinite(list(asdict(self).values())).all() or self.flow <= 0 or not 273.15 <= self.temperature <= 373.15 or not -1e-9 <= self.fraction <= 1+1e-9 or self.pressure <= 0:
            raise ValueError("Stream outside the liquid property model domain")
        return self


class Flowsheet:
    def __init__(self, project):
        self.project = copy.deepcopy(project)
        self.units = {n["id"]: n for n in project["nodes"]}
        self.inlets = {}; self.energy = {}; self.outgoing = {}; incoming = {k: 0 for k in self.units}
        edge_ids = set()
        for edge in project["edges"]:
            eid, a, b = edge.get("id"), edge.get("source"), edge.get("target")
            sp, tp = edge.get("source_port", "out"), edge.get("target_port", "in")
            if not isinstance(eid, str) or eid in edge_ids or a not in self.units or b not in self.units or a == b:
                raise ValueError("Invalid stream ID or endpoints")
            edge_ids.add(eid)
            ca, cb = CATALOG[self.units[a]["kind"]], CATALOG[self.units[b]["kind"]]
            kind = edge.get("kind", "material")
            if kind == "energy":
                if self.units[a]["kind"] != "energy" or sp != "heat" or tp != "heat" or not cb.get("energy") or b in self.energy:
                    raise ValueError("Incompatible energy ports")
                self.energy[b] = a
            elif kind == "material":
                if self.units[a]["kind"] == "energy" or sp not in ca["outputs"] or tp not in cb["inputs"] or (b, tp) in self.inlets or (a, sp) in self.outgoing:
                    raise ValueError("Incompatible/occupied material ports; use a splitter to branch")
                self.inlets[b, tp] = (a, sp); self.outgoing[a, sp] = b
            else:
                raise ValueError("Unsupported stream type; instrumentation is configured separately")
            incoming[b] += 1
        for n in self.units.values():
            c = CATALOG[n["kind"]]
            if any((n["id"], port) not in self.inlets for port in c["inputs"]):
                raise ValueError(f"{n['id']}: connect every required input")
            if n["kind"] != "energy" and any((n["id"], port) not in self.outgoing for port in c["outputs"]):
                raise ValueError(f"{n['id']}: connect every outlet to preserve material balance")
            if n["kind"] == "energy" and n["id"] not in self.energy.values():
                raise ValueError(f"{n['id']}: unused energy source")
        order = []; queue = [k for k, v in incoming.items() if v == 0]
        while queue:
            a = queue.pop(0); order.append(a)
            for edge in project["edges"]:
                if edge["source"] == a:
                    incoming[edge["target"]] -= 1
                    if incoming[edge["target"]] == 0:
                        queue.append(edge["target"])
        if len(order) != len(self.units):
            raise ValueError("Recycle/DAE loops are not supported in this version")
        self.order = order
        self.dynamic = [k for k in order if self.units[k]["kind"] in ("tank", "cstr")]
        self.indices = {k: 2*i for i, k in enumerate(self.dynamic)}
        self.x0 = np.array([v for k in self.dynamic for v in (self.units[k]["parameters"]["fraction"], self.units[k]["parameters"]["temperature"])])
        self.names = [v for k in self.dynamic for v in (f"{k}.A", f"{k}.T")]
        self.state_units = [v for _ in self.dynamic for v in ("kg/kg", "K")]
        self.target = project.get("control_equipment", self.dynamic[-1] if self.dynamic else None)
        if self.target is not None and self.target not in self.dynamic:
            raise ValueError("Control target must be a dynamic tank or CSTR")
        self.tidx = self.indices[self.target]+1 if self.target else None
        self.qidx = self.indices[self.target] if self.target else None
        self.measurement_indices = list(range(1, len(self.x0), 2))
        self.input_name = "Potência no tanque"; self.input_unit = "W"
        self.bounds = (0., 100000.); self.slew = 20000.
        self.u0 = self.units[self.target]["parameters"]["duty"] if self.target else 0.
        self.scale = np.array([v for _ in self.dynamic for v in (.1, 10.)])
        self.temperature_limit = 373.15
        self.provenance = "Liquid/tracer constant Cp=4180 J/(kg K), rho=1000 kg/m³; no phase equilibrium or hydraulic solve"

    def evaluate(self, x=None, manipulated=None, disturbance=0.):
        x = self.x0 if x is None else np.asarray(x)
        streams = {}; derivatives = np.zeros_like(x); units = {}; supply = 0.; products = 0.
        heat_total = 0.; inlet_energy = 0.; outlet_energy = 0.; accumulation = 0.
        for key in self.order:
            n = self.units[key]; kind = n["kind"]; p = n["parameters"]
            if kind == "energy":
                units[key] = {"duty_W": p["duty"]}; continue
            ins = [streams[self.inlets[key, port]] for port in CATALOG[kind]["inputs"]]
            duty = p.get("duty", 0.)
            if key in self.energy:
                duty += self.units[self.energy[key]]["parameters"]["duty"]
            if key == self.target and manipulated is not None:
                duty = float(manipulated)  # total applied duty, including the connected source
            if kind == "source":
                out = Stream(p["flow"], p["temperature"]+disturbance, p["fraction"], p["pressure"])
                supply += out.flow; inlet_energy += out.flow*CP*(out.temperature-273.15)
            elif kind == "sink":
                out = ins[0]; products += out.flow; outlet_energy += out.flow*CP*(out.temperature-273.15)
            elif kind == "mixer":
                flow = sum(s.flow for s in ins)
                out = Stream(flow, sum(s.flow*s.temperature for s in ins)/flow, sum(s.flow*s.fraction for s in ins)/flow, min(s.pressure for s in ins))
            else:
                out = copy.copy(ins[0])
                if kind in ("tank", "cstr"):
                    i = self.indices[key]; mass = RHO*p["volume"]
                    conversion = p.get("k", 0.)*x[i]
                    heat = mass*conversion*p.get("heat_release", 0.)
                    derivatives[i] = out.flow/mass*(out.fraction-x[i])-conversion
                    derivatives[i+1] = out.flow/mass*(out.temperature-x[i+1])+(duty+heat)/(mass*CP)
                    accumulation += mass*CP*derivatives[i+1]
                    out.fraction, out.temperature = float(x[i]), float(x[i+1]); heat_total += duty+heat
                elif kind in ("heater", "cooler"):
                    out.temperature += duty/(out.flow*CP); heat_total += duty
                elif kind == "exchanger":
                    t = p["utility_temperature"]+(out.temperature-p["utility_temperature"])*np.exp(-p["UA"]/(out.flow*CP))
                    heat_total += out.flow*CP*(t-out.temperature); out.temperature = float(t)
                elif kind == "pump":
                    out.pressure += p["pressure_rise"]
                    # Dissipative fraction heats the fluid; useful hydraulic work remains pressure energy.
                    dissipated = out.flow*p["pressure_rise"]/RHO*(1/p["efficiency"]-1)
                    out.temperature += dissipated/(out.flow*CP); heat_total += dissipated
                elif kind == "valve":
                    out.pressure -= p["pressure_drop"]
                    heat_total += out.flow*p["pressure_drop"]/RHO
                    out.temperature += p["pressure_drop"]/(RHO*CP)
            out.check(); units[key] = asdict(out)
            for port in CATALOG[kind]["outputs"]:
                s = copy.copy(out)
                if kind == "splitter":
                    s.flow *= p["split"] if port == "out1" else 1-p["split"]
                    if s.flow <= 0:
                        raise ValueError("Zero-flow branches unsupported; splitter must be strictly between 0 and 1")
                streams[key, port] = s
        return {"derivative": derivatives, "units": units, "streams": {f"{a}:{b}": asdict(s) for (a,b),s in streams.items()}, "mass_residual_kg_s": supply-products, "energy_residual_W": inlet_energy+heat_total-outlet_energy-accumulation, "property_package": self.provenance}

    def rhs(self, x, u, disturbance=0.):
        return self.evaluate(x, u, disturbance)["derivative"]

    def steady(self, u=None):
        if not len(self.x0):
            return self.x0.copy(), self.evaluate()
        sol = root(lambda x: self.rhs(x, self.u0 if u is None else u), self.x0)
        result = self.evaluate(sol.x, self.u0 if u is None else u)
        if not sol.success or np.max(np.abs(result["derivative"])) > 1e-7:
            raise ValueError("Steady-state solve did not converge")
        return sol.x, result

    def quality(self, x):
        return float(x[self.qidx])

    def check(self, x):
        self.evaluate(x)
