"""Public operational records contain NO truth states or hidden parameters."""
from dataclasses import dataclass
import numpy as np
from .physics import DT

@dataclass(frozen=True)
class Record:
    seed: int
    inputs: np.ndarray
    measurements: np.ndarray
    dt: float=DT
    def prefix(self,n):
        return Record(self.seed,self.inputs[:n].copy(),self.measurements[:n+1].copy(),self.dt)
    def __post_init__(self):
        if len(self.measurements)!=len(self.inputs)+1:raise ValueError('Time alignment')
        if self.inputs.shape[1]!=6 or self.measurements.shape[1]!=2:raise ValueError('Dimensions')
        if not np.all(np.isfinite(self.inputs)) or np.any(self.inputs[:,3]<=0):raise ValueError('Inputs')
    def fingerprint(self):
        import hashlib
        return hashlib.sha256(self.inputs.tobytes()+self.measurements.tobytes()).hexdigest()

def assert_disjoint(*groups):
    allseeds=[r.seed for g in groups for r in g]
    if len(set(allseeds))!=len(allseeds):raise ValueError('Overlapping episodes')
