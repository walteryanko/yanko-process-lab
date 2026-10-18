"""Publication figures and Portuguese report from executed, immutable trial rows."""
import argparse,csv,json,hashlib,html
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from .thesis_cases import *

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'artifacts/thesis'
OUT=ROOT/'reports/thesis'
FIG=OUT/'figures'
METHODS=['UKF_Euler','UKF_RK4','Darwin']
METHOD_LABEL={'UKF_Euler':'UKF Euler','UKF_RK4':'UKF RK4','Darwin':'Darwin'}
THERMAL_LABEL={'open':'Malha aberta','none':'Sem penalização térmica','soft':'Com penalização térmica'}
COLORS={'UKF_Euler':'#c85b29','UKF_RK4':'#327aaf','Darwin':'#008b80'}
STATES=['CA','CB','CC','CM','T','Tt']
STATE_TEX=[r'$C_A$',r'$C_B$',r'$C_C$',r'$C_M$',r'$T$',r'$T_t$']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.labelsize':9,'axes.titlesize':11,
    'axes.spines.top':False,'axes.spines.right':False,'grid.alpha':.18,'axes.grid':True,
    'svg.fonttype':'none','savefig.facecolor':'white'})

def read_rows(name):
    with (DATA/name).open(encoding='utf-8') as f:return list(csv.DictReader(f))

def summary_index():
    return {(r['scenario'],r['thermal'],r['method']):r for r in read_rows('summary.csv')}

def fnum(x,places=4):
    x=float(x)
    if abs(x)<.5*10**(-places):x=0.
    return f'{x:.{places}f}'.replace('.',',')

def load_trace(s,method,thermal):
    seed=410000+SCENARIOS.index(s)*1000
    with np.load(DATA/'trajectories'/s.key/f'{method}_{thermal}_{seed}.npz') as a:
        return {k:a[k] for k in a.files}

def save_figure(fig,name):
    FIG.mkdir(parents=True,exist_ok=True)
    fig.savefig(FIG/f'{name}.png',dpi=190)
    fig.savefig(FIG/f'{name}.svg')
    plt.close(fig)

def mark_events(ax,s):
    for t in sorted({e[0] for e in s.events}):ax.axvline(t,color='#52606d',lw=.7,ls=':',alpha=.55)
    ax.set_xlim(0,s.hours);ax.ticklabel_format(style='plain',axis='y',useOffset=False)
    ax.tick_params(labelsize=8,labelleft=True)

def paired_equal():
    rows=read_rows('metrics.csv');lookup={(r['scenario'],r['thermal'],r['method'],r['seed']):r for r in rows}
    fields=[k for k in rows[0] if k.startswith(('RMSE_','IAE_'))]+['T_peak_K','T_above_limit_h']
    largest=0.
    for r in rows:
        if r['method']!='Darwin':continue
        b=lookup[(r['scenario'],r['thermal'],'UKF_RK4',r['seed'])]
        largest=max(largest,*[abs(float(r[k])-float(b[k])) for k in fields])
    if largest>1e-10:raise AssertionError('Update plot legends: Darwin and RK4 differ.')
    return dict(maximum_absolute_difference=largest,metrics=fields,paired_trials=sum(r['method']=='Darwin' for r in rows))

