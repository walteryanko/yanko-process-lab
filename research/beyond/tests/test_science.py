"""Scientific regression gates, independent identities and numerical checks."""
import unittest,tempfile
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp
from beyond.models import get_model,reference
from beyond.spectra import schedule,information
from beyond.control import FixedPolicy
from beyond.common import metrics

class ScientificTests(unittest.TestCase):
    def test_pg_source_fidelity_random_states(self):
        m=get_model('PG');ref=reference('pg');rng=np.random.default_rng(7931)
        for i in range(40):
            x=m.x0.copy();x[:4]*=rng.uniform(.8,1.2,4);x[4:]+=rng.uniform(-4,4,2)
            u=m.u0.copy();u[0]*=rng.uniform(.9,1.1);u[1]*=rng.uniform(.8,1.2)
            np.testing.assert_allclose(np.array(m.f(x,u,m.p0)).ravel(),ref.rhs(0,x,u[:3]),rtol=2e-12,atol=2e-10)
    def test_eb_source_fidelity_random_states(self):
        m=get_model('EB');ref=reference('eb');rng=np.random.default_rng(7932)
        ff=ref.build()[0]
        for i in range(40):
            x=m.x0.copy();x[:4]*=rng.uniform(.8,1.2,4);x[4]+=rng.uniform(-4,4)
            u=m.u0.copy();u[0]*=rng.uniform(.95,1.05);u[3]*=rng.uniform(.95,1.05)
            np.testing.assert_allclose(np.array(m.f(x,u,m.p0)),np.array(ff(x,u,np.zeros(12))),rtol=2e-12,atol=2e-10)
    def test_nominal_equilibria_and_units(self):
        for kind in ['PG','EB']:
            m=get_model(kind);self.assertLess(np.abs(np.array(m.f(m.x0,m.u0,m.p0))).max(),2e-9)
        self.assertAlmostEqual(get_model('PG').tmax,344.2611111111,8)
        self.assertAlmostEqual(get_model('EB').tmin,140.85,8)
    def test_asymmetric_pg_exchanger(self):
        m=get_model('PG');A=np.array(m.fx(m.x0,m.u0,m.p0))
        self.assertEqual(A[4,5],0.);self.assertNotEqual(A[5,4],0.)
    def test_element_conservation(self):
        nu=np.array([[-1,-1,0],[-1,0,-1],[1,-1,2],[0,1,-1]])
        elements=np.array([[2,6,8,10],[4,6,10,14]])
        np.testing.assert_array_equal(elements@nu,0)
        self.assertEqual(np.linalg.matrix_rank(nu),2)
    def test_hess_closure_variant(self):
        m=get_model('EB','hess');dh=m.constants['DH']
        self.assertAlmostEqual(dh[0]-dh[1]-dh[2],0.)
        self.assertLess(np.abs(np.array(m.f(m.x0,m.u0,m.p0))).max(),2e-9)
    def test_hess_cycle_does_not_create_linear_thermal_information(self):
        from scipy.linalg import null_space
        m=get_model('EB','hess');A=np.array(m.fx(m.x0,m.u0,m.p0))
        K=null_space(A[:4,:4]+m.dilution(m.u0)*np.eye(4))
        self.assertEqual(K.shape[1],2)
        self.assertLess(np.linalg.norm(A[4,:4]@K),1e-9)
        bad=get_model('EB');A=np.array(bad.fx(bad.x0,bad.u0,bad.p0))
        self.assertGreater(np.linalg.norm(A[4,:4]@K),1e-5)
    def test_equal_resource_forgetting_startup_slew(self):
        m=get_model('PG');n=40;wave=.06*np.sin(2*np.pi*(np.arange(n)+.5)/n)
        for sign in [-1,1]:
            U=np.tile(m.u0,(n,1));U[:,0]*=1+sign*wave
            self.assertTrue(np.all(abs(np.diff(np.vstack([m.u0,U]),axis=0))<=m.slew*m.dt+1e-7))
            self.assertAlmostEqual(U[:,0].mean(),m.u0[0],10)
    def test_independent_integrator(self):
        rng=np.random.default_rng(7933)
        for kind in ['PG','EB']:
            m=get_model(kind);x=m.x0.copy();x[:4]*=1.07;u=m.u0.copy();u[m.cidx]*=.97
            p=rng.normal(size=m.np)*m.pscale*.3
            sol=solve_ivp(lambda t,x:np.array(m.f(x,u,p)).ravel(),[0,m.dt],x,method='DOP853',rtol=1e-11,atol=1e-12)
            predicted=np.array(m.step(x,u,p)).ravel()
            np.testing.assert_allclose(predicted,sol.y[:,-1],rtol=5e-7,atol=5e-7)
    def test_pg_exact_unobservable_direction(self):
        m=get_model('PG');d=np.array([0,-.5*m.constants['cpC']/m.constants['cpB'],.5,0,0,0])
        U=schedule(m,'chirp',m.tau,'joint',.02,horizon=.6)
        A=m.rollout(m.x0-d/2,U);B=m.rollout(m.x0+d/2,U)
        self.assertLess(np.abs(A[:,m.yidx]-B[:,m.yidx]).max(),1e-8)
        expected=.5*np.exp(-np.r_[0,np.cumsum([m.dilution(u)*m.dt for u in U])])
        np.testing.assert_allclose(B[:,2]-A[:,2],expected,atol=2e-9)
    def test_fisher_does_not_invent_invisible_information(self):
        m=get_model('PG');U=schedule(m,'sin',m.tau,'feed',.02,horizon=.3)
        _,_,a=information(m,m.x0,U)
        d=np.zeros(m.n+m.np);d[1]=-.5*m.constants['cpC']/m.constants['cpB']/m.xscale[1];d[2]=.5/m.xscale[2]
        self.assertLess(abs(d@a['F']@d),1e-9)
        self.assertGreater(np.linalg.eigvalsh(a['P']).min(),-1e-10)
    def test_direct_policy_cannot_read_chemical_estimate(self):
        m=get_model('PG');a=FixedPolicy(m,m.x0,m.u0,'direct');b=FixedPolicy(m,m.x0,m.u0,'direct')
        for j in range(12):
            y=m.x0[m.yidx]+[.5*np.sin(j),.2*np.cos(j)]
            np.testing.assert_array_equal(a.act(y,np.full(6,np.nan)),b.act(y,m.x0*3))
    def test_actuator_slew_and_amplitude(self):
        for kind in ['PG','EB']:
            m=get_model(kind);U=schedule(m,'prbs',m.tau/4,'joint',.1,horizon=.5)
            self.assertTrue(np.all(U>=m.umin-1e-7));self.assertTrue(np.all(U<=m.umax+1e-7))
            self.assertTrue(np.all(abs(np.diff(np.vstack([m.u0,U]),axis=0))<=m.slew*m.dt+1e-7))
    def test_e2e_simulate_infer_export(self):
        for kind in ['PG','EB']:
            m=get_model(kind);U=schedule(m,'step',m.tau,'feed',.01,horizon=.3)
            info,X,a=information(m,m.x0,U);met=metrics(m,X,U)
            self.assertTrue(np.isfinite(met['production_mean']));self.assertTrue(np.isfinite(info['common_target_posterior_sd']))
            with tempfile.TemporaryDirectory() as t:
                path=Path(t)/'trajectory.npz';np.savez_compressed(path,X=X,U=U,F=a['F'])
                saved=np.load(path);np.testing.assert_array_equal(saved['X'],X)
    def test_reported_heat_uses_simulated_plant_parameters(self):
        m=get_model('EB');U=np.tile(m.u0,(2,1));X=np.tile(m.x0,(3,1));p=m.p0.copy();p[7]=.1
        met=metrics(m,X,U,plant_parameters=p)
        self.assertAlmostEqual(met['heat_mean']/m.u0[3],np.exp(.1),12)

if __name__=='__main__':unittest.main(verbosity=2)
