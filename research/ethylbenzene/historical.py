"""Historical evidence and matched PI/EKF comparisons; no native-reproduction claim.

Digitize original PNGs embedded in the author's PDF with fixed axis calibration.
Palette/axis/legend exclusions are explicit. Long occlusions remain missing.
Original numeric tables are transcribed separately and never overwritten.
"""
import argparse,json,csv,hashlib,itertools
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
from model import *
from protocol import CASES,SEEDS,scenario
from experiment import truth_step
from baseline import BASE_DIR

EST=['ukf','ukf_tuned','lstm_ukf','nake','lstm_nake']
LABEL={'ukf':'UKF Q0','ukf_tuned':'UKF validado','lstm_ukf':'LSTM-UKF','nake':'NAKE-BB','lstm_nake':'LSTM-NAKE'}
TABLES=dict(source='TFC_WALTER_FINAL_imprimir.pdf, pp. 52,54,57; visual transcription checked',
 equilibrium=dict(luyben=[.0039,.6568,.2891,.0501],aspen=[.0039,.6572,.2888,.05],
                  matlab=[.0051,.6607,.2811,.0531],fke=[.0050,.6631,.2795,.0523]),
 estimator=dict(MAE=1.626e-5,RMSE=.000514,table='4.2',window='not explicitly specified; adjacent Figure 4.5 spans 0-5 h',noise_covariance='not recovered'),
 control=dict(benzene_50=dict(closed=dict(IAE=.1476,ITAE=.3368,ISE=.0102),open=dict(IAE=.0906,ITAE=.5625,ISE=.0016)),
              recycle_minus50=dict(closed=dict(IAE=.1467,ITAE=.3291,ISE=.0102),open=dict(IAE=.3678,ITAE=2.123,ISE=.0267))),
 conditions=dict(duration_h=10.,step_h=5.,initial_condition='historical startup shown in figures; full state vector not specified',
                 PI_recipe='relay, Kc=Kcu/2.2; Ti=Tu/1.2; numeric Kcu/Tu not given',temperature_limit='not stated'),
 inconsistencies=['Table 4.3 closed-loop IAE and ISE exceed open-loop values, although discussion states improvement.',
                  'Figure 4.8 legend identifies olive as open loop and gray as real process; their responses differ from that labeling expected from Figure 4.7. Colors/labels are preserved, not silently swapped.'],
 comparability='Published values are contextual historical evidence. Percent improvement is calculated only against the reconstructed PI/EKF under the common new protocol.')

CALIBRATIONS={
 'startup':dict(page=53,index=1,x0=216,x1=1503,y0=416,y1=17,tmax=5.,ymax=.8,legend=(1312,107,1556,266),series={'black':(0,0,0)},grid_rows=[17,117,216,316,416],grid_cols=[216,344,474,602,730,859,988,1117,1246,1375,1503]),
 'benzene_50':dict(page=55,index=1,x0=199,x1=1386,y0=443,y1=60,tmax=10.,ymax=.4,legend=(1054,278,1438,423),series={'gray':(128,128,128),'olive':(96,96,64)}),
 'recycle_minus50':dict(page=56,index=0,x0=132,x1=1319,y0=453,y1=56,tmax=10.,ymax=.35,legend=(941,73,1315,210),series={'gray':(128,128,128),'olive':(96,96,64)})}

def write_csv(path,rows):
    with Path(path).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys(),lineterminator='\n');w.writeheader();w.writerows(rows)