def state_figure(s):
    closed=s.kind!='open';thermals=['none','soft'] if closed else ['open']
    if closed:fig,axes=plt.subplots(4,2,figsize=(8.2,8.1),sharex=True,sharey='row')
    else:fig,axes=plt.subplots(3,2,figsize=(8.2,6.4),sharex=True)
    fig.subplots_adjust(left=.105,right=.98,bottom=.09,top=.91,hspace=.3,wspace=.29)
    for col,th in enumerate(thermals):
        a=load_trace(s,'UKF_Euler',th);b=load_trace(s,'Darwin',th);t=a['t']
        for j in range(4 if closed else 6):
            ax=axes[j,col] if closed else axes.flat[j]
            if closed:
                for method,z in [('UKF_Euler',a),('Darwin',b)]:
                    ax.plot(t,z['truth'][:,j],color=COLORS[method],lw=1.6)
                    ax.plot(t,z['estimate'][:,j],color=COLORS[method],lw=.9,ls='--',alpha=.9)
                if j==2:ax.step(t,a['reference'],where='post',color='#28343c',ls=':',lw=1.3)
            else:
                ax.plot(t,a['truth'][:,j],color='#263843',lw=1.6)
                ax.plot(t,a['estimate'][:,j],color=COLORS['UKF_Euler'],lw=1.1,ls='--')
                ax.plot(t,b['estimate'][:,j],color=COLORS['Darwin'],lw=1.2,ls='--')
            ax.set_ylabel(STATE_TEX[j]+(' [kmol/m³]' if j<4 else ' [K]'));mark_events(ax,s)
            if j==0 and closed:ax.set_title(THERMAL_LABEL[th],fontweight='bold',pad=8)
            if (closed and j==3) or (not closed and j>=4):ax.set_xlabel('Tempo [h]')
    legend=[Line2D([0],[0],color=COLORS['UKF_Euler'],lw=2,label='UKF Euler'),
            Line2D([0],[0],color=COLORS['Darwin'],lw=2,label='Darwin = UKF RK4')]
    if closed:
        legend += [Line2D([0],[0],color='#53616b',lw=1.5,label='Planta simulada'),Line2D([0],[0],color='#53616b',lw=1.3,ls='--',label='Estimada')]
    else:legend.append(Line2D([0],[0],color='#263843',lw=1.8,label='Planta simulada'))
    fig.legend(handles=legend,loc='upper center',ncol=len(legend),bbox_to_anchor=(.5,1),frameon=False,fontsize=8.5)
    save_figure(fig,s.key+'_estados')

def control_figure(s):
    fig,axes=plt.subplots(3,2,figsize=(8.2,6.3),sharex=True,sharey='row')
    fig.subplots_adjust(left=.105,right=.98,bottom=.09,top=.84,hspace=.34,wspace=.29)
    for col,th in enumerate(['none','soft']):
        for method in ['UKF_Euler','Darwin']:
            z=load_trace(s,method,th);t=z['t'];c=COLORS[method]
            for row,j in enumerate([4,5]):
                axes[row,col].plot(t,z['truth'][:,j],color=c,lw=1.5)
                axes[row,col].plot(t,z['estimate'][:,j],color=c,lw=.9,ls='--')
            axes[2,col].step(t[:-1],z['mw'],where='post',color=c,lw=1.3)
        axes[0,col].axhline(T_LIMIT,color='#b31c45',ls=':',lw=1.4)
        axes[0,col].set_title(THERMAL_LABEL[th],fontweight='bold',pad=8)
        for row,label in enumerate(['T [K]','Tt [K]','mw [kmol/h]']):
            axes[row,col].set_ylabel(label);mark_events(axes[row,col],s)
        axes[2,col].set_xlabel('Tempo [h]')
    handles=[Line2D([0],[0],color=COLORS['UKF_Euler'],lw=2,label='UKF Euler'),
        Line2D([0],[0],color=COLORS['Darwin'],lw=2,label='Darwin = UKF RK4'),
        Line2D([0],[0],color='#52606d',ls='--',label='Temperatura estimada'),
        Line2D([0],[0],color='#b31c45',ls=':',label='Limite: 344,26 K')]
    fig.legend(handles=handles,loc='upper center',ncol=2,bbox_to_anchor=(.5,1),frameon=False,fontsize=9)
    save_figure(fig,s.key+'_temperaturas_controle')

