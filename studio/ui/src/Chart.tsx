import {useId} from 'react';
import type {Row} from './types';
export function Chart({rows,index,title,unit,input=false,quality=false,temperature=false}:{rows:Row[];index:number;title:string;unit:string;input?:boolean;quality?:boolean;temperature?:boolean}){
  const id=useId().replaceAll(':','');const values=rows.map(r=>input?r.input:quality?r.quality_truth:r.truth[index]);
  const estimates=rows.map(r=>quality?r.quality_estimate:r.estimate?.[index]);
  const all=[...values,...(!input?estimates.filter((v):v is number=>v!=null):[]),...(temperature?rows.map(r=>r.setpoint):[])];
  let lo=Math.min(...all),hi=Math.max(...all);const margin=Math.max((hi-lo)*.15,input?1:.02);lo-=margin;hi+=margin;
  const w=640,h=220,left=57,right=17,top=15,bottom=35;const tmax=Math.max(1,rows.at(-1)?.t||1);
  const X=(t:number)=>left+t/tmax*(w-left-right),Y=(v:number)=>top+(hi-v)/(hi-lo)*(h-top-bottom);
  const line=(vals:(number|null|undefined)[])=>vals.map((v,i)=>v==null?'':`${i===0||vals[i-1]==null?'M':'L'}${X(rows[i].t).toFixed(2)},${Y(v).toFixed(2)}`).join(' ');
  const f=(v:number)=>Math.abs(v)>=10000?v.toExponential(1):v.toFixed(Math.abs(v)<1?3:1);
  return <section className="chart-card"><div className="chart-heading"><h3>{title}</h3><span>{unit}</span></div>
    <svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label={`${title}: ${rows.length} amostras calculadas`}><defs><linearGradient id={id} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#67dfbf" stopOpacity=".12"/><stop offset="100%" stopColor="#67dfbf" stopOpacity="0"/></linearGradient></defs>
      {[0,1,2,3,4].map(i=>{const value=lo+(hi-lo)*i/4;return <g key={i}><line x1={left} x2={w-right} y1={Y(value)} y2={Y(value)} stroke="#263140" strokeDasharray="3 5"/><text x={left-10} y={Y(value)+4} textAnchor="end" fill="#7f91a8" fontSize="10">{f(value)}</text></g>})}
      {[0,1,2,3,4].map(i=><text key={i} x={X(tmax*i/4)} y={h-13} textAnchor="middle" fill="#7f91a8" fontSize="10">{Math.round(tmax*i/4)} s</text>)}
      {values.length>1&&<path d={`${line(values)} L${X(tmax)},${h-bottom} L${left},${h-bottom} Z`} fill={`url(#${id})`}/>}
      {temperature&&<path d={line(rows.map(r=>r.setpoint))} fill="none" stroke="#d8ab64" strokeWidth="1.5" strokeDasharray="5 5"/>}
      <path d={line(values)} fill="none" stroke="#64dfbc" strokeWidth="2"/>
      {!input&&<path d={line(estimates)} fill="none" stroke="#8eb3ff" strokeWidth="1.8" strokeDasharray="4 3"/>}
      {values.length===1&&<circle cx={X(0)} cy={Y(values[0])} r="3" fill="#64dfbc"/>}
    </svg><div className="legend"><span className="mint-dot"/>{input?'Variável manipulada':'Estado simulado'}{!input&&<><span className="blue-dot"/>Estimativa</>}{temperature&&<><span className="gold-dot"/>Referência</>}</div></section>;
}
