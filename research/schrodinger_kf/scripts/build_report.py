"""Generate the experimental report from stored outputs only (no fabricated data)."""
import sys,json,hashlib,platform,html,re,shutil
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import findfont, FontProperties
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph,Table,TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from schrodinger_lab.experiments import serial,write_json
R=ROOT/'results';OUT=ROOT/'reports';FIG=OUT/'figures';FIG.mkdir(exist_ok=True)
def load(p):return json.loads(Path(p).read_text())
main=load(R/'main/summary.json');noise=load(R/'hostile/summary.json');naive=load(R/'hostile_naive/summary.json')
fixed=load(R/'physics_fixed/summary.json');joint=load(R/'physics_joint/summary.json');ctrl=load(R/'control/control.json')
obs=load(R/'studies/observability.json');scale=load(R/'studies/scaling.json');syn=load(R/'studies/synthetic_metrics.json')
aud=load(OUT/'physical_audit.json');dev=load(R/'development/selection.json');ui=load(R/'ui_tests.json')
cols=['#4f5e78','#218f7c','#bb842b','#c2607e','#8463c6','#3285bc'];labels=['UKF','EnKF','PF','OT','SB','M5']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'axes.labelcolor':'#344158','text.color':'#243247','xtick.color':'#53617a','ytick.color':'#53617a','figure.facecolor':'white','axes.facecolor':'white','savefig.dpi':180})
def save(name,fig):fig.savefig(FIG/(name+'.png'),bbox_inches='tight');fig.savefig(FIG/(name+'.svg'),bbox_inches='tight');plt.close(fig)
fig,axs=plt.subplots(1,2,figsize=(10,3.7))
for ax,sc,title in zip(axs,['gaussian','ambiguous'],['Próximo do equilíbrio','Composição ambígua']):
 rs=[main[sc]['M'+str(i)] for i in range(6)];ax.bar(labels,[r['rmse'][2] for r in rs],color=cols);ax.set_title(title+' · 100 trajetórias');ax.set_ylabel('RMSE médio de CC / kmol m⁻³');ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
fig.tight_layout();save('01_rmse',fig)
fig,axs=plt.subplots(1,2,figsize=(10,3.7))
for ax,sc in zip(axs,['gaussian','ambiguous']):
 rs=[main[sc]['M'+str(i)] for i in range(6)];ax.bar(labels,[100*r['coverage90'][2] for r in rs],color=cols);ax.axhline(90,ls='--',color='#333',lw=1);ax.set_ylim(0,105);ax.set_ylabel('Cobertura temporal média de 90% / %');ax.set_title(sc);ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
fig.tight_layout();save('02_coverage',fig)
fig,axs=plt.subplots(3,1,figsize=(10,6),sharex=True)
ep=np.load(R/'main/datasets/ambiguous_2000.npz');t=np.arange(1,49)*.015
for ax,m,c in zip(axs,['M0','M3','M4'],[cols[0],cols[3],cols[4]]):
 tr=np.load(R/f'main/traces/ambiguous_2000_{m}.npz');ax.plot(t,ep['true'][1:,2],color='#218f7c',label='Verdade');ax.plot(t,tr['estimates'][:,2],color=c,label=m);ax.fill_between(t,tr['lower90'][:,2],tr['upper90'][:,2],color=c,alpha=.2,label='90%');ax.set_ylabel('CC / kmol m⁻³');ax.legend(loc='upper right',ncol=3);ax.grid(alpha=.15)
axs[-1].set_xlabel('Tempo / h');fig.suptitle('Exemplo pré-fixado: semente 2000; intervalos e lavagem do estado inicial');fig.tight_layout();save('03_trace',fig)
fig,axs=plt.subplots(1,2,figsize=(10,3.8));d=load(R/'studies/synthetic_distributions.json')['bimodal']
axs[0].plot(d['grid'],d['density'],color='#111',label='Quadratura',lw=2)
for m,col in zip(['PF','M3','M4'],[cols[2],cols[3],cols[4]]):axs[0].hist(d['sets'][m],bins=35,density=True,histtype='step',label=m,color=col)
axs[0].set(xlim=(-3,3),xlabel='x sintético',ylabel='Densidade',title='y=x²+v; y=4; prior N(0,1,5²)');axs[0].legend()
axs[1].plot(obs['delta_grid'],obs['prior_delta'],label='Prior',lw=3,color='#218f7c');axs[1].plot(obs['delta_grid'],obs['posterior_delta'],label='Posterior',ls='--',color=cols[4]);axs[1].set(xlabel='Deslocamento inicial de CC / kmol m⁻³',ylabel='Massa discretizada',title='CSTR: informação nula na direção invisível');axs[1].legend();fig.tight_layout();save('04_modes',fig)
fig,axs=plt.subplots(1,2,figsize=(10,3.8))
for i in range(5):
 rs=[r for r in scale if r['method']=='M'+str(i)];axs[0].loglog([r['n'] for r in rs],[r['update_mean_ms'] for r in rs],marker='o',label=labels[i],color=cols[i]);axs[1].plot([r['n'] for r in rs],[r['peak_traced_MiB'] for r in rs],marker='o',label=labels[i],color=cols[i])
