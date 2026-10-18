"""Generate figures, six Markdown reports and a single typeset PDF from recorded data."""
from pathlib import Path
import json,csv,sys,re,math,argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from premonition.io import save
parser=argparse.ArgumentParser();parser.add_argument('--results',default=str(ROOT/'results'));parser.add_argument('--reports',default=str(ROOT/'reports'));args=parser.parse_args()
R=Path(args.results);O=Path(args.reports);G=O/'figures';G.mkdir(parents=True,exist_ok=True)
def read(p):return json.loads((R/p).read_text())
def rows(p):return list(csv.DictReader((R/p).open()))
def num(v):return 'n/a' if v is None else f'{v:.6g}' if isinstance(v,(float,int)) else str(v)
def mdtable(records,cols):
 return '| '+' | '.join(l for k,l in cols)+' |\n| '+' | '.join('---' for _ in cols)+' |\n'+'\n'.join('| '+' | '.join(num(r.get(k)) for k,l in cols)+' |' for r in records)
COL=['#047c72','#3466a5','#a7791d','#7556aa','#c44756','#71818c','#8d8430','#308991']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.2,'figure.dpi':140})
MAP=read('A/map.json');critical=read('A/critical_points.json');A=read('A/audit.json');phys=read('physical_audit.json');B=read('B/summary.json');bx=read('B/execution.json');bt=read('B/traces.json');ds=read('CD/summary.json');dp=read('CD/probability.json');dpaired=read('CD/paired.json');cs=read('EF/summary.json');cp=read('EF/paired.json');cx=read('EF/execution.json');unc=read('CD/uncertainty_and_pairs.json')

def figsave(name):
 plt.tight_layout();plt.savefig(G/(name+'.png'),dpi=180,bbox_inches='tight');plt.savefig(G/(name+'.pdf'),bbox_inches='tight');plt.close()
fig,axs=plt.subplots(2,2,figsize=(10,7))
for ax,key in zip(axs.flat,['mw','T0','FA','UA']):
 rr=MAP[key]['rows']
 for stable,col,lab in [(True,COL[0],'Estável'),(False,COL[4],'Instável')]:
  ax.plot([r['parameter'] for r in rr],[r['T'] if r['stable']==stable else np.nan for r in rr],color=col,label=lab)
 for f in [f for f in critical if f['axis']==key and f['type']=='saddle_node']:ax.scatter([f['parameter']],[f['T']],marker='o',s=25,c='black',zorder=5)
 ax.axhline(344,color='gray',ls=':',lw=1);ax.set(xlabel=key,ylabel='T de equilíbrio [K]');ax.legend(fontsize=7)
figsave('01_bifurcations')
fig,ax=plt.subplots(figsize=(8,4));rr=rows('B/recovery.csv');ax.plot([float(r['T0']) for r in rr],[float(r['expected_recovery']) for r in rr],label='−α do Jacobiano');ax.scatter([float(r['T0']) for r in rr],[float(r['fitted_recovery']) for r in rr],s=18,label='Retorno perturbado (ajuste)');ax.set(xlabel='Temperatura de alimentação [K]',ylabel='Taxa de recuperação [h⁻¹]');ax.legend();figsave('02_recovery')
fig,axs=plt.subplots(2,2,figsize=(10,6.8));e=bt[0]
for ax,key,title in zip(axs.flat,['T','ac1','variance','alpha'],['Temperatura [K]','Autocorrelação lag-1','Variância [K²]','α reativo estimado [h⁻¹]']):
 ax.plot([r['t_h']*60 for r in e['rows']],[r[key] for r in e['rows']],lw=1,color=COL[0]);ax.set(xlabel='Tempo [min]',ylabel=title)
 if e['event'] is not None:ax.axvline((e['event']+1)*.9,c=COL[4],ls='--',label='Perda do equilíbrio médio')
 if e['transition'] is not None:ax.axvline((e['transition']+1)*.9,c=COL[1],ls=':',label='Mudança de ramo observada')
axs[0,0].legend(fontsize=7);figsave('03_ews_trace')
fig,axs=plt.subplots(1,2,figsize=(10,4));names=list(ds['test'])
for ax,metric,title in zip(axs,['recall','false_alarms_per_h'],['Recall por evento','Falsos inícios de alerta / h']):
 x=np.arange(len(names));ax.bar(x-.18,[ds['test'][n][metric] or 0 for n in names],width=.36,label='Teste',color=COL[0]);ax.bar(x+.18,[ds['falsification'][n][metric] or 0 for n in names],width=.36,label='Adversarial',color=COL[4]);ax.set_xticks(x,names,rotation=25,ha='right');ax.set_ylabel(title);ax.legend(fontsize=8)
