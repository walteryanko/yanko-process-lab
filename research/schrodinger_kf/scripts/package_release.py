"""Create a self-contained replay HTML and a complete, verified research ZIP."""
import argparse,base64,hashlib,json,re,zipfile
from pathlib import Path

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--out',default=str(root.parent/'deliverables'));args=parser.parse_args()
out=Path(args.out);out.mkdir(parents=True,exist_ok=True)

report=(root/'web/report.html').read_text(encoding='utf-8')
for match in set(re.findall(r'figures/[^" ]+\.png',report)):
    report=report.replace(match,'data:image/png;base64,'+base64.b64encode((root/'web'/match).read_bytes()).decode())
report=report.replace('<a href="index.html">← Voltar ao laboratório</a>','<p>Relatório integrado à prévia do laboratório.</p>')
report_b64=base64.b64encode(report.encode()).decode()

document=(root/'web/index.html').read_text(encoding='utf-8')
document=document.replace('<link rel="stylesheet" href="style.css">','<style>'+(root/'web/style.css').read_text()+'</style>')
data=json.loads((root/'web/data.js').read_text()[len('window.LAB_DATA='):-1])
# Two primary scenario replays keep the standalone preview small. All campaign
# metrics, synthetic validations and control comparisons remain available.
data['demos']={k:data['demos'][k] for k in ['gaussian','ambiguous']}
data_js='window.LAB_DATA='+json.dumps(data,ensure_ascii=False,separators=(',',':'))+';'
app=(root/'web/app.js').read_text()
app=app.replace("if(location.protocol==='http:'||location.protocol==='https:')",'if(false)')
document=document.replace('<script src="data.js"></script>','<script>'+data_js.replace('</','<\\/')+'</script>')
document=document.replace('<script src="app.js"></script>','<script>'+app.replace('</','<\\/')+'</script>')
extra="<script>const reportBytes=Uint8Array.from(atob('"+report_b64+"'),c=>c.charCodeAt(0));const reportLink=document.querySelector('a[href=\"report.html\"]');reportLink.href=URL.createObjectURL(new Blob([reportBytes],{type:'text/html;charset=utf-8'}));reportLink.target='_blank';document.getElementById('job-status').textContent='Prévia autônoma: dois cenários principais, todos os benchmarks e controle. Para oito cenários e novas simulações, use o ZIP e INICIAR_LAB.bat.';</script>"
document=document.replace('</body>',extra+'</body>')
standalone=out/'YCS_SchrodingerKF_Laboratorio.html';standalone.write_text(document,encoding='utf-8')

files=sorted(p for p in root.rglob('*') if p.is_file() and not any(x in p.parts for x in ['__pycache__','.venv','.git','reproductions']) and p.suffix!='.pyc')
manifest={str(p.relative_to(root)).replace('\\','/'):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files if p.name!='PACKAGE_MANIFEST.json'}
(root/'PACKAGE_MANIFEST.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
files=sorted(p for p in root.rglob('*') if p.is_file() and not any(x in p.parts for x in ['__pycache__','.venv','.git','reproductions']) and p.suffix!='.pyc')
archive=out/'YCS_SchrodingerKF_Lab_v1.0.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in files:z.write(p,'YCS_SchrodingerKF_Lab_v1.0/'+str(p.relative_to(root)))
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
info={p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [archive,standalone,root/'reports/YCS_SchrodingerKF_Relatorio_v1.0.pdf']}
(out/'SHA256.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
print(json.dumps(info,indent=2))
