import json,subprocess,unittest
from pathlib import Path
import numpy as np
from schrodinger_lab.model import *
from schrodinger_lab.filters import UKF,FilterConfig

class UpstreamParity(unittest.TestCase):
    def test_typescript_physics_and_original_ukf(self):
        root=Path(__file__).resolve().parents[1]
        fixture=root/'vendor'/'upstream_fixture.json'
        # Fixture generated directly by original TypeScript. Node is optional for users.
        r=json.loads(fixture.read_text())
        x=np.array([.42,33,2.1,3.5,337,317])
        np.testing.assert_allclose(BASE,r['base'],atol=1e-11)
        np.testing.assert_allclose(rhs(x),r['derivative'],atol=1e-11)
        np.testing.assert_allclose(step(x,dt=.12),r['integrated'],atol=1e-10)
        f=UKF(BASE,np.diag(Q_PUBLISHED),np.diag((BASE[4:]*.01)**2),FilterConfig(),original=True)
        for k in range(12):
            f.advance(U0,BASE[4:]+[.3*np.sin(k),-.4*np.cos(k)])
            np.testing.assert_allclose(f.x,r['estimates'][k],atol=3e-6,rtol=0)
