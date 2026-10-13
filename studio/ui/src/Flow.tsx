import {useCallback,useState} from 'react';
import {ReactFlow,Background,Controls,Handle,Position,ReactFlowProvider,useReactFlow,applyNodeChanges,MarkerType,type NodeProps,type Node,type Connection as RFConnection,type Edge} from '@xyflow/react';
import {Droplets,FlaskConical,GitMerge,Split,Container,ArrowUpRight,SlidersHorizontal,Flame,Snowflake,RefreshCw,Zap,PackageCheck} from 'lucide-react';
import '@xyflow/react/dist/style.css';
import {EquipmentGraphic} from './EquipmentGraphic';
import type {Project,Catalog,Result,Equipment} from './types';
export const icons:Record<string,typeof Droplets>={source:Droplets,sink:PackageCheck,mixer:GitMerge,splitter:Split,tank:Container,pump:ArrowUpRight,valve:SlidersHorizontal,heater:Flame,cooler:Snowflake,exchanger:RefreshCw,cstr:FlaskConical,energy:Zap};
type UnitData={equipment:Equipment;catalog:Catalog;result?:Record<string,number>;running?:boolean};
function Unit({data,selected}:NodeProps<Node<UnitData>>){
  const n=data.equipment,c=data.catalog[n.kind],Icon=icons[n.kind]||FlaskConical;
  return <div className={`equipment ${selected?'selected':''} ${n.kind}`}>
    {c.inputs.map((p,i)=><Handle key={p} id={p} type="target" position={Position.Left} style={{top:`${(i+1)/(c.inputs.length+1)*100}%`}} title={p}/>)}
    {c.energy&&<Handle id="heat" type="target" position={Position.Bottom} className="energy-handle" title="Entrada de energia"/>}
    <div className="equipment-head"><span>{c.label}</span><i className={data.result?'active':''}/></div><div className="equipment-body"><EquipmentGraphic kind={n.kind} active={data.running}/><strong>{n.label||n.id}</strong></div>
    <div className="equipment-value">{data.result?.temperature!=null?<><b>{data.result.temperature.toFixed(2)}</b> K <span>· {data.result.flow.toFixed(2)} kg/s</span></>:n.kind==='energy'?`${n.parameters.duty} W`:'Pronto para cálculo'}</div>
    {c.outputs.map((p,i)=><Handle key={p} id={p} type="source" position={n.kind==='energy'?Position.Top:Position.Right} className={n.kind==='energy'?'energy-handle':''} style={{top:n.kind==='energy'?undefined:`${(i+1)/(c.outputs.length+1)*100}%`}} title={p}/>)}
  </div>;
}
const nodeTypes={unit:Unit};
function Canvas({project,catalog,result,running,selected,onSelect,onChange,onError}:{project:Project;catalog:Catalog;result:Result|null;running?:boolean;selected:string;onSelect:(s:string)=>void;onChange:(p:Project)=>void;onError:(s:string)=>void}){
  const flow=useReactFlow();const [dragPositions,setDragPositions]=useState<Record<string,{x:number;y:number}>>({});
  const nodes=(project.nodes||[]).map(n=>({id:n.id,type:'unit',position:dragPositions[n.id]||n.layout,selected:n.id===selected,data:{equipment:n,catalog,running,result:result?.streams?.units[n.id]}}));
  const edges:Edge[]=(project.edges||[]).map(e=>({id:e.id,source:e.source,target:e.target,sourceHandle:e.source_port,targetHandle:e.target_port,label:e.id,type:'smoothstep',style:{stroke:e.kind==='energy'?'#d6ae70':'#6dd5bd',strokeWidth:1.7},labelStyle:{fill:'#9cabbc',fontSize:10},labelBgStyle:{fill:'#141c28'},markerEnd:{type:MarkerType.ArrowClosed,color:e.kind==='energy'?'#d6ae70':'#6dd5bd'}}));
  const isValid=useCallback((c:RFConnection|Edge)=>{
    const a=project.nodes?.find(n=>n.id===c.source),b=project.nodes?.find(n=>n.id===c.target);if(!a||!b||a.id===b.id)return false;
    if(a.kind==='energy')return c.targetHandle==='heat'&&!!catalog[b.kind].energy;
    return c.targetHandle!=='heat'&&!project.edges?.some(e=>(e.target===b.id&&e.target_port===c.targetHandle)||(e.source===a.id&&e.source_port===c.sourceHandle));
  },[project,catalog]);
  const onConnect=(c:RFConnection)=>{if(!isValid(c)){onError('Portas incompatíveis ou ocupadas. Use um divisor para criar ramificações.');return;}
    const e={id:`S-${Date.now().toString(36)}`,source:c.source,target:c.target,source_port:c.sourceHandle||'out',target_port:c.targetHandle||'in',kind:c.sourceHandle==='heat'?'energy':'material'};onChange({...project,edges:[...(project.edges||[]),e]});};
  return <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} colorMode="dark" onNodeClick={(_,n)=>onSelect(n.id)} onPaneClick={()=>onSelect('')} onNodesChange={changes=>{
    const removed=changes.filter(c=>c.type==='remove').map(c=>c.id);if(removed.length){onChange({...project,nodes:project.nodes?.filter(n=>!removed.includes(n.id)),edges:project.edges?.filter(e=>!removed.includes(e.source)&&!removed.includes(e.target))});return;}
    const moved=changes.filter(c=>c.type==='position'&&c.position);if(moved.length){const changed=applyNodeChanges(moved,nodes);setDragPositions(Object.fromEntries(changed.map(n=>[n.id,n.position])));}
  }} onNodeDragStop={(_,node)=>{onChange({...project,nodes:project.nodes?.map(n=>n.id===node.id?{...n,layout:node.position}:n)});setDragPositions({});}} onEdgesDelete={removed=>onChange({...project,edges:project.edges?.filter(e=>!removed.some(r=>r.id===e.id))})} onConnect={onConnect} isValidConnection={isValid} fitView fitViewOptions={{padding:.2}} minZoom={.25} maxZoom={1.6} onDragOver={e=>{e.preventDefault();e.dataTransfer.dropEffect='move';}} onDrop={e=>{
    e.preventDefault();const kind=e.dataTransfer.getData('application/processlab');if(!catalog[kind])return;const point=flow.screenToFlowPosition({x:e.clientX,y:e.clientY});const id=`${kind.slice(0,2).toUpperCase()}-${Date.now().toString(36).slice(-5)}`;onChange({...project,nodes:[...(project.nodes||[]),{id,kind,label:id,layout:point,parameters:Object.fromEntries(Object.entries(catalog[kind].parameters).map(([k,v])=>[k,v[0]]))}]});onSelect(id);
  }}><Background gap={22} size={1} color="#293343"/><Controls showInteractive={false}/></ReactFlow>;
}
export function Flow(props:Parameters<typeof Canvas>[0]){return <ReactFlowProvider><Canvas {...props}/></ReactFlowProvider>;}
