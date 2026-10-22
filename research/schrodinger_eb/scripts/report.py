"""Generate scientific figures and a ten-page report solely from saved results."""
import json,sys,html
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import findfont
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Image,Preformatted
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor,white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from eblab.model import BASE,Q0,DT,SCALES,SOURCE_COMMIT,F0

def load(path):return json.loads((ROOT/path).read_text())
out=ROOT/'reports';figdir=out/'figures';figdir.mkdir(parents=True,exist_ok=True)
primary=load('results/primary/summary.json');analysis=load('results/analysis.json')
obs=load('results/studies/observability.json');ref=load('results/studies/posterior_reference.json')
syn=load('results/studies/synthetic_distributions.json');selection=load('results/studies/selection.json')
scaling=load('results/studies/scaling.json');control=load('results/control/control.json')
robust=load('results/robust/summary.json');naive=load('results/naive/summary.json')
fixed=load('results/physics_fixed/summary.json')['physics'];joint=load('results/physics_joint/summary.json')['physics']
colors=['#127a62','#2375a7','#b17922','#8659a3','#bf5571','#6b7c4e'];methods=['M0','M1','M2','M3','M4','M5']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','axes.labelcolor':'#324846','grid.alpha':.2})
def savefig(fig,name):
    fig.tight_layout();fig.savefig(figdir/(name+'.png'),dpi=170,bbox_inches='tight');plt.close(fig)

fig,axs=plt.subplots(2,2,figsize=(8,5.2))
for j,(sc,title) in enumerate([('gaussian','Próximo ao equilíbrio'),('weak_thermal','Baixa informação térmica')]):
    g=primary[sc];axs[0,j].bar(methods,[g[m]['rmse'][2] for m in methods],color=colors);axs[0,j].set_title(title);axs[0,j].set_ylabel('RMSE CEB · kmol/m³')
    axs[1,j].bar(methods,[100*g[m]['coverage90'][2] for m in methods],color=colors);axs[1,j].axhline(90,color='#555',ls='--');axs[1,j].set_ylim(0,105);axs[1,j].set_ylabel('Cobertura de 90% · %')
savefig(fig,'primary')
fig,axs=plt.subplots(1,2,figsize=(8,3.2))
for i,hh in enumerate(obs['histories']):
    a=np.array(hh);axs[0].plot(obs['time'],a[:,2],color=colors[i],label=f'Hipótese {i+1}');axs[1].plot(obs['time'],a[:,4],color=colors[i])
axs[0].set_ylabel('CEB · kmol/m³');axs[1].set_ylabel('T · °C')
for ax in axs:ax.set_xlabel('Tempo · h');ax.grid(True)
axs[0].legend();savefig(fig,'ambiguity')
fig,axs=plt.subplots(1,2,figsize=(8,3.2))
for r in ref['snapshots']:
    if r['step']==23:axs[0].plot(r['grid'],r['kdes'][1]['density'],label=f"PF {r['n']}")
b=syn['bimodal'];axs[1].plot(b['grid'],b['density'],label='Quadratura');axs[1].hist(b['sets']['M4'],bins=45,density=True,alpha=.5,label='M4')
for ax in axs:ax.legend();ax.set_ylabel('Densidade');ax.grid(True)
axs[0].set_xlabel('CEB · kmol/m³, passo 24');axs[0].set_title('CSTR: prior contínua')
axs[1].set_xlabel('x');axs[1].set_title('Auxiliar: y = x² + v');savefig(fig,'posteriors')
fig,ax=plt.subplots(figsize=(8,2.8));x=np.arange(5)
ax.bar(x-.18,[fixed[m]['rmse'][2] for m in methods[:5]],width=.36,label='Parâmetros fixos',color=colors[1]);ax.bar(x+.18,[joint[m]['rmse'][2] for m in methods[:5]],width=.36,label='Estimação conjunta',color=colors[0]);ax.set_xticks(x,methods[:5]);ax.set_ylabel('RMSE CEB · kmol/m³');ax.legend();savefig(fig,'physics')
fig,axs=plt.subplots(2,2,figsize=(8,4.7))
traces=sorted([t for t in control['traces'] if t['seed']==4000],key=lambda t:(t['method'],t['policy']))
for i,tr in enumerate(traces):
    hh=tr['history'];x=np.arange(1,len(hh)+1)*DT;states=np.array([r['x'] for r in hh]);lab=tr['method']+' '+tr['policy']
    axs[0,0].plot(x,states[:,2]/states[:,:4].sum(1),color=colors[i],label=lab);axs[0,1].plot(x,states[:,4],color=colors[i]);axs[1,0].plot(x,[r['fE'] for r in hh],color=colors[i]);axs[1,1].plot(x,[r['Q_MW'] for r in hh],color=colors[i])
