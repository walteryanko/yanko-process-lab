"""Only this module and scoring may read simulated truth."""
import numpy as np


class Sensors:
    def __init__(self, model, config):
        self.model, self.c = model, config
        self.rng = np.random.default_rng(config["seed"])
        self.queue = []; self.lagged = None; self.last_values = None; self.last_sample = None
        self.acquired = 0; self.dropped = 0

    def sample(self, step, truth):
        c = self.c; values = np.asarray(truth)[self.model.measurement_indices].copy()
        if self.lagged is None:
            self.lagged = values.copy()
        alpha = 1. if c["sensor_lag"] == 0 else -np.expm1(-c["dt"]/c["sensor_lag"])
        self.lagged += alpha*(values-self.lagged)
        if step % c["sensor_period"] == 0:
            noise = self.rng.normal(0, c["sensor_sigma"], len(values))
            measured = self.lagged+noise+c["sensor_bias"]+c["sensor_drift"]*step*c["dt"]/3600
            measured = np.clip(measured, c["sensor_min"], c["sensor_max"])
            if c["sensor_quantization"] > 0:
                measured = np.round(measured/c["sensor_quantization"])*c["sensor_quantization"]
            self._event(step, "thermal", measured, max(c["sensor_sigma"]**2, 1e-8), c["sensor_delay"])
        if c["chemical_period"] and step % c["chemical_period"] == 0:
            value = self.model.quality(truth)+self.rng.normal(0,c["chemical_sigma"])
            self._event(step,"chemical",[value],max(c["chemical_sigma"]**2,1e-10),c["chemical_delay"])
        available = [e for e in self.queue if e["arrival"] == step]
        self.queue = [e for e in self.queue if e["arrival"] > step]
        for e in available:
            if e["kind"] == "thermal":
                self.last_values = e["values"].copy()
                self.last_sample = e["sample"]
        return available

    def _event(self, step, kind, values, variance, delay):
        self.acquired += 1
        if self.rng.random() < self.c["sensor_dropout"]:
            self.dropped += 1; return
        self.queue.append({"id": f"{kind}-{step}","sample": step,"arrival": step+delay,"kind": kind,"values": list(map(float,values)),"variance": [variance]*len(values)})
