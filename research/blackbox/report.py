"""Create a source-qualified Portuguese report from the completed benchmark."""
from pathlib import Path
import argparse,csv,json,shutil
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,PageBreak
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from common import *
from protocol import CASES,CONFIGS

KINDS=list(CONFIGS);SHORT=['P/U','P/N','N/U','N/N']
LABELS={k:CONFIGS[k]['label'] for k in KINDS}
COLORS=['#334155','#0d9488','#d97706','#8b5cf6']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})

def summarize(records):
    cells=[]
    for c in CASES:
        for on in [False,True]:
            for k in KINDS:
                a=[r for r in records if r['case']==c and r['constrained']==on and r['configuration']==k]
                if not a:raise ValueError('Missing benchmark cell '+str((c,on,k)))
                full=[r for r in a if r['completed']];s=dict(case=c,constrained=on,configuration=k,
                    completed_count=len(full),count=len(a),stopped_count=len(a)-len(full))
                for metric in ['IAE','ISE','ITAE','ITSE','CC_estimation_RMSE','CC_coverage95','NIS_mean','NEES_mean',
                      'coolant_total_kmol','control_TV_kmol_h','normalized_control_effort',
                      'solver_latency_median_ms','solver_latency_p95_ms','estimator_latency_median_ms']:
                    s[metric]=float(np.mean([r[metric] for r in full])) if full else None
                s['T_max']=max(r.get('T_max',0) for r in a)
                s['thermal_violation_K']=max(r.get('thermal_violation_K',0) for r in a)
                s['thermal_violation_runs']=sum(r.get('thermal_violation_K',0)>.001 for r in a)
                s['time_above344_h']=float(np.mean([r.get('time_above344_h',0) for r in a]))
                s['solver_failures']=sum(r.get('solver_failure_count',0) for r in a)
                s['fallbacks']=sum(r.get('fallback_count',0) for r in a)
                cells.append(s)
    by={(r['case'],r['constrained'],r['configuration']):r for r in cells}
    gains=[]
    for c in CASES:
        for on in [False,True]:
            base=by[c,on,'physical_ukf']
            for k in KINDS[1:]:
                candidate=by[c,on,k];g=None
                # A smaller partial IAE never wins against a complete baseline.
                if candidate['completed_count']==candidate['count'] and base['completed_count']==base['count']:
                    g=100*(1-candidate['IAE']/base['IAE'])
                gains.append(dict(case=c,constrained=on,configuration=k,IAE_reduction_pct=g))
    macro={}
    for on in [False,True]:
        for k in KINDS[1:]:
            a=[g for g in gains if g['constrained']==on and g['configuration']==k and g['IAE_reduction_pct'] is not None]
            macro[k+'_'+str(on)]=dict(mean_case_reduction_pct=float(np.mean([g['IAE_reduction_pct'] for g in a])) if a else None,
                comparable_cases=len(a),wins=sum(g['IAE_reduction_pct']>0 for g in a))
    return dict(cells=cells,gains=gains,macro=macro,runs=len(records),
      complete_runs=sum(r['completed'] for r in records),
      incomplete_runs=[r for r in records if not r['completed']],
      solver_failures=sum(r.get('solver_failure_count',0) for r in records),
      fallbacks=sum(r.get('fallback_count',0) for r in records),
      covariance_repairs=sum(r.get('estimator_covariance_repairs',0) for r in records))

