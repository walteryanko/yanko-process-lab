"""Versioned model schema, separate from layout. Only executable ports are exposed."""
import copy
import json
import re
from .units import quantity

VERSION = 1
CATALOG = {
    "source": {"label": "Alimentação", "inputs": [], "outputs": ["out"], "parameters": {"flow": [1, "kg/s"], "temperature": [298.15, "K"], "pressure": [101325, "Pa"], "fraction": [.1, "dimensionless"]}},
    "sink": {"label": "Produto", "inputs": ["in"], "outputs": [], "parameters": {}},
    "mixer": {"label": "Misturador", "inputs": ["in1", "in2"], "outputs": ["out"], "parameters": {}},
    "splitter": {"label": "Divisor", "inputs": ["in"], "outputs": ["out1", "out2"], "parameters": {"split": [.5, "dimensionless"]}},
    "tank": {"label": "Tanque", "inputs": ["in"], "outputs": ["out"], "energy": True, "parameters": {"volume": [.1, "m^3"], "temperature": [298.15, "K"], "fraction": [.1, "dimensionless"], "duty": [0, "W"]}},
    "pump": {"label": "Bomba", "inputs": ["in"], "outputs": ["out"], "parameters": {"pressure_rise": [100000, "Pa"], "efficiency": [.8, "dimensionless"]}},
    "valve": {"label": "Válvula", "inputs": ["in"], "outputs": ["out"], "parameters": {"pressure_drop": [50000, "Pa"]}},
    "heater": {"label": "Aquecedor", "inputs": ["in"], "outputs": ["out"], "energy": True, "parameters": {"duty": [20000, "W"]}},
    "cooler": {"label": "Resfriador", "inputs": ["in"], "outputs": ["out"], "energy": True, "parameters": {"duty": [-20000, "W"]}},
    "exchanger": {"label": "Trocador", "inputs": ["in"], "outputs": ["out"], "parameters": {"UA": [1000, "W/K"], "utility_temperature": [350, "K"]}},
    "cstr": {"label": "CSTR A → B", "inputs": ["in"], "outputs": ["out"], "energy": True, "parameters": {"volume": [.1, "m^3"], "temperature": [298.15, "K"], "fraction": [.1, "dimensionless"], "duty": [0, "W"], "k": [.001, "1/s"], "heat_release": [100000, "J/kg"]}},
    "energy": {"label": "Fonte de calor", "inputs": [], "outputs": ["heat"], "parameters": {"duty": [20000, "W"]}},
}


