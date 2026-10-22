'use strict';
const D=window.LAB_DATA||{demos:{},summaries:{},rows:{},studies:{},control:null};
const $=id=>document.getElementById(id), colors=['#7ee0b6','#78b9e9','#efbd78','#c89bf0','#e893a6','#b8cdb4'], names=['CE','CB','CEB','CDEB','T'], methods={M0:'UKF',M1:'EnKF',M2:'Bootstrap PF',M3:'Transporte entrópico',M4:'Schrödinger–Föllmer',M5:'Adaptativo · EnKF'};
let view='twin',timer=null;const fmt=(x,n=3)=>Number.isFinite(x)?x.toFixed(n):'—';
const current=()=>D.demos[$('scenario').value]?.[$('method').value];
const frame=()=>Math.min(+$('frame').value,(current()?.trace.snapshots.length||1)-1);
function option(el,values,labels){el.innerHTML=values.map((v,i)=>`<option value="${v}">${labels?.[i]||v}</option>`).join('');}
option($('method'),Object.keys(methods),Object.values(methods));
for(const id of ['axisX','axisY','axisZ'])option($(id),[0,1,2,3,4],names);
$('axisX').value=1;$('axisY').value=2;$('axisZ').value=4;
const campaignNames={primary:'Principal · 100 sementes',robust:'Ruído hostil · informado',naive:'Ruído hostil · gaussiano ingênuo',physics_fixed:'Física incerta · fixos',physics_joint:'Física incerta · conjuntos',q64:'UKF · Q × 64',no_observations:'UKF · sem medições'};
option($('campaign'),Object.keys(D.summaries),Object.keys(D.summaries).map(k=>campaignNames[k]||k));
function benchOptions(){option($('benchScenario'),Object.keys(D.summaries[$('campaign').value]||{}));}
benchOptions();
const titleCopy={twin:['Reactor Digital Twin','O que a temperatura revela sobre a composição química?'],probability:['Probability Universe','A evolução da incerteza, uma atualização de cada vez.'],transport:['Transport Explorer','Massa probabilística, marginais e viés da transformação.'],arena:['Filter Arena','Comparações pareadas, incluindo os resultados negativos.'],chemical:['Chemical Multiverse','Ambiguidade de composição não implica posterior bimodal.'],bench:['Scientific Benchmarks','Sementes independentes, métricas abertas e custo medido.'],control:['Control Laboratory','A informação probabilística muda as decisões do NMPC?']};
function setupCanvas(id){const c=$(id),r=c.getBoundingClientRect(),w=Math.max(r.width,250),h=Math.max(r.height,180),d=window.devicePixelRatio||1;c.width=w*d;c.height=h*d;const ctx=c.getContext('2d');ctx.scale(d,d);ctx.clearRect(0,0,w,h);return {ctx,w,h};}
function line(id,series,{ylabel='',xlabel='Tempo · h',xmax=null,ymin=null,ymax=null,cursor=null}={}){
 const {ctx,w,h}=setupCanvas(id),pad={l:55,r:18,t:15,b:37};let all=series.flatMap(s=>s.y.filter(Number.isFinite));if(!all.length)return;
 let lo=ymin??Math.min(...all),hi=ymax??Math.max(...all);if(hi===lo){hi+=.1;lo-=.1;}else if(ymin==null){let a=(hi-lo)*.08;hi+=a;lo-=a;}
 const xhi=xmax??Math.max(...series.flatMap(s=>s.x));const xlo=Math.min(...series.flatMap(s=>s.x));
 const X=x=>pad.l+(x-xlo)/(xhi-xlo||1)*(w-pad.l-pad.r),Y=y=>h-pad.b-(y-lo)/(hi-lo)*(h-pad.t-pad.b);
 ctx.font='10px system-ui';ctx.fillStyle='#93aaa7';ctx.strokeStyle='#2a4145';ctx.lineWidth=1;
 for(let i=0;i<=4;i++){const yy=lo+(hi-lo)*i/4;ctx.beginPath();ctx.moveTo(pad.l,Y(yy));ctx.lineTo(w-pad.r,Y(yy));ctx.stroke();ctx.fillText(fmt(yy,hi-lo>20?1:hi-lo<.1?4:2),2,Y(yy)+3);}
 for(let i=0;i<=4;i++){const xx=xlo+(xhi-xlo)*i/4;ctx.fillText(fmt(xx,xhi>10?0:2),X(xx)-10,h-18);}
 ctx.fillText(ylabel,pad.l,10);ctx.fillText(xlabel,Math.max(pad.l,w-100),h-2);
 for(let s of series){ctx.strokeStyle=s.color||colors[0];ctx.fillStyle=s.color||colors[0];ctx.globalAlpha=s.alpha??1;ctx.lineWidth=s.width||1.8;ctx.setLineDash(s.dash?[5,4]:[]);ctx.beginPath();let started=false;
  s.y.forEach((y,i)=>{if(!Number.isFinite(y)){started=false;return;}if(s.dots){ctx.moveTo(X(s.x[i])+2,Y(y));ctx.arc(X(s.x[i]),Y(y),2,0,Math.PI*2);}else{if(started)ctx.lineTo(X(s.x[i]),Y(y));else ctx.moveTo(X(s.x[i]),Y(y));started=true;}});if(s.dots)ctx.fill();else ctx.stroke();}
 ctx.globalAlpha=1;ctx.setLineDash([]);if(cursor!=null){ctx.strokeStyle='#ffffff55';ctx.beginPath();ctx.moveTo(X(cursor),pad.t);ctx.lineTo(X(cursor),h-pad.b);ctx.stroke();}
}
function legend(id,labels,cs){$(id).innerHTML=labels.map((s,i)=>`<span><i style="background:${cs[i]}"></i>${s}</span>`).join('');}
function table(id,headers,rows){$(id).innerHTML='<thead><tr>'+headers.map(x=>`<th>${x}</th>`).join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr>'+r.map(c=>`<td>${c}</td>`).join('')+'</tr>').join('')+'</tbody>';}
function histogram(x,w,bins=32){let lo=Math.min(...x),hi=Math.max(...x);if(hi===lo){lo-=.001;hi+=.001;}const a=new Array(bins).fill(0),dx=(hi-lo)/bins;x.forEach((v,i)=>a[Math.min(bins-1,Math.floor((v-lo)/dx))]+=w[i]/dx);return{x:a.map((_,i)=>lo+(i+.5)*dx),y:a};}
function renderTwin(a,k){const t=a.episode.true[k+1],m=a.trace.estimates[k],lo=a.trace.lower90[k],hi=a.trace.upper90[k],r=a.result;
 $('twinStats').innerHTML=[['CEB ESTIMADO',fmt(m[2]),'kmol/m³'],['TEMPERATURA',fmt(m[4],2),'°C · única variável medida'],['RMSE · CEB',fmt(r.rmse?.[2],4),'trajetória selecionada'],['COBERTURA 90%',fmt(100*r.coverage?.['0.9']?.[2],1)+'%','trajetória selecionada']].map(s=>`<div class="stat"><small>${s[0]}</small><strong>${s[1]}</strong><em>${s[2]}</em></div>`).join('');
 $('reactorT').textContent=fmt(t[4],2)+' °C';$('duty').textContent=fmt(a.episode.u[k][3]*4184/3.6e9,2)+' MW';
 table('stateTable',['Estado','Verdade','Estimativa','IC90%'],names.map((n,j)=>[n,fmt(t[j],j===4?2:4),fmt(m[j],j===4?2:4),`${fmt(lo[j])}–${fmt(hi[j])}`]));
 const x=a.trace.estimates.map((_,i)=>(i+1)*.025);
 for(const [id,j] of [['twinCEB',2],['twinTemp',4]]){
  let ss=[{x,y:a.trace.lower90.map(r=>r[j]),color:'#78b9e955',dash:true},{x,y:a.trace.upper90.map(r=>r[j]),color:'#78b9e955',dash:true},{x,y:a.episode.true.slice(1).map(r=>r[j]),color:colors[0]},{x,y:a.trace.estimates.map(r=>r[j]),color:colors[1]}];
  if(j===4)ss.unshift({x,y:a.episode.y.map(r=>r[0]),color:'#b6c1b155',dots:true});line(id,ss,{ylabel:j===2?'kmol/m³':'°C',cursor:x[k]});
 }
 legend('truthLegend',['Verdade','Média posterior','Limites 90%'],[colors[0],colors[1],'#78b9e955']);
}
function renderProbability(a,k){const snap=a.trace.snapshots[k],p=snap.particles,wts=snap.weights;let ax=+$('axisX').value,ay=+$('axisY').value,az=+$('axisZ').value;
 const {ctx,w,h}=setupCanvas('particles'),mins=names.map((_,j)=>Math.min(...p.map(x=>x[j]))),maxs=names.map((_,j)=>Math.max(...p.map(x=>x[j]))),norm=(v,j)=>(v-mins[j])/(maxs[j]-mins[j]||1)-.5;
 const proj=+$('projection').value,points=p.map((v,i)=>({u:norm(v[ax],ax),v:norm(v[ay],ay),z:norm(v[az],az),wt:wts[i]}));
 ctx.strokeStyle='#2b4849';ctx.strokeRect(42,25,w-72,h-75);let maxwt=Math.max(...wts);
 points.sort((a,b)=>a.z-b.z).forEach(q=>{const u=proj===3?q.u*.8+q.z*.42:q.u,v=proj===3?q.v*.8-q.z*.24:q.v;ctx.globalAlpha=.2+.8*q.wt/maxwt;ctx.fillStyle=colors[1];ctx.beginPath();ctx.arc(w/2+u*(w-120),h/2-v*(h-90),2+2*q.wt/maxwt,0,Math.PI*2);ctx.fill();});ctx.globalAlpha=1;ctx.fillStyle='#a9bfba';ctx.font='11px system-ui';ctx.fillText(names[ax]+` [${fmt(mins[ax])}, ${fmt(maxs[ax])}]`,45,h-16);ctx.fillText(names[ay],10,18);if(proj===3)ctx.fillText('Profundidade: '+names[az]+' · projeção oblíqua',45,18);
 const hh=histogram(p.map(v=>v[2]),wts);line('marginal',[{...hh,color:colors[1]}],{ylabel:'Densidade',xlabel:'CEB · kmol/m³',ymin:0});
 const d=a.trace.diagnostics[k];$('probStats').textContent=`Partículas: ${p.length} · ESS antes da atualização: ${fmt(d.ess,1)} · Diversidade: ${fmt(100*d.unique_fraction,1)}% · Fallback: ${d.fallback}.`;
}
function renderTransport(k){const bundle=D.demos[$('scenario').value],a=bundle.M3,b=bundle.M4;if(!a)return;const s=a.trace.snapshots[Math.min(k,a.trace.snapshots.length-1)],d=a.trace.diagnostics[k]?.transport||{},p=s.transport;
 const {ctx,w,h}=setupCanvas('heatmap');if(p){let max=Math.max(...p.flat()),n=p.length,size=Math.min(w-60,h-40),ox=(w-size)/2,oy=15;
  for(let i=0;i<n;i++)for(let j=0;j<n;j++){ctx.fillStyle=`rgba(126,224,182,${.06+.94*Math.sqrt(p[i][j]/max)})`;ctx.fillRect(ox+j*size/n,oy+i*size/n,size/n+.5,size/n+.5);}ctx.fillStyle='#9bb2ad';ctx.font='10px system-ui';ctx.fillText('Destino uniforme →',ox,h-4);
  const sums=p.map(r=>r.reduce((a,b)=>a+b,0));line('weights',[{x:sums.map((_,i)=>i),y:sums,color:colors[0]}],{xlabel:'Bloco de origem',ylabel:'Massa',ymin:0});
 }else{ctx.fillStyle='#efbd78';ctx.font='13px system-ui';ctx.fillText('Sem plano aceito neste instante.',25,h/2);ctx.fillText('Verifique fallback e convergência.',25,h/2+24);setupCanvas('weights');}
 $('transportStats').innerHTML=`<table><tbody>${[['ε',d.epsilon??D.selection?.epsilon],['Erro das marginais',d.marginal_error?.toExponential(2)],['Massa total',fmt(d.mass,10)],['Custo normalizado',fmt(d.cost,6)],['Iterações',d.iterations],['Razão de variâncias',fmt(d.variance_ratio,4)],['Erro da média',d.mean_error?.toExponential(2)],['Fallback',a.trace.diagnostics[k]?.fallback]].map(r=>`<tr><td>${r[0]}</td><td>${r[1]??'—'}</td></tr>`).join('')}</tbody></table>`;
 const bd=b?.trace.diagnostics[k]?.bridge;$('bridgeDiag').textContent=bd?`M4 no instante atual: ${bd.steps} passos; h = ${bd.bandwidth}; deslocamento normalizado da média = ${fmt(bd.mean_shift)}; traço-alvo = ${fmt(bd.target_trace)}; traço gerado = ${fmt(bd.generated_trace)}.`:'Sem atualização de ponte neste instante.';
}
function renderArena(k){const sc=$('scenario').value,b=D.demos[sc],summary=D.summaries.primary?.[sc];if(!summary)return;const a=b.M0,x=a.trace.estimates.map((_,i)=>(i+1)*.025);
 let ss=[{x,y:a.episode.true.slice(1).map(r=>r[2]),color:'#fff',dash:true}];Object.keys(methods).forEach((m,i)=>{if(b[m])ss.push({x,y:b[m].trace.estimates.map(r=>r[2]),color:colors[i]});});line('arenaCEB',ss,{ylabel:'kmol/m³',cursor:x[k]});legend('arenaLegend',['Verdade',...Object.values(methods)],['#fff',...colors]);
 const keys=Object.keys(summary);line('arenaCoverage',[{x:keys.map((_,i)=>i),y:keys.map(m=>summary[m].coverage90?.[2]),color:colors[1]},{x:[0,keys.length-1],y:[.9,.9],color:colors[2],dash:true}],{xlabel:'M0 → M5',ylabel:'Cobertura',ymin:0,ymax:1});
 table('arenaTable',['Filtro','N','RMSE CEB','CRPS CEB','Cob.90%','Latência média','Falhas'],keys.map(m=>[methods[m],summary[m].n,fmt(summary[m].rmse?.[2],5),fmt(summary[m].crps?.[2],5),fmt(100*summary[m].coverage90?.[2],1)+'%',fmt(summary[m].latency_mean_ms,1)+' ms',summary[m].failed]));
 const d=summary.M4?.paired_vs_M0;$('finding').textContent=d?`Resultado deste cenário: M4 apresentou ΔRMSE CEB = ${fmt(d.delta_rmse_ceb,5)} kmol/m³ frente ao UKF; IC95% [${fmt(d.ci95[0],5)}, ${fmt(d.ci95[1],5)}]. M5 mantém o ramo EnKF porque a ablação não justificou ativar a ponte.`:'Resultados em preparação.';
}
function renderChemical(){const o=D.studies.observability;if(!o)return;
 for(const [id,j] of [['hypCEB',2],['hypTemp',4]])line(id,o.histories.map((hh,i)=>({x:o.time,y:hh.map(r=>r[j]),color:colors[i]})),{ylabel:j===2?'CEB · kmol/m³':'T · °C'});
 $('hypStats').textContent=`Separação inicial: ${fmt(o.initial_CEB_separation)} kmol/m³. Diferença térmica RMS: ${fmt(o.thermal_rms,4)} °C. Posto local escalonado: ${o.rank_relative_1e_7}/5.`;
 const refs=D.studies.posterior_reference?.snapshots?.filter(r=>r.step===+$('refStep').value)||[];
 line('refPosterior',refs.map((r,i)=>({x:r.grid,y:r.kdes[1].density,color:colors[i]})),{xlabel:'CEB · kmol/m³',ylabel:'Densidade',ymin:0});
 $('refModes').textContent=refs.map(r=>`${r.n} partículas: modos = ${r.kdes.map(k=>k.modes.length).join('/')} para suavização 0,8/1/1,2`).join(' · ')+'. Picos sensíveis à suavização não estabelecem multimodalidade persistente.';
 const syn=D.studies.synthetic_distributions?.bimodal;if(syn){let hh=histogram(syn.sets.M4,new Array(syn.sets.M4.length).fill(1/syn.sets.M4.length),60);line('bimodal',[{x:syn.grid,y:syn.density,color:colors[0]},{...hh,color:colors[4]}],{xlabel:'Estado escalar x',ylabel:'Densidade',ymin:0});}
}
function renderBench(){const group=$('campaign').value,sc=$('benchScenario').value,sum=D.summaries[group]?.[sc]||{},rows=(D.rows[group]||[]).filter(r=>r.scenario===sc),keys=Object.keys(sum);
 table('benchTable',['Método','n / falhas','RMSE CEB','Δ vs UKF [IC95%]','Vitórias','Cob.90%','Fallbacks'],keys.map(m=>{const r=sum[m],d=r.paired_vs_M0;return[methods[m],`${r.n} / ${r.failed}`,fmt(r.rmse?.[2],5),d?`${fmt(d.delta_rmse_ceb,5)} [${fmt(d.ci95[0],5)}, ${fmt(d.ci95[1],5)}]`:'—',d?.wins??'—',fmt(100*r.coverage90?.[2],1)+'%',fmt(r.fallback_count*r.completed,0)];}));
 line('seedsChart',keys.map((m,i)=>{const rr=rows.filter(r=>r.method===m&&!r.failure).sort((a,b)=>a.seed-b.seed);return{x:rr.map(r=>r.seed),y:rr.map(r=>r.rmse[2]),color:colors[i]};}),{xlabel:'Semente',ylabel:'RMSE · kmol/m³'});
 const scale=D.studies.scaling||[];line('scalingChart',['M0','M2','M3','M4'].map((m,i)=>{const r=scale.filter(r=>r.method===m);return{x:r.map(r=>r.n),y:r.map(r=>r.update_mean_ms),color:colors[i]};}),{xlabel:'Partículas',ylabel:'ms / atualização',ymin:0});
 $('provenance').innerHTML=`<p class="mini">Commit físico: <code>16aaafb63572d62e0e3341e26d8317b0651bdde0</code><br>Integração da planta: DOP853. Filtros: RK4, 8 subpassos. Δt = 0,025 h.<br>Campanhas independentes de desenvolvimento e teste. Posterior causal. Etilbenzeno em kmol/m³; fração molar calculada como CEB / ΣCi.<br>O controle e o modelo térmico são experimentais. Parâmetros completos, falhas e sementes estão no pacote.</p>`;
}
function renderControl(){const c=D.control;if(!c){$('controlTable').innerHTML='<tr><td>Campanha de controle indisponível neste pacote.</td></tr>';return;}const key=$('controlPolicy').value;const t=c.traces.find(t=>t.method+'_'+t.policy===key&&t.seed===Math.min(...c.traces.map(t=>t.seed)));if(!t)return;const h=t.history,x=h.map((_,i)=>(i+1)*.025),frac=a=>a[2]/a.slice(0,4).reduce((u,v)=>u+v,0);
 line('controlFrac',[{x,y:h.map(r=>frac(r.x)),color:colors[0]},{x,y:h.map(r=>frac(r.estimate)),color:colors[1]},{x,y:h.map(r=>r.reference),color:colors[2],dash:true}],{ylabel:'xEB'});
 line('controlTemp',[{x,y:h.map(r=>r.x[4]),color:colors[0]},{x,y:h.map(r=>r.estimate[4]),color:colors[1]},{x,y:x.map(()=>165),color:colors[4],dash:true}],{ylabel:'°C'});
 line('controlFlow',[{x,y:h.map(r=>r.fE),color:colors[1]}],{ylabel:'m³/h'});line('controlHeat',[{x,y:h.map(r=>r.Q_MW),color:colors[2]}],{ylabel:'MW'});
 table('controlTable',['Política','n / falhas','IAE xEB','Δ vs UKF [IC95%]','T máxima média','Violações','Fallbacks'],Object.entries(c.summary).map(([k,r])=>[k,`${r.n} / ${r.failed}`,fmt(r.iae_xEB,6),r.vs_UKF?`${fmt(r.vs_UKF.mean_delta,6)} [${fmt(r.vs_UKF.ci95[0],6)}, ${fmt(r.vs_UKF.ci95[1],6)}]`:'—',fmt(r.peak_T,2),fmt(r.violations*r.completed,0),fmt(r.fallbacks*r.completed,0)]));
}
function render(){const a=current();if(!a)return;const k=frame();$('frame').max=a.trace.snapshots.length-1;$('clock').textContent=`t = ${fmt((k+1)*.025,3)} h · passo ${k+1}`;$('seedtag').textContent=`semente ${a.result.seed} · N = ${a.result.particles}`;
 ({twin:()=>renderTwin(a,k),probability:()=>renderProbability(a,k),transport:()=>renderTransport(k),arena:()=>renderArena(k),chemical:renderChemical,bench:renderBench,control:renderControl}[view])();}
$('nav').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;view=b.dataset.view;document.querySelectorAll('.panel').forEach(p=>p.classList.toggle('active',p.id===view));document.querySelectorAll('nav button').forEach(p=>p.classList.toggle('active',p===b));$('title').textContent=titleCopy[view][0];$('subtitle').textContent=titleCopy[view][1];render();});
for(const id of ['scenario','method','axisX','axisY','axisZ','projection','refStep','benchScenario','controlPolicy'])$(id).addEventListener('change',render);
$('campaign').onchange=()=>{benchOptions();render();};$('frame').oninput=render;
$('play').onclick=()=>{if(timer){clearInterval(timer);timer=null;$('play').textContent='▶ Reproduzir';}else{timer=setInterval(()=>{$('frame').value=(+$('frame').value+1)%(+$('frame').max+1);render();},230);$('play').textContent='❚❚ Pausar';}};
window.addEventListener('resize',render);if(D.control)option($('controlPolicy'),Object.keys(D.control.summary));
function download(ext){const rows=(D.rows[$('campaign').value]||[]).filter(r=>r.scenario===$('benchScenario').value);let text;
 if(ext==='json')text=JSON.stringify(rows,null,2);else{const fields=['seed','scenario','method','rmse_CEB','crps_CEB','coverage90','latency_mean_ms','fallback_count','failure'];text=fields.join(',')+'\n'+rows.map(r=>{const flat={...r,rmse_CEB:r.rmse?.[2],crps_CEB:r.crps?.[2],coverage90:r.coverage?.['0.9']?.[2]};return fields.map(k=>'"'+String(typeof flat[k]==='object'?JSON.stringify(flat[k]):flat[k]??'').replaceAll('"','""')+'"').join(',');}).join('\n');}
 const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([text],{type:ext==='json'?'application/json':'text/csv;charset=utf-8'}));a.download='YCS_'+$('campaign').value+'_'+$('benchScenario').value+'.'+ext;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}
