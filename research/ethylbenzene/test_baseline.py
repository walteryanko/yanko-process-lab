"""Numerical and actuator checks for the reconstructed historical architecture."""
import unittest
import numpy as np
from model import BASE,U0,XS,DT,fraction
from compiled import Models
from baseline import EKF,PI


class BaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.models=Models()

    def test_ekf_derivative_prediction_and_missing_measurement(self):
        x=BASE+np.array([.007,.14,-.11,.035,2.])
        u=U0.copy();u[[0,3]]*=[1.08,1.05]
        obs=EKF(x,self.models)
        derivative=np.array(obs.jac(x,u));finite=np.empty((5,5))
        for j in range(5):
            h=1e-6*max(abs(x[j]),1.)
            d=np.zeros(5);d[j]=h
            finite[:,j]=(self.models.transition('physical',x+d,u)-self.models.transition('physical',x-d,u))/(2*h)
        np.testing.assert_allclose(derivative,finite,rtol=2e-6,atol=1e-7)
        physical_p=obs.p*XS[:,None]*XS[None,:]
        expected_p=derivative@physical_p@derivative.T+np.diag(obs.qbase)
        expected_x=self.models.transition('physical',x,u)
        estimate,cov,nis=obs.update(u,np.nan)
        self.assertIsNone(nis)
        np.testing.assert_allclose(estimate,expected_x,rtol=1e-12,atol=1e-12)
        np.testing.assert_allclose(cov,expected_p,rtol=1e-10,atol=1e-10)
        for j in range(30):
            estimate,cov,nis=obs.update(U0,np.nan if j%5==0 else BASE[4]+(-1)**j)
            self.assertGreater(np.linalg.eigvalsh(cov).min(),0.)
            self.assertTrue(np.all(np.isfinite(estimate)))

    def test_pi_equilibrium_valve_limits_and_antiwindup_reversal(self):
        gains=dict(Kp=20.85,Ti_h=.125)
        ctrl=PI(gains)
        action,_=ctrl.step(BASE,U0,fraction(BASE))
        np.testing.assert_allclose(action,[1.,1.],atol=1e-14)
        # An unattainable error must not accumulate an unbounded integral.
        for reference in [fraction(BASE)+1.]*30+[fraction(BASE)-1.]*30:
            previous=ctrl.previous
            action,_=ctrl.step(BASE,U0,reference)
            self.assertGreaterEqual(action[0],.04)
            self.assertLessEqual(action[0],2.)
            self.assertLessEqual(abs(action[0]-previous),.1200000001)
            self.assertEqual(action[1],1.)
            issued=1+np.log(action[0]/2)/np.log(50)
            self.assertAlmostEqual(ctrl.s0+ctrl.kp*(reference-fraction(BASE))+ctrl.integral,issued,delta=1e-12)
        self.assertAlmostEqual(ctrl.previous,.04,delta=1e-12)
        # Reverse after sustained lower saturation: command must immediately rise.
        action,_=ctrl.step(BASE,U0,fraction(BASE)+.02)
        self.assertAlmostEqual(action[0],.16,delta=1e-12)


if __name__=='__main__':unittest.main()