axs[0,0].plot(x,[r['reference'] for r in hh],color='black',ls='--',label='Referência');axs[0,1].axhline(165,color='black',ls='--');axs[0,0].legend(fontsize=7)
for ax,label in zip(axs.flat,['Fração xEB','T · °C','fE · m³/h','Q efetivo · MW']):ax.set_ylabel(label);ax.set_xlabel('Tempo · h');ax.grid(True)
savefig(fig,'control')
fig,ax=plt.subplots(figsize=(8,3.1))
for i,m in enumerate(methods[:5]):
    rr=[r for r in scaling if r['method']==m];ax.plot([r['n'] for r in rr],[r['update_mean_ms'] for r in rr],marker='o',color=colors[i],label=m)
ax.set_xscale('log',base=2);ax.set_yscale('log');ax.set_xticks([64,128,256,512,1024],[64,128,256,512,1024]);ax.set_xlabel('Número de partículas');ax.set_ylabel('Latência média · ms');ax.grid(True);ax.legend(ncol=5);savefig(fig,'scaling')

pdfmetrics.registerFont(TTFont('YCS',findfont('DejaVu Sans')));pdfmetrics.registerFont(TTFont('YCS-Bold',findfont('DejaVu Sans:weight=bold')))
pdfmetrics.registerFontFamily('YCS',normal='YCS',bold='YCS-Bold',italic='YCS',boldItalic='YCS-Bold')
ink=HexColor('#183b37');muted=HexColor('#526e68');mint=HexColor('#e9f4ed');gold=HexColor('#fbf1df')
styles={
 'title':ParagraphStyle('title',fontName='YCS-Bold',fontSize=25,leading=30,textColor=ink,spaceAfter=16),
 'h1':ParagraphStyle('h1',fontName='YCS-Bold',fontSize=18,leading=23,textColor=ink,spaceAfter=13),
 'h2':ParagraphStyle('h2',fontName='YCS-Bold',fontSize=11,leading=15,textColor=ink,spaceBefore=9,spaceAfter=6),
 'body':ParagraphStyle('body',fontName='YCS',fontSize=9.1,leading=13.4,textColor=ink,spaceAfter=9),
 'small':ParagraphStyle('small',fontName='YCS',fontSize=7.7,leading=11,textColor=muted,spaceAfter=7),
 'code':ParagraphStyle('code',fontName='YCS',fontSize=8,leading=12,textColor=ink,backColor=mint,borderPadding=8,spaceAfter=10),
 'cell':ParagraphStyle('cell',fontName='YCS',fontSize=8,leading=11,textColor=ink)}
story=[];md=[]
def P(text,style='body'):story.append(Paragraph(text,styles[style]));md.append(text.replace('<b>','**').replace('</b>','**'))
def page(title):
    if story:story.append(PageBreak())
    P(title,'h1');md.append('')
