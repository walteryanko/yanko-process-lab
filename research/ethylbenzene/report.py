"""Portuguese scientific report and standalone charts from retained results."""
import argparse,json,csv,itertools
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,PageBreak
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from model import *
from protocol import CASES,SEEDS

ESTIMATORS=['ukf','ukf_tuned','lstm_ukf','nake','lstm_nake']
EL={'ukf':'UKF Q0','ukf_tuned':'UKF validado','lstm_ukf':'LSTM-UKF','nake':'NAKE-BB','lstm_nake':'LSTM-NAKE'}
CL={'servo_up':'Servo +10%','servo_down':'Servo -10%','benzene_50':'Benzeno +50%',
    'recycle_minus50':'Reciclo -50%','thermal_loss':'Perda térmica 20%','kinetics_noise':'Cinética, ruído e perda de sensor'}
PALETTE=['#1e3a8a','#0f766e','#dc2626','#9333ea','#c27d0e']

def data():
    rows=json.loads((RESULTS/'metrics.json').read_text())+json.loads((RESULTS/'metrics_tuned.json').read_text())
    obs=json.loads((RESULTS/'metrics_openloop.json').read_text())+json.loads((RESULTS/'metrics_openloop_tuned.json').read_text())
    index={(r['case'],r['seed'],r['estimator'],r['prediction'],r['mode'],r['constrained']):r for r in rows}
    protocol=json.loads((RESULTS/'protocol.json').read_text())
    protocol['configurations'] += [dict(estimator='ukf_tuned',prediction=p,mode=m) for p,m in itertools.product(['physical','neural'],['siso','mimo'])]
    protocol['runs']=720;protocol['observer_runs']=75
    protocol['estimators']['ukf_tuned']='physical prediction; constant Q selected on independent validation seed 4601'
    protocol['ukf_tuning']=json.loads((RESULTS/'tuning_ukf.json').read_text())
    dump(RESULTS/'protocol_all.json',protocol)
    summary=[]
    for e,p,m,con in itertools.product(ESTIMATORS,['physical','neural'],['siso','mimo'],[False,True]):
        rr=[r for r in rows if (r['estimator'],r['prediction'],r['mode'],r['constrained'])==(e,p,m,con)]
        complete=[r for r in rr if r['status']=='complete'];paired=[];nominal=[]
        for r in complete:
            base=index[r['case'],r['seed'],'ukf_tuned','physical',m,con]
            old=index[r['case'],r['seed'],'ukf','physical',m,con]
            if base['status']=='complete' and base['IAE_event']>1e-12:paired.append(1-r['IAE_event']/base['IAE_event'])
            if old['status']=='complete' and old['IAE_event']>1e-12:nominal.append(1-r['IAE_event']/old['IAE_event'])
        summary.append(dict(estimator=e,prediction=p,mode=m,constrained=con,runs=len(rr),complete=len(complete),
          IAE_event_mean=float(np.mean([r['IAE_event'] for r in complete])) if complete else None,
          IAE_mean=float(np.mean([r['IAE'] for r in complete])) if complete else None,
          macro_gain_vs_tuned_pct=100*float(np.mean(paired)) if paired else None,
          macro_gain_vs_Q0_pct=100*float(np.mean(nominal)) if nominal else None,
          paired_comparisons=len(paired),Tmax_C=max(r['Tmax_C'] for r in rr),
          actual_violating_runs=sum(r['violation_h']>0 for r in rr),
          violation_mean_min=float(np.mean([r['violation_h']*60 for r in rr])),
          thermal_IAE_mean=float(np.mean([r['temperature_IAE_K_h'] for r in complete])) if complete else None,
          fallbacks=sum(r['fallbacks'] for r in rr),solver_failed_statuses=sum(r['solver_failed_statuses'] for r in rr),
          median_latency_ms=float(np.median([r['median_latency_ms'] for r in rr]))))
    observer=[]
    for case in ['servo_up','benzene_50','recycle_minus50','thermal_loss','kinetics_noise']:
        for e in ESTIMATORS:
            rr=[r for r in obs if r['case']==case and r['estimator']==e and r['status']=='complete']
            vals=[r['xEB_RMSE_after5'] for r in rr];tv=[r['T_RMSE_after5'] for r in rr]
            observer.append(dict(case=case,estimator=e,complete=len(rr),xEB_RMSE_mean=float(np.mean(vals)) if vals else None,
                                 xEB_RMSE_std=float(np.std(vals)) if vals else None,T_RMSE_mean=float(np.mean(tv)) if vals else None))
    dump(RESULTS/'summary.json',dict(control=summary,observer=observer))
    with (RESULTS/'summary.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=summary[0].keys(),lineterminator='\n');w.writeheader();w.writerows(summary)
    bycase=[]
    for e,p,m,con,case in itertools.product(ESTIMATORS,['physical','neural'],['siso','mimo'],[False,True],CASES):
        rr=[r for r in rows if (r['estimator'],r['prediction'],r['mode'],r['constrained'],r['case'])==(e,p,m,con,case)]
        good=[r for r in rr if r['status']=='complete']
        bycase.append(dict(estimator=e,prediction=p,mode=m,constrained=con,case=case,runs=len(rr),complete=len(good),
            IAE_event_mean=float(np.mean([r['IAE_event'] for r in good])) if good else None,
            IAE_event_std=float(np.std([r['IAE_event'] for r in good])) if good else None,
            Tmax_C=max(r['Tmax_C'] for r in rr),actual_violating_runs=sum(r['violation_h']>0 for r in rr),
            violation_mean_min=float(np.mean([r['violation_h']*60 for r in rr])),fallbacks=sum(r['fallbacks'] for r in rr)))
    dump(RESULTS/'summary_by_case.json',bycase)
    with (RESULTS/'summary_by_case.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=bycase[0].keys(),lineterminator='\n');w.writeheader();w.writerows(bycase)
    return rows,obs,summary,observer

def heatmap(summary,out):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axs=plt.subplots(1,2,figsize=(12,4.6),sharey=True)
    combos=[('physical','siso'),('neural','siso'),('physical','mimo'),('neural','mimo')]
    images=[]
    for ax,con in zip(axs,[False,True]):
        arr=np.array([[next(r['macro_gain_vs_tuned_pct'] for r in summary if (r['estimator'],r['prediction'],r['mode'],r['constrained'])==(e,p,m,con)) for p,m in combos] for e in ESTIMATORS])
        im=ax.imshow(arr,cmap='RdYlGn',vmin=-60,vmax=60,aspect='auto');images.append(im)
        for i in range(5):
            for j in range(4):
                val=arr[i,j];ax.text(j,i,f'{val:+.1f}%',ha='center',va='center',fontsize=10,fontweight='bold',color='white' if abs(val)>48 else '#0f172a')
        ax.set_xticks(range(4),['Físico\nSISO','Blackbox\nSISO','Físico\nMIMO','Blackbox\nMIMO'])
        ax.set_yticks(range(5),[EL[e] for e in ESTIMATORS]);ax.set_title('Sem restrição térmica' if not con else 'Restrição prevista: T ≤ 165 °C',fontweight='bold',pad=12)
    fig.suptitle('Etilbenzeno: o ganho depende da combinação',fontweight='bold',fontsize=17,y=.98)
    fig.text(.13,.025,'Ganho médio pareado de IAE após evento vs. UKF validado + NMPC físico do mesmo modo. Positivo = menor IAE.',fontsize=9,color='#475569')
    fig.subplots_adjust(left=.13,right=.91,top=.84,bottom=.16,wspace=.13)
    cb=fig.colorbar(images[0],cax=fig.add_axes([.925,.16,.012,.68]));cb.set_label('Ganho (%)',fontsize=9)
    fig.savefig(out/'Etilbenzeno_Comparacao.png',dpi=180);plt.close(fig)

def traces(cases,out,filename,con=True):
    configs=[('ukf_tuned','physical','siso'),('ukf_tuned','physical','mimo'),('lstm_ukf','physical','mimo'),('lstm_nake','neural','mimo')]
    labels=['UKF validado / físico SISO','UKF validado / físico MIMO','LSTM-UKF / físico MIMO','LSTM-NAKE / blackbox MIMO']
    fig,axs=plt.subplots(3,2,figsize=(11.4,8.6),sharex=True)
    for col,case in enumerate(cases):
        for j,(e,p,m) in enumerate(configs):
            name=f'{case}__{e}__{p}__{m}__{int(con)}__9002';z=np.load(RESULTS/'traces'/f'{name}.npz')
            t=z['time'];axs[0,col].plot(t,fraction(z['true']),color=PALETTE[j],lw=1.45)
            axs[1,col].plot(t,z['true'][:,4],color=PALETTE[j],lw=1.1)
            axs[2,col].plot(t,z['command'][:,0]/F0[0],color=PALETTE[j],lw=1.)
            if m=='mimo':axs[2,col].plot(t,z['command'][:,3]/Q0,color=PALETTE[j],lw=.9,ls='--')
            if j==0:axs[0,col].plot(t,z['reference'],color='#334155',ls=':',lw=1.8)
        axs[0,col].set_title(CL[case],fontweight='bold',pad=10)
        axs[1,col].axhline(T_LIMIT,color='#991b1b',ls='--',lw=1.,label='Limite assumido')
        axs[2,col].set_xlabel('Tempo (h)')
        for ax in axs[:,col]:ax.grid(alpha=.18);ax.set_xlim(0,10.)
    axs[0,0].set_ylabel('Fração molar xEB');axs[1,0].set_ylabel('Temperatura simulada (°C)');axs[2,0].set_ylabel('Comando / nominal')
    fig.legend([Line2D([0],[0],color=PALETTE[j],lw=2) for j in range(4)],labels,loc='upper center',ncol=2,frameon=False,fontsize=9)
    fig.text(.13,.014,'Semente 9002. Restrição prevista ativada. Na atuação: linha contínua = etileno; tracejada = remoção de calor.',color='#475569',fontsize=9)
    fig.subplots_adjust(top=.88,bottom=.075,left=.09,right=.98,hspace=.23,wspace=.2)
    fig.savefig(out/filename,dpi=170);plt.close(fig)

def observer_chart(observer,out):
    cases=['servo_up','benzene_50','recycle_minus50','thermal_loss','kinetics_noise']
    fig,ax=plt.subplots(figsize=(10.6,4.5));xx=np.arange(5);width=.15
    for i,e in enumerate(ESTIMATORS):
        vals=[next(r['xEB_RMSE_mean'] for r in observer if r['case']==c and r['estimator']==e) for c in cases]
        ax.bar(xx+(i-2)*width,vals,width,label=EL[e],color=PALETTE[i])
    ax.set_yscale('log');ax.set_xticks(xx,['Nominal','Benzeno +50%','Reciclo -50%','Perda térmica','Cinética + ruído'])
    ax.set_ylabel('RMSE de xEB após 5 h (fração molar)')
    fig.suptitle('Estimadores sobre a mesma trajetória, sem controle',x=.095,y=.98,ha='left',fontweight='bold',fontsize=14)
    ax.grid(axis='y',alpha=.2);fig.legend(ncol=5,frameon=False,fontsize=10,loc='upper left',bbox_to_anchor=(.09,.91))
    fig.subplots_adjust(left=.095,right=.985,top=.79,bottom=.14)
    fig.savefig(out/'Etilbenzeno_Estimadores.png',dpi=180);plt.close(fig)

def pdf(rows,obs,summary,observer,out):
    font=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf');bold=font.with_name('DejaVuSans-Bold.ttf')
    pdfmetrics.registerFont(TTFont('DV',str(font)));pdfmetrics.registerFont(TTFont('DVB',str(bold)))
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleEB',fontName='DVB',fontSize=21,leading=26,textColor=colors.HexColor('#0f172a'),spaceAfter=14))
    styles.add(ParagraphStyle(name='HeadEB',fontName='DVB',fontSize=14,leading=19,textColor=colors.HexColor('#0f766e'),spaceBefore=5,spaceAfter=9))
    styles.add(ParagraphStyle(name='BodyEB',fontName='DV',fontSize=9.4,leading=14,spaceAfter=8))
    styles.add(ParagraphStyle(name='SmallEB',fontName='DV',fontSize=8,leading=11,spaceAfter=6,textColor=colors.HexColor('#475569')))
    styles.add(ParagraphStyle(name='CellEB',fontName='DV',fontSize=7.8,leading=10))
    story=[];width=515.
    def p(s,style='BodyEB'):story.append(Paragraph(s,styles[style]))
    def title(s):p(s,'HeadEB')
    def chart(name,h):story.append(Image(str(out/name),width=width,height=h));story.append(Spacer(1,8))
    def table(data,widths):
        cells=[[Paragraph(str(x),styles['CellEB']) for x in row] for row in data]
        t=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e2e8f0')),('VALIGN',(0,0),(-1,-1),'TOP'),
                              ('LINEBELOW',(0,0),(-1,0),.5,colors.HexColor('#94a3b8')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f8fafc')]),
                              ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),4),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]));story.append(t);story.append(Spacer(1,9))
    audit=json.loads((RESULTS/'audit.json').read_text());tuning=json.loads((RESULTS/'tuning_ukf.json').read_text())
    training=json.loads((RESULTS/'training_transition.json').read_text());lstm=json.loads((RESULTS/'training_lstm.json').read_text())
    historical=json.loads((RESULTS/'tfc_published.json').read_text())
    pi_tuning=json.loads((RESULTS/'baseline_tuning.json').read_text())
    pi_gains=json.loads((RESULTS/'improvement_vs_pi.json').read_text())
    pi_comparison=json.loads((RESULTS/'tfc_control_comparison.json').read_text())
    obs_comparison=json.loads((RESULTS/'tfc_observer_comparison.json').read_text())
    pi_audit=json.loads((RESULTS/'historical_audit.json').read_text())
    complete=sum(r['status']=='complete' for r in rows)
    p('Etilbenzeno<br/>LSTM, UKF, NAKE e NMPC','TitleEB')
    p('Walter Yanko de Aragão Brandão | Estudo do primeiro reator do TFC | Outubro de 2026','SmallEB')
    p(f'<b>20 configurações NMPC: {complete}/720 ensaios; 75 ensaios de estimação.</b> A comparação com o TFC acrescenta 18 ensaios PI + FKE e 15 de estimação FKE, todos completos. A base é o modelo reduzido de cinco estados, com unidades cinéticas confirmadas no artigo original de Luyben fornecido pelo autor.')
    p('A comparação cruza cinco estimadores, predição física ou blackbox e controle SISO ou MIMO, com e sem restrição térmica. UKF Q0 é a referência nominal; UKF validado usa uma matriz Q constante escolhida em dados de validação independentes. LSTM-UKF e LSTM-NAKE usam redes recorrentes treinadas de fato.')
    chart('Etilbenzeno_Comparacao.png',200)
    baseline=next(r for r in summary if (r['estimator'],r['prediction'],r['mode'],r['constrained'])==('ukf_tuned','physical','mimo',True))
    learned=next(r for r in summary if (r['estimator'],r['prediction'],r['mode'],r['constrained'])==('lstm_ukf','physical','mimo',True))
    decrease=100*(1-learned['IAE_event_mean']/baseline['IAE_event_mean'])
    p(f'<b>Resultado agregado:</b> LSTM-UKF + NMPC físico MIMO reduziu a média de IAE após evento em {decrease:.1f}% frente ao UKF validado + NMPC físico MIMO, com restrição. O ganho médio das razões pareadas foi {learned["macro_gain_vs_tuned_pct"]:.1f}%. Ambos ultrapassaram 165 °C nos três ensaios de perda térmica; os máximos foram {learned["Tmax_C"]:.2f} °C e {baseline["Tmax_C"]:.2f} °C, respectivamente.')
    conrows=[r for r in rows if r['constrained']]
    p(f'<b>Temperatura real da simulação:</b> a restrição T ≤ 165 °C foi imposta nas previsões. Houve ultrapassagem desse valor em {sum(r["violation_h"]>0 for r in conrows)} dos {len(conrows)} ensaios com restrição; máximo observado {max(r["Tmax_C"] for r in conrows):.3f} °C. A factibilidade prevista não equivale a cumprir o limite na planta com ruído e erro de modelo.')
    p('<b>Frente ao TFC:</b> há ganhos nos dois regulatórios contra o PI + FKE reconstruído, mas perdas nos servos. As tabelas e curvas históricas são confrontadas nas seções 5-7. Ainda não se demonstra superioridade sobre a execução original, cuja sintonia e partida não foram recuperadas. Os resultados abrangem o primeiro reator com calor efetivo calibrado; a planta Aspen completa e as colunas não foram executadas.','SmallEB')
    story.append(PageBreak())
    title('1. Originais, unidades e equilíbrio')
    p('Foram conferidos TFC.zip, o PDF final do TFC, o documento “Modelagem e equações” e o artigo de Luyben (2011). O Aspen exportado conecta R1_TC.OP a R1.QR, confirmando a possibilidade de atuação térmica. O arquivo FiltroKalman.slx contém um exemplo escalar de filtro; o reator não linear de cinco estados não foi localizado como modelo Simulink executável no ZIP.')
    p('Luyben, p. 656, informa taxas em kmol/(s·m³). Por isso o fator correto é 3600 para trabalhar em horas. O rótulo “min” do TFC é corrigido. R = 1,987 cal/(mol·K), compatível com E em cal/mol; a palavra “kcal” impressa para R também é corrigida. Com a unidade de minutos, xEB seria aproximadamente 0,1525 no ponto ajustado, em vez de 0,2811.')
    table([['Componente','Luyben / TFC','Aspen / TFC','MATLAB / TFC','FKE / TFC','Reconstrução'],
           ['xE','0,0039','0,0039','0,0051','0,0050',f'{BASE[0]/BASE[:4].sum():.6f}'],
           ['xB','0,6568','0,6572','0,6607','0,6631',f'{BASE[1]/BASE[:4].sum():.6f}'],
           ['xEB','0,2891','0,2888','0,2811','0,2795',f'{fraction(BASE):.6f}'],
           ['xDEB','0,0501','0,0500','0,0531','0,0523',f'{BASE[3]/BASE[:4].sum():.6f}']], [75,85,85,90,85,95])
    p(f'Temperatura reconstruída: <b>{TNOM:.6f} °C</b>. Remoção de calor efetiva: <b>{Q0*4184/3.6e9:.6f} MW</b>. Ela fecha o balanço com os coeficientes de capacidade calorífica e densidade impressos no TFC. O TFC afirma que Q foi ajustado, mas não publica o valor usado. A carga de 10,3 MW de Luyben e as revisões Aspen não são reproduzidas por essa calibração.')
    p('A densidade molar constante impressa também difere da soma das concentrações calculadas. Essas aproximações do modelo reduzido foram mantidas e declaradas. A calibração de um ponto não identifica propriedades termodinâmicas nem valida a dinâmica industrial.')
    table([['Item','Valor / hipótese'],['Estados','CE, CB, CEB, CDEB [kmol/m³] e T [°C]'],['Medição','Somente T, desvio padrão sintético de 1,5 °C'],['Entradas conhecidas','Vazões comandadas e temperaturas de alimentação; sem estados reais'],['SISO','xEB por vazão de etileno; Q comandado fixo'],['MIMO','xEB e T por etileno e remoção de calor ideal'],['Restrição térmica','165 °C, hipótese de estudo ausente no TFC'],['Atuação','fE: 0,04-2,0 do nominal; Q MIMO: 0,6-1,4 do efetivo']],[115,400])
    story.append(PageBreak())
    title('2. Arquiteturas e comparação justa')
    table([['Estimador','Dinâmica e adaptação'],['UKF Q0','Modelo físico; Q diagonal nominal constante'],['UKF validado',f'Modelo físico; Q constante = {tuning["chosen_factor"]:g} × Q0, escolhida em validação'],['LSTM-UKF','Modelo físico; LSTM fornece fatores positivos para Q'],['NAKE-BB','Transição MLP aprendida; correção UKF/Joseph; Q adaptado pelas inovações anteriores'],['LSTM-NAKE','Transição MLP aprendida; LSTM separada fornece os fatores de Q']],[110,405])
    p('NAKE é o nome de trabalho desta arquitetura de pesquisa. O ganho de Kalman é calculado pela covariância; não foi treinado. Não é uma reprodução de KalmanNet. Na predição blackbox, a dinâmica inteira é uma função aprendida, sem resíduo de balanços físicos durante a operação. A medição conhecida h(x)=T permanece comum a todos os filtros.')
    p('As duas LSTMs têm 17 entradas, janela de 12 amostras, 16 células e cinco saídas. Os pesos recorrentes e as portas são treinados por BPTT/Adam. Estimativas anteriores, comandos e inovações passadas são as entradas online. Concentrações reais e erros de modelo entram apenas no treinamento offline e na pontuação.')
    p(f'Preditor MLP: 12-48-48-5, com incremento afim aprendido e oito subpassos. Treino: {training["training_samples"]:,} exemplos sintéticos, em sementes distintas da validação e dos testes. Erro de temperatura por passo nas trajetórias de validação: {training["trajectory_one_step_rmse"][4]:.4f} °C; em trajetórias de uma hora: {training["rollout_rmse"][4]:.4f} °C. Não houve seleção por desempenho de controle.')
    p(f'As LSTMs exploraram 150 épocas; a menor perda de validação selecionou a época {lstm["models"]["physical"]["epoch"]} na versão física e {lstm["models"]["neural"]["epoch"]} na neural. A seleção precoce e os erros de previsão de log-Q são reportados em training_lstm.json. Eles limitam qualquer alegação de superioridade da aprendizagem.')
    p('O UKF validado foi escolhido em 16 trajetórias novas, com fatores candidatos 0,25; 1; 4; 16; 64; 100. O critério combina RMSE de composição e temperatura. A matriz selecionada é fixa em todos os ensaios de teste, sem ressintonia por cenário.')
    p('Todos os ensaios de controle duram 10 h e partem do equilíbrio com uma estimativa inicial enviesada comum. As perturbações originais são preservadas em 5 h: +50% benzeno e -50% reciclo. Testes novos: servo ±10% em 3 h, retorno em 7 h; perda térmica de 20%; mudança cinética com ruído triplicado e falta do sensor de 5,5 a 6 h. São usadas três sementes pareadas.')
    p('SISO acompanha apenas xEB; MIMO acrescenta T ao objetivo. O efeito de um segundo atuador e de uma segunda variável controlada está presente no resultado. A comparação separa composição, temperatura e esforço para tornar esse compromisso visível.','SmallEB')
    story.append(PageBreak())
    for con in [True,False]:
        title('3. Controle com restrição térmica' if con else '4. Controle sem restrição térmica')
        p('IAE após evento é a integral de |xEB - referência| em 3-10 h nos testes servo e 5-10 h nos regulatórios. A tabela usa a média dos seis casos e três sementes. O ganho é a média das razões pareadas contra UKF validado + NMPC físico do mesmo modo. Positivo indica menor IAE.')
        tab=[['Estimador','NMPC','IAE × 10³','Ganho (%)','Tmax (°C)','Ultrapassagens','Emergências']]
        for r in [s for s in summary if s['constrained']==con]:
            tab.append([EL[r['estimator']],('Físico ' if r['prediction']=='physical' else 'BB ')+r['mode'].upper(),
                        f'{r["IAE_event_mean"]*1000:.3f}',f'{r["macro_gain_vs_tuned_pct"]:+.1f}',f'{r["Tmax_C"]:.2f}',
                        f'{r["actual_violating_runs"]}/18',r['fallbacks']])
        table(tab,[91,83,65,61,66,80,69])
        p('Tmax e ultrapassagens são da planta simulada, inclusive em ensaios sem restrição. Emergências são aplicações da política de fallback. Um comando de emergência pode superar o limite normal de variação de atuação; está incluído nas métricas, e não é creditado ao otimizador como uma solução factível.','SmallEB')
        p('As tabelas completas por cenário e semente, incluindo ISE, ITAE, erro dos estados, esforço e tempos do solver, acompanham o código. A média não implica ganho em todos os regimes.','SmallEB')
        p('A versão blackbox SISO apresentou pior desempenho agregado em várias combinações, apesar do pequeno erro de predição em validação. A qualidade de previsão em dados separados não certifica o desempenho da otimização em malha fechada.','SmallEB')
        story.append(PageBreak())
    title('5. Controle original: evidências recuperadas')
    p('As Tabelas 4.1-4.4 e as Figuras 4.4, 4.7 e 4.8 foram recuperadas do PDF original. A tabela abaixo transcreve os valores publicados, mantendo a ordem das colunas: malha fechada e malha aberta. Os dois degraus ocorrem em 5 h, em simulações de 10 h. As integrais históricas incluem a partida mostrada nas figuras; a janela exata de cálculo não é detalhada.')
    tab=[['Perturbação','Malha / TFC','IAE','ITAE','ISE']]
    for case in ['benzene_50','recycle_minus50']:
        for loop,label in [('closed','Fechada: PI + FKE'),('open','Aberta')]:
            r=historical['control'][case][loop]
            tab.append([CL[case],label]+[f'{r[k]:.4f}' for k in ['IAE','ITAE','ISE']])
    table(tab,[115,145,85,85,85])
    p('<b>Inconsistência preservada:</b> no caso benzeno +50%, a Tabela 4.3 publica IAE 62,9% maior e ISE 537,5% maior na malha fechada, embora o texto afirme melhoria. Somente ITAE é menor. No caso reciclo -50%, as três métricas publicadas são menores em malha fechada. Não foram trocadas colunas para favorecer a conclusão.')
    title('Observador original e observadores novos')
    p('A Tabela 4.2 publica MAE = 1,626 × 10⁻⁵ e RMSE = 0,000514 para xEB. A Figura 4.5 adjacente cobre 0-5 h; a janela, P, Q, R e amostragem usados no cálculo não são especificados. Estes valores são referências históricas descritivas, sem cálculo de ganho percentual contra os testes novos.')
    tab=[['Observador','MAE novo 0-5 h','RMSE novo 0-5 h','RMSE novo 5-10 h']]
    for e,label in [('ekf_reconstructed','FKE reconstruído'),('ukf_tuned','UKF validado'),('lstm_ukf','LSTM-UKF')]:
        r=next(x for x in obs_comparison['new'] if x['estimator']==e)
        tab.append([label,f'{r["MAE_first5"]:.7f}',f'{r["RMSE_first5"]:.7f}',f'{r["RMSE_after5"]:.7f}'])
    table(tab,[125,130,130,130])
    p('Médias de três sementes no ensaio nominal em malha aberta, com estados e medições idênticos para todos os observadores novos. O erro inicial enviesado domina 0-5 h. O RMSE novo nessa janela é maior que o RMSE publicado; a comparação não comprova melhoria do observador em relação ao TFC. A avaliação causal entre métodos novos usa o protocolo pareado.','SmallEB')
    p('As planilhas de sensibilidade do ZIP contêm varreduras estáticas, não trajetórias temporais do PI + FKE. Não foram encontrados o modelo executável deste reator e os vetores brutos dos ensaios históricos. Os arquivos e os valores originais permanecem preservados.','SmallEB')
    story.append(PageBreak())
    title('6. Houve melhoria? Referência PI + FKE comum')
    relay=pi_tuning['relay']
    p(f'Foi implementado FKE com o mesmo modelo físico e Jacobiana exata. Q constante = {pi_tuning["EKF_Q_factor"]:g} × Q0 foi escolhido em validação independente. O PI segue a receita de relé do TFC: Kc = Kcu/2,2; Ti = Tu/1,2. Um ensaio nominal separado produziu Kcu = {relay["Kcu"]:.4f}, Tu = {relay["period_h"]:.3f} h, Kc = {relay["Kp"]:.4f} e Ti = {relay["Ti_h"]:.3f} h. São ganhos reconstruídos, pois os ganhos numéricos originais não são publicados.')
    p('Válvula equipercentual 50, limites comuns 0,04-2 vezes o nominal, variação máxima 0,12 por amostra e anti-windup declarado. Os 18 testes PI + FKE usam o mesmo equilíbrio, viés inicial, planta DOP853, ruído, sementes e degraus dos 720 testes NMPC. Q de calor permanece fixo. O PI não recebe a nova restrição de 165 °C.')
    chart('Etilbenzeno_Melhoria_PI_FKE.png',223)
    tab=[['Cenário','UKF validado + físico SISO','LSTM-UKF + físico SISO']]
    for case in ['benzene_50','recycle_minus50','servo_up','servo_down','thermal_loss','kinetics_noise']:
        tab.append([CL[case]]+[f'{next(r["paired_gain_mean_pct"] for r in pi_gains if (r["case"],r["estimator"],r["prediction"],r["mode"],r["constrained"])==(case,e,"physical","siso",False)):+.2f}%' for e in ['ukf_tuned','lstm_ukf']])
    table(tab,[175,170,170])
    p('<b>Ganho = 100 × (1 − IAE_evento novo / IAE_evento PI + FKE)</b>, média de três razões pareadas. Positivo melhora; negativo piora. Janela 3-10 h nos servos e 5-10 h nos demais casos. SISO sem restrição é a comparação de mesmo atuador e objetivo. MIMO acrescenta atuador e objetivo térmico; a restrição acrescenta uma exigência ausente no PI original.','SmallEB')
    p('O ganho de aproximadamente 98% no reciclo reflete também a resposta oscilatória deste PI reconstruído à perturbação. Depende da nova sintonia e do modelo efetivo; não pode ser apresentado como ganho comprovado sobre o PI executado no TFC. Há perdas nos servos, no caso cinético e em várias combinações neurais.','SmallEB')
    story.append(PageBreak())
    title('7. Curvas e integrais: confronto com o TFC')
    chart('Etilbenzeno_TFC_Original.png',380)
    p('Digitalização aproximada das figuras originais: duas linhas de pixel equivalem a cerca de ±0,0040 na partida, ±0,0021 no benzeno e ±0,0018 no reciclo. Sobreposições longas e áreas de legenda permanecem sem dados. A Figura 4.8 tem identificação de malha ambígua; as cores e rótulos originais são preservados. Trajetórias novas: semente 9002.','SmallEB')
    tab=[['Método novo, sem restrição','IAE 0-10 h B+50%','IAE 0-10 h R−50%','Tmax B / R (°C)']]
    for method,label,e,m in [('PI + EKF reconstructed','PI + FKE reconstruído','ekf_reconstructed','siso'),('ukf_tuned physical siso','UKF validado / físico SISO','ukf_tuned','siso'),('lstm_ukf physical siso','LSTM-UKF / físico SISO','lstm_ukf','siso'),('lstm_ukf physical mimo','LSTM-UKF / físico MIMO','lstm_ukf','mimo')]:
        vals=[next(r['IAE'] for r in pi_comparison if r['case']==case and r['method']==method) for case in ['benzene_50','recycle_minus50']]
        temps=[next(r['Tmax_C'] if e!='ekf_reconstructed' else r['PI_EKF_Tmax_C'] for r in pi_gains if (r['case'],r['estimator'],r['prediction'],r['mode'],r['constrained'])==(case,e if e!='ekf_reconstructed' else 'ukf_tuned','physical',m,False)) for case in ['benzene_50','recycle_minus50']]
        tab.append([label]+[f'{v:.6f}' for v in vals]+[f'{temps[0]:.2f} / {temps[1]:.2f}'])
    table(tab,[188,108,108,111])
    p('IAE é a média de três sementes; Tmax é o máximo entre as três. Reduzir erro de composição não garante operar abaixo de 165 °C. As integrais novas de 0-10 h não incluem a partida do TFC: sua diferença em relação às Tabelas 4.3-4.4 não pode ser atribuída somente ao controlador. O ganho causal informado usa exclusivamente a referência reconstruída nas mesmas condições.','SmallEB')
    story.append(PageBreak())
    title('8. Controle servo: mudanças de composição')
    chart('Etilbenzeno_Servo.png',415)
    p('A referência de xEB aumenta ou diminui 10% em 3 h, retornando ao nominal em 7 h. São novos ensaios servo, com a mesma definição usada nas 20 configurações. O controlador recebe somente a referência atual e não prevê o retorno futuro.')
    p('O limite térmico compete com uma referência de maior produção. Os gráficos mostram esse compromisso para uma semente comum; os erros integrados incluem a permanência na nova referência e o retorno ao ponto nominal. As três sementes e as duas condições de restrição permanecem disponíveis nas métricas e trajetórias.','SmallEB')
    story.append(PageBreak())
    title('9. Regulatórios nas magnitudes do TFC')
    chart('Etilbenzeno_Regulatorio.png',415)
    p('São preservadas as magnitudes e o instante de perturbação do TFC. O estado inicial aqui é o equilíbrio reconstruído: não se atribuem estes resultados à partida histórica do Simulink. A planta recebe ruído nas entradas e no sensor. As trajetórias mostram a composição simulada, não a estimativa apresentada ao controlador.')
    p('A segunda atuação térmica permite ajustar a remoção de calor enquanto o etileno busca a referência de composição. No SISO, a temperatura depende da mesma vazão usada para xEB; o limite térmico pode exigir sacrificar a referência de composição. A carga térmica efetiva pertence ao modelo reduzido, e não deve ser transposta diretamente ao equipamento real.','SmallEB')
    story.append(PageBreak())
    title('10. Perda térmica e cinética desconhecida')
    chart('Etilbenzeno_Robustez.png',415)
    p('Na perda térmica, a planta remove somente 80% do calor comandado, sem informar essa eficiência ao observador ou ao NMPC. No teste cinético, os fatores são k1 × 1,25; k2 × 0,90; k3 × 1,10. O ruído nas entradas triplica e o sensor fica indisponível durante meia hora.')
    p('O ajuste de Q pode acelerar a correção quando a dinâmica prevista deixa de representar a planta. Ele não identifica automaticamente os novos parâmetros cinéticos. Uma medição de temperatura oferece informação limitada sobre quatro concentrações e reações concorrentes; os resultados de estimação mostram essa limitação.','SmallEB')
    story.append(PageBreak())
    title('11. Estimação isolada do efeito do controlador')
    chart('Etilbenzeno_Estimadores.png',218)
    table([['Caso','UKF Q0','UKF val.','LSTM-UKF','NAKE-BB','LSTM-NAKE']]+[
      [('Nominal' if c=='servo_up' else CL[c])]+[f'{next(r["xEB_RMSE_mean"] for r in observer if r["case"]==c and r["estimator"]==e):.6f}' for e in ESTIMATORS]
      for c in ['servo_up','benzene_50','recycle_minus50','thermal_loss','kinetics_noise']], [128,77,77,77,77,79])
    p('RMSE de xEB após 5 h, média de três sementes. Cada observador recebe a mesma trajetória e as mesmas medições. O caso “nominal” corresponde à trajetória sem alteração de atuação; uma referência servo não produz movimento em malha aberta.')
    p('A adaptação neural deve ser comparada também com o UKF ressintonizado. Quando a alteração principal é térmica, um Q maior pode melhorar muito a correção mesmo sem rede neural. Quando a cinética muda, os cinco estimadores continuam sujeitos à falta de informação sobre as concentrações. Os gráficos não sustentam uma superioridade universal de LSTM ou NAKE.')
    story.append(PageBreak())
    title('12. Verificação, reexecução e limites')
    p(f'<b>Verificação dos dados:</b> {audit["unique_runs"]} combinações de caso/configuração/restrição/semente únicas; {audit["samples"]:,} amostras registradas. Foi conferido cada arquivo de trajetória e reintegrado um ensaio por combinação de estimador, preditor, modo e restrição ({audit["reintegration_count"]} ensaios), reproduzindo os estados e as integrais registradas.')
    p(f'<b>Solver:</b> {audit["solver_failed_statuses"]} retornos com status de falha; {audit["fallbacks"]} ações de emergência; {audit["normal_move_rate_overrides"]} alterações acima da taxa normal. A maior ultrapassagem prevista em candidatos aceitos foi {audit["maximum_accepted_predicted_temperature_excess_C"]:.6g} °C, dentro da tolerância numérica da otimização. Foram registradas {audit["covariance_repairs"]} correções de covariância e {audit["positivity_projections"]} projeções de positividade.')
    p(f'<b>Referência histórica reconstruída:</b> {pi_audit["control_runs"]} ensaios de controle e {pi_audit["observer_runs"]} de estimação; {pi_audit["reintegrated_samples"]} amostras PI reintegradas. Erro máximo nos estados e integrais: {pi_audit["state_max_abs_error"]:.1g} e {pi_audit["metric_max_abs_error"]:.1g}; erro entre trajetórias comuns de estimação: {pi_audit["paired_truth_max_abs_error"]:.1g}. Limites de atuação, taxa, covariâncias e Q positivo foram conferidos.')
    p('Nove testes próprios verificam unidades e equilíbrio, conservação estequiométrica, DOP853 independente, inferência exportada, derivadas por diferenças finitas, BPTT, concordância C/CasADi/NumPy, Q causal, ausência de medição, factibilidade prevista, Jacobiana do FKE e reversão do PI saturado. O núcleo CSTR anterior permanece testado separadamente.')
    p('A integração da planta usa DOP853; a predição física usa RK4. O NMPC usa SLSQP com derivadas exatas. A compilação neural apenas aplica pesos aprendidos e a regra da cadeia. Horizonte: 40 amostras (1 h), quatro movimentos, blocos iniciais de cinco amostras. Amostragem: 90 s. O solver não conhece eventos futuros nem estados reais.')
    p('Os tempos registrados foram medidos com execuções concorrentes em ambiente computacional compartilhado. Eles não são uma certificação de execução em tempo real no hardware industrial. A política de emergência e o monitor de domínio pertencem à simulação e não substituem um sistema de proteção de planta.')
    p('<b>Reprodução:</b> requirements.txt; train.py; experiment.py; tuning.py; baseline.py; historical.py; audit.py e report.py. Pesos JSON, protocolo, métricas, tabelas históricas, curvas digitalizadas e manifesto estão no repositório. Trajetórias NPZ são fornecidas separadamente. Q e covariâncias registrados têm unidades físicas dos estados ao quadrado.')
    p('Três sementes permitem uma comparação preliminar. O estudo não identifica propriedades, não executa Aspen/MATLAB, não modela pressões ou fases e não reproduz as colunas e os reciclos completos. O limite de 165 °C e as capacidades de atuação são hipóteses declaradas. A implantação na planta completa exige reproduzir e validar a dinâmica original no simulador industrial.')
    title('Referências')
    p('Brandão, W. Y. A. (2016). Uso de sensores virtuais como observadores de estado aplicados na dinâmica e controle de processos químicos lineares e não lineares. TFC, UFPB. Arquivo original e TFC.zip fornecidos pelo autor.','SmallEB')
    p('Luyben, W. L. (2011). Design and control of the ethyl benzene process. AIChE Journal 57(3), 655-670. DOI 10.1002/aic.12289. PDF incluído nos originais.','SmallEB')
    p('Julier e Uhlmann (2004). Unscented Filtering and Nonlinear Estimation. DOI 10.1109/JPROC.2003.823141. Hochreiter e Schmidhuber (1997). Long Short-Term Memory. DOI 10.1162/neco.1997.9.8.1735. Revach et al. (2022). KalmanNet. arXiv:2107.10043; referência relacionada, não reproduzida.','SmallEB')
    def footer(c,doc):
        c.saveState();c.setStrokeColor(colors.HexColor('#e2e8f0'));c.line(40,35,555,35);c.setFont('DV',7);c.setFillColor(colors.HexColor('#64748b'));c.drawString(40,23,'Walter Yanko | Etilbenzeno | Modelo reduzido e resultados simulados');c.drawRightString(555,23,str(doc.page));c.restoreState()
    SimpleDocTemplate(str(out/'Etilbenzeno_LSTM_NAKE_NMPC_Relatorio.pdf'),pagesize=A4,leftMargin=40,rightMargin=40,topMargin=36,bottomMargin=46,
                      title='Etilbenzeno: LSTM, UKF, NAKE e NMPC',author='Walter Yanko de Aragão Brandão',
                      subject='Comparação simulada de estimadores e controladores no primeiro reator do TFC').build(story,onFirstPage=footer,onLaterPages=footer)

