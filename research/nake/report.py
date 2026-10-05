from pathlib import Path
import argparse,json,csv,shutil
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,PageBreak
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from estimator import BASE, P_ADJUSTED, P_TABLE, DT, U_BASE
from cstr import mass_ss, heat_residual, U0

ROOT=Path(__file__).resolve().parent;RES=ROOT/'results'
LABELS={'nominal':'Nominal','startup':'Partida','feed_steps':'Degraus na alimentação','coolant_steps':'Degraus na refrigeração','UA_mismatch':'UA: -12%','kinetic_mismatch':'Cinética: +10%','variable_noise':'Ruído dos sensores: ×3','sensor_dropout':'Perda de sensores','OOD_combined':'Fora do treino: combinado'}
KINDS=['ukf_published','ukf_tuned','nake_q','nake_dynamics','nake_hybrid']
KL={'ukf_published':'UKF referência','ukf_tuned':'UKF ressintonizado','nake_q':'NAKE-Q','nake_dynamics':'NAKE dinâmica','nake_hybrid':'NAKE híbrido'}
C={'ukf_published':'#94a3b8','ukf_tuned':'#334155','nake_q':'#a78bfa','nake_dynamics':'#f59e0b','nake_hybrid':'#0d9488'}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':False})


def bootstrap_gain(a,b,seed=481):
 rng=np.random.default_rng(seed);ix=rng.integers(0,len(a),(10000,len(a)))
 samples=100*(1-a[ix].mean(1)/b[ix].mean(1))
 return [float(v) for v in np.percentile(samples,[2.5,97.5])]


