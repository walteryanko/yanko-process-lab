import { BASE, euler, type State, type Inputs } from './model.ts';
import { zeros, diag, multiply, transpose, plus, minus, inverse2, cholesky, symmetrize, type Matrix } from './matrix.ts';
export type ObserverKind='ekf'|'ukf'|'off';
export type Tuning='published'|'one'|'three'|'zero';
export const Q_PUBLISHED=[5.616e-8,5.616e-5,5.616e-8,2.4246e-13,.0346356,.00666123];
const H=[[0,0,0,0,1,0],[0,0,0,0,0,1]];
// R calculated from described 1% sensor STD; P0=Q is an explicit web choice.
export const R=diag([(BASE[4]*.01)**2,(BASE[5]*.01)**2]);
export class Observer {
 x:State;cov:Matrix;kind:ObserverKind;tuning:Tuning;
 constructor(kind:ObserverKind='ukf',tuning:Tuning='published',x:State=BASE){this.kind=kind;this.tuning=tuning;this.x=[...x];this.cov=diag(Q_PUBLISHED);}
 q(){return diag(this.tuning==='published'?Q_PUBLISHED:this.tuning==='zero'?Q_PUBLISHED.map(()=>0):BASE.map(x=>(x*(this.tuning==='one'?.01:.03))**2));}
 update(u:Inputs,y:number[]):State {
   if(this.kind==='off')return this.x;
   let xp:State,pp:Matrix;
   if(this.kind==='ekf') {
     xp=euler(this.x,u);const f=zeros(6);
     for(let j=0;j<6;j++) {const d=Math.max(1e-6,Math.abs(this.x[j])*1e-6),a=[...this.x] as State,b=[...this.x] as State;a[j]+=d;b[j]-=d;const pa=euler(a,u),pb=euler(b,u);for(let i=0;i<6;i++)f[i][j]=(pa[i]-pb[i])/(2*d);}
     pp=plus(multiply(multiply(f,this.cov),transpose(f)),this.q());
   } else {
     const alpha=.001,beta=2,n=6,scale=alpha*alpha*n,lambda=scale-n,wm=[lambda/scale,...Array(12).fill(1/(2*scale))],wc=[lambda/scale+1-alpha*alpha+beta,...Array(12).fill(1/(2*scale))];
     const l=cholesky(this.cov),sigmas:State[]=[[...this.x]];
     for(let j=0;j<n;j++)for(const sign of [1,-1])sigmas.push(this.x.map((v,i)=>v+sign*Math.sqrt(scale)*l[i][j]) as State);
     const pts=sigmas.map(s=>euler(s,u));xp=Array(6).fill(0) as State;
     for(let k=0;k<13;k++)for(let i=0;i<6;i++)xp[i]+=wm[k]*pts[k][i];
     pp=zeros(6);for(let k=0;k<13;k++)for(let i=0;i<6;i++)for(let j=0;j<6;j++)pp[i][j]+=wc[k]*(pts[k][i]-xp[i])*(pts[k][j]-xp[j]);
     pp=plus(pp,this.q());
   }
   // Observation is linear T/Tt; this update is exact for either predicted Gaussian.
   const s=plus(multiply(multiply(H,pp),transpose(H)),R),K=multiply(multiply(pp,transpose(H)),inverse2(s));
   const innovation=[y[0]-xp[4],y[1]-xp[5]];
   const next=xp.map((v,i)=>v+K[i][0]*innovation[0]+K[i][1]*innovation[1]) as State;
   const I=diag(Array(6).fill(1)),a=minus(I,multiply(K,H));
   // Joseph form avoids covariance cancellation while preserving the same update.
   const cov=symmetrize(plus(multiply(multiply(a,pp),transpose(a)),multiply(multiply(K,R),transpose(K))));
   if(next.some(v=>!Number.isFinite(v))||next[4]<=0||next[5]<=0||cov.some(row=>row.some(v=>!Number.isFinite(v))))throw Error('O observador perdeu convergência. Reinicie a estimativa.');
   this.x=next;this.cov=cov;return [...next];
 }
}