def trace_figure(out,case,seed=8001):
    fig,axs=plt.subplots(3,2,figsize=(13.2,8.3),sharex=True,layout='constrained')
    for col,on in enumerate([False,True]):
        for i,k in enumerate(KINDS):
            path=RESULTS/'traces'/f'{case}__{k}__{"on" if on else "off"}__{seed}.csv'
            d=np.genfromtxt(path,delimiter=',',names=True)
            for row,field in enumerate(['CC_true','T_true','mw']):
                axs[row,col].plot(d['time_h'],d[field],color=COLORS[i],label=SHORT[i],lw=1.2)
            if i==0:axs[0,col].plot(d['time_h'],d['CC_ref'],color='black',ls='--',lw=.8,label='Setpoint')
        axs[0,col].set_title('Com restrição de 344 K' if on else 'Sem restrição de 344 K',loc='left',fontweight='bold')
        axs[1,col].axhline(344,color='#dc2626',ls='--',lw=.9,label='344 K')
        axs[1,col].axhline(355.4,color='#64748b',ls=':',lw=.8,label='Parada: 355,4 K')
        for row in range(3):axs[row,col].grid(alpha=.12)
        axs[2,col].set_xlabel('Tempo (h)')
    for row,lab in enumerate(['C_C (kmol/m³)','T (K)','m_w (kmol/h)']):axs[row,0].set_ylabel(lab)
    axs[0,0].legend(frameon=False,ncol=5,fontsize=8,loc='upper left')
    axs[1,0].legend(frameon=False,fontsize=7,loc='upper left')
    fig.suptitle(CASES[case]['label']+' · semente 8001 · temperatura e CC reais da planta simulada',fontsize=13,fontweight='bold')
    name='CSTR_Blackbox_'+('Termico' if case=='thermal_servo' else 'Partida')+'.png'
    fig.savefig(out/name,dpi=155);plt.close(fig);return name

