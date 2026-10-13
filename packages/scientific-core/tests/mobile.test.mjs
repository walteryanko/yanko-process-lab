import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {Engine,metrics,csv} from '../engine.ts';
import {newProject,importProject,exportProject,connect,validateProject} from '../project.ts';
import {buildModel,rk4} from '../models.ts';
import {Flowsheet,CP,RHO} from '../flowsheet.ts';
import {copy} from '../types.ts';
import {referenceChecks,scientificFingerprint} from '../verification.ts';
import {cholesky} from '../../../lib/simulation/matrix.ts';
import {integrate,BASE,TABLED_BASE,P,TABLED_P,NOMINAL} from '../../../lib/simulation/model.ts';
const science=e=>e.history.map(({computeMs,...s})=>s);
test('recovered PG and EB agree with independent archived DOP853 trajectories',()=>{for(const r of referenceChecks())assert.ok(r.ok,JSON.stringify(r));});
test('original TypeScript trajectories retain substep equivalence in SI seconds',()=>{
 for(const id of ['pg-calibrated','pg-table']){const m=buildModel(newProject(id)),x=id==='pg-table'?TABLED_BASE:BASE,p=id==='pg-table'?TABLED_P:P;const a=rk4(m,x,NOMINAL.mw*.97,540,2),b=integrate(x,{...NOMINAL,mw:NOMINAL.mw*.97,t0:NOMINAL.t0+2},.15,.001,p);a.forEach((v,i)=>assert.ok(Math.abs(v-b[i])<1e-9));}
});
test('every supported model and observer runs with finite PSD covariance',()=>{
 for(const model of ['pg-original','pg-calibrated','pg-table','eb-reduced','flowsheet'])for(const observer of ['ekf','ukf']){const p=newProject(model);p.science.settings.observer=observer;const e=new Engine(p);for(let i=0;i<80&&!e.done;i++){e.step();cholesky(e.estimator.cov);}assert.equal(e.error,null,model+'/'+observer);assert.ok(e.last.t>0);assert.ok(e.last.x.every(Number.isFinite));}
});
test('checkpoint recovery preserves RNG, PID and observer state exactly',()=>{const p=newProject();p.science.settings.controller='pid';p.science.settings.setpoint+=1;const e=new Engine(p);for(let i=0;i<20;i++)e.step();e.configure({disturbance:2});const restored=Engine.restore(e.checkpoint());for(let i=0;i<20;i++){e.step();restored.step()}assert.deepEqual(science(e),science(restored));assert.deepEqual(e.estimator.cov,restored.estimator.cov);});
test('observer cannot read hidden truth; initialization independent of plant override',()=>{const p=newProject(),q=copy(p);q.science.initial=[...buildModel(p).x0];q.science.initial[2]*=1.1;const a=new Engine(p),b=new Engine(q);assert.deepEqual(a.estimator.x,b.estimator.x);const sa=a.settings,y=[333,315];a.estimator.update(a.u,y,sa);b.estimator.update(a.u,y,sa);assert.deepEqual(a.estimator.x,b.estimator.x)});
test('PID, cascade and bounded NMPC change applied inputs, retain causal history',()=>{
 for(const controller of ['pid','cascade','nmpc']){const p=newProject();p.science.settings.controller=controller;p.science.settings.setpoint=controller==='cascade'?2.4:333.3;const e=new Engine(p);for(let i=0;i<30&&!e.done;i++)e.step();assert.equal(e.error,null);assert.ok(e.history.some(s=>s.u!==e.model.u0));assert.ok(e.history.every(s=>s.u>=e.model.bounds[0]&&s.u<=e.model.bounds[1]));}
});
test('predictive work can be cancelled before any scientific state changes',()=>{const p=newProject();p.science.settings.controller='nmpc';const e=new Engine(p),before=e.checkpoint(),job=e.advance();assert.equal(job.next().done,false);job.return();assert.deepEqual(e.checkpoint(),before);});
test('NMPC estimator-off fallback holds without hidden-state feedback',()=>{const p=newProject();p.science.settings.controller='nmpc';p.science.settings.observer='off';const e=new Engine(p);e.step();assert.equal(e.last.u,p.science.settings.manual);assert.match(e.last.solver,/fallback/);});
test('flowsheet preserves material and thermal balances during real dynamics',()=>{const p=newProject('flowsheet'),f=new Flowsheet(p.graph);for(let i=0;i<10;i++){const r=f.evaluate();assert.ok(Math.abs(r.massResidual)<1e-12);assert.ok(Math.abs(r.energyResidual)<1e-7);}const e=new Engine(p);e.step();assert.notDeepEqual(e.last.x,e.model.x0);});
test('tank mixing follows independent analytic response',()=>{const p=newProject('flowsheet');p.graph.nodes=p.graph.nodes.filter(n=>n.kind!=='heater');p.graph.nodes.find(n=>n.kind==='cstr').kind='tank';const tank=p.graph.nodes[1];delete tank.parameters.k;delete tank.parameters.heat_release;p.graph.edges=[{id:'a',source:'F-101',target:'R-101',source_port:'out',target_port:'in',kind:'material'},{id:'b',source:'R-101',target:'P-101',source_port:'out',target_port:'in',kind:'material'}];const m=buildModel(p),x=rk4(m,m.x0,0,30);assert.ok(Math.abs(x[0]-(.1+.05*Math.exp(-30/100)))<1e-10);assert.ok(Math.abs(x[1]-(295.15+4.85*Math.exp(-30/100)))<1e-8);});
test('invalid graph, settings and occupied ports are rejected',()=>{const p=newProject('flowsheet');assert.throws(()=>connect(p,'F-101','out','R-101','in'));const q=copy(p);q.graph.edges.pop();assert.throws(()=>new Engine(q));for(const v of [NaN,Infinity,-1,0]){const x=newProject();x.science.settings.dt=v;assert.throws(()=>new Engine(x));}const bad=newProject();bad.science.settings.measurementIndices=[2];assert.throws(()=>new Engine(bad));});
test('unknown desktop payload survives exact roundtrip and remains unexecutable',()=>{const d={schema_version:1,id:'desktop',name:'Future',model:'pg-original',nodes:[],edges:[],experiment:{solver:'BDF'},unknown:{future:[1,2,3]}};const p=importProject(JSON.stringify(d));assert.deepEqual(JSON.parse(exportProject(p)),d);assert.throws(()=>new Engine(p));});
test('mobile extension fields and separation of layout survive roundtrip',()=>{const p=newProject();p.future={retained:true};const q=importProject(exportProject(p));assert.deepEqual(p,q);const a=new Engine(p),b=new Engine({...copy(p),layout:{...p.layout,zoom:2}});a.step();b.step();assert.deepEqual(science(a),science(b));});
test('CSV exports every numerical sample without chart decimation',()=>{const e=new Engine(newProject());for(let i=0;i<12;i++)e.step();assert.equal(csv(e).split('\n').length,e.history.length+1);assert.match(csv(e),/C_C_estimate_kmol/);assert.ok(metrics(e).samples===12);});
test('seed changes sensor data and identical seeds replay deterministically',()=>{const p=newProject(),a=new Engine(p),b=new Engine(p),q=copy(p);q.science.settings.seed++;const c=new Engine(q);for(let i=0;i<10;i++){a.step();b.step();c.step();}assert.deepEqual(science(a),science(b));assert.notDeepEqual(a.last.measured,c.last.measured)});
test('RK4 refinement agrees after nonlinear disturbance',()=>{for(const id of ['pg-original','eb-reduced']){const m=buildModel(newProject(id)),a=rk4(m,m.x0,m.u0*.99,180,2),b=rk4(m,m.x0,m.u0*.99,180,2,m.maxStep/2);a.forEach((v,i)=>assert.ok(Math.abs(v-b[i])<1e-6));}});