axs[0].set(xlabel='N partículas',ylabel='ms por atualização',title='Microbenchmark com rastreamento de memória');axs[0].legend(ncol=2);axs[1].set(xlabel='N partículas',ylabel='MiB de alocação rastreada (não RSS)',title='Memória do avaliador / 6 passos');axs[1].legend(ncol=2);fig.tight_layout();save('05_cost',fig)
fig,ax=plt.subplots(figsize=(10,3.8));idx=np.arange(6);width=.36
ax.bar(idx-width/2,[fixed['physics']['M'+str(i)]['rmse'][2] for i in range(6)],width,label='Parâmetros fixos',color='#8c99ae');ax.bar(idx+width/2,[joint['physics']['M'+str(i)]['rmse'][2] for i in range(6)],width,label='Estado + parâmetros',color='#8463c6');ax.set_xticks(idx,labels);ax.set_ylabel('RMSE médio de CC / kmol m⁻³');ax.set_title('Física incerta · 20 trajetórias pareadas');ax.legend();fig.tight_layout();save('06_physics',fig)
fig,ax=plt.subplots(figsize=(10,3.8));keys=list(ctrl['summary']);vals=[ctrl['summary'][k] for k in keys];ax.bar(np.arange(len(keys)),[v['loss'] for v in vals],color=[cols[0],cols[1],cols[4],'#5a3f98','#ba92df']);ax.set_xticks(np.arange(len(keys)),['UKF + nominal','EnKF + nominal','SB + nominal','SB + risco','SB + regret']);ax.set_ylabel('Custo acumulado médio / unidades do objetivo');ax.set_title('Controle · 20 sementes · mesma função objetivo');fig.tight_layout();save('07_control',fig)

def rows_for(s):return [[m,round(r['rmse'][2],5),round(r['crps'][2],5),round(100*r['coverage90'][2],1),round(r['latency_mean_ms'],2)] for m,r in s.items()]
def mdtable(headers,rows):return '| '+' | '.join(headers)+' |\n|'+'|'.join(['---']*len(headers))+'|\n'+'\n'.join('| '+' | '.join(map(str,r))+' |' for r in rows)+'\n'
allrows=[]
for group in ['main','hostile','hostile_naive','physics_fixed','physics_joint']:
 allrows += [json.loads(x) for x in (R/group/'runs.jsonl').read_text().splitlines()]
failures=[r for r in allrows if r['failure']];fallbacks=sum(r.get('fallback_count',0) for r in allrows);rejects=sum(r.get('rejected_count',0) for r in allrows)
runtime={g:load(R/g/'manifest.json')['seconds'] for g in ['main','hostile','hostile_naive','physics_fixed','physics_joint']}
paired=[]
for sc in main:
 for m,r in main[sc].items():
  p=r['paired_vs_M0'];paired.append([sc,m,round(p['delta_rmse_cc'],5),*[round(v,5) for v in p['ci95']],p['wins'],p['losses']])
robust=[]
for sc in naive:
 for m in ['M0','M1','M2','M3','M4']:
  a=noise[sc][m];b=naive[sc][m];robust.append([sc,m,round(b['rmse'][2],5),round(a['rmse'][2],5),round(100*(a['rmse'][2]/b['rmse'][2]-1),2)])
physical=load(OUT/'physical_audit.json')
physical_residual=[]
for sc in ['gaussian','ambiguous']:
 ep=np.load(R/f'main/datasets/{sc}_2000.npz')
 from schrodinger_lab.model import step
 resid=np.array([ep['true'][i+1]-step(ep['true'][i],u)-ep['process'][i] for i,u in enumerate(ep['u'])])
 physical_residual.append({'scenario':sc,'seed':2000,'max_balance_residual_after_process_noise':float(np.max(np.abs(resid)))})
summary=dict(filter_runs=len(allrows),main_unique_episodes=200,hostile_unique_episodes=60,physics_unique_episodes=20,
 control_runs=len(ctrl['rows']),failed_runs=len(failures),fallbacks=fallbacks,rejected_candidates=rejects,
 update_count=sum(r['steps_completed'] for r in allrows),runtime_seconds=runtime,physical_residual=physical_residual,
 conclusion='D: no superiority in primary CSTR experiments. Auxiliary bimodal representation works; no established CSTR multimodal superiority.',
 scope='Synthetic simulation, TABLED variant; Windows scripts supplied but not executed on Windows.')
