import assert from 'node:assert/strict';
import test from 'node:test';
import {BASE, NOMINAL, P, DT, LIMITS, derivative, integrate, flow, fromPercent} from '../lib/simulation/model.ts';
import {SimulationEngine, DEFAULT_CONFIG} from '../lib/simulation/engine.ts';

const config = patch => ({...DEFAULT_CONFIG, percent:{...DEFAULT_CONFIG.percent}, ...patch});
const finite = snapshot => {
  for (const sample of snapshot.history) {
    for (const value of [...sample.x, ...sample.estimate, ...sample.measured, sample.u, sample.sigma]) assert.ok(Number.isFinite(value));
    assert.ok(sample.u >= LIMITS.mwMin && sample.u <= LIMITS.mwMax);
    assert.ok(sample.x.slice(0,4).every(x => x >= 0));
  }
};

test('equilibrium satisfies all six balances and remains stationary without noise', () => {
  assert.ok(derivative(BASE,NOMINAL).every(x => Math.abs(x)<1e-8));
  const engine=new SimulationEngine(config({noise:0}));
  const result=engine.step(800);
  assert.equal(result.error,null);
  assert.equal(result.sample.t,12);
  result.sample.x.forEach((x,i)=>assert.ok(Math.abs(x-BASE[i])<1e-9));
  // The documented source discrepancy is preserved, never calibrated away.
  assert.ok(Math.abs(BASE[4]-340.3034893843503)<1e-8);
  assert.ok(Math.abs(BASE[4]-332.3)>7);
});

test('stoichiometric balances and the inert analytic response are conserved', () => {
  const x=[.42,33,2.1,3.5,337,317],u={...NOMINAL,fm:NOMINAL.fm*1.2};
  const dx=derivative(x,u),v=flow(u);
  assert.ok(Math.abs(dx[0]+dx[2]-(u.fa-v*(x[0]+x[2]))/P.V)<1e-12);
  assert.ok(Math.abs(dx[1]+dx[2]-(u.fb-v*(x[1]+x[2]))/P.V)<1e-12);
  const t=.9, expected=u.fm/v+(BASE[3]-u.fm/v)*Math.exp(-v*t/P.V);
  assert.ok(Math.abs(integrate(BASE,u,t)[3]-expected)<1e-10);
});

test('RK4 agrees after step halving for a nonlinear feed disturbance', () => {
  const u={...NOMINAL,fa:NOMINAL.fa*1.1};
  const a=integrate(BASE,u,.6,.001),b=integrate(BASE,u,.6,.0005);
  a.forEach((x,i)=>assert.ok(Math.abs(x-b[i])<1e-7));
});

test('published event windows use the first sample after 4 h and 8 h; temperature percentages use Fahrenheit', () => {
  const engine=new SimulationEngine(config({scenario:'fa',noise:0}));
  engine.step(267);assert.equal(engine.last.input.fa,NOMINAL.fa);
  engine.step();assert.equal(engine.last.input.fa,NOMINAL.fa*.85);
  engine.step(266);assert.equal(engine.last.input.fa,NOMINAL.fa*.85);
  engine.step();assert.equal(engine.last.input.fa,NOMINAL.fa);
  const feedF=(NOMINAL.t0-273.15)*9/5+32;
  assert.ok(Math.abs(fromPercent('t0',70)-((feedF*.7-32)*5/9+273.15))<1e-10);
});

test('seed, observer/controller changes and consecutive disturbances replay exactly', () => {
  const engine=new SimulationEngine();
  engine.step(20);engine.configure({observer:'ekf',noise:3});engine.step(15);
  engine.configure({percent:{...DEFAULT_CONFIG.percent,fa:110}});engine.step(15);
  engine.configure({controller:'nmpc',observer:'ukf',setpoint:95});engine.step(12);
  engine.configure({controller:'cascade',noise:0});engine.step(10);
  const expected=structuredClone(engine.history);
  const replay=engine.replay();replay.step(800);
  assert.deepEqual(replay.history,expected);
  assert.equal(replay.error,null);
  assert.equal(replay.count,engine.count);
  assert.ok(replay.count<800);
  const fresh=new SimulationEngine();assert.deepEqual(fresh.snapshot(),new SimulationEngine().snapshot());
});

test('pausing is passive: reading the state never advances time or changes it', () => {
  const engine=new SimulationEngine();engine.step(30);
  const before=structuredClone(engine.snapshot());
  for(let i=0;i<100;i++)assert.deepEqual(engine.snapshot(),before);
  const a=new SimulationEngine(),b=new SimulationEngine();a.step(60);b.step(60);
  assert.deepEqual(a.history,b.history);
});

test('all controller/observer combinations finish or stop at the documented thermal boundary with finite bounded output', () => {
  for(const controller of ['open','pid','cascade','nmpc'])for(const observer of ['ekf','ukf']) {
    const engine=new SimulationEngine(config({controller,observer,scenario:'setpoint'}));
    const result=engine.step(800);finite(result);
    assert.ok(result.done,`${controller}/${observer}`);
    if(result.error){assert.equal(result.sample.thermal,'limit');assert.ok(result.error.includes('355,4 K'));}
    else assert.equal(result.count,800);
    if(controller!=='open')assert.ok(new Set(result.history.map(s=>s.u)).size>1);
  }
});

test('disabling the virtual sensor freezes the feedback actuator without reading the hidden state', () => {
  const engine=new SimulationEngine(config({controller:'nmpc'}));engine.step(10);
  engine.configure({observer:'off',setpoint:80});const u=engine.last.u;engine.step(20);
  assert.ok(engine.history.slice(-20).every(sample=>sample.u===u));
  engine.configure({observer:'ekf'});engine.step(10);finite(engine.snapshot());
});

test('thermal event halts safely, retains a valid trace and permits a clean reset', () => {
  const engine=new SimulationEngine(config({noise:0,percent:{...DEFAULT_CONFIG.percent,fa:150,mw:50,t0:150}}));
  const result=engine.step(800);finite(result);
  assert.equal(result.sample.thermal,'limit');assert.ok(result.error.includes('355,4 K'));
  const before=structuredClone(result);assert.deepEqual(engine.step(5),before);
  const reset=new SimulationEngine();assert.equal(reset.count,0);assert.equal(reset.error,null);assert.deepEqual(reset.x,BASE);
});

test('invalid values are rejected before they can corrupt a simulation', () => {
  const engine=new SimulationEngine();
  for(const noise of [NaN,Infinity,-1,4])assert.throws(()=>engine.configure({noise}));
  for(const fa of [NaN,Infinity,-1,151])assert.throws(()=>engine.configure({percent:{...DEFAULT_CONFIG.percent,fa}}));
  assert.throws(()=>engine.configure({setpoint:Infinity}));
  assert.throws(()=>integrate([0,0,0,0,340,319],NOMINAL));
  assert.throws(()=>integrate(BASE,{...NOMINAL,mw:0}));
  assert.equal(engine.count,0);assert.deepEqual(engine.x,BASE);
});

test('extreme permitted disturbance/noise settings and observer tunings never expose NaN or Infinity', () => {
  for(const tuning of ['published','one','three','zero'])for(const noise of [0,3]) {
    const engine=new SimulationEngine(config({tuning,noise,percent:{fa:150,fb:50,fm:50,mw:50,t0:150,ta:150}}));
    finite(engine.step(800));
    assert.ok(engine.done);
    const cold=new SimulationEngine(config({tuning,noise,percent:{fa:50,fb:150,fm:150,mw:150,t0:50,ta:50}}));
    finite(cold.step(800));assert.ok(cold.done);
  }
});
