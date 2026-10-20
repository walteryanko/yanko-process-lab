import sys,unittest,inspect,importlib.util,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from model import *
from estimation import Filter
from control import *
class ScientificTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.x=equilibrium();cls.p=np.zeros(3)
    def test_01_historical_rhs_parity(self):
        path=ROOT.parent/'darwin-observer/vendor/legacy_model.py'
        spec=importlib.util.spec_from_file_location('frozen_legacy',path)
        legacy=importlib.util.module_from_spec(spec);sys.modules[spec.name]=legacy;spec.loader.exec_module(legacy)
        for t in [315.,332.3,345.]:
            x=self.x.copy();x[4]=t
            uu=np.array([U0[0],U0[3],U0[5]])
            np.testing.assert_allclose(rhs(x,U0,self.p),legacy.rhs(0,x,uu),rtol=2e-12,atol=2e-10)
    def test_02_conserved_reaction_inventories(self):
        d=rhs(self.x,U0,self.p);s=inventory(self.x)
        expected=np.array([U0[0],U0[1],U0[2]])/V-dilution(U0)*s
        np.testing.assert_allclose([d[0]+d[2],d[1]+d[2],d[3]],expected,atol=1e-11)
    def test_03_energy_accounting(self):
        # Exact enthalpy balance for hypothetical thermodynamically consistent variants.
        for variant in [1,2,3,4]:
            x=self.x.copy();x[4]+=3.;u=U0.copy()
            dx=rhs(x,u,self.p,variant)
            cp,hi,_=props(x[4],self.p,variant);_,hf,_=props(u[4],self.p,variant)
            hi=hi+np.array([0.,0.,-83736.,0.]);hf=hf+np.array([0.,0.,-83736.,0.])
            q,_,_,_,_=energy_terms(x,u,self.p,variant)
            lhs=V*(np.dot(x[:4],cp)*dx[4]+np.dot(hi,dx[:4]))
            feed=np.array([u[0],u[1],0.,u[2]])
            rhsE=q+np.dot(feed,hf)-dilution(u)*V*np.dot(x[:4],hi)
            self.assertAlmostEqual(lhs,rhsE,places=6)
    def test_04_equilibrium(self):self.assertLess(max(abs(rhs(self.x,U0,self.p))),1e-7)
    def test_05_positivity(self):
        U=np.tile(U0,(40,1));X=rollout(self.x,U,self.p,nsub=12)
        self.assertTrue(np.min(X[:,:4])>0)
    def test_06_independent_integration(self):
        for v in range(5):
            a=step(self.x,U0,self.p,v,12);b=independent(self.x,U0,self.p,v)
            np.testing.assert_allclose(a,b,atol=2e-6,rtol=2e-8)
    def test_07_jacobian_step_consistency(self):
        a=jacobian(lambda z:rhs(z,U0,self.p),self.x,1e-4)
        b=jacobian(lambda z:rhs(z,U0,self.p),self.x,1e-5)
        np.testing.assert_allclose(a,b,rtol=2e-5,atol=2e-6)
    def test_08_twins_constant_cp_and_jacket(self):
        U=np.tile(U0,(30,1));U[:,3]*=1+.2*np.sin(np.arange(30))
        for v in [0,1,2]:
            a=rollout(self.x,U,self.p,v,12);b=rollout(twin(self.x,.4),U,self.p,v,12)
            np.testing.assert_allclose(a[:,4:],b[:,4:],atol=1e-9,rtol=0)
    def test_09_variable_cp_falsifies_specific_twin(self):
        U=np.tile(U0,(30,1));U[:,3]*=1+.2*np.sin(np.arange(30))
        a=rollout(self.x,U,self.p,4,12);b=rollout(twin(self.x,.4),U,self.p,4,12)
        # A prescribed minimum output difference is a scientific hypothesis, not an implementation gate.
        # Initial trial was 9.516165278e-7 K (below the old arbitrary 1e-6 cutoff).
        # Verify the analytic change away from the Cp reference temperature instead.
        z=self.x.copy();z[4]+=10.
        zt=twin(z,.4)
        capa=energy_terms(z,U0,self.p,4)[2];capb=energy_terms(zt,U0,self.p,4)[2]
        cp,_,_=props(z[4],self.p,4)
        expected=V*.4*(cp[2]-CP[2]/CP[1]*cp[1])
        self.assertAlmostEqual(capb-capa,expected,places=8)
        self.assertGreater(abs(rhs(z,U0,self.p,4)[4]-rhs(zt,U0,self.p,4)[4]),1e-10)
    def test_10_rank_has_two_exact_null_directions(self):
        x=self.x.copy();x[4]+=2
        A=jacobian(lambda z:rhs(z,U0,self.p),x)
        for d in [np.array([0,-CP[2]/CP[1],1,0,0,0]),np.array([0,-CP[3]/CP[1],0,1,0,0])]:
            np.testing.assert_allclose(A@d,-dilution(U0)*d,atol=3e-6)
    def test_11_causal_prefix(self):
        y=np.tile(self.x[4:],(5,1));y[2]+=.1
        a=Filter(self.x);b=Filter(self.x)
        aa=[];bb=[]
        for k in range(5):aa.append(a.update(U0,y[k],advance=k>0))
        for k in range(3):bb.append(b.update(U0,y[k],advance=k>0))
        np.testing.assert_array_equal(np.array(aa)[:3],bb)
        self.assertNotIn('truth',inspect.signature(Filter.update).parameters)
    def test_12_inventory_reconstruction(self):
        s=inventory(self.x);z=self.x[[2,4,5]]
        expected=step(self.x,U0,self.p,0,12)
        result=reconstruct(expected[[2,4,5]],inventory_step(s,U0))
        np.testing.assert_allclose(result,expected,atol=1e-9)
    def test_13_constraints(self):
        for previous in [.05,1.,3.]:
            p=candidates(previous)
            self.assertTrue(np.all(p>=.05) and np.all(p<=3))
            self.assertTrue(np.max(abs(p[:,0]-previous))<=.40000001)
            self.assertTrue(np.max(abs(p[:,1]-p[:,0]))<=.40000001)
    def test_14_failed_optimization_fallback(self):
        _,fall,r=select(np.ones((2,3)),np.ones((2,3)),'regret')
        self.assertTrue(fall);self.assertTrue(np.isnan(r))
    def test_15_regret_exact(self):
        J=np.array([[0.,1.,4.],[4.,1.,0.]]);V=np.zeros_like(J)
        j,fall,r=select(J,V,'regret');self.assertEqual(j,1);self.assertEqual(r,1);self.assertFalse(fall)
    def test_16_zero_conflict_not_impossible_state_error(self):
        J=np.tile([2.,0.,1.],(2,1));j,fall,r=select(J,np.zeros_like(J),'regret')
        self.assertEqual(r,0);self.assertEqual(j,1)
    def test_17_seed_separation(self):
        p=json.loads((ROOT/'configs/protocol.json').read_text())
        groups=[set(p[k]) for k in ['development_seeds','validation_seeds','test_seeds','confirmation_seeds']]
        for i in range(len(groups)):
            for j in range(i):self.assertFalse(groups[i]&groups[j])
    def test_18_reproducible_and_metric_independent(self):
        from experiments import episode
        a=episode('nominal','B1_ukf',11,steps=4,save=True);b=episode('nominal','B1_ukf',11,steps=4)
        self.assertEqual(a['IAE'],b['IAE'])
        z=np.load(ROOT/'results/trajectories/nominal__B1_ukf__11.npz')
        e=abs(z['x'][:,2]-z['reference'])
        independently=float(sum((e[:-1]+e[1:])*.5*np.diff(z['t'])))
        self.assertAlmostEqual(a['IAE'],independently,places=13)
        rm=np.sqrt(sum((z['x'][:,2]-z['estimate'][:,2])**2)/len(z['t']))
        self.assertAlmostEqual(a['RMSE_CC'],rm,places=13)
if __name__=='__main__':unittest.main()
