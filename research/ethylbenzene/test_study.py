"""Independent numerical, derivative and information-flow checks."""
import unittest
import numpy as np
from scipy.integrate import solve_ivp
from unittest.mock import patch
from model import *
from networks import LSTM,NeuralTransition
from compiled import Models,symbolic_steps,HORIZON,MOVES,BLOCK
from observer import Observer
from control import NMPC
from protocol import scenario

class StudyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.net=NeuralTransition.load();cls.models=Models()
    def test_equilibrium_units_and_stoichiometry(self):
        np.testing.assert_allclose(rhs(BASE,U0),0,atol=2e-10)
        np.testing.assert_allclose(BASE[:4]/BASE[:4].sum(),TARGET_FRACTIONS,atol=6.1e-5)
        np.testing.assert_allclose(MW@NU,0,atol=1e-12)
        self.assertGreater(abs(concentrations_at_temperature(TNOM,time_factor=60.)[0]-BASE[0]),1.)
    def test_independent_integrator_and_native_parity(self):
        x=BASE+[.007,.14,-.11,.035,2.];u=U0.copy();u[[0,3]]*=[1.08,1.05]
        truth=solve_ivp(lambda t,z:rhs(z,u),(0,DT),x,method='DOP853',rtol=1e-12,atol=1e-12).y[:,-1]
        native=self.models.transition('physical',x,u)
        np.testing.assert_allclose(native,truth,rtol=2e-6,atol=8e-6)
        np.testing.assert_allclose(native,transition(x,u),rtol=2e-12,atol=2e-12)
        np.testing.assert_allclose(self.models.transition('neural',x,u),self.net(x,u),rtol=1e-11,atol=1e-11)
    def test_neural_independence(self):
        with patch('model.rhs',side_effect=AssertionError('physical RHS must not be used online')):
            np.testing.assert_allclose(self.net(BASE,U0),BASE,atol=2e-11)
            self.assertTrue(np.all(np.isfinite(self.net(BASE+[.01,.1,-.1,.01,1.],U0))))
    def test_lstm_bptt_and_export(self):
        rng=np.random.default_rng(7);net=LSTM(3,4,2,seed=5);x=rng.normal(size=(2,5,3));y=rng.normal(size=(2,2))
        _,g=net.loss_grad(x,y);h=1e-6
        for key,index in [('W',(1,9)),('W',(5,1)),('b',(7,)),('V',(2,1)),('d',(0,))]:
            old=net.p[key][index];net.p[key][index]=old+h;plus=net.loss_grad(x,y)[0]
            net.p[key][index]=old-h;minus=net.loss_grad(x,y)[0];net.p[key][index]=old
            self.assertAlmostEqual((plus-minus)/(2*h),g[key][index],delta=2e-7)
        for k in ['physical','neural']:
            loaded=LSTM.load(WEIGHTS/f'lstm_q_{k}.json');self.assertEqual(loaded.p['W'].shape,(33,64))
    def test_native_horizon_gradients_and_rollout(self):
        q=np.tile([1.04,1.02],MOVES);theta=np.r_[BASE,U0,fraction(BASE)*1.02,TNOM,[1.,1.]]
        for kind in ['physical','neural']:
            f=self.models.evaluators[kind,'mimo',True];val=f(q,theta);h=1e-6
            for j in [0,1,5]:
                d=np.zeros(len(q));d[j]=h;vp=f(q+d,theta);vm=f(q-d,theta)
                self.assertAlmostEqual((vp[0][0]-vm[0][0])/(2*h),val[1][j],delta=3e-5)
                np.testing.assert_allclose((vp[2]-vm[2])/(2*h),val[3][:,j],atol=4e-6,rtol=3e-6)
            state=BASE.copy();cost=0.;maxT=-np.inf
            for i in range(HORIZON):
                j=min(i//BLOCK,MOVES-1);u=U0.copy();u[0]=q[2*j]*F0[0];u[3]=q[2*j+1]*Q0
                state=transition(state,u) if kind=='physical' else self.net(state,u)
                cost+=.8*((fraction(state)-theta[12])/.02)**2+.2*((state[4]-TNOM)/5.)**2;maxT=max(maxT,state[4])
            moves=q.reshape(MOVES,2);cost+=.03*np.sum(np.diff(np.vstack([[1.,1.],moves]),axis=0)**2)
            self.assertAlmostEqual(cost,val[0][0],delta=2e-7)
            self.assertAlmostEqual(maxT,T_LIMIT-5*np.min(val[2][:HORIZON]),delta=2e-8)
        reference=Models(fast_neural=False)
        for mode in ['siso','mimo']:
            nmv=1 if mode=='siso' else 2;qq=q[::2] if nmv==1 else q
            for con in [False,True]:
                native=self.models.evaluators['neural',mode,con](qq,theta)
                slow=reference.evaluators['neural',mode,con](qq,theta)
                for a,b in zip(native,slow):np.testing.assert_allclose(a,b,rtol=2e-10,atol=2e-9)
    def test_causal_q_covariance_and_missing_sensor(self):
        for k in ['lstm_ukf','nake','lstm_nake']:
            model='neural' if k in ['nake','lstm_nake'] else 'physical';lstm=LSTM.load(WEIGHTS/f'lstm_q_{model}.json')
            a=Observer(BASE,self.models,k,lstm,self.net);b=Observer(BASE,self.models,k,lstm,self.net)
            a.update(U0,TNOM-4.);b.update(U0,TNOM+4.)
            np.testing.assert_array_equal(a.last_q,b.last_q)
            x,p,nis=a.update(U0,np.nan);self.assertIsNone(nis);self.assertGreater(np.linalg.eigvalsh(p).min(),0)
            self.assertTrue(np.all(a.last_q>0));self.assertTrue(np.all(np.isfinite(x)))
    def test_original_events_and_controller_feasibility(self):
        self.assertEqual(scenario('benzene_50',4.999)[0][1],U0[1]);self.assertEqual(scenario('benzene_50',5.)[0][1],1.5*U0[1])
        self.assertEqual(scenario('recycle_minus50',5.)[0][2],.5*U0[2])
        for p in ['physical','neural']:
            for m in ['siso','mimo']:
                ctrl=NMPC(self.models,p,m,True);action,d=ctrl.step(BASE,U0,fraction(BASE))
                self.assertGreaterEqual(action[0],.04);self.assertLessEqual(action[0],2.)
                self.assertTrue(d['feasible']);self.assertFalse(d['fallback']);self.assertLessEqual(d['predicted_Tmax_C'],T_LIMIT+1e-4)

if __name__=='__main__':unittest.main()