def markdown(summary,observer,rows):
    lines=['# Etilbenzeno: resultados simulados','',f'20 configurações; {len(rows)} ensaios de controle; 75 ensaios de observadores. Primeiro reator do TFC, reconstruído.','',
           f'Equilíbrio: T={TNOM:.6f} C, xEB={fraction(BASE):.6f}; Q efetivo={Q0*4184/3.6e9:.6f} MW. Limite de pesquisa assumido: 165 C.','',
           'Ganho de IAE após evento: média das razões pareadas vs UKF validado + NMPC físico, no mesmo modo. Positivo=melhora. MIMO acrescenta objetivo térmico e atuador, portanto seu efeito inclui essa mudança de projeto.','']
    for con in [True,False]:
        lines+=['## '+('Restrição ativada' if con else 'Restrição desativada'),'','| Estimador | Preditor | Modo | IAE média evento | Ganho vs UKF val. | Tmax C | Runs >165 C | Fallbacks |','|---|---|---|---:|---:|---:|---:|---:|']
        for r in summary:
            if r['constrained']!=con:continue
            lines.append(f'| {EL[r["estimator"]]} | {r["prediction"]} | {r["mode"]} | {r["IAE_event_mean"]:.7f} | {r["macro_gain_vs_tuned_pct"]:+.2f}% | {r["Tmax_C"]:.3f} | {r["actual_violating_runs"]}/{r["runs"]} | {r["fallbacks"]} |')
        lines+=['']
    lines+=['## Estimação sem controle','','| Caso | UKF Q0 | UKF validado | LSTM-UKF | NAKE-BB | LSTM-NAKE |','|---|---:|---:|---:|---:|---:|']
    for c in ['servo_up','benzene_50','recycle_minus50','thermal_loss','kinetics_noise']:
        lines.append('| '+('Nominal' if c=='servo_up' else CL[c])+' | '+' | '.join(f'{next(r["xEB_RMSE_mean"] for r in observer if r["case"]==c and r["estimator"]==e):.7f}' for e in ESTIMATORS)+' |')
    lines+=['','RMSE de xEB após 5 h. Mesmas trajetórias por caso/semente. Redes e Q fixo selecionados em validação independente. Não há ganho universal de aprendizagem.','',
            'A comparação com as tabelas e curvas originais e com 18 ensaios PI + FKE reconstruídos está em [COMPARACAO_TFC.md](COMPARACAO_TFC.md). Os ganhos nesta página usam o UKF novo, não o controle original do TFC.','',
            'Originais conferidos: TFC.zip, PDF do TFC, Luyben 2011 e exportação Aspen. Não executado no Aspen/MATLAB. Capacidade/densidade constantes e Q efetivo são aproximações do reator reduzido; a planta completa não está reproduzida. Ver README, manifesto, protocolo e auditoria.']
    (RESULTS/'RESULTADOS.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    rows,obs,summary,observer=data();heatmap(summary,args.output)
    traces(['servo_up','servo_down'],args.output,'Etilbenzeno_Servo.png')
    traces(['benzene_50','recycle_minus50'],args.output,'Etilbenzeno_Regulatorio.png')
    traces(['thermal_loss','kinetics_noise'],args.output,'Etilbenzeno_Robustez.png')
    observer_chart(observer,args.output);markdown(summary,observer,rows);pdf(rows,obs,summary,observer,args.output)
