import unittest,sys,types
import numpy as np
from eblab.model import *
from eblab.filters import UKF,FilterConfig
from eblab.experiments import initial
from vendor import model as original

class Physics(unittest.TestCase):
    def test_equilibrium(self):
        self.assertLess(np.max(abs(rhs(BASE,U0))),1e-10)
        self.assertAlmostEqual(Q0*4184/3.6e9,25.241425676232865,8)
    def test_stoichiometry(self):
        np.testing.assert_allclose(MOIETIES@NU,0,atol=1e-12)
        np.testing.assert_allclose(MW@NU,0,atol=1e-10)
        self.assertEqual(np.linalg.matrix_rank(NU),2)
    def test_original_physics(self):
        x=BASE*np.array([1.1,.97,.99,1.1,1.001]);u=U0.copy();u[0]*=1.05
        np.testing.assert_allclose(rhs(x,u),original.rhs(x,u),atol=1e-12)
        np.testing.assert_allclose(step(x,u),original.transition(x,u),atol=1e-12)
    def test_inventory_analytic(self):
        x=BASE.copy();x[2]+=.2;end=step(x,U0,dt=.5)
        np.testing.assert_allclose(MOIETIES@(end-BASE)[:4],(MOIETIES@(x-BASE)[:4])*np.exp(-F0.sum()/V*.5),atol=1e-10)
    def test_independent_integrator(self):
        u=U0.copy();u[0]*=1.1
        np.testing.assert_allclose(step(BASE,u,dt=.5),step(BASE,u,dt=.5,method='dop853'),atol=2e-6,rtol=0)
    def test_domain_rejection(self):
        for i in range(5):
            x=BASE.copy();x[i]=-1
            with self.assertRaises(ValueError):step(x,U0)
        x=BASE.copy();x[4]=221
        self.assertFalse(valid(x))
    def test_heat_input_sign(self):
        u=U0.copy();u[3]+=1e6
        self.assertAlmostEqual(rhs(BASE,u)[4],-1e6/CAPACITY,10)
    def test_original_ukf_parity_without_projection(self):
        old=sys.modules.get('model');sys.modules['model']=original
        try:
            import importlib.util
            spec=importlib.util.spec_from_file_location('recovered_observer',__import__('pathlib').Path(__file__).resolve().parents[1]/'vendor/observer.py')
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        finally:
            if old is None:sys.modules.pop('model',None)
            else:sys.modules['model']=old
        models=types.SimpleNamespace(transition=lambda kind,x,u:original.transition(x,u))
        source=module.Observer(BASE,models);m,p=initial('gaussian');source.p=p/np.outer(XS,XS)
        ours=UKF(m,p,np.array([[2.25]]),FilterConfig())
        for k in range(12):
            y=BASE[4]+.4*np.sin(k);x,p,_=source.update(U0,y);ours.advance(U0,np.array([y]))
            np.testing.assert_allclose(ours.x,x,atol=3e-9,rtol=0)
            np.testing.assert_allclose(ours.P,p,atol=3e-9,rtol=0)
        self.assertEqual(source.projections,0)