def T(headers,rows,widths=None):
    data=[[Paragraph(html.escape(str(v)),styles['cell']) for v in r] for r in [headers]+rows]
    t=Table(data,colWidths=widths or [511/len(headers)]*len(headers),hAlign='LEFT',repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),mint),('ROWBACKGROUNDS',(0,1),(-1,-1),[white,HexColor('#f6f9f7')]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),('LINEBELOW',(0,0),(-1,0),.7,muted)]))
    story.append(t);story.append(Spacer(1,10));md.append('| '+' | '.join(map(str,headers))+' |');md.append('| '+' | '.join(['---']*len(headers))+' |');md.extend('| '+' | '.join(map(str,r))+' |' for r in rows)
def FIG(name,width=511):
    from PIL import Image as PI
    p=figdir/(name+'.png');w,h=PI.open(p).size;story.append(Image(str(p),width=width,height=width*h/w));story.append(Spacer(1,9));md.append(f'![{name}](figures/{name}.png)')
def f(x,n=5):return f'{x:.{n}f}'

P('YCS PROCESSLAB · PESQUISA CIENTÍFICA · 22 OUT 2026','small')
P('Schrödinger-KF Lab<br/>Reator de etilbenzeno','title')
P('Uma distribuição mais rica produz conhecimento químico mais útil quando só a temperatura é observada?','h2')
P('<b>Resultado desta campanha: a configuração testada não demonstrou vantagem sobre o UKF.</b> A ponte generativa funcionou nos testes matemáticos, mas teve maior erro e menor cobertura no reator. A representação de partículas preserva possibilidades; não cria informação ausente nas medições.')
T(['Cenário · 100 sementes','UKF: RMSE CEB','M4: RMSE CEB','Diferença'],[[sc,f(primary[sc]['M0']['rmse'][2]),f(primary[sc]['M4']['rmse'][2]),f(primary[sc]['M4']['paired_vs_M0']['percent'],1)+'%'] for sc in primary],[195,105,105,106])
P('RMSE em kmol/m³. A diferença positiva significa erro maior para M4. Os dois intervalos de confiança pareados de ΔRMSE excluem zero; não há alegação de dominância universal dos baselines.','small')
T(['Evidência entregue','Quantidade'],[['Execuções de estimação','2.240'],['Avaliações de desenvolvimento','176'],['Ensaios de controle + fallback','40 + 3'],['Testes automatizados aprovados','35'],['Datasets / trajetórias de estimação','600 / 2.240']],[360,151])
P('<b>Escopo:</b> primeiro reator de alquilação de benzeno com etileno; cinco estados, medição apenas de temperatura. Simulação de uma reconstrução das equações do ProcessLab. Não é operação industrial, reprodução termodinâmica de Aspen ou vantagem quântica.')
P('O pacote inclui código, dados brutos, resultados por semente, auditorias, interface offline e servidor local para novas simulações. A entrega foi reexecutada após perda do ambiente temporário; veja reports/recovery.md.','small')

page('01 · Física recuperada e auditada')
P('Fonte congelada: commit '+SOURCE_COMMIT+'. Arquivos originais model.py, observer.py e control.py em vendor/. As auditorias históricas de 2016 e a investigação térmica recuperadas acompanham o pacote.')
T(['Grandeza','Convenção nesta release'],[['Estados','CE, CB, CEB, CDEB [kmol/m³], T [°C]'],['Medição','T; não existe T de camisa neste modelo'],['Volume / período','200 m³ / 0,025 h = 90 s'],['Vazões nominais',', '.join(f(v,5) for v in F0)+' m³/h'],['Equilíbrio',', '.join(f(v,6) for v in BASE)],['Q efetivo nominal',f(Q0,3)+' kcal/h = '+f(Q0*4184/3.6e9,6)+' MW'],['Cinética','A em m³/(kmol s), multiplicador 3.600 para horas'],['Arrhenius','E=[17000,20000,15000] cal/mol; R=1,987 cal/(mol K)'],['Calores de reação','[-27150,-26950,-205,5] kcal/kmol']],[145,366])
P('Reações: E+B→EB; EB+E→DEB; DEB+B→2EB. A matriz estequiométrica tem posto 2. Inventários independentes: zA=CB+CEB+CDEB e zE=CE+CEB+2CDEB. Ambos seguem balanços lineares de alimentação/saída, independentemente das taxas.')
P('A planta usa DOP853; os filtros usam RK4 com oito subpassos. O máximo resíduo do balanço analítico de inventário, descontado o ruído de processo registrado, foi '+f(analysis['audit']['max_moiety_balance_residual'],15)+' kmol/m³. O equilíbrio e a integração foram verificados contra o código fonte e integrador independente.')
P('<b>Limitação térmica decisiva:</b> os coeficientes publicados coincidem com h/T°C do backup Aspen, não com Cp derivativo. Q=25,24 MW é o fechamento efetivo dessa equação; o backup registra 9,0879 MW e Luyben cerca de 10,3 MW. Esses valores não são intercambiáveis. A identidade de Hess também difere em 5,5 kcal/kmol. Nenhum desses ajustes foi silenciosamente aplicado ao baseline.')

