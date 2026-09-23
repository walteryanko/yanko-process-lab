import {SimulationEngine,DEFAULT_CONFIG} from '../lib/simulation/engine.ts';
const engine=new SimulationEngine({...DEFAULT_CONFIG,percent:{...DEFAULT_CONFIG.percent},noise:0,observer:'ukf'});
const result=engine.step(100);
console.log(JSON.stringify({hours:result.sample.t,temperatureK:result.sample.x[4],concentration:result.sample.x[2],estimatedConcentration:result.sample.estimate[2],error:result.error,note:'Exploratory reimplementation; does not reproduce the published equilibrium.'},null,2));
