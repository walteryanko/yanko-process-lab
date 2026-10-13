declare global {interface Window {pywebview?:{api:{request:(method:string,payload:unknown)=>Promise<{ok:boolean;data:unknown;error:string}>}}}}
export async function api<T>(method:string,payload:unknown={}):Promise<T>{
  let result;
  if(window.pywebview?.api){result=await window.pywebview.api.request(method,payload);}
  else{
    const token=new URLSearchParams(location.hash.slice(1)).get('token');
    const response=await fetch('/api',{method:'POST',headers:{'Content-Type':'application/json','X-ProcessLab-Token':token||''},body:JSON.stringify({method,payload})});
    result=await response.json();
  }
  if(!result.ok)throw new Error(result.error||'Falha no mecanismo científico');
  return result.data as T;
}
export async function ready(){
  if(location.protocol==='file:'||!new URLSearchParams(location.hash.slice(1)).has('token')){
    if(window.pywebview?.api)return;
    await new Promise<void>((resolve,reject)=>{const t=setTimeout(()=>reject(new Error('A conexão local não iniciou. Abra o aplicativo desktop ou a URL fornecida pelo servidor.')),20000);window.addEventListener('pywebviewready',()=>{clearTimeout(t);resolve();},{once:true});});
  }
}
export function download(name:string,text:string,type='application/json'){
  const url=URL.createObjectURL(new Blob([text],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
