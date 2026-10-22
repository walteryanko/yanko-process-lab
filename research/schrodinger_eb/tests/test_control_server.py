import unittest,json,threading,urllib.request,urllib.error
from http.server import ThreadingHTTPServer
import numpy as np
from eblab.server import validate_config,Handler
from eblab.control import NMPC,nominal_fallback,representatives,MOVE_LIMIT
from eblab.model import BASE,U0,fraction
from eblab.filters import FilterConfig,make_filter
from eblab.experiments import initial

class InterfaceControl(unittest.TestCase):
    def test_server_config(self):
        self.assertEqual(validate_config({'particles':64,'steps':8})[1],64)
        for v in [{'particles':2048},{'steps':1000},{'scenario':'unrecognized'},{'seed':-1}]:
            with self.assertRaises(ValueError):validate_config(v)
    def test_local_api(self):
        http=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
        try:
            base='http://127.0.0.1:'+str(http.server_address[1])
            self.assertTrue(json.loads(urllib.request.urlopen(base+'/api/status').read())['online'])
            req=urllib.request.Request(base+'/api/run',data=b'{"particles":2048}',headers={'Content-Type':'application/json'})
            with self.assertRaises(urllib.error.HTTPError) as ctx:urllib.request.urlopen(req)
            self.assertEqual(ctx.exception.code,400)
        finally:http.shutdown();http.server_close()
    def test_nominal_equilibrium(self):
        m,p=initial('gaussian');f=make_filter('M0',m,p,np.array([[2.25]]),FilterConfig(),9);x,w,_=f.posterior()
        a,d=NMPC().choose(m,x,w,U0,fraction(BASE));np.testing.assert_allclose(a,1,atol=1e-5);self.assertEqual(d['fallback'],0)
    def test_forced_fallback_limits(self):
        prev=np.ones(2);x=BASE.copy();x[4]+=15
        a=nominal_fallback(x,fraction(BASE)*1.1,prev)
        self.assertTrue(np.all(abs(a-prev)<=MOVE_LIMIT+1e-12));self.assertTrue(np.all(a>0))
    def test_joint_scenarios_not_marginal_combinations(self):
        p=np.tile(BASE,(20,1));p[:,2]+=np.linspace(-.2,.2,20);p[:,4]+=np.linspace(-1,1,20)
        s=representatives(BASE,p,np.full(20,.05),'risk');self.assertEqual(s.shape,(5,5))
        for row in s[1:]:self.assertTrue(any(np.array_equal(row,r) for r in p))