$('exportCSV').onclick=()=>download('csv');$('exportJSON').onclick=()=>download('json');$('newrun').onclick=()=>{$('modal').classList.add('open');};$('closeModal').onclick=()=>$('modal').classList.remove('open');
async function online(){try{if(location.protocol==='file:')return false;const r=await fetch('/api/status');const d=await r.json();if(d.online){$('mode').textContent='Motor local conectado';$('runStatus').textContent='Motor pronto. Novas execuções não alteram a campanha científica.';return true;}}catch(e){}return false;}
$('execute').onclick=async()=>{if(!await online()){$('runStatus').textContent='Motor indisponível. Extraia o ZIP e execute INICIAR_LAB.bat. Este arquivo mantém a exploração offline dos resultados.';return;}
 $('execute').disabled=true;try{let resp=await fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({scenario:$('scenario').value,particles:+$('runN').value,steps:+$('runSteps').value,seed:+$('runSeed').value})});let j=await resp.json();if(!resp.ok)throw new Error(j.error);let done=false;
 while(!done){await new Promise(r=>setTimeout(r,700));const r=await (await fetch('/api/jobs/'+j.job)).json();$('runProgress').value=r.progress||0;$('runStatus').textContent=r.message||r.error||r.status;if(r.status==='error')throw new Error(r.error);if(r.status==='done'){D.demos[$('scenario').value]=r.data;done=true;$('frame').value=0;render();$('runStatus').textContent='Concluído. A nova trajetória aparece nos painéis; os benchmarks preservam a campanha original.';}}
 }catch(e){$('runStatus').textContent=e.message;}finally{$('execute').disabled=false;}};
if(!Object.keys(D.demos).length){$('subtitle').textContent='Dados ausentes. Execute python scripts/bootstrap_demo.py no diretório do laboratório.';}else{render();online();}