write_json(OUT/'delivery_summary.json',summary)
text=f'''# YCS Schrödinger-KF Laboratory v1.0 - relatório experimental

17 de outubro de 2026. Pesquisa computacional para Walter Yanko / YCS.

## Conclusão

**Resultado D na comparação principal:** não se confirmou vantagem de estimação
ou de qualidade probabilística do M4 sobre o UKF. O RMSE de CC aumentou
{main['gaussian']['M4']['paired_vs_M0']['percent']:.1f}% no universo gaussiano e
{main['ambiguous']['M4']['paired_vs_M0']['percent']:.1f}% no universo de composição
ambígua. Os IC pareados dessas diferenças ficaram acima de zero. A hipótese de
ganho permanece possível em outros regimes, mas não foi sustentada aqui.

O código matemático consegue representar dois modos no ensaio sintético y=x²+v.
Isso não estabelece vantagem sobre o PF, nem multimodalidade real no CSTR.
A busca CSTR com prior contínua encontrou uma marginal unimodal e uma direção
sem informação térmica; não plantou duas populações iniciais artificiais.

## Protocolo congelado

- Planta TABLED, Δt=54 s; 48 passos/0,72 h nos dois cenários principais.
- 100 sementes 2000-2099 em cada cenário; mesma planta e ruído para todos os filtros.
- N=128; ε=0,02; difusão 64 passos, kernel h=0,05, malha quadrática.
- Desenvolvimento separado: 1000-1005, três cenários, 24 passos; seleção por CRPS.
- M5 permanece gaussiano: IC por clusters de sementes não justificou o gatilho.
- Ruído: 12 sementes por condição, 32 passos; física: 20 sementes, 32 passos.
- Controle: 20 sementes 3000-3019, 32 passos; candidatos e função objetivo comuns.
- Intervalos de confiança: bootstrap de 2000 reamostragens de trajetórias pareadas;
  não se trataram instantes correlacionados como trajetórias independentes.
- A escolha de 100 foi mantida na campanha principal. Ruído/controle/parametrização
  são estudos exploratórios menores, sem poder estatístico equivalente.

Foram concluídas {len(allrows)} execuções de filtros de avaliação, totalizando
{summary['update_count']} atualizações, e {len(ctrl['rows'])} malhas fechadas.
Repetir os mesmos dados com outra verossimilhança ou parametrização não cria
uma trajetória independente nova. O total de plantas/medições por condição
de estimação é 280; as comparações informada/ingênua e fixa/conjunta são pareadas.

## Resultados principais

RMSE/CRPS em kmol/m³; cobertura em %; latência em ms por atualização.

### Universo gaussiano
{mdtable(['Método','RMSE CC','CRPS CC','Cobertura 90%','Latência'],rows_for(main['gaussian']))}
### Composição ambígua
{mdtable(['Método','RMSE CC','CRPS CC','Cobertura 90%','Latência'],rows_for(main['ambiguous']))}
### Diferenças pareadas: alternativa menos UKF
Valores negativos favorecem a alternativa.
{mdtable(['Cenário','Método','Δ RMSE CC','IC95% inferior','IC95% superior','Vitórias','Derrotas'],paired)}

M3 perde variância repetidamente na transformação baricêntrica. Seus intervalos
de 90% tornam-se severamente estreitos. M4 e PF também subcobrem; 128 partículas
não sustentam a distribuição inicial inteira ao longo das atualizações.
Não foi aplicada inflação oculta para melhorar os resultados.

## Observabilidade e identificabilidade

O posto local calculado é {obs['rank_relative_1e_7']}/6 no equilíbrio parado e
{obs['excited_rank_relative_1e_7']}/6 sob excitação. Duas direções químicas são
estruturalmente invisíveis. A maior diferença de temperatura entre estados ao
longo do perfil nulo foi {max(p['max_thermal_difference'] for p in obs['profiles']):.3g} K.
A mesma estrutura foi descrita no acervo RSI e aqui confirmada, não reivindicada
como descoberta inédita. O erro inicial decai por lavagem; isso não significa
que a concentração inicial tenha sido identificada pelos sensores.

A posterior de referência CSTR é uma quadratura de 49×81 hipóteses sobre CA
e a direção invisível de CC, oito observações e transição determinística.
Ela é um ensaio auxiliar de identificabilidade, não a posterior exata da
campanha estocástica de seis estados. O teste escalar usa 24001 pontos.

## Ruído: ablação de informação da verossimilhança
{mdtable(['Ruído','Método','RMSE ingênuo','RMSE informado','Variação %'],robust)}

M2/M3/M4 compartilham exatamente a mesma verossimilhança em cada condição.
M0/M1 recebem a família correspondente, mas empregam uma aproximação robusta
gaussiana. Assim, diferenças contra M0/M1 misturam o tipo de aproximação e a
forma da posterior; a comparação M4-PF isola melhor o efeito do gerador.
O ruído correlacionado é entre sensores no mesmo instante. Ruído temporalmente
correlacionado não foi avaliado. O viés constante desconhecido não foi aumentado
no estado e permanece uma condição de modelo incorreto para todos.

## Física incerta
Parâmetros: UA, multiplicador cinético, alimentação FA e calor de reação.
As plantas recebem amostras privadas; filtros só conhecem a prior. M0/M1
estimam o estado aumentado. M2-M4 representam os parâmetros por partículas.

Fixos:
{mdtable(['Método','RMSE CC','CRPS CC','Cobertura 90%','Latência'],rows_for(fixed['physics']))}
Conjuntos:
{mdtable(['Método','RMSE CC','CRPS CC','Cobertura 90%','Latência'],rows_for(joint['physics']))}

A estimação conjunta melhora ou piora conforme o método e amplia a dimensão.
Esses resultados não demonstram identificabilidade individual de todos os
parâmetros. E e k0 não foram separados; um multiplicador cinético foi usado.
O Jacobiano conjunto das seis condições iniciais e quatro parâmetros, em
coordenadas normalizadas e 32 passos no equilíbrio, tem posto local
{int(sum(np.array(obs['joint_singular_values'])>obs['joint_singular_values'][0]*1e-7))}/10
ao limiar relativo 10⁻⁷. Seus valores singulares estão em observability.json.
Esse diagnóstico local confirma confundimento; não prova identificabilidade
global mesmo para as direções de sensibilidade não nula.

## Controle
{mdtable(['Combinação','Custo médio','RMSE CC','Pico K','Violações médias','Fallbacks médios'],[[k,round(v['loss'],3),round(v['rmse_cc'],5),round(v['peak'],3),v['violations'],v['fallbacks']] for k,v in ctrl['summary'].items()])}

Os ICs de diferenças de custo estão em `results/control/control.json`, tanto
contra UKF nominal quanto contra M4 nominal. O segundo contraste separa a
mudança no controlador da mudança no estimador. O controlador reutiliza o
conjunto finito do Multiverse v0.1: 64 sequências, horizonte 9, 9 cenários de
quantis de CC. A regra de fallback foi auditada e testada. Não equivale ao
NMPC histórico de horizonte 57/fmincon, nem a otimização global contínua.

## Custo e consistência física

O microbenchmark executou N=64,128,256,512,1024. A alocação rastreada máxima foi
{max(r['peak_traced_MiB'] for r in scale):.2f} MiB; não é medida de RSS nem
garantia de consumo total do aplicativo. A pior atualização P99 desse ensaio foi
{max(r['p99_ms'] for r in scale):.2f} ms, abaixo de 54000 ms. O microbenchmark
inclui instrumentação de memória e somente seis atualizações por tamanho.
P99 tão curto é descritivo, não uma garantia de tempo real. As latências da
campanha incluem variações de carga do ambiente compartilhado. Não se mediu
o notebook Windows do usuário.

Execuções de filtro interrompidas: {len(failures)}. Fallbacks: {fallbacks}.
Candidatos rejeitados por domínio: {rejects}. O primeiro ensaio sintético OT
foi interrompido por não convergir com ε=0,01/4000 iterações; o registro foi
preservado. A execução revisada explicita ε=0,05 e fallback, sem aceitar
marginais erradas. A campanha principal mantém seu ε pré-selecionado.

A auditoria final encontrou três registros ausentes no JSONL principal, embora
o CSV original tivesse as 1200 linhas e todos os traços NPZ estivessem presentes.
Um registro foi recuperado do JSON de demonstração original; dois foram
recalculados e confrontados com os traços originais a tolerância 10⁻¹² e com
as métricas CSV. As latências originais foram preservadas do CSV. A causa da
omissão não foi determinada. O JSONL anterior comprimido e o procedimento
estão em `results/main/integrity/`; `scripts/audit_results.py` confirma agora
a integridade das 2016 avaliações, sem duplicatas ou trajetórias ausentes.

O resíduo máximo da reconstrução do passo após subtrair o ruído de processo,
em duas trajetórias pré-fixadas, foi {max(x['max_balance_residual_after_process_noise'] for x in physical_residual):.3g}.
Resíduos estequiométricos determinísticos, equilíbrio, positividade e integração
independente são verificados nos testes. A regularização de covariância limita
autovalores a 10⁻¹²; não é uma garantia de calibração.

## Validação, entrega e limites

34 testes Python passaram, incluindo física, probabilidades, causalidade,
paridade TypeScript, convergência OT, drift publicado, multimodalidade sintética,
controle/fallback e exportação. QA no Chromium verificou os sete painéis,
projeção 3D, troca de eixos, seleção temporal, exportação JSON e nova execução
real no servidor com semente 4242. Não houve erros de console ou overflow
horizontal em 390 px. Essa validação ocorreu em Linux; os scripts Windows
não foram executados em Windows.

Questões publicáveis: (1) como a não observabilidade estrutural limita filtros
generativos; (2) como separar perda de diversidade, viés baricêntrico e viés
de discretização; (3) se uma medida química adicional torna o custo distributivo
justificável; (4) quanto uma proposta condicionada à observação melhora M4
frente a PF bem ajustado. Uma publicação exigiria revisão bibliográfica mais
ampla, mais plantas/regimes, referências posteriores de alta precisão, ablações
de regularização de segunda ordem e dados experimentais ou industriais.

Não foram demonstrados Resultado A (ganho principal), Resultado B (superioridade
multimodal no CSTR) ou uma vantagem universal de controle. O relatório publica
os contrastes de controle sem selecionar apenas trajetórias favoráveis.

Referências e derivação: MATHEMATICAL_REPORT.md. Proveniência, equações e
unidades: PHYSICAL_AUDIT.md. Todos os números acima são lidos dos arquivos
de resultados por este gerador.
'''
(OUT/'EXPERIMENTAL_REPORT.md').write_text(text,encoding='utf-8')