def heatmap(out,summary):
    fig,axs=plt.subplots(1,2,figsize=(13.2,7.7),sharey=True,layout='constrained')
    for j,on in enumerate([False,True]):
        matrix=np.full((len(CASES),3),np.nan)
        for i,c in enumerate(CASES):
            for col,k in enumerate(KINDS[1:]):
                v=next(g['IAE_reduction_pct'] for g in summary['gains'] if g['case']==c and g['constrained']==on and g['configuration']==k)
                if v is not None:matrix[i,col]=v
        im=axs[j].imshow(np.ma.masked_invalid(matrix),cmap='RdYlGn',norm=TwoSlopeNorm(0,vmin=-25,vmax=25),aspect='auto')
        for (i,col),v in np.ndenumerate(matrix):
            axs[j].text(col,i,'parcial' if not np.isfinite(v) else f'{v:+.1f}%',ha='center',va='center',fontsize=10,
                         color='#0f172a',fontweight='bold')
        axs[j].set_xticks(range(3),['IA no NAKE','IA no NMPC','IA em ambos']);axs[j].set_title('Com limite de 344 K' if on else 'Sem limite de 344 K',loc='left',fontweight='bold',pad=12)
        axs[j].tick_params(axis='both',length=0);axs[j].set_yticks(range(len(CASES)),[c['label'] for c in CASES.values()])
        axs[j].spines[['left','bottom']].set_visible(False)
    cb=fig.colorbar(im,ax=axs,shrink=.75,pad=.025);cb.set_label('Redução do IAE versus NMPC físico + UKF (%)')
    fig.suptitle('IA no NMPC e no NAKE: efeito no controle',fontsize=18,fontweight='bold',x=.03,ha='left')
    fig.supxlabel('Positivo: menor erro integrado. Negativo: piora. Média de 3 sementes; cores saturam em ±25%.',fontsize=10)
    fig.savefig(out/'CSTR_Blackbox_Comparacao.png',dpi=170);plt.close(fig)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',default=str(RESULTS/'report'));args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    records=json.loads((RESULTS/'metrics.json').read_text());training=json.loads((RESULTS/'training.json').read_text())
    protocol=json.loads((RESULTS/'protocol.json').read_text());s=summarize(records)
    expected=protocol['run_count']
    if len(records)!=expected:raise ValueError(f'Incomplete batch: {len(records)} of {expected}')
    dump(RESULTS/'summary.json',s)
    with (RESULTS/'summary.csv').open('w',newline='') as f:
        wr=csv.DictWriter(f,list(s['cells'][0]),lineterminator='\n');wr.writeheader();wr.writerows(s['cells'])
    heatmap(out,s);thermal=trace_figure(out,'thermal_servo');startup=trace_figure(out,'startup')
    by={(r['case'],r['constrained'],r['configuration']):r for r in s['cells']}
    lines=['# IA black-box no NMPC e no NAKE - malha fechada','',
       f"{s['runs']} execuções; {s['complete_runs']} completas; {len(s['incomplete_runs'])} interrompidas. Três sementes independentes por combinação.",
       '', 'P/U = NMPC físico+UKF; P/N=físico+NAKE-BB; N/U=neural+UKF; N/N=neural+NAKE-BB.',
       'IAE calculado com CC real da planta simulada. Unidades: kmol h/m³. Média de trajetórias completas; `*` indica que alguma semente foi interrompida.', '']
    for on in [False,True]:
        lines+=['## '+('Com' if on else 'Sem')+' restrição de 344 K','','| Caso | P/U | P/N | N/U | N/N |','|---|---:|---:|---:|---:|']
        for c in CASES:
            vals=[]
            for k in KINDS:
                a=by[c,on,k];v='-' if a['IAE'] is None else f"{a['IAE']:.6f}"
                vals.append(v+('*' if a['completed_count']<a['count'] else ''))
            lines.append('| '+CASES[c]['label']+' | '+' | '.join(vals)+' |')
        lines.append('')
    lines+=['## Limites da comparação','',
      'Dados sintéticos no modelo com entalpia efetiva calibrada em um ponto; sem dados industriais ou execução MATLAB/Simulink.',
      'A Figura39 e a partida exigem hipóteses explícitas de reconstrução. A penalidade térmica histórica foi substituída por desigualdades na predição.',
      'Uma restrição satisfeita na predição não garante que T real da planta ruidosa respeite344K. Ver Tmax e duração das violações em summary.csv.',
      'Resultados interrompidos no evento355.4K têm IAE parcial e não entram no cálculo de ganhos.',
      f"Falhas declaradas de SLSQP: {s['solver_failures']}; ações de fallback: {s['fallbacks']}; reparos de covariância: {s['covariance_repairs']}.",
      'A versão NAKE-BB usa dinâmica neural e adaptação causal de Q por inovações. Não aprende o ganho K e não é a versão grey-box anterior nem uma reprodução de KalmanNet.']
    if (RESULTS/'metrics_margin.json').exists():
        diag=json.loads((RESULTS/'metrics_margin.json').read_text())
        lines+=['','## Diagnóstico adicional com margem térmica de 4 K','',
          f"{len(diag)} execuções em partida e servo térmico; {sum(r['completed'] for r in diag)} completas. Temperatura máxima {max(r.get('T_max',0) for r in diag):.6f} K; violações de344K {sum(r.get('thermal_violation_K',0)>.001 for r in diag)}.",
          f"Falhas SQP {sum(r.get('solver_failure_count',0) for r in diag)}; fallback de resfriamento máximo {sum(r.get('fallback_count',0) for r in diag)}. Esses eventos ocorreram na partida.",
          'A margem vem do máximo térmico de57passos da validação independente (3.710K), arredondado para4K. A ausência de violações observadas inclui a política de fallback e não constitui garantia geral. Ver metrics_margin.csv e relatório.']
    (RESULTS/'RESULTADOS.md').write_text('\n'.join(lines)+'\n')
    # Stable layouts, explicit page breaks, source and numerical limitations.
    pdfmetrics.registerFont(TTFont('DV','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
    pdfmetrics.registerFont(TTFont('DVB','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
    styles=getSampleStyleSheet()
    for name,font,size,leading,col in [('Body','DV',9.2,13.1,'#334155'),('Small','DV',7.5,10.5,'#475569'),
       ('Head','DVB',14,18,'#0f766e'),('Title','DVB',23,29,'#0f172a')]:
        styles.add(ParagraphStyle('BB'+name,fontName=font,fontSize=size,leading=leading,textColor=colors.HexColor(col),spaceAfter=8))
    story=[]
    def para(t,sty='Body'):story.append(Paragraph(t,styles['BB'+sty]))
    def table(rows,widths):
        cells=[[Paragraph(str(v),styles['BBSmall']) for v in row] for row in rows]
        tbl=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT')
        tbl.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e0f2f1')),
          ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f8fafc')]),
          ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
          ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
        story.extend([tbl,Spacer(1,8)])
    def img(name,w,h):story.extend([Image(str(out/name),width=w,height=h),Spacer(1,8)])
    def page():story.append(PageBreak())
    para('IA no NMPC e no NAKE','Title')
    para('CSTR com equilíbrio ajustado | Controle servo e regulatório | Walter Yanko | Outubro de 2026','Small')
    para('1. Como a IA entra em cada combinação','Head')
    para('No <b>NMPC neural</b>, a rede prevê os seis estados futuros a partir dos estados estimados e dos comandos. O otimizador continua escolhendo a vazão de resfriamento para minimizar o erro de concentração e a variação da ação de controle. A rede é um modelo do processo; não substitui a otimização por uma política de ação.')
    para('No <b>NAKE black-box</b>, a mesma transição neural propaga os pontos sigma. As temperaturas medidas corrigem a estimativa e a covariância por uma atualização de Kalman em forma de Joseph. A covariância Q inclui o erro de validação e é adaptada por uma média móvel das inovações anteriores; fator limitado a 1-25. O ganho K é calculado, não aprendido.')
    table([['Código','Preditor NMPC','Preditor do estimador'],['P/U','Balanços físicos','UKF físico'],['P/N','Balanços físicos','NAKE-BB neural'],['N/U','Rede neural','UKF físico'],['N/N','Rede neural','NAKE-BB neural']],[55,211,211])
    para('O NAKE anterior ajustava UA e k0 dentro dos balanços e era <b>híbrido</b>. Aqui a dinâmica inteira é aprendida: mapa afim e MLP tanh 12-48-48-6, com cinco subpassos aprendidos de 0,003 h. A inferência neural não consulta as equações de reação ou troca térmica. O mapa afim e os pesos também são ajustados aos dados.')
    para('2. Comparação sob as mesmas condições','Head')
    para(f"<b>{s['runs']} execuções</b> = 10 casos x 4 combinações x 2 opções térmicas x 3 sementes. Apenas T e Tt são medidos. A concentração verdadeira é usada offline e nas métricas, nunca no feedback. As combinações compartilham as realizações de ruído e o erro inicial da estimativa.")
    para('A planta usa os balanços com entalpia efetiva <b>-84.138,653537 kJ/kmol</b>, calibrada para T = <b>332,3 K</b> e CC = <b>2,280915 kmol/m³</b>. A calibração é nominal em um único ponto e não identifica a entalpia química real nem recupera o código histórico do Simulink.')
    para('Ts = 0,015 h; p = 57; m = 6; Qe = 0,8; RΔu = 0,2. A variável manipulada é mw entre 22,7 e 1.366,2 kmol/h. Com limite: T predita <= 344 K. Sem limite: apenas essa desigualdade é removida. A planta é interrompida ao atingir 355,4 K.','Small')
    page()
    para('3. Erro de controle nas trajetórias completas','Head')
    para('IAE de CC real em kmol h/m³, média entre sementes. Menor é melhor. P/U: físico + UKF; P/N: físico + NAKE-BB; N/U: neural + UKF; N/N: neural + NAKE-BB. Um asterisco indica que alguma semente não completou o horizonte; o valor então corresponde somente às completas. Se nenhuma completou, aparece um traço.','Small')
    for on in [False,True]:
        para('Com limite de 344 K' if on else 'Sem limite de 344 K','Head')
        rows=[['Caso','P/U','P/N','N/U','N/N']]
        for c in CASES:
            vals=[]
            for k in KINDS:
                r=by[c,on,k];v='-' if r['IAE'] is None else f"{r['IAE']:.5f}"
                vals.append(v+('*' if r['completed_count']<r['count'] else ''))
            rows.append([CASES[c]['label']]+vals)
        table(rows,[177,75,75,75,75])
    para('Os oito primeiros casos seguem degraus descritos no texto histórico. O servo térmico usa +20% em t=3 h, lidos aproximadamente da Figura 39; a partida usa mistura de alimentação sem produto e temperaturas iniciais T0/Ta, hipótese ausente no texto. Esses dois casos são reconstruções explicitamente qualificadas.','Small')
    page()
    para('4. Onde a IA melhora ou piora o controle','Head')
    img('CSTR_Blackbox_Comparacao.png',493,288)
    para('O ganho é 100 x (1 - IAE da combinação / IAE de P/U), com os mesmos testes e as mesmas três sementes. Células com trajetórias incompletas não recebem ganho. Os resultados descrevem este conjunto simulado; três sementes dão uma indicação exploratória e não uma conclusão estatística geral.','Small')
    rows=[['Combinação','Ganho médio por caso sem limite','Com limite','Casos comparáveis sem/com']]
    for k in KINDS[1:]:
        a=s['macro'][k+'_False'];b=s['macro'][k+'_True']
        vals=[('-' if q['mean_case_reduction_pct'] is None else f"{q['mean_case_reduction_pct']:+.2f}%") for q in [a,b]]
        rows.append([LABELS[k],*vals,f"{a['comparable_cases']}/{b['comparable_cases']}"])
    table(rows,[171,104,99,103])
    para('Média das reduções percentuais por caso, com peso igual entre casos comparáveis. A exclusão de trajetórias interrompidas muda o conjunto da média; consulte o número de casos. Melhorar a estimação isolada não implica melhorar o controle. O erro de modelo neural pode acumular ao longo do horizonte.','Small')
    rows=[['Combinação','NMPC mediano (ms)','NAKE/UKF mediano (ms)','Falhas SQP / fallback']]
    for k in KINDS:
        a=[r for r in records if r['configuration']==k and 'solver_latency_median_ms' in r]
        rows.append([LABELS[k],f"{np.mean([r['solver_latency_median_ms'] for r in a]):.3f}",
          f"{np.mean([r['estimator_latency_median_ms'] for r in a]):.3f}",
          f"{sum(r['solver_failure_count'] for r in a)} / {sum(r['fallback_count'] for r in a)}"])
    table(rows,[171,100,112,94])
    para(f"Latências: média dos medianos por execução na CPU local, com {protocol['workers']} processos em paralelo e uma thread BLAS por processo. Compilação e treinamento não estão incluídos. Não são garantias de tempo real ou um benchmark entre máquinas.",'Small')
    page()
    para('5. Controle, temperatura e resfriamento','Head')
    para('Semente 8001, declarada previamente para ilustrar trajetórias. Linhas: P/U cinza, P/N verde, N/U laranja, N/N roxo. A linha tracejada em CC é o setpoint. Os dados são os estados reais da planta simulada, e não apenas as estimativas.','Small')
    img(thermal,493,310)
    img(startup,493,310)
    page()
    para('6. A restrição prevista foi respeitada na planta?','Head')
    para('Temperatura máxima real nas três sementes, com a restrição ativada. A integração independente usa 21 pontos de avaliação em cada intervalo de amostragem. Valores acima de 344 K são violações reais, mesmo que a solução do otimizador tenha sido viável no modelo.','Small')
    rows=[['Caso','P/U','P/N','N/U','N/N']]
    for c in CASES:
        rows.append([CASES[c]['label']]+[f"{by[c,True,k]['T_max']:.3f}" for k in KINDS])
    table(rows,[177,75,75,75,75])
    rows=[['Combinação','Execuções >344 K com limite','Maior excesso (K)','Tempo médio >344 K (h)']]
    for k in KINDS:
        a=[r for r in records if r['constrained'] and r['configuration']==k]
        rows.append([LABELS[k],f"{sum(r.get('thermal_violation_K',0)>.001 for r in a)}/{len(a)}",
          f"{max(r.get('thermal_violation_K',0) for r in a):.3f}",f"{np.mean([r.get('time_above344_h',0) for r in a]):.4f}"])
    table(rows,[171,106,90,110])
    para('A desigualdade de 344 K atua sobre uma predição nominal. Há erro do modelo, erro de estimação e perturbações não observadas. Logo, <b>não há garantia de cumprimento exato na planta</b>. A margem térmica de incerteza precisa ser projetada e validada antes de interpretar esse mecanismo como proteção operacional. Não foi introduzida uma margem escondida nos resultados principais.')
    para(f"A bateria terminou com <b>{s['complete_runs']}/{s['runs']} trajetórias completas</b>; {len(s['incomplete_runs'])} foram interrompidas. Falhas declaradas do SLSQP: {s['solver_failures']}; fallback: {s['fallbacks']}; reparos de covariância: {s['covariance_repairs']}. Um status de falha SQP pode ainda fornecer uma solução numericamente viável; o código registra os dois sinais separadamente. A ação de fallback para predição inviável é resfriamento máximo, idêntica em todas as combinações.",'Small')
    page()
    para('7. Treinamento, validação e reprodução','Head')
    para(f"Treinamento offline: <b>{training['training_samples']:,} transições</b>, excitação aleatória de estados e entradas e 48 trajetórias independentes. Validação: {training['validation_samples']:,} transições e 8 trajetórias. Sementes 6101/6111 para treino, 6201 para validação, 6501 para validação de 57 passos e 8001-8003 para controle. O teste não escolhe os pesos. Seleção por erro de validação de subpasso; Adam e refinamento L-BFGS.")
    rows=[['Estado','RMSE um passo, domínio','Um passo, trajetórias','57 passos sem correção']]
    for i,n in enumerate(STATE_NAMES):
        rows.append([n]+[f'{v[i]:.6f}' for v in [training['one_step_rmse'],training['trajectory_one_step_rmse'],training['rollout']['rmse']]])
    table(rows,[55,140,141,141])
    para(f"Unidades: concentrações em kmol/m³; temperaturas em K. Nos 12 ensaios independentes de 57 passos não houve divergência. O maior erro térmico acumulado foi <b>{training['rollout']['max_error'][4]:.3f} K</b>. A Q neural usa o MSE de um passo nas trajetórias de validação, não o erro dos testes de controle. O domínio aleatório tem erros maiores e é informado separadamente.",'Small')
    para('Hipóteses que distinguem a reprodução do original','Head')
    para('Os degraus regulatórios em FA, FB, T0 e Ta começam em 4 h e retornam em 8 h. Por Ts=0,015 h, entram nos primeiros pontos após esses horários. Percentuais de temperatura são aplicados em Fahrenheit, conforme o texto. O servo severo de -20% permanece após 4 h. Não há antecipação dos degraus no horizonte.')
    para('Ruído sintético: 1% multiplicativo não observado em todas as entradas por amostra e sensores com desvios de 3,323 K e 3,1449 K. A planta usa DOP853; o preditor físico usa RK4. SQP é implementado por SciPy SLSQP e sensibilidades exatas: CasADi físico e regra da cadeia neural compilada em C, conferida contra NumPy. A penalidade térmica QR não especificada no original é substituída por desigualdades. Não foram executados MATLAB/Simulink nem dados de planta real.','Small')
    para('Código, pesos e métricas','Head')
    para('Módulo research/blackbox: train.py, control.py, experiment.py, test_control.py, report.py; pesos em weights/transition_mlp.json. metrics.csv/json incluem IAE/ISE/ITAE/ITSE, estimação, cobertura, esforço, temperatura e solver. Todas as trajetórias brutas são exportadas para CSV. Foram aprovados 26 testes locais: 11 do núcleo, 8 do estimador anterior e 7 novos de controle.','Small')
    para('Fontes','Head')
    para('Brandão, W.Y.A. (2019), Uso de observadores de estado aplicados no controle inferencial preditivo de processos não lineares: equações33-55; seções5.3.1 e5.3.2, pp63-73. Manuscrito PAPER_BRANDAO_W-Y-A_REV05, controle inferencial e limites térmicos.','Small')
    para('Revach etal. (2022), KalmanNet, IEEE TSP, arXiv:2107.10043; Shrivastava (2012), Modeling and Control of CSTR using Model based Neural Network Predictive Control, arXiv:1208.3600; documentação oficial SciPy SLSQP. O NAKE-BB deste estudo é uma variante de pesquisa, não uma reprodução de KalmanNet.','Small')
    marginfile=RESULTS/'metrics_margin.json'
    if marginfile.exists():
        page();diag=json.loads(marginfile.read_text());mcfg=json.loads((RESULTS/'protocol_margin.json').read_text())
        para('8. Diagnóstico adicional: margem térmica','Head')
        para(f"Foram executados <b>{len(diag)} ensaios adicionais</b> nos casos de partida e servo térmico, com as mesmas combinações, sementes e ruídos. A predição foi limitada a <b>344 - {mcfg['temperature_margin_K']:g} = {344-mcfg['temperature_margin_K']:g} K</b>. A margem de 4 K foi escolhida a partir do maior erro térmico de 57 passos na validação independente (3,710 K), arredondado para cima; os testes de controle não escolhem a margem.")
        rows=[['Caso','Combinação','IAE sem margem / com','Tmax sem / com (K)','Execuções >344 K com margem']]
        for c in ['thermal_servo','startup']:
            for k in KINDS:
                a=[r for r in diag if r['case']==c and r['configuration']==k]
                full=[r for r in a if r['completed']];base=by[c,True,k]
                iae='-' if not full else f"{np.mean([r['IAE'] for r in full]):.4f}"
                original='-' if base['IAE'] is None else f"{base['IAE']:.4f}"
                rows.append([CASES[c]['label'],LABELS[k],original+' / '+iae,
                  f"{base['T_max']:.3f} / {max(r.get('T_max',0) for r in a):.3f}",
                  f"{sum(r.get('thermal_violation_K',0)>.001 for r in a)}/{len(a)}"])
        table(rows,[78,119,105,106,69])
        para(f"No diagnóstico houve <b>{sum(r.get('solver_failure_count',0) for r in diag)} status de falha SQP</b> e <b>{sum(r.get('fallback_count',0) for r in diag)} ações de fallback</b>, todas nos ensaios de partida. O fallback usa resfriamento máximo. A ausência de violações observadas pertence ao conjunto controlador + política de fallback; não demonstra que o otimizador sempre resolveu um problema viável.",'Small')
        para('A comparação principal permanece com a desigualdade original de 344 K e sem essa margem. O diagnóstico mostra o custo de afastar a predição do limite: quanto mais restrita a temperatura, maior pode ser o erro de CC quando o setpoint exige temperaturas superiores. São dados simulados em três sementes por célula; ausência de violações observadas não equivale a uma garantia robusta ou probabilística.')
        para('A margem se apoia em um máximo finito de validação, não em um limite formal do erro da rede, e não cobre automaticamente ruídos gaussianos ou todas as regiões da operação. Um NMPC de planta real exigiria identificação com dados medidos, análise de incerteza por região e validação do esquema de proteção.','Small')
    def footer(canvas,doc):
        canvas.saveState();canvas.setFont('DV',7);canvas.setFillColor(colors.HexColor('#64748b'))
        canvas.drawString(42,25,'Walter Yanko | CSTR / IA | resultados simulados, equilíbrio efetivo calibrado')
        canvas.drawRightString(553,25,str(doc.page));canvas.restoreState()
    pdf=out/'CSTR_Blackbox_NMPC_NAKE_Relatorio.pdf'
    SimpleDocTemplate(str(pdf),pagesize=A4,leftMargin=42,rightMargin=42,topMargin=38,bottomMargin=45).build(story,onFirstPage=footer,onLaterPages=footer)
    print(json.dumps({'report':str(pdf),'runs':s['runs'],'complete':s['complete_runs'],'macro':s['macro']},ensure_ascii=False))

if __name__=='__main__':main()
