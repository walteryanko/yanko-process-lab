import copy
import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp
from processlab.schema import canonical
from processlab.scenarios import scenarios,node,edge
from processlab.models import ResearchModel,reference
from processlab.flowsheet import Flowsheet,CP,RHO
from processlab.numerics import integrate,covariance
from processlab.simulation import Simulation
from processlab.estimation import Observer
from processlab.storage import Storage,atomic_json
from processlab.api import API
from processlab.sensors import Sensors


class ScientificStudio(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.examples=scenarios()
    def example(self,i=1):return copy.deepcopy(self.examples[i])

    def test_dimensional_conversion_and_rejection(self):
        p=self.example();p['nodes'][0]['parameters']['flow']={'value':3600,'unit':'kg/h'}
        self.assertEqual(canonical(p)['nodes'][0]['parameters']['flow'],1)
        p['nodes'][0]['parameters']['flow']={'value':1,'unit':'kelvin'}
        with self.assertRaises(Exception):canonical(p)

    def test_steady_mass_and_energy_analytic(self):
        m=Flowsheet(self.example(0));x,r=m.steady(0)
        target=(295.15+0.5*315.15)/1.5+15000/(1.5*CP)
        self.assertAlmostEqual(x[1],target,9);self.assertAlmostEqual(x[0],1/6,10)
        self.assertLess(abs(r['mass_residual_kg_s']),1e-12)
        self.assertLess(abs(r['energy_residual_W']),1e-7)

    def test_tank_transient_matches_analytic_solution(self):
        p=self.example();m=Flowsheet(p);x=integrate(m,m.x0,20000,0,100,p['experiment'])
        expected=298.15+20000/CP*(1-np.exp(-1))
        self.assertAlmostEqual(x[1],expected,7)

    def test_splitter_mixer_and_energy_connections(self):
        p=self.example();p['nodes']=[node('F','source',0,0,flow=2,temperature=298.15),node('S','splitter',1,0,split=.3),node('M','mixer',2,0),node('T','tank',3,0),node('Q','energy',3,1,duty=10000),node('P','sink',4,0)]
        p['edges']=[edge('1','F','S'),edge('2','S','M','out1','in1'),edge('3','S','M','out2','in2'),edge('4','M','T'),edge('5','T','P'),edge('6','Q','T','heat','heat','energy')];p['control_equipment']='T'
        m=Flowsheet(canonical(p));r=m.evaluate();self.assertAlmostEqual(r['streams']['S:out1']['flow'],.6)
        self.assertAlmostEqual(r['mass_residual_kg_s'],0);self.assertAlmostEqual(r['energy_residual_W'],0,7)

    def test_cstr_material_conversion_balance(self):
        p=self.example();p['nodes'][1]['kind']='cstr';p['nodes'][1]['parameters'].update(k=.01,heat_release=100000,duty=0)
        m=Flowsheet(canonical(p));x,r=m.steady(0)
        self.assertAlmostEqual(x[0],.05,9);self.assertAlmostEqual(x[1],298.15+5000/CP,7)
        self.assertLess(abs(r['energy_residual_W']),1e-6)

    def test_pump_valve_exchanger_equipment_executes(self):
        p=self.example();p['nodes']=[node('F','source',0,0),node('B','pump',1,0),node('V','valve',2,0),node('H','exchanger',3,0),node('P','sink',4,0)]
        p['edges']=[edge(str(i),a,b) for i,(a,b) in enumerate(zip(['F','B','V','H'],['B','V','H','P']))];p.pop('control_equipment')
        m=Flowsheet(canonical(p));x,r=m.steady();self.assertEqual(len(x),0)
        self.assertAlmostEqual(r['units']['P']['pressure'],151325);self.assertGreater(r['units']['P']['temperature'],298.15)
        self.assertLess(abs(r['energy_residual_W']),1e-6)

    def test_ports_reject_duplicate_connections(self):
        p=self.example();p['edges'].append(edge('duplicate','F-101','P-101'))
        with self.assertRaisesRegex(ValueError,'occupied'):Flowsheet(p)

    def test_disconnected_and_recycles_rejected(self):
        p=self.example();p['edges'].pop()
        with self.assertRaises(ValueError):Flowsheet(p)
        p=self.example();p['edges'][0]['target_port']='heat'
        with self.assertRaises(ValueError):Flowsheet(p)

    def test_pg_nominal_and_source_derivative_parity(self):
        m=ResearchModel('pg-original');r=reference('pg')
        np.testing.assert_allclose(m.x0,[.607025,33.989102,2.295765,3.628487,332.333618,314.397585],atol=1e-6,rtol=0)
        rng=np.random.default_rng(40)
        for _ in range(50):
            x=m.x0+rng.normal(size=6)*m.scale*.1
            np.testing.assert_allclose(m.rhs(x,m.u0)*3600,r.rhs(0,x,r.U0),rtol=2e-12,atol=2e-10)
        self.assertLess(max(abs(m.rhs(m.x0,m.u0))),1e-10)

    def test_pg_independent_imperial_equations(self):
        m=ResearchModel('pg-original');ref=reference('pg');rng=np.random.default_rng(411)
        for _ in range(100):
            x=m.x0+rng.normal(size=6)*m.scale*.2
            ci=x[:4]/ref.CUNIT;T,Tj=(x[4:]-273.15)*1.8+32
            cp=np.array([35,18,46,19.5]);V=500/7.484;v=80/.923+1000/3.45+100/1.54
            rate=16.96e12*np.exp(-32400/(1.987*(T+460)))*ci[0]
            dc=(np.array([80,1000,0,100])-v*ci)/V+rate*np.array([-1,-1,1,0])
            Q=1000*18*(60-T)*(-np.expm1(-16000/(1000*18)))
            dT=(Q-(80*35+1000*18+100*19.5)*(T-75)+36000*rate*V)/(V*(ci@cp))
            dTj=(1000*18*(60-Tj)-Q)/(3.45*18*38.85)
            independent=np.r_[dc*ref.CUNIT,dT/1.8,dTj/1.8]/3600
            np.testing.assert_allclose(m.rhs(x,m.u0),independent,atol=1e-12,rtol=1e-9)

    def test_pg_thermal_ambiguity_preserved(self):
        m=ResearchModel('pg-original');p=self.example(2);d=np.array([0,-.2*m.parameters['cpC']/m.parameters['cpB'],.2,0,0,0])
        a=integrate(m,m.x0-d/2,m.u0,0,54,p['experiment']);b=integrate(m,m.x0+d/2,m.u0,0,54,p['experiment'])
        np.testing.assert_allclose(a[4:],b[4:],atol=1e-8,rtol=0);self.assertGreater(abs(b[2]-a[2]),.1)

    def test_eb_reduced_adapter_and_hess_defect_preserved(self):
        m=ResearchModel('eb-reduced');r=reference('eb')
        np.testing.assert_allclose(m.rhs(m.x0,m.u0),np.asarray(r.F(m.x0,r.U0,np.zeros(12))).ravel()/3600,atol=1e-14)
        self.assertAlmostEqual(float(-r.DH[0]+r.DH[1]+r.DH[2]),-5.5)

    def test_rk4_converges_to_adaptive_solver(self):
        p=self.example(2);m=ResearchModel('pg-original');x=m.x0.copy();x[4]+=2
        a=integrate(m,x,m.u0,1,54,{**p['experiment'],'solver':'DOP853','rtol':1e-11,'atol':1e-12})
        b=integrate(m,x,m.u0,1,54,{**p['experiment'],'solver':'RK4'})
        np.testing.assert_allclose(a,b,atol=2e-7,rtol=0)

    def test_repeat_seed_and_save_reopen(self):
        p=self.example();p['experiment']['duration']=30
        with tempfile.TemporaryDirectory() as d:
            s=Storage(d);s.save(p);q=s.load(p['id']);s.save(q)
            a=Simulation(p).run();b=Simulation(q).run();self.assertEqual(a['rows'],b['rows'])
            self.assertTrue(s.path(p['id']).with_suffix('.bak').exists())
            self.assertFalse(list(Path(d).glob('*.tmp')))
            with self.assertRaises(ValueError):s.load('../escape')

    def test_inspection_does_not_advance_and_invalid_reset_preserves(self):
        with tempfile.TemporaryDirectory() as d:
            api=API(d);self.assertTrue(api.request('reset',self.example())['ok']);a=api.request('inspect')['data']
            self.assertEqual(a['rows'],api.request('inspect')['data']['rows'])
            p=self.example();p['experiment']['dt']=-1;self.assertFalse(api.request('reset',p)['ok'])
            self.assertEqual(a['rows'],api.request('inspect')['data']['rows'])

    def test_sensor_delay_dropout_and_determinism(self):
        p=self.example();m=Flowsheet(p);c=p['experiment'];c['sensor_delay']=2
        a=Sensors(m,c);b=Sensors(m,c)
        for k in range(5):
            aa=a.sample(k,m.x0);bb=b.sample(k,m.x0);self.assertEqual(aa,bb)
            if k<2:self.assertEqual(aa,[])
            else:self.assertEqual(aa[0]['sample'],k-2)
        c['sensor_dropout']=1;s=Sensors(m,c)
        for k in range(4):self.assertEqual(s.sample(k,m.x0),[])
        self.assertEqual(s.dropped,4)

    def test_delayed_replay_equals_chronological_filter(self):
        for estimator in ['ekf','ukf']:
            p=self.example();p['experiment']['observer']=estimator;m=Flowsheet(p)
            a=Observer(m,p['experiment']);b=Observer(m,p['experiment'])
            for k in range(6):
                if k:a.advance(0,0);b.advance(0,0)
                ea=[{'sample':k,'arrival':k,'kind':'thermal','values':[298.15+.01*k],'variance':[.01]}] if k<3 else []
                j=k-2;eb=[{'sample':j,'arrival':k,'kind':'thermal','values':[298.15+.01*j],'variance':[.01]}] if 0<=j<3 else []
                a.assimilate(k,ea);b.assimilate(k,eb)
            np.testing.assert_allclose(a.x,b.x,atol=1e-10);np.testing.assert_allclose(a.P,b.P,atol=1e-10)

    def test_no_future_events(self):
        p=self.example();o=Observer(Flowsheet(p),p['experiment'])
        with self.assertRaises(ValueError):o.assimilate(0,[{'arrival':2,'sample':0}])

    def test_estimators_are_finite_and_report_uncertainty(self):
        for name in ['ekf','ukf','mhe']:
            p=self.example();p['experiment'].update(observer=name,duration=20)
            r=Simulation(p).run();self.assertEqual(r['status'],'completed',r['error'])
            self.assertTrue(np.isfinite(r['rows'][-1]['estimate']).all())
            self.assertTrue(np.all(np.array(r['rows'][-1]['sd'])>0))

    def test_nmpc_bounds_rates_and_fallback_reporting(self):
        p=self.example(4);p['experiment']['duration']=40
        s=Simulation(p);r=s.run();self.assertEqual(r['status'],'completed',r['error'])
        U=np.array([x['input'] for x in r['rows']]);self.assertTrue(np.all(U>=s.model.bounds[0]));self.assertTrue(np.all(U<=s.model.bounds[1]))
        self.assertLessEqual(max(abs(np.diff(U))),s.model.slew*p['experiment']['dt']+1e-8)
        self.assertIn('optimizer_failures',r['controller'])

    def test_pid_changes_process_and_reduces_error(self):
        p=self.example();p['experiment']['duration']=300
        a=Simulation(p).run();p['experiment']['controller']='manual';b=Simulation(p).run()
        self.assertEqual(a['status'],'completed');self.assertEqual(b['status'],'completed')
        self.assertLess(a['metrics']['iae'],.7*b['metrics']['iae'])

    def test_invalid_values_and_covariance_rejected(self):
        p=self.example();p['experiment']['sensor_sigma']=float('nan')
        with self.assertRaises(ValueError):canonical(p)
        with self.assertRaises(ValueError):covariance(np.diag([1.,-1.]))
        p=self.example();p['schema_version']=999
        with self.assertRaises(ValueError):canonical(p)

    def test_all_scenarios_execute_and_save(self):
        with tempfile.TemporaryDirectory() as d:
            api=API(d)
            for p in self.examples:
                self.assertTrue(api.request('save',p)['ok']);q=api.request('open',{'id':p['id']})['data']
                self.assertTrue(api.request('reset',q)['ok']);r=api.request('advance',{'count':2})
                self.assertTrue(r['ok']);self.assertNotEqual(r['data']['status'],'failed',r['data']['error'])

    def test_live_setpoint_replays_and_exports_actual_rows(self):
        with tempfile.TemporaryDirectory() as d:
            api=API(d);p=self.example();api.request('reset',p);api.request('advance',{'count':3})
            api.request('setpoint',{'setpoint':305});api.request('advance',{'count':3})
            record=api.request('export')['data']['result'];replayed=Simulation.replay(record)
            self.assertEqual(record['rows'],replayed['rows'])
            exported=api.request('export_csv')['data'];self.assertTrue(Path(exported['path']).is_file())
            self.assertEqual(len(exported['csv'].splitlines()),len(record['rows'])+1)

    def test_local_http_auth_origin_and_static_serving(self):
        from processlab.server import serve
        from urllib.request import Request,urlopen
        from urllib.error import HTTPError
        with tempfile.TemporaryDirectory() as d:
            server,url=serve(API(d));origin=url.split('/#')[0];token=url.split('token=')[1]
            try:
                with urlopen(origin+'/') as r:self.assertEqual(r.status,200)
                request=Request(origin+'/api',data=b'{"method":"inspect"}',headers={'Content-Type':'application/json'})
                with self.assertRaises(HTTPError):urlopen(request)
                request.add_header('X-ProcessLab-Token',token)
                with urlopen(request) as r:self.assertTrue(json.load(r)['ok'])
                request.add_header('Origin','https://unrelated.invalid')
                with self.assertRaises(HTTPError):urlopen(request)
                with self.assertRaises(HTTPError):urlopen(origin+'/%2e%2e/desktop.py')
            finally:server.shutdown();server.server_close()

    def test_duplicate_measurement_does_not_double_update(self):
        p=self.example();o=Observer(Flowsheet(p),p['experiment'])
        e={'id':'sample-0','sample':0,'arrival':0,'kind':'thermal','values':[299.],'variance':[.1]}
        o.assimilate(0,[e]);x=o.x.copy();P=o.P.copy();o.assimilate(0,[e])
        np.testing.assert_array_equal(o.x,x);np.testing.assert_array_equal(o.P,P)


if __name__=='__main__':unittest.main(verbosity=2)
