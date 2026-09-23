export type Matrix=number[][];
export const zeros=(m:number,n=m):Matrix=>Array.from({length:m},()=>Array(n).fill(0));
export const diag=(a:number[]):Matrix=>a.map((v,i)=>a.map((_,j)=>i===j?v:0));
export const transpose=(a:Matrix):Matrix=>a[0].map((_,i)=>a.map(r=>r[i]));
export const plus=(a:Matrix,b:Matrix):Matrix=>a.map((r,i)=>r.map((v,j)=>v+b[i][j]));
export const minus=(a:Matrix,b:Matrix):Matrix=>a.map((r,i)=>r.map((v,j)=>v-b[i][j]));
export const multiply=(a:Matrix,b:Matrix):Matrix=>a.map(r=>b[0].map((_,j)=>r.reduce((s,v,k)=>s+v*b[k][j],0)));
export function inverse2(a:Matrix):Matrix {const d=a[0][0]*a[1][1]-a[0][1]*a[1][0];if(!Number.isFinite(d)||Math.abs(d)<1e-20)throw Error('Covariância singular. Reinicie o observador.');return [[a[1][1]/d,-a[0][1]/d],[-a[1][0]/d,a[0][0]/d]];}
export function cholesky(a:Matrix):Matrix {
 const l=zeros(a.length);
 for(let i=0;i<a.length;i++)for(let j=0;j<=i;j++){let s=a[i][j];for(let k=0;k<j;k++)s-=l[i][k]*l[j][k];if(i===j){if(s< -1e-9)throw Error('Covariância não positiva. Reinicie o observador.');l[i][j]=Math.sqrt(Math.max(s,1e-16));}else l[i][j]=s/l[j][j];}return l;
}
export const symmetrize=(a:Matrix):Matrix=>a.map((r,i)=>r.map((v,j)=>i===j?Math.max(v,1e-16):(v+a[j][i])/2));