def digitize(pdf_path):
    import fitz
    pdf=fitz.open(pdf_path);rows=[];metadata=[]
    for case,c in CALIBRATIONS.items():
        page=pdf[c['page']-1];xref=page.get_images(full=True)[c['index']][0];data=pdf.extract_image(xref)['image']
        from io import BytesIO
        rgb=np.asarray(Image.open(BytesIO(data)).convert('RGB'));mask_area=np.zeros(rgb.shape[:2],bool)
        mask_area[c['y1']+3:c['y0']-2,c['x0']+2:c['x1']-1]=True
        a,b,d,e=c['legend'];mask_area[b:e,a:d]=False
        for y in c.get('grid_rows',[]):mask_area[max(0,y-1):y+2,:]=False
        for x in c.get('grid_cols',[]):mask_area[:,max(0,x-1):x+2]=False
        if case=='recycle_minus50':
            # Olive dash-dot setpoint has the same palette as the olive curve.
            # Exclude its row; do not invent data when the curve overlaps it.
            mask_area[131:137,:]=False
        for color,palette in c['series'].items():
            mask=np.all(rgb==palette,axis=2)&mask_area
            xs=[];ys=[];spread=[]
            for x in range(c['x0']+2,c['x1']-1):
                yy=np.flatnonzero(mask[:,x])
                if len(yy) and yy.max()-yy.min()<=10:
                    xs.append(x);ys.append(float(np.median(yy)));spread.append(float(yy.max()-yy.min()))
            tt=(np.array(xs)-c['x0'])/(c['x1']-c['x0'])*c['tmax']
            vv=(c['y0']-np.array(ys))/(c['y0']-c['y1'])*c['ymax']
            # Only short dash gaps can be interpolated; masks/overlap are retained.
            grid=np.linspace(0,c['tmax'],501);vals=np.full(len(grid),np.nan)
            for j,t in enumerate(grid):
                k=np.searchsorted(tt,t)
                if 0<k<len(tt) and tt[k]-tt[k-1]<=.08:vals[j]=np.interp(t,tt[k-1:k+1],vv[k-1:k+1])
            for t,v in zip(grid,vals):
                rows.append(dict(case=case,color=color,time_h=float(t),xEB=float(v) if np.isfinite(v) else '',
                                 resolution_per_pixel=c['ymax']/(c['y0']-c['y1']),source_page=c['page']))
            metadata.append(dict(case=case,color=color,axis=c,png_sha256=hashlib.sha256(data).hexdigest(),
              detected_columns=len(xs),retained_grid_points=int(np.sum(np.isfinite(vals))),grid_points=len(grid),
              nominal_vertical_uncertainty=2*c['ymax']/(c['y0']-c['y1']),
              meaning='palette trace, with original color and legend preserved; not a raw simulation time series'))
    write_csv(RESULTS/'tfc_digitized.csv',rows);dump(RESULTS/'tfc_digitization.json',metadata)
    return rows

def analyze():
    rows=json.loads((RESULTS/'metrics.json').read_text())+json.loads((RESULTS/'metrics_tuned.json').read_text())
    baselines=json.loads((RESULTS/'metrics_pi_ekf.json').read_text());idx={(r['case'],r['seed']):r for r in baselines}
    summary=[]
    for case,e,p,m,con in itertools.product(CASES,EST,['physical','neural'],['siso','mimo'],[False,True]):
        rr=[r for r in rows if (r['case'],r['estimator'],r['prediction'],r['mode'],r['constrained'])==(case,e,p,m,con)]
        br=[idx[case,r['seed']] for r in rr]
        gain=[100*(1-r['IAE_event']/b['IAE_event']) for r,b in zip(rr,br)]
        summary.append(dict(case=case,estimator=e,prediction=p,mode=m,constrained=con,runs=len(rr),
          IAE_event_mean=float(np.mean([r['IAE_event'] for r in rr])),PI_EKF_IAE_event_mean=float(np.mean([r['IAE_event'] for r in br])),
          paired_gain_mean_pct=float(np.mean(gain)),paired_gain_std_pct=float(np.std(gain)),improved_seed_count=sum(g>0 for g in gain),
          gain_min_pct=min(gain),gain_max_pct=max(gain),Tmax_C=max(r['Tmax_C'] for r in rr),PI_EKF_Tmax_C=max(r['Tmax_C'] for r in br),
          actual_limit_violating_runs=sum(r['violation_h']>0 for r in rr),PI_EKF_actual_limit_violating_runs=sum(r['violation_h']>0 for r in br),
          comparison=('common SISO unconstrained protocol' if m=='siso' and not con else 'design change: '+('second actuator and thermal objective; ' if m=='mimo' else '')+('new predicted thermal constraint' if con else 'unconstrained'))))
    dump(RESULTS/'improvement_vs_pi.json',summary);write_csv(RESULTS/'improvement_vs_pi.csv',summary)
    comparison=[]
    for case in ['benzene_50','recycle_minus50']:
        for loop in ['closed','open']:
            comparison.append(dict(case=case,method='TFC published '+loop,IAE=TABLES['control'][case][loop]['IAE'],
                 ISE=TABLES['control'][case][loop]['ISE'],ITAE=TABLES['control'][case][loop]['ITAE'],IAE_event='',
                 comparability='historical startup/noise/tuning differ; no causal gain computed'))
        br=[r for r in baselines if r['case']==case]
        comparison.append(dict(case=case,method='PI + EKF reconstructed',**{k:float(np.mean([r[k] for r in br])) for k in ['IAE','ISE','ITAE','IAE_event']},comparability='common new protocol'))
        for e,p,m in [('ukf_tuned','physical','siso'),('lstm_ukf','physical','siso'),('lstm_nake','neural','siso'),('lstm_ukf','physical','mimo')]:
            rr=[r for r in rows if (r['case'],r['estimator'],r['prediction'],r['mode'],r['constrained'])==(case,e,p,m,False)]
            comparison.append(dict(case=case,method=f'{e} {p} {m}',**{k:float(np.mean([r[k] for r in rr])) for k in ['IAE','ISE','ITAE','IAE_event']},comparability='common new protocol; MIMO adds actuator/objective' if m=='mimo' else 'common new protocol'))
    dump(RESULTS/'tfc_control_comparison.json',comparison);write_csv(RESULTS/'tfc_control_comparison.csv',comparison)
    observer=[]
    for e in EST+['ekf_reconstructed']:
        er=[];first=[];late=[]
        for seed in SEEDS:
            folder=BASE_DIR/'openloop_traces' if e=='ekf_reconstructed' else RESULTS/('ukf_tuned/openloop_traces' if e=='ukf_tuned' else 'openloop_traces')
            z=np.load(folder/f'servo_up__{seed}.npz');err=fraction(z[e])-fraction(z['true'])
            er.append(err);first.append(err[:200]);late.append(err[200:])
        rr=dict(estimator=e,runs=3,source='common new nominal open-loop plant, noise and biased estimate')
        for label,arr in [('full',er),('first5',first),('after5',late)]:
            rr['MAE_'+label]=float(np.mean([np.mean(abs(x)) for x in arr]));rr['RMSE_'+label]=float(np.mean([np.sqrt(np.mean(x*x)) for x in arr]))
        observer.append(rr)
    dump(RESULTS/'tfc_observer_comparison.json',dict(published=TABLES['estimator'],new=observer,comparison='Different startup/noise/window; side-by-side descriptive values, no superiority claim against Table 4.2'))
    return rows,baselines,summary,comparison,observer

