import React,{useMemo,useState} from 'react';
import {View,Text,PanResponder} from 'react-native';
import {Canvas,Path,Skia,Line,vec} from '@shopify/react-native-skia';
import {type Sample,type Model} from '../../../packages/scientific-core/types';
import {C,T,Action,number} from './ui';
export function Chart({samples,model,index,height=185,compare}:{samples:Sample[];model:Model;index:number;height?:number;compare?:Sample[]}){
 const [width,setWidth]=useState(320),[zoom,setZoom]=useState(1),[shift,setShift]=useState(0),[cursor,setCursor]=useState<number|null>(null);
 const count=samples.length,start=Math.max(0,Math.floor(count*(1-1/zoom))-shift),end=Math.min(count,start+Math.ceil(count/zoom));
 const data=samples.slice(start,end),mi=model.measured.indexOf(index),values=data.flatMap(s=>[s.x[index],s.estimate[index],...(mi>=0?[s.measured[mi]??s.x[index]]:[]),s.estimate[index]-2*s.sigma[index],s.estimate[index]+2*s.sigma[index],...(index===model.ti?[s.sp]:[])]).filter(Number.isFinite);
 let low=Infinity,high=-Infinity;for(const v of values){low=Math.min(low,v);high=Math.max(high,v)}if(!values.length){low=0;high=1;}const pad=Math.max((high-low)*.12,.005);low-=pad;high+=pad;
 const L=46,R=8,top=12,bottom=26,cw=width-L-R,ch=height-top-bottom,t0=data[0]?.t??0,t1=data[data.length-1]?.t??1;
 const xx=(t:number)=>L+(t-t0)/Math.max(1,t1-t0)*cw,yy=(v:number)=>top+(high-v)/(high-low)*ch;
 // Min/max envelope decimation preserves spikes on screen; the original samples remain untouched.
 function points(series:Sample[],get:(s:Sample)=>number){
  const target=Math.max(40,Math.floor(cw)),out:Sample[]=[];
  for(let k=0;k<series.length;){const until=Math.min(series.length,k+Math.max(1,Math.ceil(series.length/target))),bucket=series.slice(k,until);let mn=0,mx=0;for(let j=1;j<bucket.length;j++){if(get(bucket[j])<get(bucket[mn]))mn=j;if(get(bucket[j])>get(bucket[mx]))mx=j;}out.push(bucket[Math.min(mn,mx)]);if(mx!==mn)out.push(bucket[Math.max(mn,mx)]);k=until;}
  return out;
 }
 function path(get:(s:Sample)=>number,series=data){const p=Skia.Path.Make();points(series,get).forEach((s,i)=>{if(i===0)p.moveTo(xx(s.t),yy(get(s)));else p.lineTo(xx(s.t),yy(get(s)))});return p;}
 const truth=path(s=>s.x[index]),estimate=path(s=>s.estimate[index]),measured=mi>=0?path(s=>s.measured[mi]??s.x[index]):null;
 const band=Skia.Path.Make();const reduced=points(data,s=>s.estimate[index]);reduced.forEach((s,i)=>{const x=xx(s.t),y=yy(s.estimate[index]+2*s.sigma[index]);if(i===0)band.moveTo(x,y);else band.lineTo(x,y)});[...reduced].reverse().forEach(s=>band.lineTo(xx(s.t),yy(s.estimate[index]-2*s.sigma[index])));band.close();
 const point=cursor===null?null:data[Math.max(0,Math.min(data.length-1,Math.round(cursor*(data.length-1))))];
 const touch=PanResponder.create({onStartShouldSetPanResponder:()=>true,onMoveShouldSetPanResponder:()=>true,onPanResponderGrant:e=>setCursor(Math.max(0,Math.min(1,(e.nativeEvent.locationX-L)/cw))),onPanResponderMove:e=>setCursor(Math.max(0,Math.min(1,(e.nativeEvent.locationX-L)/cw)))});
 return <View style={[T.card,{padding:12,gap:6}]} onLayout={e=>setWidth(e.nativeEvent.layout.width-24)}>
  <View style={{flexDirection:'row',justifyContent:'space-between',alignItems:'center'}}><Text style={[T.label,{color:C.text}]}>{model.names[index]} <Text style={{color:C.muted}}>· {model.units[index]}</Text></Text><Text style={{color:C.muted,fontSize:10}}>TEMPO SIMULADO</Text></View>
  <View {...touch.panHandlers} accessible accessibilityLabel={`Gráfico de ${model.names[index]}. Referência simulada, estimativa e medições.`}>
   <Canvas style={{height,width}}>
    {Array.from({length:4},(_,i)=><Line key={i} p1={vec(L,top+i*ch/3)} p2={vec(width-R,top+i*ch/3)} color={C.line} strokeWidth={1}/>)}
    <Path path={band} color="#BAA3FF18"/>
    {measured&&<Path path={measured} color={C.amber} style="stroke" strokeWidth={1}/>}
    <Path path={truth} color={C.cyan} style="stroke" strokeWidth={2}/><Path path={estimate} color={C.purple} style="stroke" strokeWidth={1.6}/>
    {compare&&<Path path={path(s=>s.x[index],compare.filter(s=>s.t>=t0&&s.t<=t1))} color={C.green} style="stroke" strokeWidth={1.6}/>}
    {index===model.ti&&data.length>0&&<Line p1={vec(L,yy(data[data.length-1].sp))} p2={vec(width-R,yy(data[data.length-1].sp))} color={C.green} strokeWidth={1}/>}
    {point&&<Line p1={vec(xx(point.t),top)} p2={vec(xx(point.t),top+ch)} color={C.text} strokeWidth={1}/>}
   </Canvas>
   <View pointerEvents="none" style={{position:'absolute',inset:0}}>{Array.from({length:4},(_,i)=><Text key={i} style={{position:'absolute',top:top+i*ch/3-6,left:0,fontSize:9,color:C.muted}}>{number(high-i*(high-low)/3,high<10?3:1)}</Text>)}<Text style={{position:'absolute',bottom:3,left:L,fontSize:10,color:C.muted}}>{number(t0/60,1)}</Text><Text style={{position:'absolute',bottom:3,right:0,fontSize:10,color:C.muted}}>{number(t1/60,1)} min</Text></View>
  </View>
  <View style={{flexDirection:'row',gap:10,flexWrap:'wrap'}}>{[['━ Referência',C.cyan],['━ Estimativa',C.purple],...(mi>=0?[['· Medição',C.amber]]:[]),['±2σ',C.purple]].map(([a,c])=><Text key={a} style={{fontSize:10,color:c}}>{a}</Text>)}</View>
  {point&&<Text style={{fontSize:11,color:C.text,fontVariant:['tabular-nums']}}>t {number(point.t)} s · {number(point.x[index],4)} {model.units[index]}</Text>}
  <View style={{flexDirection:'row',justifyContent:'flex-end'}}><Action icon="chevron-left" label="Histórico anterior" compact onPress={()=>setShift(Math.min(count-1,shift+Math.ceil(count/zoom/2)))}/><Action icon="chevron-right" label="Histórico recente" compact onPress={()=>setShift(Math.max(0,shift-Math.ceil(count/zoom/2)))}/><Action icon="magnify-minus-outline" label="Reduzir gráfico" compact onPress={()=>{setZoom(Math.max(1,zoom/2));setShift(0)}}/><Action icon="magnify-plus-outline" label="Ampliar gráfico" compact onPress={()=>{setZoom(Math.min(16,zoom*2));setShift(0)}}/></View>
 </View>;
}
