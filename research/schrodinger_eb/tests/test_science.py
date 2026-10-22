import unittest,json,tempfile,subprocess
from pathlib import Path
from unittest.mock import patch
import numpy as np
from scipy.integrate import solve_ivp
from scipy.stats import wasserstein_distance
from eblab.model import *
from eblab.probability import *
from eblab.transport import sinkhorn,transform
from eblab.bridge import generate as bridge_generate,drift
from eblab.filters import *
from eblab.experiments import generate,run,initial,measurement_spec,paired_summary,write_json,save_csv

class ProbabilityTests(unittest.TestCase):
    def test_log_normalization_extreme(self):
        w=normalize([-1e8,-1e8-1,-1e8-1000]);self.assertAlmostEqual(w.sum(),1);self.assertGreaterEqual(w.min(),0)
    def test_ess(self):
        self.assertAlmostEqual(ess(np.full(100,.01)),100);self.assertEqual(ess(np.array([1.,0.])),1)
    def test_resampling_unbiased(self):
        w=np.array([.13,.27,.6]);rng=np.random.default_rng(1);ids=np.r_[tuple(systematic(w,rng,100) for _ in range(100))]
        np.testing.assert_allclose(np.bincount(ids)/len(ids),w,atol=.003)
    def test_partial_missing_likelihood(self):
        x=np.stack([BASE,BASE+np.array([0,0,0,0,1])]);R=np.eye(1)
        a=loglik(x,np.array([BASE[4]]),R)
        self.assertAlmostEqual(a[0]-a[1],.5)
        np.testing.assert_array_equal(loglik(x,np.full(1,np.nan),R),[0,0])
    def test_score_identities(self):
        self.assertEqual(crps_ensemble(np.array([2.]),np.array([1.]),3.),1.)
        self.assertAlmostEqual(energy_score(np.array([[2.,2.]]),np.ones(1),np.array([3.,2.]),np.ones(2)),1.)
    def test_transport_marginals(self):
        rng=np.random.default_rng(4);x=rng.normal(size=(40,2));w=normalize(rng.normal(size=40))
        p,d=sinkhorn(cdist(x,x,'sqeuclidean'),w,np.full(40,1/40),epsilon=.5,max_iter=3000)
        self.assertTrue(d['converged']);self.assertTrue(np.all(p>=0));self.assertAlmostEqual(p.sum(),1)
        np.testing.assert_allclose(p.sum(1),w,atol=1e-8);np.testing.assert_allclose(p.sum(0),1/40,atol=1e-8)
    def test_transport_zero_weights(self):
        p,d=sinkhorn(np.array([[0.,1.],[1.,0.]]),np.array([1.,0.]),np.array([.5,.5]),.001)
        np.testing.assert_allclose(p,[[.5,.5],[0,0]],atol=1e-10)
    def test_transport_mean_and_variance_bias(self):
        x=np.arange(10.)[:,None];w=normalize(-.2*(x[:,0]-5)**2)
        a,p,d=transform(x,w,np.ones(1),epsilon=1.)
        np.testing.assert_allclose(a.mean(0),w@x,atol=1e-6)
        self.assertLess(d['variance_ratio'],1.)
    def test_sinkhorn_invalid(self):
        with self.assertRaises(ValueError):sinkhorn(np.ones((2,2)),np.ones(2),np.ones(2),.1)
    def test_gaussian_bridge_exact_drift(self):
        # A single kernel is N(z,h²). Its bridge drift has a closed form.
        z=np.array([[2.]]);x=np.array([[.7]]);t=.4;h=.6
        expected=(2-(1-h*h)*.7)/(1-t+t*h*h)
        self.assertAlmostEqual(drift(x,t,z,np.array([0.]),h)[0,0],expected)
    def test_published_empirical_drift(self):
        x=np.array([[.2,-.1]]);z=np.array([[1.,2.],[-.5,.1],[.1,.3]]);w=np.array([.1,.6,.3]);t=.7
        e=w*np.exp(-np.sum((z-x)**2,1)/(2*(1-t))+np.sum(z*z,1)/2)
        exact=np.sum(e[:,None]*(z-x),axis=0)/((1-t)*e.sum())
        np.testing.assert_allclose(drift(x,t,z,np.log(w),0)[0],exact,atol=1e-12)
    def test_bimodal_known_posterior(self):
        rng=np.random.default_rng(7);x=rng.normal(0,1.5,(768,1));w=normalize(-.5*((x[:,0]**2-4)/.3)**2)
        out,d,path=bridge_generate(x,w,rng,steps=128,bandwidth=.05)
        self.assertGreater(np.mean(out[:,0]<-1.5),.3);self.assertGreater(np.mean(out[:,0]>1.5),.3)
        self.assertLess(abs(out.mean()),.35)
        self.assertLess(wasserstein_distance(x[:,0],out[:,0],u_weights=w),.3)

