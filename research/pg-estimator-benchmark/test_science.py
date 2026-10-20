import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import benchmark as b
import numpy as np

class ScientificTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):b.prepare()

    def test_exact_historical_transition(self):
        rng=np.random.default_rng(102)
        for dt in (.005,.015):
            for _ in range(8):
                x=b.initial_state(b.BY_KEY["OL_FA"])+rng.normal(size=6)*np.array([.02,.1,.02,.01,.5,.5])
                u=b.U_NOM*(1+rng.uniform(-.02,.02,size=6))
                actual=np.asarray(b.step_jac()(x,u,dt)[0]).ravel()
                expected=b.transition(x,u,np.zeros(b.NP),dt,3,1)
                np.testing.assert_allclose(actual,expected,rtol=1e-11,atol=1e-9)

    def test_exact_jacobian_against_independent_finite_difference(self):
        x=b.initial_state(b.BY_KEY["OL_FA"]);u=b.U_NOM.copy()
        F=np.asarray(b.step_jac()(x,u,.015)[1]);numerical=np.empty((6,6))
        for j in range(6):
            step=max(abs(x[j])*1e-6,1e-5);a=x.copy();c=x.copy();a[j]+=step;c[j]-=step
            numerical[:,j]=(b.transition(a,u,np.zeros(b.NP),.015,3,1)-b.transition(c,u,np.zeros(b.NP),.015,3,1))/(2*step)
        np.testing.assert_allclose(F,numerical,rtol=3e-5,atol=2e-7)

    def test_measurement_updates_hidden_state_through_cross_covariance(self):
        xp=np.arange(6,dtype=float);pp=np.eye(6);pp[2,4]=pp[4,2]=.4
        y=xp[4:6]+np.array([1.,-.2])
        result,P,_=b.gaussian_update(xp,pp,y,b.R_HIST)
        self.assertAlmostEqual(result[2],xp[2]+.4/(1+b.R_HIST[0]),places=10)
        self.assertGreaterEqual(np.linalg.eigvalsh(P).min(),-1e-12)

    def test_zero_contamination_is_exact_gaussian_filter(self):
        xp=b.initial_state(b.BY_KEY["OL_FA"]);pp=np.diag([.1,.2,.3,.1,.4,.5])
        y=xp[4:6]+np.array([.1,-.2])
        expected,P,_=b.gaussian_update(xp,pp,y,b.R_HIST)
        actual,Q=b.mixture_update(xp,pp,y,epsilon=0)
        np.testing.assert_allclose(actual,expected,atol=1e-10)
        np.testing.assert_allclose(Q,P,atol=1e-10)

    def test_gross_error_downweighting(self):
        xp=b.initial_state(b.BY_KEY["OL_FA"]);pp=np.diag([.1,.2,.3,.1,.1,.1])
        y=xp[4:6]+20*np.sqrt(b.R_HIST)
        ordinary,_,_=b.gaussian_update(xp,pp,y,b.R_HIST)
        robust,P=b.mixture_update(xp,pp,y)
        self.assertLess(np.linalg.norm(robust-xp),.2*np.linalg.norm(ordinary-xp))
        self.assertGreaterEqual(np.linalg.eigvalsh(P).min(),-1e-12)

    def test_contamination_does_not_change_input_or_clean_samples(self):
        sc=b.BY_KEY["OL_FA"]
        u,g,_,_=b.noise_data(sc,700000,"gaussian")
        v,c,mask,_=b.noise_data(sc,700000,"contaminated")
        np.testing.assert_array_equal(u,v);np.testing.assert_array_equal(g[~mask],c[~mask])
        self.assertGreater(mask.sum(),0)

    def test_ukf_parity_with_existing_rollout(self):
        from darwin.thesis_experiments import rollout
        seed=704001
        expected=rollout("OL_STEADY","UKF_RK4",False,seed,dict(accepted=False),save=False)
        actual=b.run_trial("OL_STEADY","UKF_RK4",False,seed,"gaussian",save=False)
        self.assertAlmostEqual(actual["RMSE_est_CC"],expected["RMSE_est_CC"],places=10)
        self.assertAlmostEqual(actual["T_peak_K"],expected["T_peak_K"],places=10)

    def test_mhe_causal_prefix_and_bounds(self):
        x0=b.initial_state(b.BY_KEY["OL_FA"]);rng=np.random.default_rng(80)
        measurements=x0[4:6]+rng.normal(size=(9,2))*np.sqrt(b.R_HIST)
        def evaluate(y):
            observer=b.MHE(x0);out=[]
            for row in y:
                value=observer.update(b.U_NOM,row,.015)
                self.assertTrue(np.all(value[:4]>=0));self.assertTrue(np.all((value[4:]>=250)&(value[4:]<=400)))
                out.append(value)
            return np.array(out)
        changed=measurements.copy();changed[6:]+=8
        a=evaluate(measurements);c=evaluate(changed)
        np.testing.assert_array_equal(a[:6],c[:6])

if __name__=="__main__":unittest.main()