page('02 · Algoritmos e ponte genuína')
T(['Método','Implementação efetiva'],[['M0','UKF α=0,35, β=2, κ=0; RK4; Joseph; paridade com original em domínio sem projeções.'],['M1','EnKF com observações perturbadas; covariância amostral consistente.'],['M2','Bootstrap PF com log-pesos, ESS e reamostragem sistemática.'],['M3','Sinkhorn no domínio logarítmico; transformação baricêntrica; escala física; fallback explícito.'],['M4','Gerador Schrödinger–Föllmer com referência browniana pontual e alvo posterior KDE.'],['M5','Gatilho por não gaussianidade e ESS; nesta release o desenvolvimento mantém EnKF.']],[55,456])
P('M3 resolve o transporte entrópico com marginais w e 1/N. Seu custo usa escalas [0,1;1,5;0,75;0,25;15]. A análise x′j=NΣPijxi preserva a média, mas contrai dispersão. Não é uma ponte de difusão e não preserva automaticamente covariância ou modos.')
P('M4 minimiza KL(P||Q), P0=δ0, P1=Σwi N(zi,h²I), em coordenadas da previsão. Para D=1-τ+τh² e π=softmax[logw+(v·z-τ||z||²/2)/D], o drift é:','body')
P('a(v,τ) = [Σ πi zi − (1−h²)v] / D<br/>dVτ = a(Vτ,τ)dτ + dWτ; V0=0','code')
P('A fórmula com h=0 coincide com o drift empírico de Bao/Sun v1; h&gt;0 fornece alvo contínuo e evita chamar um alvo discreto singular de ponte de KL finita. Usam-se h=0,1 e 64 passos Euler–Maruyama em grade quadrática. A normalização pela previsão e o KDE são extensões explícitas à formulação publicada.')
P('<b>Distinção:</b> esta é uma ponte com marginal inicial pontual que gera a posterior. Não é a ponte física geral entre toda a prior e a posterior. Erros de Monte Carlo, suavização, discretização e domínio permanecem. A derivação completa e correspondência com as equações (3.9), (3.12), (3.13) estão em mathematics.md.')
P('Preprint consultado: arXiv:2512.18928, v1 Bao e Sun; v4 Hui Sun, agosto de 2026. ETPF: Reich 2013; transporte entrópico: Cuturi 2013. A contribuição desta entrega é implementação auditável e evidência no processo, não originalidade absoluta.','small')

