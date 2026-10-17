import {BASE,NOMINAL,LIMITS,DT,integrate,clamp,type State,type Inputs} from './model.ts';
export type ControllerKind='open'|'pid'|'cascade'|'nmpc';
class PID {
 p:number;i:number;d:number;n:number;integral=0;previous=0;filtered=0;bias:number;
 constructor(p:number,i:number,d:number,n:number,bias:number){Object.assign(this,{p,i,d,n,bias});this.p=p;this.i=i;this.d=d;this.n=n;this.bias=bias;}
 step(e:number,low:number,high:number){
   // Sampled parallel PID with first order derivative filter; a web implementation choice.
   const a=Math.exp(-this.n*DT);this.filtered=a*this.filtered+(1-a)*(e-this.previous)/DT;
   const nextI=this.integral+this.i*e*DT;const raw=this.bias+this.p*e+nextI+this.d*this.filtered;
   // Conditional integration anti-windup: explicitly differs from unspecified original saturation configuration.
   if((raw>=low&&raw<=high)||(raw>high&&this.i*e<0)||(raw<low&&this.i*e>0))this.integral=nextI;
   this.previous=e;return clamp(this.bias+this.p*e+this.integral+this.d*this.filtered,low,high);
 }
}
export class Controller {
 kind:ControllerKind;pid:PID;master:PID;slave:PID;u:number;sequence:number[];predictedMax=BASE[4];
 constructor(kind:ControllerKind='open',u=NOMINAL.mw){this.kind=kind;this.u=u;this.pid=new PID(-55959.2,-325538,-2169.6,124.2,u);this.master=new PID(250.88,7777.25,0,0,BASE[4]);this.slave=new PID(-77.16,-601.39,-1.73,76.1,u);this.sequence=Array(6).fill(u);}
 step(x:State,inputs:Inputs,sp:number,constrained:boolean):number {
   const {mwMin:lo,mwMax:hi}=LIMITS;
   if(this.kind==='open'){this.u=inputs.mw;return this.u;}
   if(this.kind==='pid')this.u=this.pid.step(sp-x[2],lo,hi);
   if(this.kind==='cascade'){const tsp=this.master.step(sp-x[2],-Infinity,Infinity);this.u=this.slave.step(tsp-x[4],lo,hi);}
   if(this.kind==='nmpc')this.u=this.optimize(x,inputs,sp,constrained);
   return this.u;
 }
 optimize(x:State,u:Inputs,sp:number,constrained:boolean):number {
   // Source Ts=.015,p=57,m=6,Qe=.8,Rdu=.2; deterministic coordinate search replaces fmincon/SQP.
   // Thermal limit: lexicographic feasibility priority replaces unspecified QR in eq70.
   const evaluate=(seq:number[])=>{
     let state=[...x] as State,cost=0,prev=this.u,violation=0,max=x[4];
     try {for(let k=0;k<57;k++){const v=seq[Math.min(k,5)];state=integrate(state,{...u,mw:v},DT,.005);cost+=.8*((sp-state[2])/sp)**2;if(k<6){cost+=.2*((v-prev)/NOMINAL.mw)**2;prev=v;}max=Math.max(max,state[4]);if(constrained)violation+=Math.max(0,state[4]-LIMITS.study)**2;}}catch {return {cost:Infinity,violation:Infinity,max:Infinity};}
     return {cost,violation,max};
   };
   const better=(a:ReturnType<typeof evaluate>,b:ReturnType<typeof evaluate>)=>constrained&&Math.abs(a.violation-b.violation)>1e-7?a.violation<b.violation:a.cost<b.cost;
   let seq=[...this.sequence.slice(1),this.sequence[5]],best=evaluate(seq);
   for(const step of [120,45,15])for(let j=0;j<6;j++)for(const sign of [-1,1]){const candidate=[...seq];candidate[j]=clamp(candidate[j]+step*sign,LIMITS.mwMin,LIMITS.mwMax);const value=evaluate(candidate);if(better(value,best)){seq=candidate;best=value;}}
   if(!Number.isFinite(best.cost))throw Error('A predição saiu do domínio do modelo. Reinicie o controle.');
   this.sequence=seq;this.predictedMax=best.max;return seq[0];
 }
}