figsave('04_detection')
fig,axs=plt.subplots(1,2,figsize=(10,4))
for ax,split in zip(axs,['test','falsification']):
 ax.plot([0,1],[0,1],'k:',lw=1)
 for i,(name,v) in enumerate(dp[split].items()):ax.plot([r['pred'] for r in v['reliability']],[r['observed'] for r in v['reliability']],'.-',label=name,color=COL[i])
 ax.set(xlabel='Probabilidade prevista',ylabel='Frequência observada',title=split,xlim=(0,1),ylim=(0,1));ax.legend(fontsize=8)
figsave('05_calibration')
fig,axs=plt.subplots(3,2,figsize=(10,9));seed=cx['seeds'][min(5,len(cx['seeds'])-1)]
tr=[]
for mode in ['C0','C1','C4','conservative','oracle_offline']:
 path=R/'EF/episodes'/f'{seed}_{mode}.json';tr.append((mode,json.loads(path.read_text())['rows']))
for ax,key,ylabel in zip(axs.flat,['T','CC','mw','score','violation','cost_cumulative'],['T [K]','CC [kmol/m³]','ṁw [kmol/h]','Probabilidade térmica','Excesso térmico [K]','Custo nominal acumulado']):
 for i,(mode,rr) in enumerate(tr):ax.plot([r['t_h']*60 for r in rr],[r[key] if r[key] is not None else np.nan for r in rr],label=mode,color=COL[i],lw=1)
 ax.set(xlabel='Tempo [min]',ylabel=ylabel)
 if key=='T':ax.axhline(344,color='gray',ls=':')
axs[0,0].legend(fontsize=7);figsave('06_controller_arena')
fig,axs=plt.subplots(1,3,figsize=(10.5,3.6))
for ax,metric in zip(axs,['IAE','violation_Kh','economic_proxy']):
 rr=[r for r in cp if r['A']=='C0' and r['B']!='oracle_offline' and r['metric']==metric];x=[r['mean_difference'] for r in rr];low=[v-r['ci95'][0] for v,r in zip(x,rr)];high=[r['ci95'][1]-v for v,r in zip(x,rr)];ax.errorbar(x,np.arange(len(rr)),xerr=[low,high],fmt='o',capsize=3,color=COL[1]);ax.set_yticks(np.arange(len(rr)),[r['B'] for r in rr],fontsize=7);ax.axvline(0,c='gray',ls=':');ax.set_title(metric);ax.set_xlabel('Diferença em relação a C0')
figsave('07_paired_effects')
# Failure example chosen deterministically, not by visual drama.
fails=read('CD/failure_cases.json');seedfail=fails[0]['seed'];z=np.load(R/'CD'/('falsification.npz' if seedfail>=400000 else 'test.npz'));j=list(z['seed']).index(seedfail);namesz=list(z['detector_names']);fig,axs=plt.subplots(2,1,figsize=(8.5,5.5),sharex=True);tt=(np.arange(z['truth'].shape[1])+1)*.9;axs[0].plot(tt,z['truth'][j,:,4],label='T verdadeira');axs[0].plot(tt,z['y'][j,:,0],alpha=.5,label='T medida');axs[0].axhline(344,c=COL[4],ls=':');axs[0].set_ylabel('T [K]');axs[0].legend();axs[1].plot(tt,z['scores'][j,namesz.index('D5')],c=COL[4]);axs[1].axhline(read('CD/thresholds.json')['D5'],ls=':',c='black');axs[1].set(xlabel='Tempo [min]',ylabel='Probabilidade D5',title=f'Caso de falsificação / semente {seedfail}');figsave('08_failure')
# Sampling study from existing independent PG bifurcation records, no retraining.
from premonition.ews import indicators
sampling=[]
for stride in [1,3,6]:
 for e in bt[:4]:
  vals=[r['yT'] for r in e['rows']][::stride];d=indicators(vals[-64:],dt=.015*stride);sampling.append(dict(seed=e['seed'],stride=stride,sample_seconds=54*stride,window_hours=len(vals[-64:])*.015*stride,**d))
save(R/'B/sampling_pilot.json',sampling)

REPORTS=[]
def section(filename,title,paragraphs,figures=()):
 text='# '+title+'\n\n'+'\n\n'.join(paragraphs)+'\n\n'+''.join(f'![{name}](figures/{name}.png)\n\n' for name in figures)
 (O/filename).write_text(text.rstrip()+'\n',encoding='utf-8');REPORTS.append((title,paragraphs,list(figures)))