def audit(baselines):
    assert len(baselines)==18 and len({(r['case'],r['seed']) for r in baselines})==18
    metric_error=state_error=0.;n=0
    for r in baselines:
        assert r['status']=='complete' and r['samples']==400
        z=np.load(BASE_DIR/'traces'/f"{r['name']}.npz");prev=BASE.copy();iae=ise=itae=event=0.
        cmd=z['command'][:,0]/F0[0];assert cmd.min()>=.04-1e-10 and cmd.max()<=2+1e-10
        assert np.max(abs(np.diff(np.r_[1.,cmd])))<=.1200000001
        np.testing.assert_allclose(z['command'][:,3],Q0)
        assert np.all(z['q']>0) and np.all(z['cov_diagonal']>0)
        for j in range(400):
            nxt,grid,dense=truth_step(prev,z['actual'][j],scenario(r['case'],j*DT)[2]);n+=1
            state_error=max(state_error,float(np.max(abs(nxt-z['true'][j]))));err=fraction(dense)-z['reference'][j]
            v=float(np.trapezoid(abs(err),grid));iae+=v;ise+=float(np.trapezoid(err**2,grid));itae+=float(np.trapezoid(abs(err)*(j*DT+grid),grid))
            if j*DT>=(3. if r['case'].startswith('servo') else 5.):event+=v
            prev=z['true'][j]
        metric_error=max(metric_error,max(abs(v-r[k]) for k,v in [('IAE',iae),('ISE',ise),('ITAE',itae),('IAE_event',event)]))
    paired_error=0.
    for case,seed in itertools.product(['servo_up','benzene_50','recycle_minus50','thermal_loss','kinetics_noise'],SEEDS):
        a=np.load(BASE_DIR/'openloop_traces'/f'{case}__{seed}.npz')['true']
        b=np.load(RESULTS/'openloop_traces'/f'{case}__{seed}.npz')['true']
        paired_error=max(paired_error,float(np.max(abs(a-b))))
    assert state_error<1e-8 and metric_error<1e-9 and paired_error<1e-12
    result=dict(control_runs=18,observer_runs=15,reintegrated_samples=n,state_max_abs_error=state_error,
                metric_max_abs_error=metric_error,paired_truth_max_abs_error=paired_error,
                published_benzene_IAE_increase_pct=100*(.1476/.0906-1),published_benzene_ISE_increase_pct=100*(.0102/.0016-1),
                no_original_raw_time_series=True,original_parameter_recovery=False)
    dump(RESULTS/'historical_audit.json',result);return result

