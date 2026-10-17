import unittest
import numpy as np
from schrodinger_lab.model import *
from schrodinger_lab.control import choose,select_scenarios
from schrodinger_lab.server import validate_config

class ControlAndInterface(unittest.TestCase):
    def test_nominal_control_is_bounded_and_replayable(self):
        pts=np.stack([BASE,BASE+.2*NULL_CC,BASE-.2*NULL_CC]);w=np.array([.25,.5,.25])
        for policy in ['nominal','risk','regret']:
            a,da=choose(BASE,pts,w,U0,U0[3],policy);b,db=choose(BASE,pts,w,U0,U0[3],policy)
            self.assertEqual(a,b);self.assertEqual(da,db);self.assertTrue(MIN_MW<=a<=MAX_MW)
    def test_infeasible_controller_has_fallback(self):
        x=BASE.copy();x[4]=350
        u,d=choose(x,x[None],np.ones(1),U0,453.6,'risk')
        self.assertEqual(d['fallback'],1);self.assertTrue(MIN_MW<=u<=MAX_MW)
    def test_server_bounds(self):
        self.assertEqual(validate_config({'scenario':'gaussian','particles':128,'steps':48,'seed':42}),('gaussian',128,48,42))
        for d in [{'particles':100000},{'steps':1000},{'scenario':'unavailable'},{'seed':-1}]:
            with self.assertRaises(ValueError):validate_config(d)
    def test_scenarios_are_existing_particles(self):
        pts=np.tile(BASE,(32,1));pts[:,2]=np.linspace(1,3,32)
        out=select_scenarios(pts,np.full(32,1/32))
        self.assertEqual(out.shape,(9,6));self.assertTrue(all(any(np.array_equal(p,q) for q in pts) for p in out))

if __name__=='__main__':unittest.main()
