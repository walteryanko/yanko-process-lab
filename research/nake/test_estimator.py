import json, subprocess, unittest
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp
from estimator import *
from experiment import trajectory, run_filter, calibrate_and_verify

class EstimatorTests(unittest.TestCase):
    def test_equilibrium_calibration_and_independent_integration(self):
        d=calibrate_and_verify()
        self.assertLess(max(abs(np.array(d['residual']))),1e-8)
        self.assertLess(d['DOP853_error'],1e-7)
        self.assertAlmostEqual(P_ADJUSTED.dH,-84138.65353748415,7)
        self.assertEqual(P_TABLE.dH,-91556.9)

    def test_conservation_for_batch_and_scalar_rhs(self):
        xs=np.vstack([BASE,BASE+[.1,.2,-.1,.3,1.,2.]])
        u=U_BASE.copy();u[2]*=1.1;dx=rhs6(xs,u)
        v=u[0]/P_ADJUSTED.rhoA+u[1]/P_ADJUSTED.rhoB+u[2]/P_ADJUSTED.rhoM
        np.testing.assert_allclose(dx[:,0]+dx[:,2],(u[0]-v*(xs[:,0]+xs[:,2]))/P_ADJUSTED.V,atol=1e-12)
        np.testing.assert_allclose(dx[:,1]+dx[:,2],(u[1]-v*(xs[:,1]+xs[:,2]))/P_ADJUSTED.V,atol=1e-12)
        np.testing.assert_allclose(dx[0],rhs6(xs[0],u),atol=1e-12)

    def test_python_typescript_parity(self):
        root=Path(__file__).resolve().parents[2]
        script="import {BASE,P,NOMINAL,derivative,integrate} from './lib/simulation/model.ts'; const x=BASE.map((z,i)=>z+[.1,.2,-.1,.3,1.,2.][i]); console.log(JSON.stringify({base:BASE,heat:P.heat,rhs:derivative(x,NOMINAL),end:integrate(x,NOMINAL,.1)}));"
        d=json.loads(subprocess.check_output(['node','--input-type=module','-e',script],cwd=root))
        np.testing.assert_allclose(d['base'],BASE,atol=1e-10)
        self.assertAlmostEqual(d['heat'],-P_ADJUSTED.dH,7)
        x=BASE+[.1,.2,-.1,.3,1.,2.]
        np.testing.assert_allclose(d['rhs'],rhs6(x,U_BASE),atol=1e-9)
        np.testing.assert_allclose(d['end'],transition(x,U_BASE,dt=.1,max_step=.001),atol=1e-9)

    def test_linear_measurement_joseph_posterior_psd(self):
        f=UKF(BASE)
        for i in range(100):
            x,p,_,d=f.update(U_BASE,BASE[4:]+[.02,-.02])
            self.assertEqual(d,2)
            self.assertGreater(np.linalg.eigvalsh(p/XS[:,None]/XS[None,:]).min(),0)
            self.assertTrue(np.all(np.isfinite(x)))

    def test_missing_measurements_are_prediction_only(self):
        a=UKF(BASE);b=UKF(BASE)
        xa,pa,na,da=a.update(U_BASE,[np.nan,np.nan]);xb,pb,nb,db=b.update(U_BASE,[np.nan,np.nan])
        np.testing.assert_array_equal(xa,xb);np.testing.assert_array_equal(pa,pb)
        self.assertEqual(da,0);self.assertTrue(np.isnan(na))
        _,p,n,d=a.update(U_BASE,[BASE[4],np.nan])
        self.assertEqual(d,1);self.assertTrue(np.isfinite(n))

    def test_estimator_never_receives_oracle_labels(self):
        a=trajectory(987,'nominal',steps=25);b=dict(a)
        b['truth']=np.full_like(a['truth'],999.)
        b['ua']=np.full(25,99.);b['ks']=np.full(25,99.)
        b['parameters']=[None]*25
        ra=run_filter(a);rb=run_filter(b)
        np.testing.assert_array_equal(ra['est'],rb['est'])
        np.testing.assert_array_equal(ra['cov'],rb['cov'])

    def test_network_is_bounded_and_cannot_access_current_measurements(self):
        class Wild:
            def predict(self,x):return np.full(8,10000.)
        f=UKF(BASE,network=Wild(),kind='nake_hybrid')
        before=f.features(U_BASE).copy()
        f.update(U_BASE,[np.nan,np.nan])
        self.assertTrue(np.all(f.last_q<=Q_PUBLISHED*1e6*(1+1e-12)))
        self.assertTrue(np.all(f.last_q>=Q_PUBLISHED*.25))
        self.assertTrue(np.all(f.last_scales<=1.3))
        self.assertEqual(len(before),26)

    def test_deterministic_seeded_trajectories_and_feature_reset(self):
        a=trajectory(977,'feed_steps',steps=160);b=trajectory(977,'feed_steps',steps=160)
        np.testing.assert_array_equal(a['truth'],b['truth']);np.testing.assert_array_equal(a['y'],b['y'])
        f=UKF(BASE);np.testing.assert_array_equal(f.features(U_BASE),np.zeros(26))
        f.update(U_BASE,BASE[4:]+1)
        self.assertTrue(np.any(f.features(U_BASE)))
        np.testing.assert_array_equal(UKF(BASE).features(U_BASE),np.zeros(26))

if __name__=='__main__':unittest.main()