class FilterTests(unittest.TestCase):
    def test_linear_gaussian_ukf(self):
        cfg=FilterConfig();m,p=initial('gaussian');R=np.eye(1)*.2
        f=UKF(m,p,R,cfg);y=BASE[4:]+np.array([.3]);F=np.eye(5);F[4,0]=.2
        propagate_linear=lambda x,u,c:x@F.T+(BASE-F@BASE)
        pp=F@p@F.T+np.diag(Q_PUBLISHED);k=pp@H.T@np.linalg.inv(H@pp@H.T+R)
        expected=m+k@(y-H@m);a=np.eye(5)-k@H;pc=a@pp@a.T+k@R@k.T
        with patch('eblab.filters.propagate',propagate_linear):f.advance(U0,y)
        np.testing.assert_allclose(f.x,expected,atol=1e-10);np.testing.assert_allclose(f.P,pc,atol=1e-10)
    def test_enkf_linear_moments(self):
        cfg=FilterConfig(particles=8000);m,p=initial('gaussian');R=np.eye(1)*.2
        f=Ensemble('enkf',m,p,R,cfg,seed=77);y=BASE[4:]+np.array([.3])
        out=f.enkf(f.x,y);k=p@H.T@np.linalg.inv(H@p@H.T+R)
        np.testing.assert_allclose(out.mean(0),m+k@(y-H@m),atol=.04)
    def test_causality_prefix(self):
        ep=generate(85,'gaussian',8);other={**ep,'y':ep['y'].copy()};other['y'][5:]+=100
        for method in METHODS:
            cfg=FilterConfig(particles=32,bridge_steps=16)
            a,ta=run(ep,method,cfg);b,tb=run(other,method,cfg)
            np.testing.assert_array_equal(ta['estimates'][:5],tb['estimates'][:5])
    def test_reproducibility(self):
        ep=generate(12,'outliers',5);cfg=FilterConfig(particles=32,bridge_steps=16,likelihood='mixture')
        a,ta=run(ep,'M4',cfg);b,tb=run(ep,'M4',cfg)
        np.testing.assert_array_equal(ta['estimates'],tb['estimates'])
    def test_no_future_or_truth_input(self):
        import inspect
        self.assertEqual(list(inspect.signature(UKF.advance).parameters),['self','u','y'])
        self.assertEqual(list(inspect.signature(Ensemble.advance).parameters),['self','u','y','inspect'])
    def test_fallback(self):
        m,p=initial('gaussian');cfg=FilterConfig(particles=16,sinkhorn_max_iter=1,epsilon=.001)
        f=Ensemble('transport',m,p,np.eye(1)*.1,cfg,1);f.advance(U0,BASE[4:]+[2])
        self.assertEqual(f.last['fallback'],1);self.assertTrue(np.all(valid(f.x)))
    def test_missing_data_prediction(self):
        m,p=initial('gaussian');cfg=FilterConfig(particles=32);f=UKF(m,p,np.eye(1),cfg)
        f.advance(U0,np.array([np.nan]));self.assertTrue(np.all(np.linalg.eigvalsh(f.P)>0))
    def test_paired_data_and_statistics(self):
        a=generate(17,'gaussian',4);b=generate(17,'gaussian',4)
        np.testing.assert_array_equal(a['true'],b['true'])
        r0,_=run(a,'M0',FilterConfig(particles=16));r1,_=run(a,'M2',FilterConfig(particles=16))
        summary=paired_summary([r0,r1]);self.assertEqual(summary['gaussian']['M2']['paired_vs_M0']['n'],1)
    def test_export_roundtrip(self):
        ep=generate(5,'gaussian',3);r,t=run(ep,'M0',FilterConfig(particles=16))
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/'data.json';write_json(file,dict(episode=ep,result=r,trace=t));v=json.loads(file.read_text())
            self.assertEqual(v['result']['seed'],5);self.assertEqual(len(v['episode']['true']),4)
            save_csv(Path(d)/'data.csv',[r]);self.assertIn('rmse_CEB',(Path(d)/'data.csv').read_text())
    def test_joint_parameters_separate(self):
        ep=generate(43,'physics',4);cfg=FilterConfig(particles=32,joint=True,bridge_steps=16)
        r,t=run(ep,'M1',cfg);self.assertIsNone(r['failure']);self.assertEqual(len(r['parameter_rmse']),5)

if __name__=='__main__':unittest.main()
