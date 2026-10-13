import {type Project,type ModelId,type Settings,type UnitNode,VERSION,copy} from './types.ts';
import {buildModel} from './models.ts';
import {CATALOG,validateNode} from './flowsheet.ts';
export function newProject(model:ModelId='pg-original'):Project{
 const nodes:UnitNode[]=[{id:'F-101',kind:'source',parameters:{...CATALOG.source.defaults}},{id:'H-101',kind:'heater',parameters:{...CATALOG.heater.defaults}},{id:'R-101',kind:'cstr',parameters:{...CATALOG.cstr.defaults}},{id:'P-101',kind:'sink',parameters:{}}];
 const p:Project={schema_version:1,id:`p-${Date.now()}-${Math.random().toString(36).slice(2,7)}`,name:model==='flowsheet'?'Minha planta':model==='eb-reduced'?'Etilbenzeno R1':'CSTR · Propilenoglicol',model,modelVersion:VERSION,science:{settings:{} as Settings},graph:{nodes,edges:nodes.slice(1).map((n,i)=>({id:`S-${i}`,source:nodes[i].id,target:n.id,source_port:'out',target_port:'in',kind:'material'}))},layout:{nodes:Object.fromEntries(nodes.map((n,i)=>[n.id,{x:40+i*170,y:110}])),zoom:1,pan:{x:0,y:0}}};
 const m=buildModel(p),flow=model==='flowsheet';
 p.science.settings={dt:flow?2:model==='eb-reduced'?72:54,duration:flow?600:4320,seed:2019,controller:'manual',observer:'ekf',setpoint:m.x0[m.ti],manual:m.u0,kp:flow?5000:model==='eb-reduced'?-100000:-60,ki:flow?10:model==='eb-reduced'?-100:-.2,kd:0,noise:.1,qScale:1,rScale:1,horizon:6,disturbance:0,initialOffset:.02,measurementIndices:m.measured};
 if(!flow){p.graph.nodes=p.graph.nodes.filter(n=>n.kind!=='heater');p.graph.edges=[{id:'S-feed',source:'F-101',target:'R-101',source_port:'out',target_port:'in',kind:'material'},{id:'S-product',source:'R-101',target:'P-101',source_port:'out',target_port:'in',kind:'material'}];p.layout.nodes=Object.fromEntries(p.graph.nodes.map((n,i)=>[n.id,{x:40+i*170,y:110}]))}
 return p;
}
export function validateSettings(s:Settings,m:ReturnType<typeof buildModel>){
 for(const k of ['dt','duration','seed','setpoint','manual','kp','ki','kd','noise','qScale','rScale','horizon','disturbance','initialOffset'] as const)if(!Number.isFinite(s[k]))throw Error(`${k}: valor não finito`);
 if(s.dt<=0||s.dt>120||s.duration<s.dt||s.duration/s.dt>20000)throw Error('Duração/passos fora do orçamento (até 20 mil amostras)');
 if(!Number.isInteger(s.seed)||s.seed<0||s.seed>4294967295)throw Error('Seed deve ser inteiro de 0 a 4294967295');
 if(!['manual','pid','cascade','nmpc'].includes(s.controller)||!['off','ekf','ukf'].includes(s.observer))throw Error('Algoritmo não suportado');
 if(s.controller==='cascade'&&(m.id==='flowsheet'||m.id==='eb-reduced'))throw Error('Cascata disponível apenas para PG');
 if(s.manual<m.bounds[0]||s.manual>m.bounds[1]||s.noise<0||s.noise>3||s.qScale<0||s.qScale>100||s.rScale<=0||s.rScale>100||s.horizon<2||s.horizon>12||!Number.isInteger(s.horizon)||Math.abs(s.disturbance)>15||Math.abs(s.initialOffset)>.1)throw Error('Parâmetro fora dos limites de exploração');
 if(!Array.isArray(s.measurementIndices)||!s.measurementIndices.length||new Set(s.measurementIndices).size!==s.measurementIndices.length||s.measurementIndices.some(i=>!m.measured.includes(i)))throw Error('Medições indisponíveis: somente sensores de temperatura modelados');
 const qi=s.controller==='cascade';if(s.setpoint<(qi?.01:m.x0[m.ti]-30)||s.setpoint>(qi?6:m.limit))throw Error('Setpoint fora do domínio');
}
export function validateProject(p:Project){
 if(p.schema_version!==1)throw Error('Versão de projeto não suportada; arquivo preservado');
 if(typeof p.id!=='string'||typeof p.name!=='string'||p.name.length>120)throw Error('Identificação inválida');
 if(!p.layout?.nodes||!p.graph?.nodes||!p.science?.settings)throw Error('Estrutura incompleta');
 if(p.readOnlyReason)return;
 const m=buildModel(p);validateSettings(p.science.settings,m);
 if(p.science.initial)m.check(p.science.initial);
 for(const xy of Object.values(p.layout.nodes))if(!Number.isFinite(xy.x)||!Number.isFinite(xy.y))throw Error('Posição inválida');
}
export function importProject(text:string):Project{
 if(text.length>25_000_000)throw Error('Arquivo acima de 25 MB');
 const p=JSON.parse(text);
 if(p.project)return importProject(JSON.stringify(p.project));
 if(p.science){validateProject(p);return p;}
 if(p.schema_version!==1||!Array.isArray(p.nodes))throw Error('Formato desconhecido');
 // Preserve the whole desktop document. Never silently convert a solver or estimator.
 const a=newProject(p.model==='flowsheet'?'flowsheet':p.model==='pg-original'?'pg-original':'eb-reduced');a.name=p.name;a.id=p.id;a.model=p.model;a.desktopSource=copy(p);
 a.graph={nodes:p.nodes,edges:p.edges};a.layout.nodes=Object.fromEntries(p.nodes.map((n:any)=>[n.id,n.layout??{x:0,y:0}]));
 a.readOnlyReason='Projeto desktop preservado para inspeção/exportação. Solver e contrato de sensores precisam de migração explícita; não são substituídos.';
 return a;
}
export function exportProject(p:Project){return JSON.stringify(p.desktopSource&&p.readOnlyReason?p.desktopSource:p,null,2);}
export function connect(p:Project,source:string,source_port:string,target:string,target_port:string):Project{
 const a=copy(p),s=a.graph.nodes.find(n=>n.id===source),t=a.graph.nodes.find(n=>n.id===target);
 if(!s||!t||source===target||!CATALOG[s.kind].outputs.includes(source_port)||!CATALOG[t.kind].inputs.includes(target_port)||a.graph.edges.some(e=>(e.source===source&&e.source_port===source_port)||(e.target===target&&e.target_port===target_port)))throw Error('Portas incompatíveis ou ocupadas');
 const reaches=(id:string,seen=new Set<string>()):boolean=>{if(id===source)return true;if(seen.has(id))return false;seen.add(id);return a.graph.edges.filter(e=>e.source===id).some(e=>reaches(e.target,seen));};
 if(reaches(target))throw Error('Reciclos não suportados');
 a.graph.edges.push({id:`S-${Date.now()}`,source,target,source_port,target_port,kind:'material'});return a;
}
export function setNodeParameter(p:Project,id:string,key:string,value:number){const a=copy(p),n=a.graph.nodes.find(n=>n.id===id);if(!n)throw Error('Equipamento ausente');n.parameters[key]=value;validateNode(n);return a;}
