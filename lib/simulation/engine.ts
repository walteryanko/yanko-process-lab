import {BASE,DT,NOMINAL,LIMITS,fromPercent,integrate,clamp,type State,type Inputs} from './model.ts';
import {Observer,type ObserverKind,type Tuning} from './observer.ts';
import {Controller,type ControllerKind} from './controller.ts';
export type Scenario='free'|'fa'|'fb'|'t0'|'ta'|'setpoint';
export type Config={controller:ControllerKind;observer:ObserverKind;tuning:Tuning;noise:number;constrained:boolean;scenario:Scenario;percent:Inputs;setpoint:number};
export const DEFAULT_CONFIG:Config={controller:'open',observer:'ukf',tuning:'published',noise:1,constrained:true,scenario:'free',percent:{fa:100,fb:100,fm:100,mw:100,t0:100,ta:100},setpoint:100};
export type Sample={t:number;x:State;estimate:State;measured:[number,number];sigma:number;u:number;sp:number;input:Inputs;thermal:'normal'|'attention'|'limit';locked:boolean;predictedMax:number};
type Event={at:number;patch:Partial<Config>};
export type Snapshot={sample:Sample;config:Config;history:Sample[];done:boolean;error:string|null;replay:boolean;count:number};
export class SeededNoise {
 seed:number;constructor(seed=2019){this.seed=seed;}
 uniform(){this.seed=(Math.imul(1664525,this.seed)+1013904223)>>>0;return (this.seed+.5)/4294967296;}
 normal(){return Math.sqrt(-2*Math.log(this.uniform()))*Math.cos(2*Math.PI*this.uniform());}
}
const cloneConfig=(c:Config):Config=>({...c,percent:{...c.percent}});
export class SimulationEngine {
 config:Config;initial:Config;observer:Observer;controller:Controller;rng=new SeededNoise();x:State=[...BASE];count=0;history:Sample[]=[];events:Event[]=[];replaying=false;replayUntil=0;done=false;error:string|null=null;last:Sample;
 constructor(config:Config=DEFAULT_CONFIG){this.config=cloneConfig(config);this.initial=cloneConfig(config);this.observer=new Observer(config.observer,config.tuning);this.controller=new Controller(config.controller);this.last={t:0,x:[...BASE],estimate:[...BASE],measured:[BASE[4],BASE[5]],sigma:Math.sqrt(this.observer.cov[2][2]),u:NOMINAL.mw,sp:BASE[2],input:{...NOMINAL},thermal:'normal',locked:true,predictedMax:BASE[4]};this.history=[this.last];}
 configure(patch:Partial<Config>,record=true){
   if(patch.noise!==undefined&&(!Number.isFinite(patch.noise)||patch.noise<0||patch.noise>3))throw Error('Ruído fora da faixa de exploração.');
   if(patch.percent&&Object.values(patch.percent).some(v=>!Number.isFinite(v)||v<50||v>150))throw Error('Perturbação fora da faixa de exploração.');
   if(patch.setpoint!==undefined&&(!Number.isFinite(patch.setpoint)||patch.setpoint<80||patch.setpoint>120))throw Error('Setpoint fora da faixa de exploração.');
   if(patch.controller&&!['open','pid','cascade','nmpc'].includes(patch.controller))throw Error('Controle inválido.');
   if(patch.observer&&!['off','ekf','ukf'].includes(patch.observer))throw Error('Observador inválido.');
   if(patch.controller&&patch.controller!==this.config.controller)this.controller=new Controller(patch.controller,this.last.u);
   if(patch.observer&&patch.observer!==this.config.observer)this.observer=new Observer(patch.observer,this.config.tuning,this.observer.x);
   if(patch.tuning)this.observer.tuning=patch.tuning;
   this.config={...this.config,...patch,percent:patch.percent?{...patch.percent}:{...this.config.percent}};
   if(record){this.replaying=false;this.events.push({at:this.count,patch:JSON.parse(JSON.stringify(patch))});}
 }
 inputs():{u:Inputs,sp:number} {
   const percent={...this.config.percent},t=this.count*DT;let spPercent=this.config.setpoint;
   // Published severe tests: t=4h / 8h; setpoint stays at -20% after4h.
   if(t>=4&&t<8){if(this.config.scenario==='fa')percent.fa=85;if(this.config.scenario==='fb')percent.fb=110;if(this.config.scenario==='t0')percent.t0=70;if(this.config.scenario==='ta')percent.ta=80;}
   if(t>=4&&this.config.scenario==='setpoint')spPercent=80;
   const u=Object.fromEntries(Object.entries(percent).map(([key,v])=>[key,fromPercent(key as keyof Inputs,v)])) as Inputs;
   u.mw=clamp(u.mw,LIMITS.mwMin,LIMITS.mwMax);
   return {u,sp:BASE[2]*spPercent/100};
 }
 step(steps=1):Snapshot {
   for(let i=0;i<steps&&!this.done;i++){
     try{
       if(this.replaying)for(const event of this.events.filter(e=>e.at===this.count))this.configure(event.patch,false);
       const {u,sp}=this.inputs();
       // With the virtual sensor disabled, freeze the feedback actuator, never access true hidden CC.
       const mv=this.config.controller==='open'?u.mw:this.config.observer==='off'?this.last.u:this.controller.step(this.observer.x,u,sp,this.config.constrained);
       const command={...u,mw:mv};
       const plant=Object.fromEntries(Object.entries(command).map(([key,v])=>[key,v*(1+this.rng.normal()*.01*this.config.noise)])) as Inputs;
       plant.mw=clamp(plant.mw,LIMITS.mwMin,LIMITS.mwMax);
       const next=integrate(this.x,plant);
       const measured:[number,number]=[next[4]+this.rng.normal()*.01*BASE[4]*this.config.noise,next[5]+this.rng.normal()*.01*BASE[5]*this.config.noise];
       const estimate=this.observer.update(command,measured);
       this.x=next;this.count++;
       const thermal=next[4]>=LIMITS.practical?'limit':next[4]>=LIMITS.study?'attention':'normal';
       this.last={t:this.count*DT,x:[...next],estimate:[...estimate],measured,sigma:Math.sqrt(this.observer.cov[2][2]),u:mv,sp,input:command,thermal,locked:Math.abs(estimate[2]-next[2])<=Math.max(.01,next[2]*.01),predictedMax:this.controller.predictedMax};
       this.history.push(this.last);
       if(thermal==='limit'){this.done=true;this.error='355,4 K: limite operacional citado atingido. A simulação foi pausada; o modelo não descreve evaporação ou explosão.';}
       if(this.count>=800||(this.replaying&&this.count>=this.replayUntil))this.done=true;
     }catch(e){this.done=true;this.error=e instanceof Error?e.message:'Não foi possível avançar a simulação.';}
   }
   return this.snapshot();
 }
 replay():SimulationEngine {const engine=new SimulationEngine(this.initial);engine.events=JSON.parse(JSON.stringify(this.events));engine.replaying=true;engine.replayUntil=Math.max(1,this.count);return engine;}
 snapshot():Snapshot {return {sample:this.last,config:cloneConfig(this.config),history:this.history,done:this.done,error:this.error,replay:this.replaying,count:this.count};}
}