def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',default=str(RES/'report'));args=ap.parse_args();out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
 metrics=json.loads((RES/'metrics.json').read_text());protocol=json.loads((RES/'protocol.json').read_text());cal=json.loads((RES/'calibration.json').read_text());historical=json.loads((RES/'historical_validation.json').read_text())
 regimes=list(LABELS);summary=[]
 for regime in regimes:
  rows=[x for x in metrics if x['regime']==regime];entry={'regime':regime,'label':LABELS[regime]}
  for kind in KINDS:
   m=[x for x in rows if x['estimator']==kind]
   for field in ['cc_rmse','cc_coverage95','nees_mean','nis_mean','latency_ms','normalized_rmse']:
    entry[kind+'_'+field]=float(np.mean([x[field] for x in m]))
  a=np.array([x['cc_rmse'] for x in rows if x['estimator']=='nake_hybrid']);b=np.array([x['cc_rmse'] for x in rows if x['estimator']=='ukf_tuned'])
  entry['hybrid_gain_pct']=float(100*(1-a.mean()/b.mean()));entry['gain_ci95']=bootstrap_gain(a,b)
  summary.append(entry)
 macro={k:float(np.mean([r[k+'_cc_rmse'] for r in summary])) for k in KINDS}
 data={'scenarios':summary,'macro_mean_CC_RMSE':macro,'macro_gain_hybrid_vs_tuned':100*(1-macro['nake_hybrid']/macro['ukf_tuned']),
 'failures':sum(x['failed'] is not None for x in metrics),'runs':len(metrics),'paired_bootstrap':'10000 seed resamples per regime; 8 independent test seeds, no multiple-comparison correction'}
 (RES/'summary.json').write_text(json.dumps(data,indent=2,ensure_ascii=False))
 with (RES/'summary.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,['regime','label']+[k+'_cc_rmse' for k in KINDS]+['hybrid_gain_pct'],extrasaction='ignore',lineterminator='\n');w.writeheader();w.writerows(summary)
 # Primary artifact: ratios remain visible on a logarithmic RMSE axis.
 fig,ax=plt.subplots(figsize=(13.2,8.3));yp=np.arange(len(summary));height=.22
 for i,k in enumerate(['ukf_published','ukf_tuned','nake_hybrid']):
  ax.barh(yp+(i-1)*height,[r[k+'_cc_rmse'] for r in summary],height=height,color=C[k],label=KL[k])
 ax.set_yticks(yp,[r['label'] for r in summary]);ax.invert_yaxis();ax.set_xscale('log');ax.set_xlabel('RMSE de C_C (kmol/m³) · menor é melhor');ax.grid(axis='x',which='both',alpha=.18)
 ax.set_title('NAKE × UKF no CSTR com equilíbrio ajustado',loc='left',fontweight='bold',fontsize=18,pad=48)
 ax.text(0,1.035,'9 regimes · 8 sementes independentes por regime · média entre sementes',transform=ax.transAxes,color='#475569',fontsize=12)
 ax.set_xticks([.005,.010,.020,.040,.080],['0,005','0,010','0,020','0,040','0,080'])
 ax.legend(loc='upper left',bbox_to_anchor=(0,-.12),ncol=3,frameon=False,borderaxespad=0)
 fig.text(.025,.015,'Calibração nominal: 332,3 K. Cenários simulados; o NAKE não melhora todos os regimes.',color='#475569',fontsize=11)
 fig.tight_layout(rect=[0,.05,1,.99]);fig.savefig(out/'CSTR_NAKE_UKF_Resumo.png',dpi=170);plt.close(fig)
 # Effect sizes and bootstrap seed uncertainty.
 fig,ax=plt.subplots(figsize=(12,6.8));g=np.array([r['hybrid_gain_pct'] for r in summary]);ci=np.array([r['gain_ci95'] for r in summary]);ax.barh(yp,g,color=np.where(g>=0,'#0d9488','#d97706'))
 ax.errorbar(g,yp,xerr=np.vstack([g-ci[:,0],ci[:,1]-g]),fmt='none',ecolor='#1e293b',capsize=3)
 ax.axvline(0,color='#475569',lw=1);ax.set_yticks(yp,[r['label'] for r in summary]);ax.invert_yaxis();ax.set_xlabel('Redução do RMSE de C_C versus UKF ressintonizado (%)');ax.set_title('Ganho depende do regime; valores negativos indicam piora',loc='left',fontweight='bold',pad=16)
 fig.tight_layout();fig.savefig(out/'CSTR_NAKE_UKF_Ganhos.png',dpi=150);plt.close(fig)
 # Equilibrium proof, not fitted trend drawing.
 T=np.linspace(285,360,450);from estimator import rhs6
 from cstr import feed
 def heat_curves(t,p):
  v,_=feed(U0,p);k=p.k0*np.exp(-p.E/(p.R*t));gen=-p.dH*(p.V/v)*k/(1+(p.V/v)*k)
  duty=U0[1]*p.cpB*(U0[2]-t)*(-np.expm1(-p.UA/(U0[1]*p.cpB)))
  rem=(U0[0]*p.cpA+p.FB*p.cpB+p.FM*p.cpM)*(t-p.T0)/U0[0]-duty/U0[0]
  return gen,rem
 gt,rem=heat_curves(T,P_TABLE);gc,_=heat_curves(T,P_ADJUSTED)
 fig,ax=plt.subplots(figsize=(10,4.4));ax.plot(T,gt/1000,label='Geração: entalpia tabelada',color='#94a3b8');ax.plot(T,gc/1000,label='Geração: entalpia efetiva',color='#0d9488',lw=2);ax.plot(T,rem/1000,label='Remoção de calor',color='#334155',lw=2)
 ax.axvline(332.3,color='#0d9488',ls='--',alpha=.6);ax.axvline(340.3034893843503,color='#94a3b8',ls='--',alpha=.6);ax.set(xlabel='Temperatura do reator (K)',ylabel='Calor por alimentação de A (MJ/kmol)');ax.legend(frameon=False,fontsize=9);ax.grid(alpha=.15);fig.tight_layout();fig.savefig(out/'CSTR_Equilibrio.png',dpi=160);plt.close(fig)
 # Sample trace chosen by predeclared first independent seed, not best-performing run.
 fig,axs=plt.subplots(3,1,figsize=(10,8.5),sharex=True)
 for ax,regime in zip(axs,['kinetic_mismatch','variable_noise','OOD_combined']):
  z=np.load(RES/f'trace_{regime}.npz');t=np.arange(1,len(z['y'])+1)*DT
  ax.plot(t,z['truth'][1:,2],color='#0f172a',lw=2,label='Planta simulada')
  for kind in ['ukf_tuned','nake_hybrid']:
   ax.plot(t,z[kind][:,2],color=C[kind],lw=1.3,label=KL[kind])
  ax.set_title(LABELS[regime],loc='left',fontsize=11,fontweight='bold');ax.set_ylabel('C_C (kmol/m³)');ax.grid(alpha=.12)
 axs[0].legend(frameon=False,ncol=3,fontsize=8);axs[-1].set_xlabel('Tempo (h)');fig.tight_layout();fig.savefig(out/'CSTR_NAKE_UKF_Tracos.png',dpi=150);plt.close(fig)
 # Human-readable research summary stored with the code and raw results.
 lines=['# NAKE x UKF - resultados simulados','',f"Equilíbrio calibrado: T=332.3 K; Tt={BASE[5]:.6f} K; CC={BASE[2]:.6f} kmol/m³.",f"Entalpia efetiva: {P_ADJUSTED.dH:.6f} kJ/kmol. Calibração em um ponto, não parâmetro físico recuperado.",'',f"{len(metrics)} execuções; {data['failures']} divergências. 19 testes numéricos aprovados localmente.",'','| Regime | UKF ref. | UKF ressint. | NAKE-Q | NAKE dinâmica | NAKE híbrido | Ganho híbrido |','|---|---:|---:|---:|---:|---:|---:|']
 for r in summary:lines.append('| '+r['label']+' | '+' | '.join(f"{r[k+'_cc_rmse']:.6f}" for k in KINDS)+f" | {r['hybrid_gain_pct']:+.1f}% |")
 lines+=['','RMSE de CC em kmol/m³. Ganho calculado contra o UKF ressintonizado. Média por semente; regimes igualmente ponderados.',f"Média macro: UKF ressintonizado {macro['ukf_tuned']:.6f}; NAKE híbrido {macro['nake_hybrid']:.6f}; redução {data['macro_gain_hybrid_vs_tuned']:.1f}%.",'','A versão híbrida ganha nos testes de cinética e combinação fora do treino, mas piora em outros regimes. Q não substitui uma adaptação de R. Calibração de incerteza é preliminar: cobertura, NEES e NIS são fornecidos, sem garantia estatística geral.','',f"Verificação histórica independente: RMSE nos 24 pontos não nominais: tabelado {historical['tabled']['RMSE_K']:.4f} K; calibrado {historical['calibrated']['RMSE_K']:.4f} K; máximo calibrado {historical['calibrated']['max_absolute_error_K']:.4f} K. Seleção da raiz mais próxima do ponto histórico: diagnóstico de melhor caso, não previsão por continuação.",'','Código e pesos reais; rede MLP de estatísticas causais, não LSTM. Sem dados da planta real, ensaio MATLAB ou comparação fechada NMPC nesta execução. Ver README e protocol.json.']
 (RES/'RESULTADOS.md').write_text('\n'.join(lines),encoding='utf-8')
 # PDF: 5 pages, deliberately fixed page breaks and generous table spacing.
 font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';bold='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
 pdfmetrics.registerFont(TTFont('DV',font));pdfmetrics.registerFont(TTFont('DVB',bold))
 styles=getSampleStyleSheet();styles.add(ParagraphStyle('BodyDV',fontName='DV',fontSize=9.1,leading=13.4,spaceAfter=8,textColor=colors.HexColor('#334155')))
 styles.add(ParagraphStyle('TitleDV',fontName='DVB',fontSize=22,leading=27,spaceAfter=12,textColor=colors.HexColor('#0f172a')))
 styles.add(ParagraphStyle('HeadDV',fontName='DVB',fontSize=13,leading=17,spaceBefore=8,spaceAfter=9,textColor=colors.HexColor('#0f766e')))
 styles.add(ParagraphStyle('SmallDV',fontName='DV',fontSize=7.5,leading=10.5,spaceAfter=6,textColor=colors.HexColor('#475569')))
 story=[]
 def para(text,sty='BodyDV'):story.append(Paragraph(text,styles[sty]))
 def table(rows,widths,small=False):
  style=styles['SmallDV'] if small else styles['BodyDV']
  cells=[[Paragraph(str(c),style) for c in r] for r in rows];tbl=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT')
  tbl.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e2f3f1')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f8fafc')]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),5),('LINEBELOW',(0,0),(-1,0),.7,colors.HexColor('#0d9488'))]));story.append(tbl);story.append(Spacer(1,8))
 def img(name,width,height):story.append(Image(str(out/name),width=width,height=height));story.append(Spacer(1,8))
 para('CSTR · NAKE × UKF','TitleDV');para('Equilíbrio ajustado e comparação de estimadores | Walter Yanko | Outubro de 2026','SmallDV')
 para('1. Ajuste transparente do equilíbrio','HeadDV')
 para('Os parâmetros tabelados produzem <b>340,303489 K</b>, enquanto o ponto nominal histórico informa <b>332,3 K</b>. Nesse ponto histórico, o balanço tabelado fornece dT/dt = 32,964620 K/h. A incompatibilidade foi tratada por calibração explícita de uma entalpia efetiva, mantendo as demais entradas e parâmetros.')
 table([['Grandeza','Tabelado','Ajustado'],['ΔH de reação (kJ/kmol)','-91.556,900','-84.138,654'],['T do reator (K)','340,303489','332,300000'],['Tt do trocador (K)','319,202323',f'{BASE[5]:.6f}'],['CC (kmol/m³)','2,539426',f'{BASE[2]:.6f}']],[190,145,145])
 para('A magnitude da entalpia caiu <b>8,102%</b>. Este é um coeficiente efetivo ajustado a <b>um único ponto</b>; não identifica a entalpia química real nem recupera a implementação histórica do Simulink. As duas variantes permanecem disponíveis no código.')
 img('CSTR_Equilibrio.png',480,211)
 para(f"Verificação dos seis balanços: maior resíduo {max(abs(np.array(cal['residual']))):.2e} nas respectivas unidades. Equilíbrio localmente estável; deriva nula no teste de 4 h. RK4 e DOP853 concordaram a {cal['DOP853_error']:.2e} no teste de perturbação.",'SmallDV')
 story.append(PageBreak())
 para('2. Comparação nos nove regimes','HeadDV');para('360 execuções = 9 regimes × 8 sementes × 5 estimadores. Todas terminaram sem divergência. A figura mostra o RMSE médio de concentração de produto entre sementes; a escala logarítmica permite comparar regimes com amplitudes distintas.')
 img('CSTR_NAKE_UKF_Resumo.png',485,305)
 para(f"Média macro de RMSE de CC: UKF ressintonizado <b>{macro['ukf_tuned']:.6f}</b>; NAKE híbrido <b>{macro['nake_hybrid']:.6f} kmol/m³</b>. Redução de <b>{data['macro_gain_hybrid_vs_tuned']:.1f}%</b> para esta ponderação igual dos nove regimes.")
 para('A média global encobre diferenças relevantes. O híbrido melhora nos testes de alteração cinética e combinação fora do treino; piora nos testes de ruído variável, perda de sensores e em vários cenários próximos do modelo nominal. Não há dominância geral do NAKE.')
 para('Os testes usam o mesmo modelo ajustado, comandos, condições iniciais e realizações de ruído para todos. A planta é integrada por DOP853; os filtros compartilham RK4. O UKF de referência usa a Q histórica no novo modelo; sua sintonia não é declarada ótima para os novos regimes.','SmallDV')
 story.append(PageBreak())
 para('3. Resultados completos de CC','HeadDV')
 rows=[['Regime','UKF ref.','UKF ress.','NAKE-Q','NAKE din.','NAKE híbr.']]
 for r in summary:rows.append([r['label']]+[f"{r[k+'_cc_rmse']:.6f}" for k in KINDS])
 table(rows,[137,69,69,69,69,69],True)
 para('Valores em kmol/m³. O segundo UKF foi ressintonizado apenas em trajetórias de treinamento, em uma grade de nove combinações de Q. Esse benchmark adicional reduz a chance de atribuir à rede ganhos obtidos apenas por trocar a sintonia.','SmallDV')
 para('Incerteza e custo computacional','HeadDV')
 rows=[['Estimador','Cobertura CC 95%','NEES médio (6 estados)','Tempo mediano médio (ms)']]
 for k in KINDS:
  a=[x for x in metrics if x['estimator']==k];rows.append([KL[k],f"{100*np.mean([x['cc_coverage95'] for x in a]):.1f}%",f"{np.mean([x['nees_mean'] for x in a]):.2f}",f"{np.mean([x['latency_ms'] for x in a]):.3f}"])
 table(rows,[137,105,124,116],True)
 para('Cobertura próxima de 95% e NEES próximo de 6 são referências diagnósticas, não prova de calibração. As séries são correlacionadas, e a cobertura muda por regime. A Q neural aprende um alvo heurístico de erro de modelo; R permanece fixa. Não ocorreram reparos de covariância neste conjunto.','SmallDV')
 para('As latências são medições locais de CPU, com uma thread BLAS. Não constituem garantia de tempo real ou de desempenho em outra máquina. Os dados brutos incluem RMSE/MAE dos seis estados, NIS, cobertura por estado e percentil 95 de latência.','SmallDV')
 story.append(PageBreak())
 para('4. Ganhos e deteriorações','HeadDV')
 img('CSTR_NAKE_UKF_Ganhos.png',485,275)
 para('Barras mostram a redução do RMSE do híbrido versus o UKF ressintonizado. Intervalos: bootstrap pareado de 10.000 reamostragens das oito sementes independentes, por regime. Não há correção por comparações múltiplas; são intervalos exploratórios deste conjunto simulado.','SmallDV')
 para('Checagem dos pontos históricos fora da calibração','HeadDV')
 para(f"Nos <b>24 pontos não nominais</b> da Tabela 2, o erro RMS da temperatura caiu de <b>{historical['tabled']['RMSE_K']:.3f} K</b> para <b>{historical['calibrated']['RMSE_K']:.3f} K</b>; o maior erro ajustado foi <b>{historical['calibrated']['max_absolute_error_K']:.3f} K</b>. Esses pontos não foram usados para ajustar a entalpia.")
 para('Essa checagem seleciona a raiz calculada mais próxima de cada temperatura histórica. É um diagnóstico de melhor caso, que usa a referência para escolher a ramificação; não demonstra que uma operação física seguiria todas essas raízes. Os arquivos registram todas as contagens de raízes e a estabilidade da raiz escolhida.','SmallDV')
 para('A calibração resolve o conflito nominal e melhora a compatibilidade da tabela, mas o erro residual permanece. Resultados anteriores de seleção de MVs, RGA e NMPC sobre a versão tabelada precisam ser recalculados antes de serem usados como resultados do modelo ajustado.','SmallDV')
 story.append(PageBreak())
 para('5. Protocolo e reprodutibilidade','HeadDV')
 para('Rede real treinada: MLP tanh <b>26 → 32 → 24 → 8</b>, com 5.760 amostras de 36 trajetórias (sementes 100-135). Há seis trajetórias independentes de validação (500-505) e oito sementes de teste (900-907). Cada trajetória dura 2,4 h, com Ts = 0,015 h.')
 para('As entradas online são estimativas anteriores, comandos, variações de comandos e estatísticas das 12 inovações anteriores. A rede aprende escalas de UA e k0 para corrigir a dinâmica física e fatores positivos de Q. Estados verdadeiros e parâmetros da planta são usados somente nos rótulos offline e nas métricas. Um teste específico confirma essa separação.')
 para('A implementação usa uma MLP sobre estatísticas de janela, não LSTM. NAKE é o nome de trabalho desta arquitetura; o módulo não é uma reprodução de KalmanNet nem uma alegação de novidade científica. Os pesos exportados em JSON foram conferidos contra o modelo de treinamento.')
 para('Ruído de sensores nominal sintético: desvios de 0,35 K e 0,30 K. No cenário variável, esses desvios triplicam sem aviso ao filtro. Não há ruído aditivo independente nos estados da planta. Alterações paramétricas e erro numérico motivam Q. O estudo avalia estimação em malha aberta; NMPC fechado e medições reais não foram testados.')
 para('19 testes passaram: 11 do núcleo TypeScript e 8 do módulo de pesquisa. Eles verificam balanços, integração independente, conservação, paridade Python/TypeScript, positividade de covariância, medições ausentes, inferência sem acesso à verdade e determinismo.')
 para('Reproduzir a execução','HeadDV')
 for text in ['npm test','python -m unittest discover -s research/nake -p test_*.py -v','python research/nake/experiment.py --seeds 8 --steps 160','python research/nake/equilibrium_validation.py','python research/nake/report.py']:
  para(text,'SmallDV')
 para('Fontes e escopo','HeadDV')
 para('Brandão, W. Y. A. (2019). Uso de observadores de estado aplicados no controle inferencial preditivo de processos não lineares. Equações 33-55, Tabela 1 (parâmetros), Tabela 2 (pontos históricos); páginas impressas 25-32 e 50. Manuscrito PAPER_BRANDAO_W-Y-A_REV05: conferência da tabela de parâmetros.','SmallDV')
 para('Julier e Uhlmann (2004), Unscented Filtering and Nonlinear Estimation, DOI 10.1109/JPROC.2003.823141. Revach et al. (2022), KalmanNet: Neural Network Aided Kalman Filtering for Partially Known Dynamics, arXiv:2107.10043. Documentação oficial MathWorks: unscentedKalmanFilter.','SmallDV')
 para('Não foi executado MATLAB/Simulink nesta sessão, não há validação industrial e não foi alterado o site já publicado. Código, pesos, métricas e protocolo permitem repetir esta comparação simulada.','SmallDV')
 def footer(canvas,doc):
  canvas.saveState();canvas.setStrokeColor(colors.HexColor('#e2e8f0'));canvas.line(42,37,553,37);canvas.setFont('DV',7);canvas.setFillColor(colors.HexColor('#64748b'));canvas.drawString(42,24,'Walter Yanko · CSTR / NAKE · resultados simulados e calibração explícita');canvas.drawRightString(553,24,str(doc.page));canvas.restoreState()
 SimpleDocTemplate(str(out/'CSTR_NAKE_UKF_Relatorio.pdf'),pagesize=A4,rightMargin=42,leftMargin=42,topMargin=38,bottomMargin=47).build(story,onFirstPage=footer,onLaterPages=footer)
 print(json.dumps({'out':str(out),'macro_gain_pct':data['macro_gain_hybrid_vs_tuned'],'runs':len(metrics)},ensure_ascii=False))

if __name__=='__main__':main()
