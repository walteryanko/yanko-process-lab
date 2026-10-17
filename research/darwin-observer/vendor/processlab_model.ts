/** Literal SI transcription: Brandão (2019), eq.33–55, Table 1, PO2.
 * This reimplementation does NOT reproduce Table2's nominal equilibrium.
 * See docs/scientific-map.md. No fitted/calibrated coefficients. */
export type State = [number, number, number, number, number, number];
export type Inputs = { fa: number; fb: number; fm: number; mw: number; t0: number; ta: number };
export const P = Object.freeze({ cp: [146.5,75.4,192.6,81.6], rho: [14.8,55.3,24.7], E:75362.4, R:8.314, k0:16.96e12, heat:91556.9, V:1.89, Vt:1.1, UA:30385.6 });
export const NOMINAL: Inputs = Object.freeze({fa:36.3,fb:453.6,fm:45.4,mw:453.6,t0:297,ta:289});
export const LIMITS = Object.freeze({mwMin:22.7,mwMax:1366.2,study:344,practical:355.4});
export const DT=.015;
export const clamp=(x:number,a:number,b:number)=>Math.max(a,Math.min(b,x));
export const flow=(u:Inputs)=>u.fa/P.rho[0]+u.fb/P.rho[1]+u.fm/P.rho[2];
export const rate=(t:number)=>P.k0*Math.exp(-P.E/(P.R*t));
export const cooling=(t:number,u:Inputs)=>u.mw*P.cp[1]*(u.ta-t)*(-Math.expm1(-P.UA/(u.mw*P.cp[1])));
export function derivative(x:State,u:Inputs):State {
  const v=flow(u),r=rate(x[4])*x[0],q=cooling(x[4],u);
  const cap=P.V*x.slice(0,4).reduce((s,c,i)=>s+c*P.cp[i],0);
  if(!Number.isFinite(cap)||cap<=0||x[4]<=0||u.mw<=0) throw Error('Domínio numérico inválido. Reinicie o experimento.');
  const sensible=(u.fa*P.cp[0]+u.fb*P.cp[1]+u.fm*P.cp[3])*(x[4]-u.t0);
  return [(u.fa-v*x[0])/P.V-r,(u.fb-v*x[1])/P.V-r,r-v*x[2]/P.V,(u.fm-v*x[3])/P.V,(q-sensible+P.heat*r*P.V)/cap,(u.mw*P.cp[1]*(u.ta-x[5])-q)/(P.rho[1]*P.Vt*P.cp[1])];
}
function add(x:State,k:State,h:number):State {return x.map((v,i)=>v+k[i]*h) as State;}
export function euler(x:State,u:Inputs,h=DT):State {return add(x,derivative(x,u),h);}
export function integrate(x:State,u:Inputs,dt=DT,maxStep=.001):State {
  let y=[...x] as State;const n=Math.ceil(dt/maxStep),h=dt/n;
  for(let j=0;j<n;j++) {
    const a=derivative(y,u),b=derivative(add(y,a,h/2),u),c=derivative(add(y,b,h/2),u),d=derivative(add(y,c,h),u);
    y=y.map((z,i)=>z+h*(a[i]+2*b[i]+2*c[i]+d[i])/6) as State;
    if(y.some(z=>!Number.isFinite(z))||y.slice(0,4).some(z=>z<0)||y[4]<150||y[4]>600||y[5]<150||y[5]>600) throw Error('Integração fora do domínio do modelo. O último estado válido foi preservado.');
  }
  return y;
}
export function heatCurves(t:number,u:Inputs) {
  const tau=P.V/flow(u),k=rate(t);
  return {generation:P.heat*tau*k/(1+tau*k),removal:(u.fa*P.cp[0]+u.fb*P.cp[1]+u.fm*P.cp[3])*(t-u.t0)/u.fa-cooling(t,u)/u.fa};
}
export function equilibrium(u:Inputs=NOMINAL):State {
  const f=(t:number)=>{const c=heatCurves(t,u);return c.generation-c.removal;};
  const roots:number[]=[];
  for(let t=250;t<400;t+=.25) if(f(t)*f(t+.25)<=0){let a=t,b=t+.25;for(let j=0;j<45;j++){const c=(a+b)/2;if(f(a)*f(c)<=0)b=c;else a=c;}roots.push((a+b)/2);}
  if(!roots.length) throw Error('Equilíbrio não encontrado no intervalo de cálculo.');
  const t=roots[roots.length-1],v=flow(u),ca=u.fa/(v+P.V*rate(t)),cc=P.V*rate(t)*ca/v;
  return [ca,u.fb/v-cc,cc,u.fm/v,t,u.ta-cooling(t,u)/(u.mw*P.cp[1])];
}
export const BASE=equilibrium();
export function fromPercent(key:keyof Inputs,value:number):number {
  // Source temperature percentages refer to degrees Fahrenheit, not Kelvin.
  const k=NOMINAL[key];return key==='t0'||key==='ta'?((k-273.15)*1.8+32)*value/100/1.8-32/1.8+273.15:k*value/100;
}