def plots(digitized,summary,out):
    out.mkdir(parents=True,exist_ok=True);plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axs=plt.subplots(1,2,figsize=(12,5.2),sharey=True)
    for ax,mode in zip(axs,['siso','mimo']):
        combos=[('benzene_50','physical'),('benzene_50','neural'),('recycle_minus50','physical'),('recycle_minus50','neural')]
        arr=np.array([[next(r['paired_gain_mean_pct'] for r in summary if (r['case'],r['estimator'],r['prediction'],r['mode'],r['constrained'])==(c,e,p,mode,False)) for c,p in combos] for e in EST])
        im=ax.imshow(arr,cmap='RdYlGn',vmin=-100,vmax=100,aspect='auto')
        for i,j in itertools.product(range(5),range(4)):
            val=arr[i,j];ax.text(j,i,f'{val:+.1f}%',ha='center',va='center',color='white' if abs(val)>78 else '#0f172a',fontweight='bold')
        ax.set_xticks(range(4),['Benzeno\nFísico','Benzeno\nBlackbox','Reciclo\nFísico','Reciclo\nBlackbox'])
        ax.set_yticks(range(5),[LABEL[e] for e in EST]);ax.set_title('SISO: mesmo atuador' if mode=='siso' else 'MIMO: acrescenta atuação térmica',fontweight='bold')
    fig.suptitle('Melhoria frente ao PI + FKE reconstruído',fontsize=17,fontweight='bold',y=.98)
    fig.text(.13,.06,'Ganho pareado de IAE após 5 h, três sementes. Sem restrição de temperatura. Positivo = menor erro.',fontsize=10)
    fig.text(.13,.023,'Comparação no modelo novo comum; não é ganho comprovado sobre a execução histórica do TFC.',fontsize=9,color='#475569')
    fig.subplots_adjust(left=.13,right=.91,top=.83,bottom=.19,wspace=.13)
    cb=fig.colorbar(im,cax=fig.add_axes([.925,.19,.012,.64]));cb.set_label('Ganho (%)')
    fig.savefig(out/'Etilbenzeno_Melhoria_PI_FKE.png',dpi=180);plt.close(fig)
    fig,axs=plt.subplots(3,1,figsize=(8.5,6.3))
    for ax,case in zip(axs,['startup','benzene_50','recycle_minus50']):
        for color in (['black'] if case=='startup' else ['gray','olive']):
            rr=[r for r in digitized if r['case']==case and r['color']==color]
            ax.plot([r['time_h'] for r in rr],[r['xEB'] if r['xEB']!='' else np.nan for r in rr],ls='--',color={'black':'#111827','gray':'#64748b','olive':'#877314'}[color],lw=1.8,label='TFC: '+('composição real' if color=='black' else 'curva '+('cinza' if color=='gray' else 'oliva')))
        if case=='startup':
            z=np.load(RESULTS/'openloop_traces'/'servo_up__9002.npz');ax.plot(np.arange(1,201)*DT,fraction(z['true'][:200]),color='#0f766e',label='Novo: nominal no equilíbrio')
        else:
            for e,p,m,color,label in [('ekf_reconstructed','physical','siso','#1e3a8a','PI + FKE reconstruído'),('ukf_tuned','physical','siso','#0f766e','UKF validado / NMPC SISO'),('lstm_ukf','physical','mimo','#dc2626','LSTM-UKF / NMPC MIMO')]:
                name=f'{case}__{e}__{p}__{m}__0__9002';folder=BASE_DIR if e=='ekf_reconstructed' else RESULTS
                z=np.load(folder/'traces'/f'{name}.npz');ax.plot(z['time'],fraction(z['true']),color=color,lw=1.2,label=label)
            ax.axvline(5.,color='#94a3b8',lw=.8,ls=':')
        ax.set_xlabel('Tempo (h)',fontsize=9);ax.set_ylabel('xEB',fontsize=9)
        ax.tick_params(labelsize=9);ax.grid(alpha=.18);ax.set_xlim(0,5 if case=='startup' else 10)
        ax.set_title({'startup':'Partida histórica × início no equilíbrio','benzene_50':'Benzeno +50% em 5 h','recycle_minus50':'Reciclo -50% em 5 h'}[case],fontweight='bold',fontsize=10)
        ax.legend(loc='center left',bbox_to_anchor=(1.02,.5),fontsize=7.6,frameon=False,ncol=1)
    fig.subplots_adjust(left=.085,right=.67,top=.945,bottom=.14,hspace=.57)
    fig.text(.085,.047,'Originais: Figuras 4.4, 4.7 e 4.8, digitalização aproximada. Novos: semente 9002.',fontsize=7.6,color='#475569')
    fig.text(.085,.02,'Cores históricas preservadas. A legenda da Figura 4.8 exige conferência.',fontsize=7.6,color='#475569')
    fig.savefig(out/'Etilbenzeno_TFC_Original.png',dpi=180);plt.close(fig)