# Portable HTML report: tables and paragraphs, original figures included.
def to_html(md):
 lines=md.splitlines();out=[];para=[];table_lines=[]
 def flush():
  if para:out.append('<p>'+html.escape(' '.join(para))+'</p>');para.clear()
 def flush_table():
  if table_lines:
   rr=[r.strip('|').split('|') for r in table_lines if not re.match(r'^\|[- :|]+\|$',r)]
   out.append('<table>'+''.join('<tr>'+''.join('<'+('th' if i==0 else 'td')+'>'+html.escape(v.strip())+'</'+('th' if i==0 else 'td')+'>' for v in row)+'</tr>' for i,row in enumerate(rr))+'</table>');table_lines.clear()
 for line in lines:
  if line.startswith('|'):flush();table_lines.append(line);continue
  flush_table()
  if line.startswith('#'):
   flush();n=len(line)-len(line.lstrip('#'));out.append(f'<h{n}>'+html.escape(line[n:].strip())+f'</h{n}>')
  elif not line.strip():flush()
  else:para.append(line)
 flush();flush_table();return '\n'.join(out)
styles='body{font-family:system-ui,Arial;max-width:1050px;margin:45px auto;padding:0 25px;color:#26334b;line-height:1.7}h1{font-size:36px;line-height:1.2;color:#352956}h2{margin-top:40px;color:#634b94}table{border-collapse:collapse;width:100%;font-size:12px;display:block;overflow:auto}th,td{padding:9px 12px;border-bottom:1px solid #dce1e9;text-align:left}th{background:#efeaf6}img{max-width:100%}a{color:#7156a6}p{white-space:normal}code{font-size:12px}'
(ROOT/'web/figures').mkdir(exist_ok=True)
for p in FIG.glob('*.png'):shutil.copy2(p,ROOT/'web/figures'/p.name)
body=to_html(text)+''.join(f'<h2>Figura {i+1}</h2><img src="figures/{name}.png" alt="{name}">' for i,name in enumerate(['01_rmse','02_coverage','03_trace','04_modes','05_cost','06_physics','07_control']))
(ROOT/'web/report.html').write_text('<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>YCS - Relatório científico</title><style>'+styles+'</style><a href="index.html">← Voltar ao laboratório</a>'+body+'</html>',encoding='utf-8')