def input_figure(s):
    th='open' if s.kind=='open' else 'none';z=load_trace(s,'Darwin',th);t=z['t']
    fig,axes=plt.subplots(3,2,figsize=(8.2,4.8),sharex=True)
    fig.subplots_adjust(left=.105,right=.98,bottom=.1,top=.9,hspace=.34,wspace=.29)
    indices=list(range(6)) if s.kind=='open' else [0,1,2,4,5,None]
    labels=['FA [kmol/h]','FB [kmol/h]','FM [kmol/h]','mw [kmol/h]','T0 [K]','Ta1 [K]']
    for ax,j in zip(axes.flat,indices):
        if j is None:
            ax.step(t,z['reference'],where='post',color='#273843',lw=1.5);ax.set_ylabel('CC ref. [kmol/m³]')
        else:
            ax.step(t[:-1],z['input_actual_evaluation_only'][:,j],where='post',color='#8caab5',lw=.7,alpha=.8)
            ax.step(t[:-1],z['input_commanded'][:,j],where='post',color='#273843',lw=1.3);ax.set_ylabel(labels[j])
        mark_events(ax,s)
    for ax in axes[-1]:ax.set_xlabel('Tempo [h]')
    fig.legend(handles=[Line2D([0],[0],color='#273843',lw=1.5,label='Valor conhecido pelo observador'),
        Line2D([0],[0],color='#8caab5',lw=1,label='Entrada efetiva com ruído (avaliação)')],
        loc='upper center',ncol=2,bbox_to_anchor=(.5,1),frameon=False,fontsize=8.5)
    save_figure(fig,s.key+'_disturbios')

def overview_figure():
    s=summary_index();closed=[c for c in SCENARIOS if c.kind!='open'];y=np.arange(len(closed))
    fig,axes=plt.subplots(1,2,figsize=(10,6),sharey=True)
    for th,offset,color,label in [('none',-.15,'#327aaf','Sem penalização'),('soft',.15,'#008b80','Com penalização')]:
        values=[float(s[(c.key,th,'Darwin')]['IAE_track_CC']) for c in closed]
        peaks=[float(s[(c.key,th,'Darwin')]['T_peak_K']) for c in closed]
        axes[0].barh(y+offset,values,height=.27,color=color,label=label)
        axes[1].plot(peaks,y+offset,'o',color=color,label=label)
    axes[0].set_yticks(y,[c.key for c in closed]);axes[0].invert_yaxis()
    axes[0].set_xlabel('IAE de CC [kmol·h/m³]');axes[1].set_xlabel('Pico de T [K]')
    axes[0].set_title('Rastreamento de concentração');axes[1].set_title('Exposição térmica')
    axes[1].axvline(T_LIMIT,color='#b31c45',ls=':',label='160 °F')
    axes[0].legend(frameon=False);axes[1].legend(frameon=False)
    fig.suptitle('Darwin / UKF RK4 · médias de 20 realizações',fontweight='bold')
    fig.tight_layout();save_figure(fig,'Resumo_controle_termico')

def make_figures():
    OUT.mkdir(parents=True,exist_ok=True)
    (DATA/'equivalence_check.json').write_text(json.dumps(paired_equal(),indent=2))
    for s in SCENARIOS:
        state_figure(s)
        if s.kind!='open':control_figure(s)
        input_figure(s)
        print('FIGURES',s.key,flush=True)
    overview_figure()