def markdown(summary,comparison,observer):
    lines=['# Houve melhoria frente ao TFC?','',
      'Há melhorias e pioras frente a uma referência **PI + FKE reconstruída no mesmo protocolo novo**. A superioridade sobre a execução histórica do TFC ainda não está demonstrada: sua sintonia numérica, estado inicial completo, matrizes P/Q/R e amostragem não foram recuperados. O ganho de 14,8% informado no estudo anterior é contra o **UKF novo + NMPC MIMO**, não contra o PI do TFC.','',
      '## Números publicados, preservados','','| Perturbação | Malha | IAE | ITAE | ISE |','|---|---|---:|---:|---:|']
    for case in ['benzene_50','recycle_minus50']:
        for loop,label in [('closed','Fechada: PI + FKE'),('open','Aberta')]:
            r=TABLES['control'][case][loop]
            lines.append(f'| {case} | {label} | {r["IAE"]:.4f} | {r["ITAE"]:.4f} | {r["ISE"]:.4f} |')
    lines+=['','Fonte: Tabelas 4.3-4.4 do PDF do autor, p. 57. No benzeno, os valores publicados de IAE e ISE fechados são **62,9% e 537,5% maiores** que os abertos; somente ITAE melhora. Isso contradiz a discussão do texto e foi preservado. No reciclo, as três métricas publicadas melhoram em malha fechada.','',
      'Tabela 4.2: MAE=0,00001626 e RMSE=0,000514 para xEB; janela e condições não estão integralmente especificadas. As frações FKE da Tabela 4.1 também foram incorporadas: [0,0050; 0,6631; 0,2795; 0,0523].','',
      '## Comparação controlada com PI + FKE reconstruído','',
      'Todos recebem a mesma planta reduzida, equilíbrio, viés inicial, medição de temperatura, ruído, sementes 9001–9003, períodos e limites de atuação. O FKE tem Jacobiana exata e Q constante=64×Q0, escolhido em validação independente. A receita de relé do TFC aplicada em ensaio nominal separado produziu Kcu=45,878237, Tu=0,15 h, Kc=20,853744 e Ti=0,125 h. São parâmetros novos, não recuperados do TFC. A válvula equipercentual tem rangeabilidade 50, capacidade 2, taxa máxima 0,12 por amostra e anti-windup explicitamente introduzido.','',
      'Ganho = média de três razões pareadas, 100×(1−IAE_evento_novo/IAE_evento_PI). Positivo significa redução de erro; negativo significa piora. Janelas: 3–10 h nos servos e 5–10 h nos demais casos. A comparação de mesmo atuador/objetivo usa **SISO sem restrição térmica**. MIMO e a nova restrição térmica alteram o projeto.','',
      '| Cenário | UKF validado / físico SISO | LSTM-UKF / físico SISO |','|---|---:|---:|']
    for case in ['benzene_50','recycle_minus50','servo_up','servo_down','thermal_loss','kinetics_noise']:
        vals=[next(r['paired_gain_mean_pct'] for r in summary if (r['case'],r['estimator'],r['prediction'],r['mode'],r['constrained'])==(case,e,'physical','siso',False)) for e in ['ukf_tuned','lstm_ukf']]
        lines.append(f'| {case} | {vals[0]:+.2f}% | {vals[1]:+.2f}% |')
    lines+=['','O ganho próximo de 98% no reciclo inclui a dificuldade do PI reconstruído, que oscila nesse caso. Depende da sintonia e do modelo efetivo adotados. Nos servos os dois NMPC físicos SISO pioram; no caso cinético a diferença é inferior a 0,1% e não sustenta uma conclusão robusta com apenas três sementes. LSTM-UKF SISO piora também na perda térmica.','',
      '## Todas as combinações SISO sem restrição nos dois casos históricos','','| Estimador | Preditor NMPC | Benzeno +50% | Reciclo −50% |','|---|---|---:|---:|']
    for e,p in itertools.product(EST,['physical','neural']):
        vv=[next(r['paired_gain_mean_pct'] for r in summary if (r['case'],r['estimator'],r['prediction'],r['mode'],r['constrained'])==(case,e,p,'siso',False)) for case in ['benzene_50','recycle_minus50']]
        lines.append(f'| {LABEL[e]} | {p} | {vv[0]:+.2f}% | {vv[1]:+.2f}% |')
    lines+=['','A predição blackbox SISO com UKF/LSTM-UKF piora cerca de 67% no reciclo. NAKE-BB e LSTM-NAKE SISO pioram no benzeno. Portanto aprendizagem não demonstra superioridade universal. Os 240 grupos por cenário, preditor, estimador, modo e restrição, com temperatura e contagem de sementes que melhoram, estão em `improvement_vs_pi.csv/json`.','',
      '## Temperatura e integrabilidade','',
      'Sem restrição, o PI reconstruído atinge 182,38 °C no benzeno e 201,03 °C no reciclo. UKF validado / NMPC físico SISO atinge 182,34 °C e 165,65 °C. A redução de IAE não garante cumprir o limite assumido de 165 °C. O PI histórico não possuía esse limite. Compará-lo com NMPC restrito mede também uma exigência nova; a auditoria térmica anterior mantém 128/360 execuções restritas com ultrapassagem real simulada.','',
      'As integrais novas 0–10 h e as publicadas estão lado a lado em `tfc_control_comparison.csv/json`. Não se calcula ganho causal entre elas: a partida histórica difere do início novo em equilíbrio, e ruído/sintonia/amostragem não coincidem.','',
      '## Observadores','',
      '| Observador novo | MAE 0–5 h | RMSE 0–5 h | RMSE 5–10 h |','|---|---:|---:|---:|']
    for e in EST+['ekf_reconstructed']:
        r=next(x for x in observer if x['estimator']==e)
        lines.append(f'| {LABEL.get(e,"FKE reconstruído")} | {r["MAE_first5"]:.7f} | {r["RMSE_first5"]:.7f} | {r["RMSE_after5"]:.7f} |')
    lines+=['','A estimação nova usa verdade e medições comuns, sem influência do controlador. O viés inicial domina a janela 0–5 h. Seu RMSE é maior que o RMSE original publicado; os protocolos diferentes impedem atribuir a diferença somente ao estimador. Nenhum ganho sobre a Tabela 4.2 é reivindicado.','',
      '## Curvas originais e auditoria','',
      '`tfc_digitized.csv` contém digitalização das Figuras 4.4, 4.7 e 4.8, não séries brutas recuperadas. Máscaras, calibragem, hashes de PNGs e resolução estão em `tfc_digitization.json`. Incerteza vertical nominal de dois pixels: ±0,0040 / ±0,0021 / ±0,0018 em xEB. Sobreposições longas não são interpoladas. A legenda da Figura 4.8 é ambígua; cores e rótulos são preservados.','',
      'As planilhas originais são varreduras estáticas, não registros temporais do PI/FKE. Não foi localizado o Simulink executável deste reator de cinco estados. A planta Aspen completa continua fora do escopo.','',
      '18/18 testes PI + FKE e 15/15 testes de estimação FKE concluídos. Todas as 7.200 amostras PI foram reintegradas, com erro de estados/integrais igual a zero; trajetórias verdadeiras de estimação coincidem exatamente com as dos outros filtros. Nove testes numéricos do módulo, incluindo FKE/Jacobiana e reversão de PI saturado. Q e covariâncias nos NPZ usam **unidades físicas dos estados ao quadrado**; o escalonamento normalizado é apenas interno.','',
      'Reprodução: `baseline.py`, `historical.py`, `report.py`; dados e código versionados, trajetórias separadas. Não houve sintonia usando pontuação dos testes de controle.']
    (RESULTS/'COMPARACAO_TFC.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source-pdf',type=Path);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    dump(RESULTS/'tfc_published.json',TABLES)
    if args.source_pdf:digitized=digitize(args.source_pdf)
    else:
        with (RESULTS/'tfc_digitized.csv').open() as f:digitized=list(csv.DictReader(f))
        for r in digitized:r['time_h']=float(r['time_h']);r['xEB']=float(r['xEB']) if r['xEB']!='' else ''
    rows,br,summary,comparison,observer=analyze();result=audit(br);plots(digitized,summary,args.output);markdown(summary,comparison,observer)
    print(json.dumps(result,indent=2))