page('03 · Desenho experimental e seleção')
T(['Campanha','Seeds / métodos','Execuções'],[['Principal','2000–2099; 2 condições; M0–M5','1200'],['Ruído informado','3000–3011; 6 condições; M0–M4','360'],['Ruído ingênuo','mesmas seeds; 4 condições; M0–M4','240'],['Física fixa / conjunta','3500–3519; M0–M4','100 + 100'],['UKF Q × 64','2000–2019; 2 condições','40'],['Sem observações','2000–2099; 2 condições; M0','200'],['Desenvolvimento','101–108; 2 condições; 11 candidatos','176'],['Controle','4000–4009; 4 braços','40']],[155,290,66])
P('Cada trajetória tem 60 amostras (1,5 h), 128 partículas nos métodos de ensemble. Prior contínua gaussiana condicionada ao domínio: desvios [0,012;0,35;0,18;0,06;1,5]; no cenário de ambiguidade [0,012;0,8;0,4;0,15;1,5]. Nenhum modo foi plantado na prior do CSTR. Ruído térmico nominal σ=1,5 °C.')
P('As plantas, entradas e ruídos são pareados; o filtro só acessa u e y. Seeds de desenvolvimento e teste são disjuntas. Para modelos robustos, todos recebem a mesma classe de ruído, nunca sua realização verdadeira. IC95% principal: bootstrap pareado com 2.000 reamostragens, sem ajuste de multiplicidade.')
T(['Seleção no desenvolvimento','Resultado'],[['M3: ε ∈ {0,005;0,02;0,1}','ε=0,1: 5% fallback; menores ε: 75,6% e 38,8%'],['M4: 32/64/128 passos; h=0,02/0,05/0,1','64 passos, h=0,1: menor CRPS entre candidatos'],['M5: limiares 2 e 6','Ganho não demonstrado; limiar infinito']], [270,241])
P('Regra M3: exigir pelo menos 90% de atualizações convergentes e então minimizar CRPS. M4: menor CRPS. Gatilho: limite superior de IC95% de ΔCRPS agrupado por seed abaixo de zero. Foram congelados antes da campanha teste.')
P('Testes matemáticos: linear-gaussiano, função seno, observação parcial e y=x²+v bimodal. Ablações guardam sensibilidade ao número de passos, largura KDE, viés de momentos, W1 e massas dos modos.','small')

page('04 · Comparação principal: resultado negativo')
FIG('primary')
T(['Cenário','ΔRMSE M4−UKF','IC95% pareado','Vitórias M4'],[[sc,f(primary[sc]['M4']['paired_vs_M0']['delta_rmse_ceb']),str([round(x,5) for x in primary[sc]['M4']['paired_vs_M0']['ci95']]),str(primary[sc]['M4']['paired_vs_M0']['wins'])+'/100'] for sc in primary],[175,110,150,76])
P('M3 ficou próximo do UKF em RMSE no caso gaussiano, mas a cobertura de 90% caiu para 1,7%; sob ambiguidade, 11,2%. Isso mostra por que erro pontual não valida a representação probabilística. M4 cobriu 60,9% e 66,4%, também abaixo do nominal.')
P('UKF e EnKF ficaram próximos; M5 reproduz EnKF porque o gatilho não foi justificado. As 1.200 execuções principais concluíram, sem excluir sementes desfavoráveis. Resultados de MAE de todos os estados, CRPS, energy, ESS e previsão em 1/3/6 passos estão nos JSONL.','small')

page('05 · Ambiguidade térmica e modos posteriores')
FIG('ambiguity')
P('Duas hipóteses admissíveis separadas inicialmente por '+f(obs['initial_CEB_separation'],3)+' kmol/m³ em CEB produzem diferença térmica RMS de '+f(obs['thermal_rms'],4)+' °C, muito menor que σ=1,5 °C. A KL entre suas observações térmicas nominais é '+f(obs['thermal_kl'],6)+'. Isso demonstra ambiguidade local, não dois modos posteriores.')
FIG('posteriors')
P('A sensibilidade térmica escalonada em 81 instantes tem posto local 4/5; o problema com cinco parâmetros adicionais tem posto 5/10 pelo limiar relativo 1e-7. Singularidades: '+', '.join(f'{v:.3g}' for v in obs['singular_values'])+'. São diagnósticos locais, não provas globais.','small')
P('PF 4.096/8.192, mesma seed, prior contínua: picos extras do passo 24 aparecem apenas na menor suavização KDE e desaparecem nas demais. Não foi estabelecida bimodalidade persistente. Já o problema auxiliar conhecido tem dois modos e o M4 os reproduz. W1 em relação ao PF 8.192 está em analysis.json.','small')