def metric_tables():
    OUT.mkdir(parents=True,exist_ok=True)
    index=summary_index();rows=[]
    for s in SCENARIOS:
        for th in (['open'] if s.kind=='open' else ['none','soft']):
            for method in METHODS:
                r=index[(s.key,th,method)]
                for state in STATES:
                    unit='kmol/m3' if state.startswith('C') else 'K'
                    rows.append(dict(cenario=s.key,condicao=th,metodo=method,tipo='estimacao',variavel=state,n=r['n'],
                        RMSE=r['RMSE_est_'+state],RMSE_IC95_inf=r['RMSE_est_'+state+'_lo'],RMSE_IC95_sup=r['RMSE_est_'+state+'_hi'],
                        unidade_RMSE=unit,IAE=r['IAE_est_'+state],IAE_IC95_inf=r['IAE_est_'+state+'_lo'],IAE_IC95_sup=r['IAE_est_'+state+'_hi'],unidade_IAE=unit+' h'))
                if s.kind!='open':
                    rows.append(dict(cenario=s.key,condicao=th,metodo=method,tipo='controle',variavel='CC',n=r['n'],
                        RMSE=r['RMSE_track_CC'],RMSE_IC95_inf=r['RMSE_track_CC_lo'],RMSE_IC95_sup=r['RMSE_track_CC_hi'],
                        unidade_RMSE='kmol/m3',IAE=r['IAE_track_CC'],IAE_IC95_inf=r['IAE_track_CC_lo'],IAE_IC95_sup=r['IAE_track_CC_hi'],unidade_IAE='kmol h/m3'))
    with (OUT/'Metricas_RMSE_IAE_por_cenario.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter=';');w.writeheader()
        for row in rows:
            w.writerow({k:(v.replace('.',',') if k.startswith(('RMSE','IAE')) and isinstance(v,str) else v) for k,v in row.items()})

def make_pdf():
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph,Table,TableStyle
    from reportlab.lib.utils import ImageReader
    from reportlab.lib.pagesizes import A4
    from matplotlib.font_manager import findfont,FontProperties
    for name,weight in [('DV','normal'),('DVB','bold')]:
        pdfmetrics.registerFont(TTFont(name,findfont(FontProperties(family='DejaVu Sans',weight=weight))))
    pdfmetrics.registerFontFamily('DV',normal='DV',bold='DVB',italic='DV',boldItalic='DVB')
    W,H=A4;left=43;width=W-86
    filename=OUT/'Comparacao_Darwin_Dissertacao.pdf'
    c=canvas.Canvas(str(filename),pagesize=A4)
    c.setTitle('Darwin Observer nos cenários da dissertação — RMSE, IAE e restrição térmica')
    c.setAuthor('Laboratório Darwin Observer — análise computacional para Walter Yanko')
    index=summary_index();execution=json.loads((DATA/'execution.json').read_text());discovery=json.loads((DATA/'discovery.json').read_text())
    page=0;y=0
    style=ParagraphStyle('body',fontName='DV',fontSize=9.1,leading=13.4,textColor=colors.HexColor('#273843'),spaceAfter=6)
    small=ParagraphStyle('small',parent=style,fontSize=7.8,leading=10.6)
    cell=ParagraphStyle('cell',parent=style,fontSize=7.4,leading=10)
    def p(text,small_text=False):
        nonlocal y
        a=Paragraph(text,small if small_text else style);_,h=a.wrap(width,800);a.drawOn(c,left,y-h);y-=h+7
        assert y>=38,(page,'paragraph',y)
    def table(data,widths=None,font=7.7,row_h=None):
        nonlocal y
        t=Table(data,colWidths=widths,rowHeights=row_h,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('FONTNAME',(0,0),(-1,-1),'DV'),('FONTNAME',(0,0),(-1,0),'DVB'),
            ('FONTSIZE',(0,0),(-1,-1),font),('LEADING',(0,0),(-1,-1),font+3),
            ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e5f2f0')),('TEXTCOLOR',(0,0),(-1,0),colors.HexColor('#123e43')),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f5f8fa')]),
            ('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
            ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
            ('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor('#79a7aa'))]))
        _,h=t.wrap(width,800);t.drawOn(c,left,y-h);y-=h+10
        assert y>=38,(page,'table',y,h)
    def picture(name,height):
        nonlocal y
        path=FIG/(name+'.png');ir=ImageReader(str(path));iw,ih=ir.getSize();w=min(width,height*iw/ih);h=w*ih/iw
        c.drawImage(ir,left+(width-w)/2,y-h,width=w,height=h);y-=h+7
        assert y>=38,(page,'image',y)
    def new(title,subtitle=''):
        nonlocal page,y
        if page:c.showPage()
        page+=1;y=H-47
        c.bookmarkPage('page_'+str(page))
        c.addOutlineEntry(title,'page_'+str(page),level=1 if ('temperaturas e atuação' in title or 'distúrbios e erros' in title) else 0)
        c.setFillColor(colors.HexColor('#008b80'));c.rect(left,H-27,46,3,fill=1,stroke=0)
        c.setFillColor(colors.HexColor('#173a47'));c.setFont('DVB',16);c.drawString(left,y,title);y-=24
        if subtitle:p(subtitle,True)
        c.setFont('DV',7.5);c.setFillColor(colors.HexColor('#647782'))
        c.drawString(left,22,'Darwin Observer · cenários da dissertação · 18/10/2026')
        c.drawRightString(W-left,22,str(page))
    def estimation_table(s):
        closed=s.kind!='open';thermals=['none','soft'] if closed else ['open']
        head=['Estado']+[METHOD_LABEL[m]+('\nsem / com' if False else ('\nsem' if th=='none' else '\ncom' if th=='soft' else '')) for th in thermals for m in METHODS]
        data=[head]
        for state in STATES:
            line=[state+(' [C]' if state.startswith('C') else ' [T]')]
            for th in thermals:
                for m in METHODS:
                    r=index[(s.key,th,m)];line.append(fnum(r['RMSE_est_'+state])+'\n'+fnum(r['IAE_est_'+state]))
            data.append(line)
        table(data,[49]+[(width-49)/(len(head)-1)]*(len(head)-1),font=7.5)
        p('Cada célula: <b>RMSE na primeira linha; IAE na segunda</b>. Médias de 20 realizações. '
          '[C]: RMSE em kmol/m³ e IAE em kmol·h/m³. [T]: RMSE em K e IAE em K·h. '
          'Intervalos de confiança de 95% e valores por semente nos arquivos CSV.',True)

    new('Darwin Observer na dissertação','Walter Yanko de Aragão Brandão · comparação computacional dos cenários de 2019')
    p('<b>Resultado principal:</b> o Darwin reteve a hipótese nominal H0 e apresentou os mesmos resultados do UKF RK4 em todos os ensaios. '
      'Não houve ganho atribuível à descoberta de uma nova equação nesta campanha. As diferenças frente ao UKF Euler decorrem da integração numérica.')
    table([['Escopo executado','Quantidade'],['Cenários físicos','19 (8 em malha aberta e 11 com NMPC)'],
           ['Métodos','UKF Euler · UKF RK4 · Darwin'],['Realizações por configuração','20, com ruídos pareados'],
           ['Simulações concluídas',str(execution['completed'])+'; falhas: '+str(execution['failed'])],
           ['Condição térmica do NMPC','Sem penalização / penalização original QR = 1000']],
           [176,width-176],font=8.5)
    picture('Resumo_controle_termico',310)
    p('O termo “com restrição” é implementado como a <b>penalização suave</b> do código original. '
      'Não há garantia matemática de T ≤ 344,26 K. Os ensaios registram os picos e a duração real das violações.',True)
    p('Este relatório contém concentrações, temperaturas, entradas perturbadas, variável manipulada, referências e tabelas de RMSE/IAE. '
      'Os dados são de simulações novas, executadas a partir do modelo recuperado; não são curvas digitalizadas nem medidas experimentais.',True)

    new('Protocolo de comparação','As mesmas condições físicas e o mesmo controlador são compartilhados pelos três observadores.')
    table([['Item','Valor utilizado'],['Modelo','Transformação SI completa do modelo MATLAB histórico'],
        ['Ponto nominal','CC = '+fnum(X_NOM[2])+' kmol/m³; T = '+fnum(X_NOM[4],3)+' K'],
        ['Estados','CA, CB, CC, CM, T e Tt; somente T e Tt são medidas'],
        ['Amostragem / horizontes','Ts = 0,015 h; previsão p = 57; controle m = 6'],
        ['Função custo','Qe = 0,8; Rdu = 0,2; QR = 0 ou 1000'],
        ['Limites da vazão de refrigeração','50–3000 lbmol/h = 22,68–1360,78 kmol/h'],
        ['Limite térmico','160 °F = 344,2611 K (344 K arredondado no texto)'],
        ['Modelo de previsão do NMPC','RK4, um passo por amostra; referência futura conhecida'],
        ['Integração da planta','RK4, subpassos ≤ 0,0025 h; divisão exata nos eventos'],
        ['Otimização','SLSQP; gradiente exato CasADi; 100 iterações; ftol 10⁻⁶'],
        ['UKF','α = 0,001; β = 2; κ = 0; Euler ou RK4'],
        ['Covariância inicial','10⁻⁶ I nas unidades imperiais, convertida para SI'],
        ['Desvio das medições T / Tt','1,385 °F / 1,062 °F, convertidos para K'],
        ['Ruídos de entrada','1% dos valores nominais; mw sem ruído; retenção 0,1 h']],
        [173,width-173],font=8)
    p('<b>Condição inicial conhecida:</b> receita de partida [0; ρB; 0; 0; T0; Ta1], ou equilíbrio nominal nos outros ensaios. '
      'Essa hipótese favorece a estimação química e não demonstra observabilidade global dos seis estados.')
    p('<b>Fonte prioritária:</b> o arquivo SLX recuperado usa Q = diag(5,616×10⁻⁸; 5,616×10⁻⁸; 5,616×10⁻⁸; '
      '2,4246×10⁻¹³; 0,0346356; 0,0066123), nas unidades originais. O texto da dissertação traz diferenças em q22 e q66; '
      'foi mantido o valor executável, convertido pelo quadrado da escala de cada estado.')
    p('O UKF Euler reproduz a discretização do arquivo modeloFun_KF.m. O UKF RK4 isola o efeito da integração. '
      'O Darwin usa o mesmo UKF RK4, com seleção e validação de correções físicas. SLSQP e as sementes novas tornam esta análise '
      'uma reconstrução dos cenários, e não uma repetição bit a bit do MATLAB de 2019.',True)

    for kind,title in [('open','Mapa dos cenários de estimação'),('closed','Mapa dos cenários de controle')]:
        new(title,'Figuras e páginas referem-se à numeração impressa da dissertação; no PDF, somar 10 ao número da página.')
        data=[['Identificador / duração','Fonte','Perturbação ou referência']]
        cases=[s for s in SCENARIOS if (s.kind=='open')==(kind=='open')]
        for s in cases:
            if not s.events:desc='Partida com receita conhecida.' if s.startup else 'Regime nominal com ruídos de entrada e medição.'
            else:desc='; '.join(f'{fnum(t,0)} h: {var} → {fnum(factor*100,0)}% do nominal' for t,var,factor in s.events)+'.'
            data.append([Paragraph('<b>'+s.key+'</b><br/>'+fnum(s.hours,0)+' h',cell),
                Paragraph(s.figures+'<br/>p. '+s.pages,cell),Paragraph(desc,cell)])
        table(data,[121,61,width-182],font=8)
        p('Variações percentuais de T0 e Ta1 foram aplicadas em graus Fahrenheit, como no experimento original, e só depois convertidas para K. '
          'O retorno ao nominal sempre usa 100% do valor inicial; não multiplica sucessivamente os degraus.',True)
        if kind=='open':
            p('A malha aberta avalia a estimação sem atuação do NMPC. A Figura 26 (Q nula) e as tabelas de sintonia de EKF/UKF '
              'não são tratadas como novos cenários físicos nesta comparação: os três métodos usam a covariância congelada do código original.',True)
            p('Na Figura 25, o eixo da temperatura não é consistente com Ta1 nominal de 60 °F do código e da tabela. '
              'Foram usados os 60 °F e os degraus ±20% descritos, em vez de ajustar o modelo para coincidir com o desenho.',True)
        else:
            p('Todos os onze cenários são executados com e sem a penalização térmica, inclusive aqueles que originalmente apareceram apenas em uma das condições. '
              'As curvas PID simples/cascata da dissertação não foram digitalizadas nem usadas como dados quantitativos: aqui os observadores são comparados sob o mesmo NMPC.',True)
            p('SERVO_P20: amplitude +20% e instante 3 h lidos da referência tracejada da Figura 39. A simulação cobre 0–6 h; '
              'a figura original exibe o recorte 2–6 h. OL_STEADY foi registrado em um adendo ao protocolo antes das suas 60 execuções.',True)

    for th in ['none','soft']:
        new('RMSE e IAE do controle de CC',THERMAL_LABEL[th]+' · média de 20 realizações em cada linha')
        data=[['Cenário','Método','RMSE CC','IAE CC','T pico [K]','T > limite [min]']]
        for s in SCENARIOS:
            if s.kind=='open':continue
            for method in METHODS:
                r=index[(s.key,th,method)]
                data.append([s.key,METHOD_LABEL[method],fnum(r['RMSE_track_CC']),fnum(r['IAE_track_CC']),
                    fnum(r['T_peak_K'],2),fnum(float(r['T_above_limit_h'])*60,2)])
        table(data,[94,70,70,70,80,width-384],font=7.5,row_h=17)
        p('RMSE CC em kmol/m³; IAE CC em kmol·h/m³. Erro de controle = CC da planta simulada menos a referência programada. '
          'O tempo acima do limite é integrado nos subpassos da planta, sem usar medições ruidosas. Os intervalos de 95% estão no CSV.',True)

    new('Como interpretar os resultados','Separação entre qualidade da estimação, desempenho de controle e proteção térmica.')
    p('<b>Estimação:</b> RMSE = √média[(x estimado − x verdadeiro)²]; IAE = ∫|x estimado − x verdadeiro| dt. '
      'Ambos são calculados para CA, CB, CC, CM, T e Tt, na janela completa de cada ensaio.')
    p('<b>Controle:</b> RMSE = √média[(CC verdadeiro − CC referência)²]; IAE = ∫|CC verdadeiro − CC referência| dt. '
      'Integrais pelo método dos trapézios. Em malha aberta, a diferença para o nominal não é interpretada como erro de um controlador.')
    p('<b>Convenção RMSE:</b> a Equação 61 da dissertação, tal como está impressa, coloca a raiz no erro quadrático de cada amostra antes da média, '
      'o que corresponde a MAE. Esta entrega usa a definição convencional de RMSE acima; seus valores não devem ser comparados diretamente '
      'a uma coluna histórica calculada com a fórmula impressa sem verificar o código correspondente.')
    p('<b>Validação independente:</b> Darwin com 12 episódios de treino, oito de validação e 20 de calibração. '
      'Melhor candidato irrestrito: '+html.escape(discovery['best_unrestricted'])+'; ganho de validação '+fnum(100*discovery['relative_gain'],2)+'%, abaixo do limiar de 10%; '
      'IC95% da diferença de perda ['+fnum(discovery['paired_CI'][0],4)+'; '+fnum(discovery['paired_CI'][1],4)+'] inclui zero. Resultado: H0 retida.')
    p('<b>Conclusão científica:</b> manter H0 evita atribuir ao Darwin uma descoberta que os dados independentes não sustentam. '
      'O ganho observado em estudos anteriores com erro físico artificial de UA não pode ser transferido para esta campanha, '
      'na qual o gerador usa a física histórica sem defeito estrutural oculto adicional.')
    for key in ['CL_START','SERVO_P20']:
        a=index[(key,'none','Darwin')];b=index[(key,'soft','Darwin')]
        p('<b>'+key+':</b> pico médio de T '+fnum(a['T_peak_K'],2)+' → '+fnum(b['T_peak_K'],2)+' K; '
          'IAE de CC '+fnum(a['IAE_track_CC'])+' → '+fnum(b['IAE_track_CC'])+' kmol·h/m³. '
          'Com penalização, '+str(b['violation_episodes'])+'/20 realizações ultrapassam o limite ao menos uma vez.')
    p('<b>Incerteza e gráficos:</b> médias e intervalos bootstrap de 95% por realização (2.000 reamostragens). '
      'As curvas exibem sempre a primeira semente predefinida de cada cenário, sem seleção visual. As tabelas usam todas as 20 sementes. '
      'As comparações pareadas ficam em paired_comparisons.csv; não se infere superioridade global a partir de diferenças pequenas isoladas.',True)
    p('<b>Fonte:</b> Brandão, Walter Yanko de Aragão. <i>Uso de observadores de estado aplicados no controle inferencial preditivo de processos não lineares</i>. '
      'Dissertação, UFCG, 2019, pp. 51–72; arquivos MATLAB/Simulink recuperados de Codigo_CSTR_Reproduzivel.zip. '
      'Hashes e decisões de interpretação em artifacts/thesis/source_provenance.json.',True)

    for s in SCENARIOS:
        seed=410000+SCENARIOS.index(s)*1000
        subtitle=s.title+' · figuras '+s.figures+' · páginas '+s.pages+' · semente ilustrada '+str(seed)
        new(s.key+' · concentrações' if s.kind!='open' else s.key+' · seis estados',subtitle)
        picture(s.key+'_estados',575 if s.kind!='open' else 510)
        p('Linhas sobrepostas Darwin/UKF RK4 representam igualdade numérica, confirmada nos dados de todos os ensaios. '
          +('Traço contínuo: planta simulada; tracejado: estimativa; pontilhado em CC: referência. '
            'A escala de cada painel é mostrada no eixo; compare os valores numéricos entre colunas.' if s.kind!='open' else
             'Planta simulada em cinza; estimativas em laranja (Euler) e verde (Darwin/UKF RK4).') ,True)
        if s.note:p(s.note,True)
        if s.kind!='open':
            new(s.key+' · temperaturas e atuação',subtitle)
            picture(s.key+'_temperaturas_controle',440)
            data=[['Darwin = UKF RK4','RMSE CC','IAE CC','Pico T [K]','Acima [min]','Episódios']]
            for th in ['none','soft']:
                r=index[(s.key,th,'Darwin')]
                data.append(['Sem penalização' if th=='none' else 'Com penalização',fnum(r['RMSE_track_CC']),fnum(r['IAE_track_CC']),
                    fnum(r['T_peak_K'],2),fnum(float(r['T_above_limit_h'])*60,2),r['violation_episodes']+'/20'])
            table(data,[136,70,70,75,75,width-426],font=7.5)
            p('Métricas acima: média de 20 realizações; “episódios” conta aqueles com T > 344,2611 K em algum instante. '
              'A faixa permitida de mw é mantida nas duas condições. A penalização térmica pode aceitar violações para reduzir outros termos do custo.',True)
        new(s.key+' · distúrbios e erros',subtitle)
        picture(s.key+'_disturbios',310)
        if s.kind!='open':p('As entradas exógenas e a referência são iguais para os métodos e as duas condições térmicas. A vazão mw é exibida na página anterior.',True)
        estimation_table(s)
    c.save()
    print(json.dumps(dict(pdf=str(filename),pages=page)),flush=True)

def make_gallery():
    sections=[]
    for s in SCENARIOS:
        names=[('estados','Concentrações e estados')]
        if s.kind!='open':names.append(('temperaturas_controle','Temperaturas e controle'))
        names.append(('disturbios','Distúrbios e referência'))
        panels=''.join('<figure><figcaption>'+label+'</figcaption><img loading="lazy" src="figures/'+s.key+'_'+suffix+'.png" alt="'+label+' — '+s.key+'"/></figure>' for suffix,label in names)
        sections.append('<section id="'+s.key+'"><h2>'+html.escape(s.title)+'</h2><p>'+s.key+' · Dissertação: '+s.figures+', p. '+s.pages+'</p>'+panels+'</section>')
    nav=''.join('<a href="#'+s.key+'">'+s.key+'</a>' for s in SCENARIOS)
    document='''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Darwin · cenários da dissertação</title>
<style>body{font:16px/1.5 system-ui,sans-serif;color:#173a47;background:#f4f7f8;margin:0}main,header{max-width:1100px;margin:auto;padding:30px}header{background:#fff}nav{display:flex;flex-wrap:wrap;gap:8px}nav a{background:#e5f2f0;padding:4px 9px;border-radius:5px;color:#123e43}section{margin:28px 0;padding:22px;background:white;border-radius:10px}figure{margin:22px 0}img{max-width:100%;height:auto}figcaption{font-weight:650}a{color:#007e75}p{max-width:85ch}.note{border-left:4px solid #008b80;padding:15px;background:#e5f2f0}</style>
<header><h1>Darwin Observer nos cenários da dissertação</h1><p>19 cenários · 20 realizações por configuração · UKF Euler, UKF RK4 e Darwin.</p><p class="note">O Darwin reteve H0 e coincidiu com o UKF RK4. “Com restrição” corresponde à penalização suave original e pode permitir violações térmicas. As curvas usam a primeira semente predefinida; as métricas agregam 20.</p><p><a href="Comparacao_Darwin_Dissertacao.pdf">Relatório completo em PDF</a> · <a href="Metricas_RMSE_IAE_por_cenario.csv">RMSE e IAE com IC95%</a></p><nav>'''+nav+'</nav></header><main>'+''.join(sections)+'</main></html>'
    (OUT/'Graficos_Darwin_Dissertacao.html').write_text(document,encoding='utf-8')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--stage',choices=['figures','pdf','tables','gallery','all'],default='all');a=ap.parse_args()
    if a.stage in ['figures','all']:make_figures()
    if a.stage in ['tables','all']:metric_tables()
    if a.stage in ['pdf','all']:make_pdf()
    if a.stage in ['gallery','all']:make_gallery()

if __name__=='__main__':main()