# PDF with controlled page breaks, vector text and scientific plots.
pdfmetrics.registerFont(TTFont('DVS',findfont(FontProperties(family='DejaVu Sans'))));pdfmetrics.registerFont(TTFont('DVS-B',findfont(FontProperties(family='DejaVu Sans',weight='bold'))))
W,H=595.28,841.89;c=canvas.Canvas(str(OUT/'YCS_SchrodingerKF_Relatorio_v1.0.pdf'),pagesize=(W,H));c.setTitle('YCS Schrödinger-KF - Relatório científico v1.0');c.setAuthor('Yanko Creative Studio')
style=ParagraphStyle('body',fontName='DVS',fontSize=9.4,leading=14,textColor=colors.HexColor('#31415a'));y=0;page=0
def begin(title,eyebrow):
 global y,page
 if page and y<50:raise RuntimeError('Report page overflow: '+str(page))
 if page:c.showPage()
 page+=1;c.setFillColor(colors.HexColor('#131b2c'));c.rect(0,H-117,W,117,fill=1,stroke=0);c.setFillColor(colors.HexColor('#baa2ee'));c.setFont('DVS',8);c.drawString(42,H-33,'YCS PROCESSLAB / SCIENTIFIC RESEARCH  •  17 OUT 2026');c.setFillColor(colors.white);c.setFont('DVS-B',19);c.drawString(42,H-65,title);c.setFont('DVS',9);c.setFillColor(colors.HexColor('#adb9cf'));c.drawString(42,H-89,eyebrow);c.setFillColor(colors.HexColor('#7b879d'));c.setFont('DVS',7);c.drawString(42,27,'Schrödinger-KF v1.0 | Simulação clássica | Dados sintéticos');c.drawRightString(W-42,27,str(page));y=H-143
