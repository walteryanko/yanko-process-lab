import fixtures from './fixtures/reference.json' with {type:'json'};
import {buildModel,rk4} from './models.ts';
import {Engine} from './engine.ts';
import {newProject} from './project.ts';
import {type ModelId} from './types.ts';
export function referenceChecks(){
 return fixtures.cases.map(c=>{
  const m=buildModel(newProject(c.model as ModelId));let x=[...c.x0],maxError=0;
  const derivativeError=Math.max(...m.rhs(x,c.u,c.disturbance).map((v,i)=>Math.abs(v-c.rhs[i])));
  for(let j=1;j<c.times.length;j++){x=rk4(m,x,c.u,c.dt,c.disturbance);maxError=Math.max(maxError,...x.map((v,i)=>Math.abs(v-c.trajectory[j][i])));}
  return{model:c.model,maxError,derivativeError,tolerance:c.tolerance,ok:maxError<c.tolerance&&derivativeError<1e-10};
 });
}
export function scientificFingerprint(){
 const p=newProject('pg-original');p.id='fixture';p.science.settings.controller='pid';p.science.settings.setpoint+=1;p.science.settings.seed=42;const e=new Engine(p);
 for(let i=0;i<24;i++)e.step();
 return[...e.last.x,...e.last.estimate,...e.last.sigma,e.last.u];
}
