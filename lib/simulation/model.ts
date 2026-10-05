/** Brandão (2019), eq.33–55. kmol, m³, K, kJ, h.
 * Default: calibrated effective heat release at historical T=332.3 K.
 * TABLED_P preserves the literal table. Calibration is NOT parameter recovery. */
export type State = [number, number, number, number, number, number];
export type Inputs = { fa: number; fb: number; fm: number; mw: number; t0: number; ta: number };
export const TABLED_P = Object.freeze({ cp: [146.5,75.4,192.6,81.6], rho: [14.8,55.3,24.7], E:75362.4, R:8.314, k0:16.96e12, heat:91556.9, V:1.89, Vt:1.1, UA:30385.6 });
export type Parameters = typeof TABLED_P;
export const NOMINAL: Inputs = Object.freeze({fa:36.3,fb:453.6,fm:45.4,mw:453.6,t0:297,ta:289});
export const CALIBRATION_T=332.3;
/** Inverse energy balance, holding all other table values fixed. */
export function requiredHeatForEquilibrium(t:number,u:Inputs=NOMINAL,p:Parameters=TABLED_P):number {
  const v=u.fa/p.rho[0]+u.fb/p.rho[1]+u.fm/p.rho[2];
  const k=p.k0*Math.exp(-p.E/(p.R*t)),ca=u.fa/(v+p.V*k);
  const duty=u.mw*p.cp[1]*(u.ta-t)*(-Math.expm1(-p.UA/(u.mw*p.cp[1])));
  const sensible=(u.fa*p.cp[0]+u.fb*p.cp[1]+u.fm*p.cp[3])*(t-u.t0);
  const heat=(sensible-duty)/(k*ca*p.V);
  if(!Number.isFinite(heat)||heat<=0)throw Error('Equilíbrio alvo incompatível com calor de reação positivo.');
  return heat;
}
export const P:Parameters=Object.freeze({...TABLED_P,heat:requiredHeatForEquilibrium(CALIBRATION_T)});
export const LIMITS = Object.freeze({mwMin:22.7,mwMax:1366.2,study:344,practical:355.4});
export const DT=.015;
export const clamp=(x:number,a:number,b:number)=>Math.max(a,Math.min(b,x));
export const flow=(u:Inputs,p:Parameters=P)=>u.fa/p.rho[0]+u.fb/p.rho[1]+u.fm/p.rho[2];
export const rate=(t:number,p:Parameters=P)=>p.k0*Math.exp(-p.E/(p.R*t));
export const cooling=(t:number,u:Inputs,p:Parameters=P)=>u.mw*p.cp[1]*(u.ta-t)*(-Math.expm1(-p.UA/(u.mw*p.cp[1])));
export function derivative(x:State,u:Inputs,p:Parameters=P):State {
  const v=flow(u,p),r=rate(x[4],p)*x[0],q=cooling(x[4],u,p);
  const cap=p.V*x.slice(0,4).reduce((s,c,i)=>s+c*p.cp[i],0);
  if(!Number.isFinite(cap)||cap<=0||x[4]<=0||u.mw<=0) throw Error('Domínio numérico inválido. Reinicie o experimento.');
  const sensible=(u.fa*p.cp[0]+u.fb*p.cp[1]+u.fm*p.cp[3])*(x[4]-u.t0);
  return [(u.fa-v*x[0])/p.V-r,(u.fb-v*x[1])/p.V-r,r-v*x[2]/p.V,(u.fm-v*x[3])/p.V,(q-sensible+p.heat*r*p.V)/cap,(u.mw*p.cp[1]*(u.ta-x[5])-q)/(p.rho[1]*p.Vt*p.cp[1])];
}
function add(x:State,k:State,h:number):State {return x.map((v,i)=>v+k[i]*h) as State;}
export function euler(x:State,u:Inputs,h=DT,p:Parameters=P):State {return add(x,derivative(x,u,p),h);}
export function integrate(x:State,u:Inputs,dt=DT,maxStep=.001,p:Parameters=P):State {
  let y=[...x] as State;const n=Math.ceil(dt/maxStep),h=dt/n;
  for(let j=0;j<n;j++) {
    const a=derivative(y,u,p),b=derivative(add(y,a,h/2),u,p),c=derivative(add(y,b,h/2),u,p),d=derivative(add(y,c,h),u,p);
    y=y.map((z,i)=>z+h*(a[i]+2*b[i]+2*c[i]+d[i])/6) as State;
    if(y.some(z=>!Number.isFinite(z))||y.slice(0,4).some(z=>z<0)||y[4]<150||y[4]>600||y[5]<150||y[5]>600) throw Error('Integração fora do domínio do modelo. O último estado válido foi preservado.');
  }
  return y;
}
export function heatCurves(t:number,u:Inputs,p:Parameters=P) {
  const tau=p.V/flow(u,p),k=rate(t,p);
  return {generation:p.heat*tau*k/(1+tau*k),removal:(u.fa*p.cp[0]+u.fb*p.cp[1]+u.fm*p.cp[3])*(t-u.t0)/u.fa-cooling(t,u,p)/u.fa};
}
/** All roots in the declared range. Select near a physical operating point,
 * rather than silently picking the hottest branch. */
export function equilibria(u:Inputs=NOMINAL,p:Parameters=P):State[] {
  if(Object.values(u).some(z=>!Number.isFinite(z))||u.fa<=0||u.fb<=0||u.fm<0||u.mw<=0)throw Error('Entradas inválidas para equilíbrio.');
  const f=(t:number)=>{const c=heatCurves(t,u,p);return c.generation-c.removal;};
  const roots:number[]=[];
  for(let t=250;t<430;t+=.1) if(f(t)*f(t+.1)<=0){let a=t,b=t+.1;for(let j=0;j<45;j++){const c=(a+b)/2;if(f(a)*f(c)<=0)b=c;else a=c;}const root=(a+b)/2;if(!roots.some(r=>Math.abs(r-root)<1e-7))roots.push(root);}
  return roots.map(t=>{const v=flow(u,p),ca=u.fa/(v+p.V*rate(t,p)),cc=p.V*rate(t,p)*ca/v;return [ca,u.fb/v-cc,cc,u.fm/v,t,u.ta-cooling(t,u,p)/(u.mw*p.cp[1])] as State;});
}
export function equilibrium(u:Inputs=NOMINAL,p:Parameters=P,hint=CALIBRATION_T):State {
  const roots=equilibria(u,p);
  if(!roots.length) throw Error('Equilíbrio não encontrado no intervalo de cálculo.');
  return roots.reduce((a,b)=>Math.abs(a[4]-hint)<Math.abs(b[4]-hint)?a:b);
}
export const BASE=equilibrium();
export const TABLED_BASE=equilibrium(NOMINAL,TABLED_P,340.3034893843503);
export function fromPercent(key:keyof Inputs,value:number):number {
  // Source temperature percentages refer to degrees Fahrenheit, not Kelvin.
  const k=NOMINAL[key];return key==='t0'||key==='ta'?((k-273.15)*1.8+32)*value/100/1.8-32/1.8+273.15:k*value/100;
}