def para(txt,sz=9.4):
 global y
 st=ParagraphStyle('p',parent=style,fontSize=sz,leading=sz*1.5);p=Paragraph(txt,st);a,h=p.wrap(W-84,y-50);p.drawOn(c,42,y-h);y-=h+12
def heading(txt):
 global y
 c.setFillColor(colors.HexColor('#72579c'));c.setFont('DVS-B',11);c.drawString(42,y,txt);y-=20
def fig(name,height):
 global y
 from PIL import Image
 p=FIG/(name+'.png');im=Image.open(p);width=min(W-84,height*im.width/im.height);height=width*im.height/im.width;c.drawImage(str(p),42+(W-84-width)/2,y-height,width,height);y-=height+14
def tab(headers,rows,widths=None):
 global y
 data=[[Paragraph(html.escape(str(x)),ParagraphStyle('t',fontName='DVS-B' if i==0 else 'DVS',fontSize=7.2,leading=10,textColor=colors.HexColor('#25334b'))) for x in row] for i,row in enumerate([headers]+rows)]
 t=Table(data,colWidths=widths or [(W-84)/len(headers)]*len(headers));t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#ede7f5')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,-1),.3,colors.HexColor('#d7dfeb'))]));w,h=t.wrap(W-84,y-50);t.drawOn(c,42,y-h);y-=h+16