page('06 · Ruído hostil e física incerta')
T(['Condição','UKF informado','M4 informado','M4 ingênuo'],[[sc,f(robust[sc]['M0']['rmse'][2],4),f(robust[sc]['M4']['rmse'][2],4),f(naive[sc]['M4']['rmse'][2],4) if sc in naive else 'não aplicável'] for sc in robust],[178,111,111,111])
P('RMSE CEB, 12 sementes por condição. Em outliers, conhecer a mistura melhora M4 frente ao próprio M4 ingênuo; isso é benefício do modelo de ruído, não prova de superioridade do transporte. Student-t e estados latentes não melhoraram universalmente. Coberturas, falhas e contrastes pareados completos permanecem disponíveis.')
FIG('physics')
P('Incertezas são cinco log-fatores: k1, k2, k3, calor reacional e concentração efetiva de etileno na alimentação. Desvios [0,08;0,08;0,08;0,03;0,03]. Filtros fixos desconhecem a realização verdadeira; conjuntos estimam fatores estáticos. Não se inventa UA no modelo com entrada Q ideal.')
P('A estimação conjunta melhorou RMSE de vários métodos, mas não resolve a identificabilidade. O posto local aumentado é deficiente. Estimar A e E separadamente numa faixa térmica estreita não seria sustentado por estes ensaios. A comparação fixa/conjunta também altera a representação da incerteza, não apenas o estimador.')

page('07 · Integração experimental com NMPC')
FIG('control')
T(['Braço','IAE médio xEB·h','Δ vs UKF','IC95%'],[[k,f(r['iae_xEB'],6),f(r['vs_UKF']['mean_delta'],6),str([round(x,6) for x in r['vs_UKF']['ci95']])] for k,r in control['summary'].items()],[127,117,107,160])
P('Dez seeds por braço; mesmos ruídos exógenos, plantas dependentes da política. Horizonte 20 passos, quatro movimentos, SLSQP com derivadas CasADi. Limites fE/fE0=[0,04;2], Q/Q0=[0,6;1,4], variação máxima [0,12;0,08] por amostra e T≤165 °C como limite de estudo.')
P('M4 com cenários usa a média e partículas representativas dos quantis 10/90% de xEB e T. É uma aproximação de incerteza, não controle de risco garantido. Não houve violação térmica nem fallback nos 40 ensaios. O fallback nominal limitado foi exercitado em três ensaios forçados. Nenhum braço demonstrou melhoria clara; todos os IC95% de ΔIAE versus UKF incluem zero.','small')

page('08 · Custo, domínio e verificações')
FIG('scaling')
T(['N','M4 média (ms)','P99 descritivo (ms)','Pico rastreado (MiB)'],[[r['n'],f(r['update_mean_ms'],2),f(r['p99_ms'],2),f(r['peak_traced_MiB'],2)] for r in scaling if r['method']=='M4'],[65,145,155,146])
P('Cinco atualizações após aquecimento por ponto. P95/P99 não são garantias de cauda com essa amostra. tracemalloc mede alocações rastreadas, não RSS total. O maior P99 medido foi '+f(max(r['p99_ms'] for r in scaling),1)+' ms, ante 90.000 ms de amostragem EB. Os números são de Linux/Python '+sys.version.split()[0]+'; não foram validados em notebook Windows.')
T(['Método','Rejeições inicial + dinâmica','Fallbacks','Amostras diagnósticas rejeitadas'],[[m,r['initial_rejected']+r['analysis_or_process_rejected'],r['fallbacks'],r['diagnostic_sample_rejected']] for m,r in analysis['primary_domain_events'].items()],[60,181,80,190])
P('Rejeição condiciona a distribuição; fallback troca a análise inteira por PF. Nenhuma concentração negativa foi aceita silenciosamente. Intervalos UKF são analíticos; seus scores de ensemble usam amostras gaussianas condicionadas. Essa diferença é documentada.','small')

