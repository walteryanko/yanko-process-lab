export type ModelId = 'pg-original' | 'pg-calibrated' | 'pg-table' | 'eb-reduced' | 'flowsheet';
export type Control = 'manual' | 'pid' | 'cascade' | 'nmpc';
export type Estimator = 'off' | 'ekf' | 'ukf';
export type NodeKind = 'source'|'sink'|'mixer'|'splitter'|'tank'|'cstr'|'pump'|'valve'|'heater'|'cooler'|'exchanger';
export type UnitNode = {id:string;kind:NodeKind;parameters:Record<string,number>;[key:string]:unknown};
export type Edge = {id:string;source:string;target:string;source_port:string;target_port:string;kind:'material';[key:string]:unknown};
export type FlowGraph = {nodes:UnitNode[];edges:Edge[]};
export type Settings = {
  dt:number;duration:number;seed:number;controller:Control;observer:Estimator;setpoint:number;
  manual:number;kp:number;ki:number;kd:number;noise:number;qScale:number;rScale:number;
  horizon:number;disturbance:number;initialOffset:number;measurementIndices:number[];
};
export type Project = {
  schema_version:1;id:string;name:string;model:ModelId;modelVersion:string;
  science:{settings:Settings;initial?:number[];parameters?:Record<string,number>;[key:string]:unknown};
  graph:FlowGraph;layout:{nodes:Record<string,{x:number;y:number}>;zoom:number;pan:{x:number;y:number}};
  desktopSource?:unknown;readOnlyReason?:string;[key:string]:unknown;
};
export type Model = {
  id:ModelId;label:string;version:string;names:string[];units:string[];x0:number[];
  ti:number;qi:number;measured:number[];scale:number[];u0:number;inputUnit:string;inputLabel:string;
  bounds:[number,number];limit:number;maxStep:number;provenance:string;warning:string;
  rhs:(x:number[],u:number,d:number)=>number[];check:(x:number[])=>void;
};
export type Sample = {t:number;x:number[];estimate:number[];measured:number[];sigma:number[];u:number;sp:number;disturbance:number;solver:string;computeMs:number};
export const copy = <T>(v:T):T => JSON.parse(JSON.stringify(v));
export const clamp = (v:number,a:number,b:number)=>Math.max(a,Math.min(b,v));
export const VERSION='mobile-core-0.1.0';
