"""Meaningful numerical and information-boundary checks for the control study."""
import unittest
import numpy as np
from scipy.integrate import solve_ivp
import casadi as ca
from common import *
from control import build_step,CompiledTransition,NMPC,BlackBoxNAKE,NeuralEvaluator
from protocol import inputs

class ControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.net=NeuralTransition.load();cls.physical=build_step('physical')
        cls.neural=build_step('neural',cls.net)
    def test_independent_physical_integrator(self):
        x=BASE+np.array([.1,.3,-.1,.05,2,1]);u=U_BASE.copy();u[3]*=1.1
        exact=solve_ivp(lambda t,z:rhs6(z,u),(0,DT),x,method='DOP853',rtol=1e-12,atol=1e-13).y[:,-1]
        pred=np.asarray(self.physical(x,u)).ravel()
        np.testing.assert_allclose(pred,exact,atol=3e-6,rtol=0)
    def test_neural_export_and_gradients(self):
        x=BASE+np.array([.1,.3,-.1,.05,2,1]);u=U_BASE.copy();u[3]*=1.1
        np.testing.assert_allclose(np.asarray(self.neural(x,u)).ravel(),self.net(x,u),atol=1e-10,rtol=0)
        sx=ca.SX.sym('x',6);su=ca.SX.sym('u',6)
        jac=ca.Function('j',[sx,su],[ca.jacobian(self.neural(sx,su),sx)])
        numerical=np.column_stack([(self.net(x+np.eye(6)[j]*1e-5,u)-self.net(x-np.eye(6)[j]*1e-5,u))/2e-5 for j in range(6)])
        np.testing.assert_allclose(np.asarray(jac(x,u)),numerical,atol=2e-7,rtol=2e-6)
    def test_anchor_and_no_physics_in_neural_inference(self):
        np.testing.assert_allclose(self.net(BASE,U_BASE),BASE,atol=1e-11,rtol=0)
        # A poisoned optional physical-parameter argument cannot change learned inference.
        np.testing.assert_array_equal(self.net(BASE,U_BASE,object()),self.net(BASE,U_BASE,None))
    def test_nmpc_objective_and_constraint_derivatives(self):
        for step in [self.physical,self.neural]:
            ctrl=NMPC(step,True,network=self.net if step.name().startswith('neural') else None);q=np.array([1.,1.01,1.02,1.01,1,1])
            theta=np.r_[BASE,U_BASE,BASE[2]*1.1,1.]
            obj,grad,con,jac=[np.asarray(a) for a in ctrl.evaluate(q,theta)]
            if step.name().startswith('neural'):
                independent=NeuralEvaluator(self.net,0)(q,theta)
                for a,b in zip([obj,grad,con,jac],independent):
                    np.testing.assert_allclose(a,b,atol=1e-9,rtol=1e-10)
            # Independently reconstruct eq69 and the 57-step hold schedule in NumPy.
            state=BASE.copy();expected_cost=0.;predicted=[]
            model=self.net if step.name().startswith('neural') else transition
            for i in range(57):
                command=U_BASE.copy();command[3]=q[min(i,5)]*U_BASE[3]
                state=model(state,command)
                expected_cost+=.8*((state[2]-theta[12])/theta[12])**2
                predicted.append((T_LIMIT-state[4])/10.)
            expected_cost+=.2*np.sum(np.diff(np.r_[1.,q])**2)
            self.assertAlmostEqual(float(obj.item()),expected_cost,places=9)
            np.testing.assert_allclose(con.ravel(),predicted,atol=1e-9,rtol=0)
            numerical=[];nc=[]
            for j in range(6):
                delta=np.eye(6)[j]*1e-5
                v1=ctrl.evaluate(q+delta,theta);v0=ctrl.evaluate(q-delta,theta)
                numerical.append((np.asarray(v1[0]).item()-np.asarray(v0[0]).item())/2e-5)
                nc.append((np.asarray(v1[2]).ravel()-np.asarray(v0[2]).ravel())/2e-5)
            np.testing.assert_allclose(grad.ravel(),numerical,atol=1e-6,rtol=2e-5)
            np.testing.assert_allclose(jac,np.column_stack(nc),atol=1e-6,rtol=2e-5)
    def test_causal_q_adaptation_and_psd_missing_measurements(self):
        f=BlackBoxNAKE(BASE,CompiledTransition(self.neural),self.net)
        x,p,_,_=f.update(U_BASE,BASE[4:]+[5.,-5.])
        first=f.last_q.copy();factor=f.factor
        np.testing.assert_allclose(first,f.base_q,rtol=0,atol=0)
        x,p,_,dof=f.update(U_BASE,[np.nan,np.nan])
        np.testing.assert_allclose(f.last_q,f.base_q*factor,rtol=1e-12)
        self.assertEqual(dof,0);self.assertGreater(np.linalg.eigvalsh(p).min(),0)
        self.assertTrue(1<=f.factor<=25)
    def test_fahrenheit_disturbances_and_schedule(self):
        pre,_=inputs('t0_minus30F',3.99);post,_=inputs('t0_minus30F',4.005);back,_=inputs('t0_minus30F',8.01)
        self.assertEqual(pre[4],U_BASE[4]);self.assertEqual(back[4],U_BASE[4])
        before=(pre[4]-273.15)*1.8+32.;after=(post[4]-273.15)*1.8+32.
        self.assertAlmostEqual(after,.7*before)
        _,sp=inputs('servo_minus20',9.);self.assertAlmostEqual(sp,.8*BASE[2])
    def test_controller_bounds_and_predicted_thermal_feasibility(self):
        for step in [self.physical,self.neural]:
            ctrl=NMPC(step,True,network=self.net if step.name().startswith('neural') else None)
            mw,info=ctrl.step(BASE,U_BASE,BASE[2]*1.2)
            self.assertTrue(MW_MIN<=mw<=MW_MAX)
            self.assertTrue(info['solver_feasible']);self.assertFalse(info['fallback'])
            self.assertLessEqual(info['predicted_Tmax'],T_LIMIT+1e-4)

if __name__=='__main__':unittest.main()