def canonical(project):
    p = copy.deepcopy(project)
    if not isinstance(p, dict) or p.get("schema_version") != VERSION:
        raise ValueError("Unsupported project schema; version 1 required (no implicit migration)")
    if p.get("model") not in ("flowsheet", "pg-original", "eb-reduced"):
        raise ValueError("Unknown physical model")
    if not isinstance(p.get("id"), str) or not re.fullmatch(r"[\w-]{1,80}", p["id"]):
        raise ValueError("Invalid project ID")
    json.dumps(p, allow_nan=False)
    cfg = p.setdefault("experiment", {})
    defaults = {"dt": 5., "duration": 600., "seed": 42, "solver": "RK45", "rtol": 1e-7, "atol": 1e-9, "controller": "manual", "observer": "ekf", "setpoint": 310., "manual": 20000., "kp": 7000., "ki": 100., "kd": 0., "horizon": 8, "sensor_sigma": .1, "sensor_period": 1, "sensor_delay": 0, "sensor_dropout": 0., "sensor_bias": 0., "sensor_drift": 0., "sensor_lag": 0., "sensor_quantization": 0., "sensor_min": -1000., "sensor_max": 2000., "chemical_period": 0, "chemical_delay": 0, "chemical_sigma": .02, "q_scale": 1., "r_scale": 1., "disturbance_time": 200., "disturbance_value": -8., "initial_estimate_offset": .1, "control_target": "temperature"}
    for k, v in defaults.items():
        cfg.setdefault(k, v)
    cfg["move_weight"] = quantity(cfg.get("move_weight", .05), "dimensionless")
    if not 0 <= cfg["move_weight"] <= 100:
        raise ValueError("NMPC move weight must be between 0 and 100")
    for k in defaults:
        if isinstance(defaults[k], (int, float)):
            cfg[k] = quantity(cfg[k], "s" if k in ("dt", "duration", "disturbance_time", "sensor_lag") else "dimensionless")
    if not .05 <= cfg["dt"] <= 300 or not cfg["dt"] <= cfg["duration"] <= 86400 or cfg["duration"]/cfg["dt"] > 4000:
        raise ValueError("Use 0.05–300 s per sample and at most 4000 samples / 24 h")
    if cfg["solver"] not in ("RK4", "RK45", "BDF", "Radau", "DOP853"):
        raise ValueError("Unsupported ODE solver")
    if cfg["controller"] not in ("manual", "pid", "nmpc") or cfg["observer"] not in ("none", "ekf", "ukf", "mhe"):
        raise ValueError("Unsupported controller/observer")
    if cfg["control_target"] not in ("temperature", "quality"):
        raise ValueError("Unknown controlled variable")
    if cfg["control_target"] == "quality" and cfg["controller"] == "pid":
        raise ValueError("PID currently controls measured temperature; choose NMPC for estimated quality")
    if cfg["controller"] == "nmpc" and cfg["observer"] == "none":
        raise ValueError("NMPC requires an estimator; simulator truth is not a fallback")
    for k in ("sensor_period", "sensor_delay", "chemical_period", "chemical_delay", "horizon", "seed"):
        if cfg[k] != int(cfg[k]):
            raise ValueError(f"{k} must be an integer")
        cfg[k] = int(cfg[k])
    if not 1 <= cfg["sensor_period"] <= 100 or not 0 <= cfg["sensor_delay"] <= 100 or not 0 <= cfg["chemical_delay"] <= 100 or not 0 <= cfg["chemical_period"] <= 1000 or not 2 <= cfg["horizon"] <= 20:
        raise ValueError("Invalid sensor clock or prediction horizon")
    if not 0 <= cfg["seed"] < 2**32 or not 0 <= cfg["sensor_dropout"] <= 1 or min(cfg["sensor_sigma"], cfg["chemical_sigma"], cfg["sensor_lag"], cfg["sensor_quantization"], cfg["q_scale"]) < 0 or cfg["r_scale"] <= 0:
        raise ValueError("Invalid seed, noise or covariance")
    if cfg["sensor_min"] >= cfg["sensor_max"] or not 1e-12 <= cfg["rtol"] <= 1e-2 or not 1e-14 <= cfg["atol"] <= 1e-2:
        raise ValueError("Invalid sensor range or solver tolerances")
    if p["model"] != "flowsheet":
        return p
    nodes, edges = p.get("nodes", []), p.get("edges", [])
    if not 2 <= len(nodes) <= 40 or len(edges) > 100:
        raise ValueError("Flowsheet requires 2–40 units and at most 100 streams")
    ids = set()
    for n in nodes:
        if n.get("kind") not in CATALOG or not re.fullmatch(r"[\w-]{1,80}", str(n.get("id", ""))) or n["id"] in ids:
            raise ValueError("Invalid equipment type or duplicate ID")
        ids.add(n["id"])
        params = n.setdefault("parameters", {})
        template = CATALOG[n["kind"]]["parameters"]
        if set(params)-set(template):
            raise ValueError(f"Unknown parameters in {n['id']}")
        for key, (default, unit) in template.items():
            params[key] = quantity(params.get(key, default), unit)
        for key in ("fraction", "split"):
            if key in params and not 0 <= params[key] <= 1:
                raise ValueError(f"{key} must be a fraction")
        for key in ("flow", "volume", "pressure", "efficiency"):
            if key in params and params[key] <= 0:
                raise ValueError(f"{key} must be positive")
        if params.get("efficiency", 1) > 1 or min(params.get("k", 0), params.get("UA", 0), params.get("pressure_drop", 0), params.get("pressure_rise", 0)) < 0:
            raise ValueError("Invalid equipment parameter")
        if any(not 273.15 <= params[k] <= 373.15 for k in ("temperature", "utility_temperature") if k in params):
            raise ValueError("Constant-property liquid package supports 273.15–373.15 K only")
    if not any(n["kind"] == "source" for n in nodes) or not any(n["kind"] == "sink" for n in nodes):
        raise ValueError("A source and a product sink are required")
    return p