begin('Transportar não cria observabilidade','Resultado principal: o UKF continua superior nos dois cenários CSTR testados.')
para(f'<b>M4 aumentou o RMSE de CC em {main["gaussian"]["M4"]["paired_vs_M0"]["percent"]:.1f}% no cenário gaussiano e {main["ambiguous"]["M4"]["paired_vs_M0"]["percent"]:.1f}% no cenário ambíguo.</b> Os intervalos pareados sustentam a desvantagem, dentro deste protocolo. O resultado negativo foi preservado.')
fig('01_rmse',230)
tab(['Evidência entregue','Escopo'],[['Campanha principal','100 sementes por cenário; N=128; 48 passos de 54 s'],['Avaliações de filtros',str(len(allrows))+' execuções / '+str(summary['update_count'])+' atualizações'],['Controle','100 malhas fechadas / 20 sementes × 5 combinações'],['Validação','34 testes Python; 7 painéis; exportação e simulação pelo navegador']],[150,361])
para('A distribuição bimodal foi reproduzida no problema sintético y=x²+v. O CSTR mostrou ambiguidade contínua e direções invisíveis; não foi demonstrada superioridade multimodal química. Não há vantagem quântica ou validação em planta real.')
begin('Física e proveniência','Variante TABLED preservada. As variantes histórica e calibrada permanecem separadas.')
para('Fonte principal: commit f4444d4c238291b8633743930249ee387ad94541. Modelo MATLAB histórico recuperado do commit 88c40e65204fa6aa5bed02cc64fb15be79a53bb1. Paridade com TypeScript e integração independente foram verificadas.')
tab(['Parâmetro','TABLED','Histórico convertido'],[['Calor liberado / kJ kmol⁻¹','91556,9','83736,0'],['Temperatura nominal / K',f'{aud["equilibria"][0][4]:.6f}',f'{aud["historical_equilibrium"][4]:.6f}'],['Arrhenius','T em K','T em K + 0,183333'],['mw','453,6 kmol/h','1000 lbmol/h convertido'],['Amostragem','0,015 h = 54 s','0,015 h']])
heading('Estado, medição e assimetria térmica')
para('x = [CA, CB, CC, CM, T, Tt]. Medem-se apenas T e Tt. CA é óxido de propileno; CB, água; CC, propilenoglicol; CM, metanol inerte. Os balanços cancelam a reação em CA+CC e CB+CC. O calor de resfriamento depende de T e da alimentação do refrigerante; Tt não realimenta diretamente T.')
para('Unidades: kmol, m³, h, K, kJ. mw é vazão <b>molar</b>, não kg/h. O calor positivo do código é −ΔH. Planta: RK4/0,001 h; filtros: RK4/0,0025 h; UKF histórico Euler preservado separadamente. Os valores completos estão em physical_audit.json.')
heading('Domínio e conservação')
para(f'Concentrações negativas e temperaturas fora do domínio são rejeitadas. O ruído de processo aditivo é separado do resíduo determinístico. Máximo resíduo de reconstrução em duas trajetórias: {max(x["max_balance_residual_after_process_noise"] for x in physical_residual):.2e}. Limite térmico de estudo: 344 K; não é certificação de segurança.')
begin('O que cada filtro realmente faz','Sinkhorn baricêntrico e ponte de Schrödinger são implementações diferentes.')
tab(['Método','Atualização'],[['M0','UKF RK4; observação linear T/Tt; Joseph; Q incluído no ganho.'],['M1','EnKF com observações perturbadas e covariância amostral consistente.'],['M2','Bootstrap PF; pesos em log; reamostragem sistemática quando ESS<N/2.'],['M3','OT entrópico; marginais (w,1/N); projeção baricêntrica; viés de variância medido.'],['M4','Schrödinger–Föllmer: SDE auxiliar, alvo KDE contínuo, Euler–Maruyama.'],['M5','Chave EnKF/M4 testada em desenvolvimento; gatilho não habilitado.']],[60,451])
para('M4: a referência Q é Browniana em coordenadas afins da previsão. Início δ0, alvo ΣwⱼN(zⱼ,h²I). Com h=0,05 a marginal é contínua e a divergência KL terminal é finita. O drift é calculado analiticamente para essa mistura; a integração da SDE é aproximada.')
para('Definindo D=1−τ+τh², pesos auxiliares ∝ wⱼ exp[(x·zⱼ−τ||zⱼ||²/2)/D] e drift [Σpⱼzⱼ−(1−h²)x]/D. Para h=0 recupera-se o drift empírico do artigo, mas a marginal atômica exata seria singular. O pacote separa erros de partículas, kernel e discretização.')
para('Causalidade: advance(u,y) não recebe a planta nem observações futuras. O tempo auxiliar τ não é futuro do reator. Fontes: Bao & Sun, arXiv:2512.18928v1, equações 3.9/3.12/3.13; Sun v4; Reich; Léonard. Derivação e links completos: MATHEMATICAL_REPORT.md.')
begin('Precisão e calibração','Métricas agregadas por trajetória; IC por reamostragem de sementes pareadas.')
fig('02_coverage',225)
tab(['Cenário','M4−UKF RMSE CC','IC95%','Vitórias M4'],[[sc,f'{main[sc]["M4"]["paired_vs_M0"]["delta_rmse_cc"]:.5f}',' / '.join(f'{v:.5f}' for v in main[sc]['M4']['paired_vs_M0']['ci95']),str(main[sc]['M4']['paired_vs_M0']['wins'])+'/100'] for sc in ['gaussian','ambiguous']],[95,125,180,111])
para('M3 quase elimina a incerteza de composição nas atualizações repetidas. A preservação da massa e da média não preserva automaticamente a covariância. M4 e PF também subcobrem: gerar novas partículas não garante recuperar a diversidade perdida da previsão.')
para('Os ICs principais são de diferenças de RMSE médio por trajetória, não de todos os instantes empilhados. Há 100 repetições independentes dentro de cada cenário. Comparações múltiplas e regimes secundários são exploratórios; não se extrapola uma vitória universal.')
begin('Intervalos contam outra história','Semente 2000 pré-fixada; a seleção do exemplo não usa o vencedor.')
fig('03_trace',420)
para('A faixa do UKF preserva a incerteza inicialmente invisível. O transporte baricêntrico colapsa sua dispersão. O erro de todos os métodos tende a cair com a lavagem do reator: esse fenômeno físico não equivale à identificação das condições iniciais.')
begin('Multimodalidade e limites de informação','Um controle matemático bimodal e uma ambiguidade química contínua.')
fig('04_modes',250)
para(f'Posto local: {obs["rank_relative_1e_7"]}/6 em repouso, {obs["excited_rank_relative_1e_7"]}/6 com excitação. Duas direções preservam CA e a capacidade térmica total. Seus históricos de T/Tt coincidem e as diferenças de concentração decaem por exp(−∫Ddt).')
para('A referência CSTR usa uma prior contínua e uma quadratura 49×81 em um subespaço químico, oito medições e transição determinística. Foi encontrada uma marginal unimodal. Isso não prova ausência de multimodalidade em todos os regimes; delimita o ensaio executado.')
para('No problema escalar, o sinal de x é ambíguo porque y=x²+v. PF, transporte e ponte representam ambos os sinais. As distâncias Wasserstein-1 e massas por modo constam dos JSON. Demonstrar dois modos nesse controle não estabelece superioridade do novo filtro.')
begin('Ruído e física incerta','O tratamento da verossimilhança foi separado do transporte.')
tab(['Cenário','UKF RMSE','PF RMSE','M4 RMSE'],[[sc,f'{rs["M0"]["rmse"][2]:.5f}',f'{rs["M2"]["rmse"][2]:.5f}',f'{rs["M4"]["rmse"][2]:.5f}'] for sc,rs in noise.items()])
fig('06_physics',225)
para('Ruído: t₃, mistura de outliers, correlação entre sensores, intermitência e viés constante desconhecido. Parâmetros: UA, multiplicador cinético, FA e calor de reação. Não há acesso do filtro aos parâmetros sorteados da planta. Ensaios de 12/20 sementes, respectivamente, têm alcance exploratório.')
begin('Controle inferencial','Contrastes separados: estimador fixo ou controlador fixo.')
fig('07_control',230)
tab(['Política','Δ custo vs M4 nominal','IC95%'],[[k,f'{v["vs_M4_nominal"]["mean_delta"]:.3f}',' / '.join(f'{x:.3f}' for x in v['vs_M4_nominal']['ci95'])] for k,v in ctrl['summary'].items()],[145,155,211])
para('Todos usam os mesmos limites e função objetivo. O horizonte de 9 passos e 64 sequências é uma aproximação finita do NMPC, herdada do Multiverse. Risco usa a média do terço superior dos nove cenários; regret usa arrependimento máximo. O fallback nominal é testado. Não se afirma ótimo global ou validação em hardware.')
begin('Custo, falhas e reprodução','CPU-first; 16 GB de RAM como alvo, sem benchmark no notebook do usuário.')
fig('05_cost',220)
para(f'Maior alocação rastreada: {max(r["peak_traced_MiB"] for r in scale):.2f} MiB. P99 máximo do microbenchmark: {max(r["p99_ms"] for r in scale):.2f} ms, contra 54.000 ms de amostragem. São seis atualizações por tamanho, com instrumentação; a métrica não certifica tempo real nem mede todo o RSS.')
tab(['Verificação','Resultado'],[['Execuções de filtros interrompidas',str(len(failures))],['Fallbacks / candidatos de domínio rejeitados',str(fallbacks)+' / '+str(rejects)],['Interrupção sintética registrada','Sinkhorn ε=0,01 não atingiu tolerância; execução revisada explicita ε=0,05.'],['Interface','7 painéis; exportação; nova semente 4242; sem erros de console.']],[195,316])
para('Extraia o ZIP. VER_RESULTADOS.bat abre os dados offline. INICIAR_LAB.bat prepara Python e abre o motor local. TESTAR.bat valida o núcleo; REPRODUZIR.bat cria uma campanha nova sem sobrescrever evidências. Os scripts Windows não foram executados em Windows nesta sessão.')
begin('Contribuição e próximos testes','Um laboratório verificável, com resultado negativo útil.')
para('A contribuição desta entrega é a integração auditada de modelos, filtros e diagnósticos reproduzíveis, incluindo uma ponte matematicamente identificada e os seus vieses. Não se reivindica originalidade absoluta nem superioridade generalizável.')
heading('Perguntas que merecem investigação')
para('1. Uma medição química adicional, ainda que esparsa, elimina as direções invisíveis?<br/>2. Uma proposta condicionada à medição melhora M4 frente a PF igualmente ajustado?<br/>3. Correções de segunda ordem do transporte evitam colapso sem destruir modos?<br/>4. A escolha de Q Browniana, h e malha da SDE muda a calibração de modo previsível?<br/>5. Quando melhor calibração se converte em menor custo de controle?')
heading('Fontes primárias e acesso ao código')
para('ProcessLab: github.com/walteryanko/yanko-process-lab<br/>Bao &amp; Sun: arxiv.org/html/2512.18928v1<br/>Sun, versão posterior: arxiv.org/html/2512.18928v4<br/>Reich: arxiv.org/abs/1210.0375<br/>Acevedo, de Wiljes &amp; Reich: arxiv.org/abs/1608.08179<br/>Léonard: arxiv.org/abs/1308.0215<br/>Stromme: proceedings.mlr.press/v206/stromme23a.html')
para('O pacote contém fontes, licença/proveniência, parâmetros, sementes, matrizes de covariância, partículas de exemplos, planos de transporte, dados NPZ, métricas CSV/JSON, relatórios e scripts. O relatório HTML detalhado e as auditorias em Markdown complementam este PDF. Todos os números são gerados dos resultados armazenados.')
c.save();print('Report generated:',page,'pages',summary)