section('01_Auditoria_Fisica.md','1. Auditoria física e matemática',[
'YCS Premonition-MPC Lab v1.0. Referência do projeto: 18/10/2026. Pesquisa exclusivamente computacional. O modelo primário é a transformação SI do arquivo MATLAB modeloCT.m recuperado do ProcessLab; a tabela da dissertação e a variante calibrada são mantidas separadas.',
'Fontes: repositório walteryanko/yanko-process-lab; main f4444d4c238291b8633743930249ee387ad94541; histórico b55a46cd182c70100b50ff5e6c98ba82ed96a5a8; referência independente 88c40e65204fa6aa5bed02cc64fb15be79a53bb1. A dissertação de Brandão (UFCG, 2019) foi recuperada e consultada nas equações 33–55 e seções 4.1.1.5, 4.3.2.3 e 5.3.2.3. Seu PDF não é redistribuído neste pacote.',
'Convenções: x=[CA,CB,CC,CM,T,Tt]; u=[FA,FB,FM,mw,T0,Ta]. Concentrações em kmol/m³, temperaturas em K, vazões em kmol/h, tempo em h. Δt=0,015 h (54 s). O modelo assume fase líquida e volume constante. Extrapolações acima do domínio físico de fase não constituem previsões industriais.',
'v=FA/ρA+FB/ρB+FM/ρM; D=v/V; k=k0 exp[−E/(R(T+δ))]; r=k CA. Balanços: dCA/dt=(FA−vCA)/V−r; dCB/dt=(FB−vCB)/V−r; dCC/dt=r−DCC; dCM/dt=(FM−vCM)/V.',
'Q=mw CpB (Ta−T)[1−exp(−UA/(mw CpB))]; Ccap=V Σ Ci Cpi; Fcp=FA CpA+FB CpB+FM CpM. dT/dt=[Q−Fcp(T−T0)+H r V]/Ccap; dTt/dt=[mw CpB(Ta−Tt)−Q]/(ρB Vt CpB). A assimetria é preservada: Tt não realimenta Q. Alterar isso criaria outro modelo.',
mdtable([dict(name=v['name'],heat=v['heat'],R=v['R'],offset=v['arrhenius_offset_K'],T=v['roots'][0][4]) for v in phys['variants']],[('name','Variante'),('heat','H kJ/kmol'),('R','R kJ/(kmol K)'),('offset','δ K'),('T','T nominal K')]),
mdtable([dict(name=list(A['parameters'])[i],value=list(A['parameters'].values())[i],name2=list(A['parameters'])[i+1] if i+1<len(A['parameters']) else '',value2=list(A['parameters'].values())[i+1] if i+1<len(A['parameters']) else '') for i in range(0,len(A['parameters']),2)],[('name','Parâmetro'),('value','Valor SI'),('name2','Parâmetro'),('value2','Valor SI')]),
'δ=0,183333333 K preserva T_F+460. O R convertido é 8,3191716, não 8,314. O calor de reação histórico é 83.736 kJ/kmol, enquanto a tabela usa 91.556,9. Nenhum ajuste foi aplicado ao primário. O nominal calculado é '+', '.join(num(x) for x in A['base'])+'.',
'344 K é o limite de estudo mantido no ProcessLab. A conversão exata de 160 °F seria 344,261111 K; essa diferença é explicitada, não ocultada. A dissertação associa 355,4 K à restrição prática por possibilidade de evaporação do óxido de propileno. Esses valores não são pontos de bifurcação nem certificação de segurança.',
'O UKF conserva α=0,001, β=2, κ=0, predição Euler e Q/R extraídos do Simulink, convertidos para SI. P0 e estado inicial são próprios da campanha em torno do equilíbrio, não uma reprodução da partida. A atualização linear T/Tt usa Joseph e regularização SPD. Ablações RK4, adaptativa e EKF foram executadas com as mesmas trajetórias.',
'O C0 preserva P=57, M=6, Qe=0,8, RΔu=0,2 e a busca coordenada do controller.ts público. Há substituição explícita da variante tabelada pelo primário histórico e um guard comum. Não se declara equivalência binária ao fmincon/MATLAB. O fonte arquivado de NMPC_Fmincon.m é referência, com o aviso de direitos autorais preservado.',
'Oracle-KF v0.1, NAKE, Schrödinger-KF e os checkpoints Quantum/Multiverse foram auditados. Usam família tabelada/calibrada ou modelos treinados incompatíveis com o primário histórico; não foram transplantados. RSI aponta para a pesquisa beyond na fonte recuperada. Não se atribuem ganhos a esses métodos nesta entrega.',
'Testes: balanços e invariantes; comparação com pg_reference.py; RK4 versus DOP853; Jacobiano analítico versus diferenças centrais; espectro completo versus forma reduzida; guard, fallback, causalidade, separação de sementes e JSON estrito. O resultado automatizado completo está em results/tests_final.log e results/tests.xml.'
])
section('02_Mapa_Estabilidade.md','2. Mapa de estabilidade',[
'A busca usa redução estacionária exata dos balanços materiais e energético. CA=FA/(v+Vk), CC=VkCA/v, CB=FB/v−CC, CM=FM/v e Tt=Ta+(T−Ta)[1−exp(−UA/(mwCpB))]. O problema escalar de calor é equivalente aos seis balanços no equilíbrio.',
'Continuação: tangente pelo núcleo do Jacobiano escalado, preditor em pseudo-arco e corretor Newton com hiperplano. Passo nominal 0,025 em coordenadas escaladas; falha de correção reduz o passo pela metade. Uma varredura independente em 121 valores por eixo verifica raízes adicionais. Intervalo térmico matemático: 250–430 K. Foram computados '+str(A['scan_points'])+' registros na malha de um parâmetro e '+str(A['joint_equilibria'])+' equilíbrios em 400 combinações aleatórias. A malha conjunta é exploratória.',
mdtable([dict(axis=k,lo=v['range'][0],hi=v['range'][1],points=len(v['rows']),failures=len(v['failures'])) for k,v in MAP.items()],[('axis','Eixo'),('lo','Mínimo'),('hi','Máximo'),('points','Pontos no ramo'),('failures','Correções rejeitadas')]),
'As faixas são domínios de investigação computacional. Não equivalem a faixas operacionais aprovadas. Foram refinadas '+str(len([x for x in critical if x['type']=='saddle_node']))+' dobras em famílias de um parâmetro. Essas ocorrências não são necessariamente bifurcações distintas no espaço multidimensional.',
mdtable([x for x in critical if x['axis'] in ['mw','T0','FA']],[('axis','Eixo'),('parameter','Parâmetro na dobra'),('T','T K'),('residual','Resíduo'),('second_derivative','∂²f/∂T²')]),
'As dobras satisfazem f=0 e ∂f/∂T=0; derivadas em relação ao parâmetro e segunda derivada térmica são não nulas. Candidatos gerados por troca de autovalor dominante foram refinados antes da classificação. Nenhum Hopf foi confirmado nessa triagem; algumas sinalizações grosseiras eram passagem por dobra seguida de um par complexo estável. Não há exclusão global de Hopf fora das regiões varridas.',
'No nominal, α=−5,3832686 h⁻¹ e há um par −5,3832686 ± 8,9581585i h⁻¹. A baixa vazão de resfriamento, o modo desacoplado de Tt tem λ=−mw/(ρB Vt), próximo de zero mesmo quando a reação permanece fortemente estável. Usar apenas α completo criaria uma interpretação enganosa.',
'Validação temporal: perturbações nos três equilíbrios encontrados a T0=295 K confirmam restauração local nos ramos extremos e afastamento do ramo intermediário. results/A/local_validation.json contém as trajetórias. Uma seção da bacia foi amostrada em 31 condições iniciais térmicas e integrada por seis horas; não é uma descrição completa da bacia em seis dimensões.',
'Observabilidade: a matriz de saídas propagadas por 57 passos, escalada pelas unidades de estado, tem posto 3/6 no nominal. A capacidade calorífica torna algumas direções observáveis fora do equilíbrio, mas persistem limitações estruturais. Variância pequena do UKF não elimina incerteza estrutural ou de parâmetros.'
],['01_bifurcations'])
section('03_Early_Warning.md','3. Early Warning Signals e detecção',[
'A hipótese foi separada em dois alvos: B usa desaparecimento do equilíbrio frio em T0=295,5196437 K; C/D usa primeiro cruzamento de T>344 K nos próximos 20 passos. Um modelo de probabilidade de bifurcação foi treinado separadamente, com horizonte de 80 passos. A janela de antecedência térmica é 18 min; a de bifurcação, 72 min.',
'Na campanha B, 80 trajetórias de treino, 40 de calibração e 100 de teste usam apenas medições térmicas ruidosas, entrada corrente e UKF causal. A rampa média progride de 294,8 K até além da dobra, ou para antes dela em controles negativos. Ruído de processo atua na alimentação. A data do evento é a perda do equilíbrio da família congelada nas entradas médias; a transição observada é registrada separadamente em T>T_dobra+3 K.',
mdtable([dict(name=k,**v) for k,v in B.items()],[('name','Detector B'),('events','Eventos'),('detected','Antecipados'),('recall','Recall'),('false_alarms_per_h','Falsos/h'),('lead_median_min','Antecedência min')]),
'No teste B houve '+str(bx['fold_events'])+' perdas de equilíbrio e '+str(bx['observed_transitions'])+' mudanças de ramo observadas; '+str(bx['thermal_events_in_test'])+' episódios cruzaram 344 K. Logo, o êxito do detector espectral nessa campanha não representa previsão de perigo térmico. O modelo e a alimentação corrente são conhecidos; não é previsão apenas por uma temperatura isolada.',
'EWS: regressão linear removida em janela causal; AR(1), variância residual, assimetria, energia de baixa frequência e −ln(φ)/Δt para 0<φ<1. Fora desse intervalo, a taxa é indefinida. O EWS térmico D2 usa escore φ+0,12 ln(variância). O detector de modelo usa a abscissa reativa e considera estado quase estacionário no alvo térmico; valores fora do equilíbrio são indicadores congelados, não certificados de estabilidade.',
'D4: regressão logística padronizada. D5: 55 árvores de boosting com profundidade 2, taxa 0,06, folhas com pelo menos 60 amostras; calibração sigmoidal em trajetórias separadas. As probabilidades são condicionadas à mistura sintética e à política geradora. Não são probabilidades de acidente. Modelos são JSON legíveis, sem pickle.',
'Para C/D: 160 trajetórias de treino, 80 de calibração, 100 de teste final e 100 adversariais. Modelos e limiares foram congelados antes de usar as sementes finais 300000–300099 e 400000–400099. Sementes do piloto e da avaliação exploratória foram excluídas da avaliação final. Nenhum limiar foi reajustado após o teste final.',
'Critério de alerta: somente o início de um alerta antes do evento, dentro do horizonte, recebe crédito. Alarmes persistentes iniciados antes da janela não ganham crédito retroativo. Os últimos horizontes incompletos, o período após o primeiro evento e a inicialização de 31 amostras são censurados. Precisão usa inícios de alerta; recall usa eventos por trajetória. Há registro separado de alertas redundantes.',
mdtable([dict(name=k,**v) for k,v in ds['test'].items()],[('name','Detector térmico'),('events','Eventos'),('detected','Antecipados'),('precision','Precisão'),('recall','Recall'),('false_alarms_per_h','Falsos/h'),('lead_median_min','Lead min')]),
mdtable([dict(split=split,name=name,**v) for split,models in dp.items() for name,v in models.items()],[('split','Conjunto'),('name','Modelo'),('brier','Brier'),('ece','ECE'),('average_precision','AP'),('prevalence','Prevalência por amostra')]),
'As curvas de calibração reportam frequências empíricas, Brier, ECE e precision-recall. Os intervalos de recall são binomiais exatos. Intervalos de efeitos pareados são calculados por reamostragem de trajetórias, não pela falsa independência de pontos temporais.',
'Sensibilidade B: janelas 24/64/128, ruído dobrado, ruído colorido, rampas rápidas/lentas e resfriamento oscilante, 12 trajetórias por condição. As rampas lentas têm duração ampliada para atingir o mesmo ponto final. Na oscilação, a dobra é recalculada para a vazão corrente. O estudo adicional de subamostragem é um piloto descritivo de quatro trajetórias e não valida desempenho estatístico.'
],['02_recovery','03_ews_trace','04_detection','05_calibration'])
section('04_Premonition_MPC.md','4. Premonition-MPC e controle',[
'Arquitetura operacional: pacote causal → detector → supervisor com confirmação por dois passos → NMPC → guard físico independente → fallback. O avaliador mantém estados verdadeiros, parâmetros ocultos e perturbações futuros fora desse contrato. A referência oracle_offline é a única exceção deliberada e identificada.',
'J0=Σ(k=1..57)0,8[(CC_sp−CC_hat_k)/CC_sp]² + Σ(k=1..6)0,2[(mw_k−mw_(k−1))/mw0]². Todos os controladores usam 22,7≤mw≤1366,2 kmol/h, o mesmo integrador e a mesma busca coordenada determinística. A soma de violações previstas acima de 344 K tem prioridade lexicográfica sobre o custo.',
'R_T=0,02 Σ[max(0,T_hat_k−(344−m))]². C1 usa m=2 K; C3/C4 usam m=1+2I_supervisor K; o conservador fixo usa m=4 K. R_α=0,02 Σ[max(0,α_reativo+1)]² somente onde ||f/S||²<1. C2 adiciona R_α; C4 adiciona R_T+R_α+10⁻⁴Σ(mw/umax)⁴[1+min(σT,3)]. As constantes são escolhas do protocolo, não leis universais nem margens formais de robustez.',
'C3 usa D4; C4 usa D5. A ablação C4_noEWS usa a mesma arquitetura probabilística sem atributos EWS. O supervisor também reage a previsão física próxima do limite. D5 foi calibrado sob a distribuição de detecção, não sob todas as políticas em malha fechada. Essa mudança de distribuição é uma limitação central.',
'O guard verifica a sequência inteira. Se a política modificada falha e a nominal é viável, a nominal é usada. Se não há sequência aceita, aplica-se resfriamento máximo e a inviabilidade permanece registrada. Não há garantia formal de recuperação; a vazão real pode ser limitada por saturação da planta virtual. Falha do detector não desabilita essas verificações.',
'Experimentos E/F: '+str(cx['pairs'])+' sementes independentes; '+str(cx['rollouts'])+' execuções, cada uma com 120 decisões (1,8 h). Todas as políticas compartilham estado inicial, ruído, parâmetros e distúrbios por semente. Há mudanças de setpoint, perda de UA, perturbações de alimentação, saturação, deriva, ruído colorido e oscilação.',
mdtable([dict(name=k,**v) for k,v in cs.items()],[('name','Controle'),('n','Pares'),('events','Eventos térmicos'),('IAE','IAE médio'),('violation_Kh','Violação K·h'),('production_kmol','Produção kmol'),('economic_proxy','Proxy econômico')]),
'IAE=Σ|CC−CC_sp|Δt; RMSE químico usa estado verdadeiro e estimativa causal no mesmo instante. Produção=Σv CC Δt; esforço=Σ(Δmw/mw0)². O proxy econômico é produção−0,0005×refrigerante, em kmol-equivalentes arbitrários. Não é lucro nem resultado monetário.',
'O gráfico de efeitos pareados apresenta somente políticas operacionais para preservar a resolução da escala; a referência offline permanece nas tabelas e na arena. A referência offline recebe estado verdadeiro, parâmetros, perturbações e capacidade futura do atuador. Ainda usa um horizonte finito e um otimizador local com orçamento fixo. Portanto, não é limite superior de desempenho nem solução ótima de controle com futuro perfeito. Uma decisão excessivamente conservadora pode conduzir a outro ramo de equilíbrio e prejudicar a produção.',
'Tempo do núcleo de controle (supervisor, NMPC e guard) medido por perf_counter; a métrica mean_ms exclui a atualização do UKF e dos atributos do detector. A duração total de E/F foi '+num(cx['seconds'])+' s. Medidas no ambiente Linux de execução; não é benchmark do notebook do usuário. A primeira compilação JIT pode contaminar a primeira medida. Falhas numéricas e passos inviáveis são contados separadamente; ausência de falha numérica não implica estacionariedade ou otimalidade da solução.'
],['06_controller_arena','07_paired_effects'])
mainpairs=[dict(metric=r['metric'],delta=r['mean_difference'],lo=r['ci95'][0],hi=r['ci95'][1]) for r in cp if r['A']=='C0' and r['B']=='C4']
section('05_Resultados_Falsificacao.md','5. Resultados e falsificação',[
'Os resultados sustentam a existência de múltiplos equilíbrios e dobras no modelo PG histórico. Também mostram que prever perda de um equilíbrio e prever ultrapassagem térmica são tarefas diferentes. O detector de modelo antecipou transições da campanha B; o EWS estatístico simples falhou nesse teste mesmo havendo desaceleração observável em perturbações controladas.',
mdtable([dict(name=k,**v) for k,v in ds['falsification'].items()],[('name','Detector sob ruído adversarial'),('events','Eventos'),('detected','Antecipados'),('false_onsets','Falsos alertas'),('false_alarms_per_h','Falsos/h'),('lead_median_min','Lead min')]),
'Contribuição incremental dos EWS: os intervalos pareados do Brier completo menos sem EWS são '+str(dpaired['test_brier_full_minus_noEWS']['ci95'])+' no teste e '+str(dpaired['falsification_brier_full_minus_noEWS']['ci95'])+' no adversarial. A decisão deve considerar esses intervalos e os falsos alertas; um valor médio isolado não demonstra superioridade.',
mdtable(mainpairs,[('metric','C4 menos C0'),('delta','Diferença média'),('lo','IC95 inferior'),('hi','IC95 superior')]),
mdtable(read('EF/counterfactual.json'),[('controller','Política'),('avoided','Eventos evitados'),('caused','Eventos causados'),('n','Pares'),('nominal_no_event_pairs','C0 sem evento'),('potentially_unnecessary_actions','Ações nesses pares')]),
'As diferenças em intensidade de violação, IAE e proxy econômico devem ser lidas conjuntamente. Um IC bootstrap [0,0] quando não há discordância observada não prova equivalência. Para C4, o intervalo binomial exato da frequência de discordância é '+str(next(r['discordance_exact_ci'] for r in read('EF/counterfactual.json') if r['controller']=='C4'))+'.',

'Os intervalos são exploratórios, obtidos com 2.000 reamostragens pareadas; não foram corrigidos para multiplicidade. Eventos raros são apresentados com seus denominadores. Desempenho no conjunto sintético não estima frequências de falha industrial.',
'Covariância e observabilidade: a cobertura média de 95% para CC no teste final foi '+num(unc['test']['coverage95_mean'])+'; no adversarial, '+num(unc['falsification']['coverage95_mean'])+'. Cobertura baixa denuncia excesso de confiança do filtro sob erro estrutural. results/CD/uncertainty_and_pairs.json contém estratificação por erro químico e antecedência condicionada a ambos detectarem.',
'Intervenções em pares nos quais C0 não teve evento são um indicador de custo preventivo potencialmente desnecessário. Não se afirma que seriam desnecessárias em qualquer planta ou horizonte. O controlador C4 pode alterar o evento que o classificador pretendia prever; isso exige distinguir risco anterior à ação e desfecho após a ação.',
'Falhas e resultados negativos preservados: D2 pode confundir ruído colorido com resiliência; D3 pode falhar para eventos térmicos sem bifurcação; probabilidades podem perder calibração sob nova política; limitador físico não vence falta de capacidade de resfriamento; a referência offline pode perder desempenho por efeitos não convexos e orçamento local.',
'Casos individuais estão em results/CD/failure_cases.json e no Failure Explorer. O arquivo dead_detector.json documenta uma probabilidade deliberadamente inválida sem desativação do guard. Todos os episódios de controle, inclusive falhas, são preservados. A interface identifica contrafactuais como simulações pareadas.'
],['08_failure'])
refs=[
'[1] Brandão, W. Y. A. (2019). Uso de observadores de estado aplicados no controle inferencial preditivo de processos não lineares. Dissertação, UFCG. Fonte primária recuperada e conferida; equações implementadas rastreáveis no repositório https://github.com/walteryanko/yanko-process-lab .',
'[2] Scheffer et al. (2009). Early-warning signals for critical transitions. Nature 461, 53–59. https://doi.org/10.1038/nature08227 . Fundamenta a associação entre certos mecanismos de perda de estabilidade e indicadores antecipativos; não garante eficácia universal.',
'[3] Boettiger & Hastings (2012). Quantifying limits to detection of early warning for critical transitions. J. R. Soc. Interface. https://doi.org/10.1098/rsif.2012.0125 . Motiva quantificar falsos positivos e negativos, em vez de selecionar apenas séries que sofreram transição.',
'[4] Boettiger & Hastings. Early Warning Signals and the Prosecutor’s Fallacy. https://arxiv.org/abs/1210.1204 . A seleção retrospectiva de transições pode inflar evidência de EWS; foram incluídos controles negativos e sementes independentes.',
'[5] Radhakrishnan et al. (2025). Early warnings are too late when parameters change rapidly. Scientific Reports 15, 20256. https://doi.org/10.1038/s41598-025-06525-5 ; preprint dos autores: https://arxiv.org/abs/2408.07296 . O estudo termoacústico mostra limitações sob variação rápida. Sua transferência ao PG é uma hipótese, não um resultado já comprovado pela fonte.',
'[6] Use of bifurcation analysis for identification of a safe CSTR operability. https://www.sciencedirect.com/science/article/abs/pii/S0950423004000713 . O resumo trata de hidrólise de óxido de propileno com reações consecutivas; esse modelo não é idêntico ao PG de seis estados utilizado aqui.',
'[7] Heinlein, Subramanian & Lucia (2025). Robust Model Predictive Control Exploiting Monotonicity Properties. IEEE TAC, DOI https://doi.org/10.1109/TAC.2025.3558137 ; https://arxiv.org/abs/2408.17348 . Estuda conjuntos alcançáveis e conservadorismo em sistemas não lineares, incluindo cascata de reatores. O presente laboratório não implementa nem reivindica essas garantias robustas.',
'[8] Köhler et al. A computationally efficient robust model predictive control framework for uncertain nonlinear systems. Fonte dos autores: https://www.ist.uni-stuttgart.de/de/institut/team/PDFs_MA-Seiten/JK/Robust_Nonlin.pdf . Construção de tubos robustos exige hipóteses e verificações adicionais à penalização de risco adotada neste laboratório.',
'[9] Ma (2026). Early warning of noise-induced critical transitions in two-dimensional ecosystems. Chaos 36, 023121. https://pubs.aip.org/aip/cha/article/36/2/023121/3379059/Early-warning-of-noise-induced-critical . Referência recente consultada pelo resumo; não estabelece capacidade preditiva para este CSTR.',
'[10] Sanders & Bastiaansen (2025), preprint. Early warning of critical transitions: distinguishing tipping points from Turing destabilizations. https://arxiv.org/abs/2510.01959 . Reforça distinguir o mecanismo de transição; sistemas espacialmente distribuídos não são equivalentes ao CSTR concentrado.'
]
section('06_Potencial_Publicacao.md','6. Potencial de publicação e referências',[
'Conclusão científica: é possível perceber perda de estabilidade antes de um alarme térmico neste modelo e neste protocolo, principalmente quando a física, a entrada corrente e o ramo operacional são conhecidos. Isso não valida uma previsão universal de catástrofes por EWS nem demonstra superioridade geral do controlador proposto.',
'Contribuição possível: benchmark auditável de bifurcação versus excursão térmica, com a assimetria histórica do trocador preservada, análise de observabilidade, separação causal, calibração independente e ablações. O resultado negativo sobre informação incremental de EWS é publicável como questão científica, se confrontado com literatura e baselines adicionais.',
'O pacote é um laboratório de pesquisa v1.0, não um manuscrito pronto para aceitação. Antes de submissão: revisão independente das conversões históricas; análise de sensibilidade aos pesos e horizontes em protocolo pré-definido; controladores robustos e SQP de maior orçamento; validação cruzada por família de perturbação; caracterização mais ampla de bacias e fronteiras de viabilidade; validação experimental se houver infraestrutura apropriada.',
'Não se confirma Hopf do PG nesta entrega. Um par imaginário em benchmark matemático valida a rotina básica, mas não substitui uma classificação local completa no reator. A continuação, a varredura e os testes de retorno tratam regiões delimitadas, sem certificação global.',
'O controle econômico usa um proxy declarado. Uma análise econômica real exigiria preços, capacidade de equipamento, especificação de produto e custos de transição. Nenhum valor monetário foi inferido.',
'Fontes verificáveis consultadas em outubro de 2026. Revisão focalizada, não sistemática. Distinguem-se artigos publicados, preprints, resumos acessíveis e resultados próprios.',*refs
])
# Aggregate printable PDF with a clean report style.
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Table,TableStyle,Image,KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT
font=str(Path(matplotlib.get_data_path())/'fonts/ttf/DejaVuSans.ttf');bold=str(Path(matplotlib.get_data_path())/'fonts/ttf/DejaVuSans-Bold.ttf')
pdfmetrics.registerFont(TTFont('DV',font));pdfmetrics.registerFont(TTFont('DVB',bold))
styles=getSampleStyleSheet();styles.add(ParagraphStyle(name='BodyX',fontName='DV',fontSize=9,leading=13,spaceAfter=9,textColor=colors.HexColor('#203442')));styles.add(ParagraphStyle(name='TitleX',fontName='DVB',fontSize=24,leading=29,spaceAfter=20,textColor=colors.HexColor('#0b4451')));styles.add(ParagraphStyle(name='HeadX',fontName='DVB',fontSize=16,leading=22,spaceAfter=15,textColor=colors.HexColor('#0b4451')));styles.add(ParagraphStyle(name='CellX',fontName='DV',fontSize=7,leading=9));styles.add(ParagraphStyle(name='SmallX',fontName='DV',fontSize=7,leading=10,spaceAfter=8,textColor=colors.HexColor('#547080')))
from xml.sax.saxutils import escape
story=[Spacer(1,50),Paragraph('YCS PREMONITION-MPC',styles['TitleX']),Paragraph('Laboratório científico v1.0',styles['HeadX']),Paragraph('Bifurcações, sinais antecipativos e controle inferencial de um CSTR de propilenoglicol',styles['BodyX']),Spacer(1,20),Paragraph('Walter Yanko de Aragão Brandão<br/>Yanko Creative Studio · YCS ProcessLab',styles['BodyX']),Paragraph('Referência do projeto: outubro de 2026<br/>Execução computacional reproduzível · CPU-first',styles['SmallX']),Spacer(1,25)]
for t,_,_ in REPORTS:story.append(Paragraph(escape(t),styles['BodyX']))
story += [Spacer(1,20),Paragraph('Resultados de simulação. Nenhuma garantia de segurança industrial. Fontes, modelos, sementes, testes e registros completos acompanham o código.',styles['SmallX']),PageBreak()]
for title,paras,figures in REPORTS:
 story.append(Paragraph(escape(title),styles['HeadX']))
 for para in paras:
  if para.startswith('| '):
   lines=para.splitlines();cells=[[c.strip() for c in l.strip('|').split('|')] for l in [lines[0]]+lines[2:]];n=len(cells[0]);widths=[490/n]*n
   data=[[Paragraph(escape(c).replace('−','-'),styles['CellX']) for c in r] for r in cells]
   tab=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT');tab.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e0eeed')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),6),('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor('#237c7b')),('LINEBELOW',(0,1),(-1,-1),.3,colors.HexColor('#c5d1d6'))]));story.append(KeepTogether([tab,Spacer(1,12)]))
  else:story.append(Paragraph(escape(para).replace('\n','<br/>'),styles['BodyX']))
 for fig in figures:
  from PIL import Image as PILImage
  path=G/(fig+'.png');im=PILImage.open(path);w,h=im.size;ww=430;hh=ww*h/w
  if hh>600:ww*=600/hh;hh=600
  story.extend([Spacer(1,12),Image(str(path),width=ww,height=hh),Paragraph(escape(fig.replace('_',' '))+'. Dados completos e unidades nos arquivos de resultados.',styles['SmallX'])])
 story.append(PageBreak())
if isinstance(story[-1],PageBreak):story.pop()
def footer(canvas,doc):
 canvas.saveState();canvas.setStrokeColor(colors.HexColor('#bfd0d4'));canvas.line(48,43,547,43);canvas.setFont('DV',7);canvas.setFillColor(colors.HexColor('#547080'));canvas.drawString(48,30,'YCS Premonition-MPC Lab v1.0 | Relatório de simulação');canvas.drawRightString(547,30,str(doc.page));canvas.restoreState()
SimpleDocTemplate(str(O/'YCS_Premonition_MPC_Relatorios_v1.0.pdf'),title='YCS Premonition-MPC Laboratory v1.0 — Relatórios científicos',author='YCS ProcessLab Scientific Research',pagesize=(595.28,841.89),rightMargin=52,leftMargin=52,topMargin=50,bottomMargin=58).build(story,onFirstPage=footer,onLaterPages=footer)
save(R/'report_sources.json',{'report_files':[p.name for p in O.glob('*.md')],'figures':[p.name for p in G.glob('*.png')],'input_seeds':'final 300000/400000 detection; 50000 control; 62000 bifurcation','refs':refs})
print('Reports and figures written',flush=True)
