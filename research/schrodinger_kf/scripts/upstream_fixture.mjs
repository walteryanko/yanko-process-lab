import {BASE,NOMINAL,derivative,integrate} from '../vendor/processlab/model.ts';
import {Observer} from '../vendor/processlab/observer.ts';
const x=[.42,33,2.1,3.5,337,317];
const observer=new Observer('ukf','published',BASE);
const estimates=[];
for(let k=0;k<12;k++)estimates.push(observer.update(NOMINAL,[BASE[4]+.3*Math.sin(k),BASE[5]-.4*Math.cos(k)]));
console.log(JSON.stringify({base:BASE,derivative:derivative(x,NOMINAL),integrated:integrate(x,NOMINAL,.12),estimates,cov:observer.cov}));
