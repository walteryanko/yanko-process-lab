import {type FlowGraph,type NodeKind,type UnitNode} from './types.ts';
export const CP=4180,RHO=1000;
export const CATALOG:Record<NodeKind,{label:string;inputs:string[];outputs:string[];defaults:Record<string,number>}>={
 source:{label:'Alimentação',inputs:[],outputs:['out'],defaults:{flow:1,temperature:295.15,fraction:.1,pressure:101325}},
 sink:{label:'Produto',inputs:['in'],outputs:[],defaults:{}},
 mixer:{label:'Misturador',inputs:['in1','in2'],outputs:['out'],defaults:{}},
 splitter:{label:'Divisor',inputs:['in'],outputs:['out1','out2'],defaults:{split:.5}},
 tank:{label:'Tanque',inputs:['in'],outputs:['out'],defaults:{volume:.1,temperature:300,fraction:.15,duty:0}},
 cstr:{label:'CSTR A → B',inputs:['in'],outputs:['out'],defaults:{volume:.1,temperature:300,fraction:.15,duty:0,k:.005,heat_release:15000}},
 pump:{label:'Bomba',inputs:['in'],outputs:['out'],defaults:{pressure_rise:100000,efficiency:.8}},
 valve:{label:'Válvula',inputs:['in'],outputs:['out'],defaults:{pressure_drop:10000}},
 heater:{label:'Aquecedor',inputs:['in'],outputs:['out'],defaults:{duty:15000}},
 cooler:{label:'Resfriador',inputs:['in'],outputs:['out'],defaults:{duty:-10000}},
 exchanger:{label:'Trocador',inputs:['in'],outputs:['out'],defaults:{UA:1000,utility_temperature:310}},
};
export const PARAM_UNITS:Record<string,string>={flow:'kg/s',temperature:'K',fraction:'kg/kg',pressure:'Pa',split:'0–1',volume:'m³',duty:'W',k:'s⁻¹',heat_release:'J/kg',pressure_rise:'Pa',pressure_drop:'Pa',efficiency:'0–1',UA:'W/K',utility_temperature:'K'};
export function validateNode(n:UnitNode){
 const c=CATALOG[n.kind];if(!c)throw Error(`Equipamento não suportado: ${n.kind}`);
 for(const k of Object.keys(c.defaults))if(!Number.isFinite(n.parameters[k]))throw Error(`${n.id}: ${k} inválido`);
 const p=n.parameters;
 for(const k of ['flow','volume','pressure'])if(k in p&&p[k]<=0)throw Error(`${n.id}: ${k} deve ser positivo`);
 for(const k of ['temperature','utility_temperature'])if(k in p&&(p[k]<273.15||p[k]>373.15))throw Error(`${n.id}: ${k} fora de 273,15–373,15 K`);
 if('fraction' in p&&(p.fraction<0||p.fraction>1))throw Error('Fração fora de 0–1');
 if('split' in p&&(p.split<=0||p.split>=1))throw Error('Divisão deve estar entre 0 e 1');
 if('efficiency' in p&&(p.efficiency<=0||p.efficiency>1))throw Error('Eficiência fora de (0, 1]');
 for(const k of ['UA','k','pressure_rise','pressure_drop','heat_release'])if(k in p&&p[k]<0)throw Error(`${k} não pode ser negativo`);
}
export type Stream={flow:number;temperature:number;fraction:number;pressure:number};
export class Flowsheet {
 graph:FlowGraph;nodes:Map<string,UnitNode>;order:string[]=[];inlets:Record<string,string>={};dynamic:string[];x0:number[];target:string|undefined;
 constructor(graph:FlowGraph){
  this.graph=graph;this.nodes=new Map(graph.nodes.map(n=>[n.id,n]));
  if(!graph.nodes.length||graph.nodes.length>100||this.nodes.size!==graph.nodes.length)throw Error('Planta vazia, duplicada ou acima de 100 equipamentos');
  const incoming:Record<string,number>={},outgoing=new Set<string>(),ids=new Set<string>();
  for(const n of graph.nodes){validateNode(n);incoming[n.id]=0;}
  for(const e of graph.edges){
   const a=this.nodes.get(e.source),b=this.nodes.get(e.target),ik=`${e.target}:${e.target_port}`,ok=`${e.source}:${e.source_port}`;
   if(!a||!b||a===b||ids.has(e.id)||e.kind!=='material'||!CATALOG[a.kind].outputs.includes(e.source_port)||!CATALOG[b.kind].inputs.includes(e.target_port)||ik in this.inlets||outgoing.has(ok))throw Error('Conexão incompatível ou porta ocupada');
   ids.add(e.id);outgoing.add(ok);this.inlets[ik]=ok;incoming[e.target]++;
  }
  for(const n of graph.nodes){
   if(CATALOG[n.kind].inputs.some(p=>!this.inlets[`${n.id}:${p}`])||CATALOG[n.kind].outputs.some(p=>!outgoing.has(`${n.id}:${p}`)))throw Error(`${n.id}: conecte todas as portas`);
  }
  const queue=graph.nodes.filter(n=>incoming[n.id]===0).map(n=>n.id);
  while(queue.length){const a=queue.shift()!;this.order.push(a);for(const e of graph.edges)if(e.source===a&&--incoming[e.target]===0)queue.push(e.target);}
  if(this.order.length!==graph.nodes.length)throw Error('Reciclos/DAE não suportados');
  this.dynamic=this.order.filter(k=>['tank','cstr'].includes(this.nodes.get(k)!.kind));
  this.x0=this.dynamic.flatMap(k=>{const p=this.nodes.get(k)!.parameters;return[p.fraction,p.temperature]});
  this.target=this.dynamic[this.dynamic.length-1];
 }
 evaluate(x=this.x0,u?:number,d=0){
  const streams:Record<string,Stream>={},units:Record<string,Stream>={},dx=x.map(()=>0);let supply=0,products=0,ein=0,eout=0,heat=0,acc=0;
  for(const id of this.order){const n=this.nodes.get(id)!,p=n.parameters,c=CATALOG[n.kind],ins=c.inputs.map(k=>streams[this.inlets[`${id}:${k}`]]);let out:Stream;
   const duty=id===this.target&&u!==undefined?u:p.duty??0;
   if(n.kind==='source'){out={flow:p.flow,temperature:p.temperature+d,fraction:p.fraction,pressure:p.pressure};supply+=out.flow;ein+=out.flow*CP*(out.temperature-273.15);}
   else if(n.kind==='mixer'){const f=ins[0].flow+ins[1].flow;out={flow:f,temperature:ins.reduce((s,v)=>s+v.flow*v.temperature,0)/f,fraction:ins.reduce((s,v)=>s+v.flow*v.fraction,0)/f,pressure:Math.min(...ins.map(s=>s.pressure))};}
   else {out={...ins[0]};
    if(n.kind==='sink'){products+=out.flow;eout+=out.flow*CP*(out.temperature-273.15);}
    if(n.kind==='tank'||n.kind==='cstr'){const i=this.dynamic.indexOf(id)*2,m=RHO*p.volume,r=(p.k??0)*x[i],q=m*r*(p.heat_release??0);dx[i]=out.flow/m*(out.fraction-x[i])-r;dx[i+1]=out.flow/m*(out.temperature-x[i+1])+(duty+q)/(m*CP);acc+=m*CP*dx[i+1];heat+=duty+q;out.fraction=x[i];out.temperature=x[i+1];}
    if(n.kind==='heater'||n.kind==='cooler'){out.temperature+=duty/(out.flow*CP);heat+=duty;}
    if(n.kind==='exchanger'){const t=p.utility_temperature+(out.temperature-p.utility_temperature)*Math.exp(-p.UA/(out.flow*CP));heat+=out.flow*CP*(t-out.temperature);out.temperature=t;}
    if(n.kind==='pump'){out.pressure+=p.pressure_rise;const q=out.flow*p.pressure_rise/RHO*(1/p.efficiency-1);out.temperature+=q/(out.flow*CP);heat+=q;}
    if(n.kind==='valve'){out.pressure-=p.pressure_drop;out.temperature+=p.pressure_drop/(RHO*CP);heat+=out.flow*p.pressure_drop/RHO;}
   }
   if(Object.values(out).some(v=>!Number.isFinite(v))||out.flow<=0||out.pressure<=0||out.temperature<273.15||out.temperature>373.15||out.fraction< -1e-8||out.fraction>1+1e-8)throw Error(`${id}: fora do domínio líquido`);
   units[id]=out;
   for(const port of c.outputs)streams[`${id}:${port}`]={...out,flow:out.flow*(n.kind==='splitter'?(port==='out1'?p.split:1-p.split):1)};
  }
  return{dx,streams,units,massResidual:supply-products,energyResidual:ein+heat-eout-acc};
 }
}