page('09 · Reprodução, limites e publicação')
P('<b>Verificação:</b> 35 testes passaram, incluindo física, equilíbrio, integração, conservação, domínio, UKF recuperado, linear-gaussiano, posterior bimodal, causalidade, Sinkhorn, momentos, reamostragem, fallback, exportação e API. Testes estocásticos usam sementes e tolerâncias explícitas; não constituem prova de convergência para qualquer distribuição.')
P('A interface foi verificada em navegador: sete painéis, projeção 3D, CSV, tela estreita, arquivo offline e nova execução N=64/8 passos. Os gráficos usam dados reais. O botão de simulação precisa do servidor local; o HTML isolado permite apenas exploração dos dados entregues.')
P('<b>Uso:</b> extraia o ZIP; execute INICIAR_LAB.bat no Windows com Python 3.11+ x64. VER_RESULTADOS.bat abre o HTML offline. TESTAR.bat verifica o código; REPRODUZIR.bat cria uma cópia isolada para repetir as campanhas. Fontes em eblab/, dados em results/, equações e parâmetros em configs/. O README contém comandos portáveis.')
P('<b>Limites da contribuição:</b> modelo térmico herdado com ressalvas; 1,5 h por trajetória; N=128 na inferência principal; um único processo e ponto operacional; referência posterior numérica em uma seed; incertezas paramétricas estáticas e idealização do atuador Q. Não se validaram dados industriais, termodinâmica completa, robustez global do controlador ou ganhos em outros regimes.')
P('Perguntas sustentáveis para pesquisa','h2')
P('1. Quanto da inferência de CEB vem das medições, versus dissipação de inventário e prior? A ablação sem medições tem RMSE muito semelhante: 0,06949 versus 0,06992 e 0,15462 versus 0,15582. Isso não significa que T seja inútil para estimar T.')
P('2. Correção de covariância/segunda ordem e atualizações condicionadas por ESS evitam o colapso de M3 sem destruir modos? Isso deve ser avaliado em nova partição teste, não ajustado retrospectivamente.')
P('3. Com termodinâmica de referência consistente, excitação térmica e medições químicas esparsas, pontes melhoram calibração e decisões? A auditoria de h/T é pré-requisito para uma alegação física mais ampla.')
P('Fontes e rastreabilidade','h2')
P('ProcessLab: github.com/walteryanko/yanko-process-lab, commit 16aaafb...<br/>Luyben (2011): doi.org/10.1002/aic.12289<br/>EnSBF: arxiv.org/abs/2512.18928v1; arxiv.org/html/2512.18928v4<br/>Reich (2013): doi.org/10.1137/130907367<br/>Cuturi (2013): arxiv.org/abs/1306.0895','small')
P('A recuperação preservou CSV e NPZ completos; três linhas ausentes do journal sem medições foram reconstruídas por execução determinística e comparação exata. Auditou-se a correspondência de todos os RMSE com os NPZ. Todos os resultados, inclusive negativos, rejeições e fallbacks, permanecem no pacote.','small')

def footer(c,doc):
    w,h=A4;c.saveState();c.setStrokeColor(HexColor('#c9dcd2'));c.line(42,41,w-42,41);c.setFont('YCS',7.5);c.setFillColor(muted)
    c.drawString(42,27,'YCS ProcessLab · Etilbenzeno · Pesquisa em simulação · 22/10/2026');c.drawRightString(w-42,27,str(doc.page));c.restoreState()
pdf=out/'YCS_Ethylbenzene_Relatorio_Cientifico.pdf'
SimpleDocTemplate(str(pdf),pagesize=A4,rightMargin=42,leftMargin=42,topMargin=40,bottomMargin=53,title='YCS Ethylbenzene Schrödinger-KF Laboratory',author='Yanko Creative Studio | ProcessLab').build(story,onFirstPage=footer,onLaterPages=footer)
(out/'experimental.md').write_text('\n\n'.join(md),encoding='utf-8')
print(pdf)
