"""Build five scientific reports, figures and a self-contained offline explorer.
Every numerical result below is calculated from saved campaign data.
"""
import csv,json,hashlib,platform,sys,re,html
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import norm
from .physics import *
from .discovery import paired_interval
from .identification import local_observability
from .experiments import savejson,savecsv,clean
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts'/'main';REPORT=ROOT/'reports';FIG=REPORT/'figures'

def rows(name):return list(csv.DictReader((ART/f'{name}.csv').open()))
def val(r,k):return float(r[k])
def wilson(k,n):
    z=1.95996398454;p=k/n;den=1+z*z/n;center=(p+z*z/(2*n))/den;half=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [max(0,float(center-half)),min(1,float(center+half))]
def f(n,d=4):return f'{n:.{d}f}'
def table(headers,data):return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(str(x) for x in r)+' |' for r in data])

def aggregate():
    es=json.loads((ART/'estimation_summary.json').read_text(encoding='utf-8'));er=rows('estimation');cr=rows('control');br=rows('blind');ar=rows('ablations')
    ctrl={};base={int(r['seed']):val(r,'iae') for r in cr if r['method']=='nominal'}
    for m in sorted({r['method'] for r in cr}):
        a=[r for r in cr if r['method']==m];d=np.array([base[int(r['seed'])]-val(r,'iae') for r in a]);
        ctrl[m]={k:float(np.mean([val(r,k) for r in a])) for k in ['iae','tracking_rmse','rmse_CC','production_kmol','effort','feasible_fraction','solver_mean_ms','observer_fallbacks','model_fallbacks']}
        ctrl[m].update(n=len(a),violation_episodes=sum(val(r,'violations')>0 for r in a),IAE_gain_percent=float(100*d.mean()/np.mean(list(base.values()))),paired_IAE_CI=paired_interval(d),violation_rate_CI=wilson(sum(val(r,'violations')>0 for r in a),len(a)))
    blind={}
    for s in sorted({r['scenario'] for r in br}):
        a=[r for r in br if r['scenario']==s];counts={m:sum(r['predicted']==m for r in a) for m in sorted({r['predicted'] for r in a})}
        false=sum(r['false_equation']=='True' for r in a)
        blind[s]=dict(n=len(a),counts=counts,correct=sum(r['predicted']==r['expected'] for r in a),abstentions=sum(r['predicted'] in ('ambiguous','insufficient_evidence') for r in a),false_equations=false,false_equation_CI=wilson(false,len(a)),detections=sum(r['detected']=='True' for r in a))
    ab={}
    for s in sorted({r['scenario'] for r in ar}):
        ab[s]={m:dict(mean_rmse=float(np.mean([val(r,'rmse_CC') for r in ar if r['scenario']==s and r['method']==m])),n=sum(r['scenario']==s and r['method']==m for r in ar),fallbacks=sum(float(r.get('fallbacks') or 0) for r in ar if r['scenario']==s and r['method']==m)) for m in sorted({r['method'] for r in ar if r['scenario']==s})}
    discoveries={};structure=[]
    for p in (ART/'discoveries').glob('*.json'):
        d=json.loads(p.read_text(encoding='utf-8'));discoveries[p.stem]=d
        if p.stem.startswith('A_'):
            strength=.15 if p.stem=='A_mild' else .4;pa=np.array(d['model']['params']);grid=np.linspace(220,1050,101)
            expected=(grid/453.6)**strength;got=[]
            for w in grid:
                u=U0.copy();u[3]=w;got.append(correction(BASE,u,pa)[0])
            nr=float(np.sqrt(np.mean((np.array(got)-expected)**2))/np.sqrt(np.mean(expected**2)))
            terms=set(np.flatnonzero(abs(pa[:6])>.02));precision=len(terms&{2})/max(len(terms),1)
            structure.append(dict(scenario=p.stem,selected=d['selected'],relative_UA_function_error=nr,term_precision=precision,
                recovered_exponent=float(pa[2]) if d['selected']=='UA_power' else None,hidden_exponent=strength,plausible=d['plausible']))
    comparisons={}
    for s in es:
        a={int(r['seed']):val(r,'rmse_CC') for r in er if r['scenario']==s and r['method']=='Adaptive'}
        b={int(r['seed']):val(r,'rmse_CC') for r in er if r['scenario']==s and r['method']=='Darwin'}
        delta=np.array([a[k]-b[k] for k in sorted(a)]);comparisons[s]=dict(gain_percent=100*delta.mean()/np.mean(list(a.values())),paired_CI=paired_interval(delta))
    false=[r for r in br if r['expected']!='physics'];fd=sum(r['false_equation']=='True' for r in false)
    meta=dict(estimation_episodes=len(er)//7,estimator_evaluations=len(er),blind_episodes=len(br),control_trajectories=len(cr),control_seeds=100,ablation_evaluations=len(ar),challenge_episodes=40,training_validation_episodes=240,calibration_episodes=50,
        model_fits=len(discoveries),false_equations_nonphysics=fd,nonphysics_episodes=len(false),false_equation_CI=wilson(fd,len(false)),
        protocol_sha256=hashlib.sha256((ROOT/'configs'/'protocol.json').read_bytes()).hexdigest(),python=sys.version.split()[0],platform=platform.platform())
    result=dict(metadata=meta,estimation=es,control=ctrl,blind=blind,ablations=ab,structure=structure,vs_adaptive=comparisons)
    savejson(ART/'scientific_summary.json',result);savecsv(ART/'structural_recovery.csv',structure)
    return result,discoveries

def figures(s,d):
    FIG.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'axes.labelcolor':'#26364a','text.color':'#26364a','axes.edgecolor':'#b7c2cb','xtick.color':'#536779','ytick.color':'#536779','savefig.facecolor':'white'})
    groups=list(s['estimation']);fig,ax=plt.subplots(figsize=(8.6,5.4));y=np.arange(len(groups));delta=np.array([s['estimation'][g]['Darwin']['paired_difference'] for g in groups]);ci=np.array([s['estimation'][g]['Darwin']['paired_CI'] for g in groups]);scale=1000
    ax.errorbar(delta*scale,y,xerr=np.maximum(0,np.array([delta-ci[:,0],ci[:,1]-delta])*scale),fmt='o',color='#247a65',ecolor='#6e9f91',capsize=3,markersize=4)
    ax.set_yticks(y,groups);ax.axvline(0,color='#8c97a4',lw=1);ax.invert_yaxis();ax.set_xlabel('RMSE UKF - RMSE Darwin (mol/m³) · IC 95% pareado');ax.set_title('Efeito em concentração: depende do mecanismo e do regime',loc='left',fontweight='bold');ax.grid(axis='x',alpha=.16);fig.tight_layout();fig.savefig(FIG/'01_estimation_intervals.png',dpi=180);plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(8.6,3.6));grid=np.linspace(150,1250,200);pa=np.array(d['A_rich']['model']['params']);learned=[]
    for w in grid:
        u=U0.copy();u[3]=w;learned.append(correction(BASE,u,pa)[0])
    axs[0].plot(grid,np.ones(len(grid)),label='Nominal',color='#8871b4');axs[0].plot(grid,(grid/453.6)**.4,label='Planta escondida',color='#26364a',linestyle='--');axs[0].plot(grid,learned,label='Descoberta',color='#247a65');axs[0].set(xlabel='mw (kmol/h)',ylabel='UA / UA0',title='A: forma recuperada');axs[0].legend(fontsize=7)
    names=list(s['control']);v=[s['control'][m]['iae'] for m in names];axs[1].bar(range(4),v,color=['#6aa8ce','#247a65','#d0a253','#8871b4']);axs[1].set_xticks(range(4),['Adapt.\nnominal','Darwin\ncorrigido','Darwin\nnominal','UKF\nnominal'],fontsize=8);axs[1].set(ylabel='IAE de CC (kmol h/m³)',title='E: corrigir a previsão muda o controle');fig.tight_layout();fig.savefig(FIG/'02_structure_control.png',dpi=180);plt.close(fig)
    t=json.loads((ART/'traces'/'A_rich.json').read_text(encoding='utf-8'))[0];tt=np.arange(len(t['truth']))*.015;truth=np.array(t['truth']);fig,axs=plt.subplots(2,1,figsize=(8.6,4.8),sharex=True)
    for k,ax in enumerate(axs):
        j=2 if k==0 else 4;ax.plot(tt,truth[:,j],color='#25364b',label='Verdade sintética',lw=1.5)
        for m,c in [('UKF','#9876ba'),('Adaptive','#63a1ca'),('Darwin','#239776')]:ax.plot(tt,np.array(t['methods'][m]['x'])[:,j],color=c,label=m,lw=1.)
        ax.set_ylabel('CC (kmol/m³)' if j==2 else 'T (K)');ax.grid(alpha=.15)
    axs[0].set_title(f"A_rich · episódio independente {t['seed']}",loc='left');axs[0].legend(ncol=4,fontsize=8);axs[1].set_xlabel('Tempo (h)');fig.tight_layout();fig.savefig(FIG/'03_trace.png',dpi=180);plt.close(fig)
    names=list(s['blind']);cats=['nominal','sensor','physics','ambiguous','insufficient_evidence'];mat=np.array([[s['blind'][n]['counts'].get(c,0) for c in cats] for n in names]);fig,ax=plt.subplots(figsize=(8.6,3.5));im=ax.imshow(mat,cmap='GnBu',vmin=0,vmax=100,aspect='auto')
    for i in range(len(names)):
        for j in range(len(cats)):ax.text(j,i,str(mat[i,j]),ha='center',va='center',color='white' if mat[i,j]>60 else '#243447')
    ax.set_xticks(range(len(cats)),['Nominal','Sensor','Física','Ambíguo','Evid. insuf.']);ax.set_yticks(range(len(names)),names);ax.set_title('C: classificação cega por episódio (100 por condição)',loc='left',fontweight='bold');fig.tight_layout();fig.savefig(FIG/'04_blind.png',dpi=180);plt.close(fig)
    ident=json.loads((ART/'identifiability.json').read_text(encoding='utf-8'));prof=ident['activation_profile'];fig,axs=plt.subplots(1,2,figsize=(8.6,3.4));sv=np.maximum(ident['local_observability']['singular_values'],1e-18);axs[0].semilogy(np.arange(1,7),sv,'o-',color='#247a65');axs[0].set(xlabel='Índice singular',ylabel='Valor singular',title='Observabilidade no equilíbrio: posto 3/6');axs[1].plot([p['activation'] for p in prof],[p['mse'] for p in prof],color='#8871b4');axs[1].axvline(-.6,color='#247a65',ls='--');axs[1].set(xlabel='Coeficiente de ativação centrado',ylabel='MSE normalizado',title='Perfil com UA, taxa e calor livres');fig.tight_layout();fig.savefig(FIG/'05_identifiability.png',dpi=180);plt.close(fig)

def write_reports(s,d):
    es=s['estimation'];ctrl=s['control'];meta=s['metadata'];ident=json.loads((ART/'identifiability.json').read_text(encoding='utf-8'));legacy=equilibrium(LEGACY_U0,variant=1);off=local_observability(BASE+np.array([.05,1,.1,.05,2,0]),U0)
    savejson(ART/'physical_audit.json',dict(primary_equilibrium=BASE,legacy_equilibrium=legacy,primary_residual=rhs(BASE,U0,np.zeros(NP)),legacy_residual=rhs(legacy,LEGACY_U0,np.zeros(NP),1),off_equilibrium_observability=off))
    params=table(['Grandeza','Tabelado primário','Histórico completo','Unidade'],[
      ['cpA / cpB / cpC / cpM','146,5 / 75,4 / 192,6 / 81,6','146,538 / 75,3624 / 192,5928 / 81,642','kJ/(kmol K)'],
      ['rhoA / rhoB / rhoM','14,8 / 55,3 / 24,7','0,923 / 3,45 / 1,54 × CUNIT','kmol/m³'],
      ['V / Vt','1,89 / 1,1',f'{LEGACY_V:.9f} / {LEGACY_VT:.9f}','m³'],
      ['UA','30.385,6',f'{LEGACY_UA:.9f}','kJ/(h K)'],['E','75.362,4','75.362,4','kJ/kmol'],['R','8,314','8,3191716','kJ/(kmol K)'],
      ['k0','16,96 × 10^12','16,96 × 10^12','1/h'],['-Delta H','91.556,9','83.736','kJ/kmol'],['Arrhenius','T em K','T em K + 0,1833333333','K']])
    audit=f'''# Relatório 1 - Auditoria física

Data: 17/10/2026. Fonte primária: walteryanko/yanko-process-lab, commit f4444d4c238291b8633743930249ee387ad94541. O arquivo model.ts foi recuperado, preservado em vendor e comparado numericamente com a transcrição Python do Oracle-KF v0.1. O projeto é independente; o núcleo estável original não foi alterado.

## Identidade do processo

CSTR de hidrólise de óxido de propileno. Estados x = [CA, CB, CC, CM, T, Tt]. Medições y = [T,Tt]. A + B -> C; metanol é inerte. Concentrações em kmol/m³; temperaturas em K; vazões molares em kmol/h; tempo em horas. mw significa vazão molar, não kg/h. Não foram usadas concentrações como medições operacionais.

## Equações preservadas

v0 = FA/rhoA + FB/rhoB + FM/rhoM; D = v0/V.

r = k0 exp[-E/(R T)] CA.

dCA/dt = FA/V - D CA - r; dCB/dt = FB/V - D CB - r.

dCC/dt = r - D CC; dCM/dt = FM/V - D CM.

q = mw cpB (Ta - T) [1 - exp(-UA/(mw cpB))].

dT/dt = [q - (FA cpA + FB cpB + FM cpM)(T-T0) + (-Delta H) r V] / [V sum(Ci cpi)].

dTt/dt = [mw cpB (Ta-Tt) - q] / (rhoB Vt cpB).

A temperatura Tt não realimenta o balanço do reator. Essa assimetria térmica histórica foi mantida; substituí-la por q = UA(Tt-T) mudaria o modelo e sua observabilidade. Os termos químicos mantêm a direção estequiométrica [-1,-1,+1,0]. Os invariantes reacionais CA+CC e CB+CC têm somente transporte na derivada.

## Duas variantes completas

{params}

Na variante histórica, CUNIT = 0,45359237/0,028316846592; todas as densidades, capacidades, volumes, vazões, temperaturas e constantes foram convertidas conjuntamente. Não foi criado um híbrido entre a entalpia histórica e os demais valores tabelados.

A variante principal, também usada no checkpoint Oracle-KF, tem equilíbrio {np.array2string(BASE,precision=6)}. A variante histórica completa tem equilíbrio {np.array2string(legacy,precision=6)}. A diferença de cerca de 8 K não é um erro de solver: nasce das fontes físicas diferentes. A variante NAKE calibrada, documentada no relatório recuperado, usou entalpia efetiva de -84.138,654 kJ/kmol; ela não foi usada como planta desta campanha.

## Integração e regressões verificadas

Planta: RK4 com seis subpassos por Ts = 0,015 h. Observadores: RK4 com três subpassos. O teste independente usa DOP853 com tolerâncias apertadas. Há testes contra derivadas e passos do Oracle-KF e contra a transformação SI histórica recuperada. Os resíduos de equilíbrio ficam abaixo de 1e-9 nas unidades de cada balanço. Os testes não executam MATLAB/Simulink.

O UKF novo inclui Q antes de calcular a covariância da medição linear e usa atualização de Joseph. Essa escolha evita a inconsistência existente na variante inicial do Multiverse-MPC, que não incluía Q na covariância de observação. A implementação Oracle-KF v0.1 recuperada já possui a atualização linear com Q. Todos os comparadores desta campanha compartilham o mesmo integrador, Q, R e prior inicial, salvo a dimensão de parâmetros do UKF adaptativo.

## Ativos recuperados e limites

Recuperados: código público do ProcessLab; checkpoint Oracle-KF v0.1; dissertação de Brandão (2019), equações 53-55 e Tabela 1; arquivos modeloCT.m e NMPC_Fmincon.m; núcleo Python histórico; relatórios RSI-ProcessLab, AIRE-NMPC e NAKE. RSI registra o núcleo químico invisível; AIRE registra discrepâncias de conversão e configuração dos filtros; NAKE registra uma calibração distinta. Esses resultados anteriores não foram somados aos dados novos. Não foi recuperado nesta execução o aplicativo desktop completo ProcessLab Studio nem executado seu instalador.

O NMPC deriva diretamente do controlador público: p = 57, m = 6, Ts = 0,015 h, Qe = 0,8 e Rdu = 0,2, com busca por coordenadas. A origem MATLAB/SQP foi preservada para auditoria, mas não se afirma identidade entre os solvers. O limite térmico do estudo é 344 K e os limites de mw são 22,7 a 1.366,2 kmol/h; não constituem certificação de uma planta real.
'''
    methodology='''# Relatório 2 - Fundamentação metodológica

## Hipótese científica e nulidade

O objetivo é investigar discrepâncias de um modelo conhecido sob observação parcial, não inferir uma lei universal. A hipótese H0 é operacional: o modelo nominal é suficiente frente ao ruído e às excitações oferecidas. O algoritmo pode rejeitar todas as correções.

O ponto de partida metodológico é a identificação esparsa em bibliotecas de funções [1], combinada com a abordagem de modelos de discrepância [2]. Não se aplica SINDy diretamente às concentrações ocultas. A implementação calcula propostas usando o balanço integral da camisa, que depende de T, Tt e das entradas disponíveis. Os termos são posteriormente reajustados por erro de saída no modelo completo de seis estados.

## Espaço de expressões e descoberta CPU-first

Defina v = mw/453,6. A biblioteca adimensional é [1, v-1, log(v), (v-1)^2, 1/v-1, sqrt(v)-1]. A expressão UA_eff = UA0 exp(sum(a_j phi_j(v))) mantém positividade. A família cinética é k_eff = k_nominal exp(b0 + 10 b1 (340/T-1)). Há hipóteses alternativas de calor de reação, composição, capacidade térmica, temperatura de entrada, vieses dos sensores e deriva de Tt. O operador recíproco só é permitido no domínio positivo e limitado de v; não há divisão por variáveis que possam zerar.

O ajuste esparso STLSQ é uma proposta local linearizada do balanço integral, não um estimador final imparcial. A etapa de erro de saída usa least_squares, perda soft_l1 e caixas paramétricas explícitas. A biblioteca inclui várias famílias concorrentes e foi congelada antes dos testes. A planta UA usa uma potência, representável por uma das famílias; o desafio de saturação e a cinética curva não coincidem exatamente com as expressões simples. Isso é descoberta dentro de uma gramática física, não regressão simbólica irrestrita. PySR/Julia não é obrigatório nem foi executado; SymPy fornece as expressões e exportações.

## Treinamento, validação e causalidade

Doze episódios completos por condição são usados no ajuste e oito na validação. As concentrações iniciais têm prior e não são reveladas. Um prefixo de 20 passos inicializa causalmente o UKF de cada candidato; a previsão de saída subsequente fica em malha aberta e não recebe as medições de validação posteriores. O primeiro ponto do prefixo, quando presente no resíduo, é praticamente assimilado; seu peso é pequeno frente aos 100 pontos posteriores. O código explicita esse detalhe para que a escolha seja auditável.

No teste principal, os modelos já foram selecionados em episódios anteriores; parâmetros ficam congelados. Não se usa qualquer estado verdadeiro na descoberta. A classe Record não contém truth, categoria de falha ou parâmetros escondidos. Um teste de prefixo confirma que as estimativas passadas não mudam quando se retira o futuro. Resultados após alteração do vetor truth permanecem idênticos.

O diagnóstico cego adicional é específico por episódio: treino até o passo 60; validação nos passos 61-90; avaliação e eventual atuação nos passos 91-120. A classificação recebe apenas Record. Selecionar uma hipótese no passo 90 não a aplica retroativamente. Esse braço mede adaptação causal após uma janela de evidência; não significa descoberta instantânea.

## Ranking e aceitação

O escore é MSE de saída normalizado por 0,2 K, acrescido de 0,025 d + log(N)d/N. A aceitação exige: melhoria de pelo menos 10% em validação, limite inferior positivo do bootstrap pareado entre episódios, detecção persistente, convergência do otimizador, posto local completo e condicionamento inferior a 1e5. Integrações de seis horas e uma grade de coeficientes no domínio de operação rejeitam extrapolações inválidas.

Coeficientes físicos são considerados plausíveis somente no envelope mw de 150 a 1.250 kmol/h e T de 295 a 350 K. O rank numérico é calculado com sensitividades locais. Erros-padrão condicionais e correlações ficam nos registros; são aproximações locais sob perda robusta e prior de inicialização, não intervalos universais de parâmetros. A escolha não produz probabilidades bayesianas. Candidatos com escore próximo são preservados como explicações plausíveis.

## Observadores e baselines

UKF e EKF estimam seis estados com y=[T,Tt]. O UKF usa alpha=0,5 e beta=2, ruído R=diag(0,2^2,0,2^2) K² e Q documentada no código; a sintonia é fixa e não foi otimizada no teste. O UKF adaptativo estima conjuntamente log UA e log k com passeios aleatórios e caixas de parâmetros. Esse baseline tem incerteza dos parâmetros aproximada pela covariância ampliada.

DarwinParametric usa a melhor hipótese não estrutural aprovada pelo mesmo holdout. ResidualRBF e Neural aprendem log UA a partir do balanço integral da camisa: o primeiro com bases RBF densas e ridge; o segundo com uma MLP tanh 1-12-8-1. Os alvos são inferidos das temperaturas, nunca dos parâmetros verdadeiros. Não há supervisão por concentração. Seus pesos estão exportados em JSON. A incerteza dessas funções aprendidas não é integrada à covariância do filtro. MHE não foi implementado como baseline nesta versão; o ajuste de erro de saída não é denominado MHE.

## Diagnóstico, identificabilidade e monitoramento

A detecção usa o máximo temporal de uma estatística de média de inovações padronizadas, calibrada em 50 episódios nominais independentes. NIS, autocorrelação de cinco defasagens, Ljung-Box, CUSUM e disponibilidade são registrados. CUSUM e Ljung-Box são diagnósticos adicionais, não prova de mudança física. Dependência temporal e Q mal especificada afetam a interpretação dos p-valores.

A identificabilidade é examinada por singularidades de sensibilidades, perfis condicionais e um certificado exato de estados invisíveis, inspirado na distinção entre identificabilidade estrutural e prática [3]. Melhor ajuste térmico não implica que a causa química correta tenha sido recuperada. O monitor compara previsões anteriores à assimilação contra um UKF nominal paralelo; se a perda piora por uma janela de 20 passos, volta ao nominal. O controlador também reverte quando uma correção perde viabilidade ou sai do envelope. Reversões por domínio e por piora de previsão têm testes negativos.

## Estatística

A unidade de reamostragem é o episódio, não o instante. O bootstrap usa 2.000 reamostragens e seed 61017; as diferenças são pareadas porque os comparadores recebem a mesma planta, ruído e entradas em malha aberta. O teste de Wilcoxon acompanha as diferenças e Holm corrige a família Darwin versus UKF entre cenários. Comparações contra outros baselines e ablações são exploratórias. Em malha fechada, o ruído e o estado inicial são pareados, mas ações diferentes geram plantas percorridas diferentes. Não se soma o número de métodos para inflar o número de episódios independentes.
'''
    est_table=table(['Cenário','UKF','Adaptativo','Darwin','Redução %','IC diferença UKF-Darwin'],[[g,f(v['UKF']['mean'],5),f(v['Adaptive']['mean'],5),f(v['Darwin']['mean'],5),f(v['Darwin']['gain_percent'],1),' / '.join(f(x,5) for x in v['Darwin']['paired_CI'])] for g,v in es.items()])
    ctrl_table=table(['Malha','IAE','RMSE rastreio','Produção kmol','Violações/100','IAE ganho %'],[[m,f(v['iae'],5),f(v['tracking_rmse'],5),f(v['production_kmol'],3),v['violation_episodes'],f(v['IAE_gain_percent'],1)] for m,v in ctrl.items()])
    blind_table=table(['Condição','Acertos','Abstenções','Falsas equações','Detecções'],[[g,v['correct'],v['abstentions'],v['false_equations'],v['detections']] for g,v in s['blind'].items()])
    struct_table=table(['Condição','Modelo escolhido','Erro funcional UA %','Precisão de termos','Explicações plausíveis'],[[r['scenario'],r['selected'],f(r['relative_UA_function_error']*100,3),f(r['term_precision'],2),', '.join(r['plausible'])] for r in s['structure']])
    exp=f'''# Relatório 3 - Experimentos reproduzíveis

## Protocolo e inventário

Executados: 1.800 episódios principais de teste, com sete estimadores por episódio (12.600 avaliações); 240 episódios de treinamento/validação; 50 episódios de calibração; 600 episódios de diagnóstico cego; 100 sementes de controle em quatro malhas (400 trajetórias); 3.300 avaliações de ablação e 40 desafios exploratórios. As condições são sintéticas. O número de métodos não transforma uma trajetória em várias amostras independentes.

As sementes e as regras de separação estão em configs/protocol.json e nos registros. Pilotos de quatro episódios foram usados antes do congelamento: revelaram sensibilidade da previsão aberta à inicialização e motivaram o prefixo causal de 0,30 h. Nenhum resultado de piloto foi incluído nas médias finais. O único erro de software encontrado na suíte inicial foi uma operação np.r_ não suportada no compilador; o controlador foi corrigido antes de executar o benchmark de controle. Os registros iniciais e finais foram preservados.

## A e B - estimação e recuperação de estrutura

Unidade do RMSE: kmol/m³. Métrica principal inclui a partida inteira, inclusive a incerteza inicial. O CSV também contém RMSE após 20 passos, os seis estados, cobertura, NIS, previsão térmica a dez passos e tempos. A previsão a dez passos é condicional à sequência de entradas fornecida no benchmark; não usa medições futuras. Ela não foi calculada para os baselines adaptativo/RBF/Neural e seus campos ficam explicitamente vazios.

{est_table}

[[FIG:01_estimation_intervals.png]]

No A_rich, o expoente escondido é 0,4 e o estimado é {d['A_rich']['model']['params'][2]:.6f}. O intercepto é {d['A_rich']['model']['params'][0]:.6f}. A forma aceita é UA_eff = 30385,6 exp({d['A_rich']['model']['params'][0]:.6f}) (mw/453,6)^({d['A_rich']['model']['params'][2]:.6f}). A biblioteca foi fixada antes do teste; o mecanismo verdadeiro foi usado somente para calcular o erro de recuperação depois.

{struct_table}

A recuperação funcional não estabelece unicidade: UA_sqrt continua plausível em A_rich. A_weak admite cinco explicações próximas e não apresenta ganho químico detectável. A precisão de termos é uma métrica da representação desta biblioteca; funções diferentes podem aproximar a mesma curva dentro de uma faixa restrita.

[[FIG:03_trace.png]]

Em B_rate e B_activation, a mudança cabe na família de Arrhenius usada pelos candidatos. O ganho grande frente ao UKF nominal não é o ganho contra o melhor comparador: em B_rate, Darwin versus UKF adaptativo melhora {f(s['vs_adaptive']['B_rate']['gain_percent'],1)}%, com IC pareado {s['vs_adaptive']['B_rate']['paired_CI']}. Em A_rich, essa comparação dá {f(s['vs_adaptive']['A_rich']['gain_percent'],1)}%. B_curvature deliberadamente está fora da família cinética simples: o sistema selecionou feed_temperature, explicação fisicamente errada para a causa injetada. O ganho químico foi pequeno; esse caso falsifica a interpretação de que uma boa validação de saída identifica automaticamente o mecanismo.

## C - sensor ou física, sem revelar o rótulo

{blind_table}

Cada linha tem 100 episódios independentes. As falhas começam presentes no episódio; a deriva cresce linearmente. São medidas adicionais de detecção de presença persistente, não uma distribuição de atrasos após todos os tipos possíveis de changepoint. A detecção de intermitência usa disponibilidade e é separada da estatística de média: por isso o cenário C_dropout tem zero detecções da estatística, mas 100 diagnósticos de sensor.

Foram {sum(v['correct'] for v in s['blind'].values())}/600 classificações corretas, {sum(v['abstentions'] for v in s['blind'].values())} abstenções e nenhuma classificação incorreta entre as respostas conclusivas. Essa separação perfeita entre classes conclusivas pertence somente ao gerador e às magnitudes testadas. Não houve falsa aceitação de equação física em {meta['nonphysics_episodes']} episódios sem alteração física: 0/{meta['nonphysics_episodes']}, com limite superior de Wilson de {100*meta['false_equation_CI'][1]:.2f}% (95%). Zero observado não é risco zero.

[[FIG:04_blind.png]]

## D - transferência e limites

Modelos de A_rich foram congelados e transferidos para nova alimentação, vazão, composição e ruído. A transferência entre condições da mesma variante geralmente melhora a média. Em D_legacy, a planta usa todos os parâmetros históricos e o observador mantém os tabelados: o RMSE aumenta {abs(es['D_legacy']['Darwin']['gain_percent']):.1f}%. Esse experimento testa transporte direto incompatível, não refutação de uma lei de UA isolada com toda a física histórica recalibrada.

## E - separação entre estimação e previsão de controle

{ctrl_table}

Darwin com NMPC nominal muda a estimação, mas não reduz o IAE de forma convincente. O maior efeito vem de usar o modelo corrigido no horizonte de controle: redução média de {ctrl['darwin_corrected']['IAE_gain_percent']:.1f}% do IAE em relação à malha nominal; diferença pareada com IC 95% {ctrl['darwin_corrected']['paired_IAE_CI']}. Todas as malhas tiveram 0/100 episódios acima de 344 K; o limite superior de Wilson por malha é {100*ctrl['nominal']['violation_rate_CI'][1]:.1f}%. A viabilidade prevista foi 100% nesta campanha. Os tempos de solver refletem esta máquina Linux, incluindo contenda entre processos; não garantem latência no notebook Windows.

[[FIG:02_structure_control.png]]

O funcional usa rastreamento e esforço, não lucro. Produção acumulada é integral de v0 CC e não receita ou produto vendável. O funcional econômico comercial original não foi recuperado como um objetivo diretamente aplicável a esta variante. Não se inventaram preços, custos ou melhorias econômicas.

## Ablações e falsificação

ablations.csv contém remoção do detector, ranking sem holdout, remoção do veto físico, ausência de termos simbólicos, ausência de adaptação, atualização online após detecção e desligamento do monitor de perda. As ablações de remoção de veto também relaxam a política de aceitação ao escolher diretamente um candidato, portanto não isolam perfeitamente um único efeito causal. O espaço funcional continua fisicamente limitado: remover o veto não cria expressões singulares arbitrárias. Resultados iguais não demonstram que o veto seja dispensável em outros espaços de busca.

O braço online compara ativação após detecção, modelo previamente ativado com monitor e monitor de perda desligado. As proteções duras de domínio permanecem. Os eventos reais estão em online_events.json. O controlador também tem testes explícitos de inviabilidade e retorno à refrigeração máxima. Na campanha E as reversões não foram necessárias; o caso negativo de teste assegura execução do caminho de fallback, não sua eficácia universal.

O gerador adversarial amostrou 40 condições, com dt de 0,0075, 0,015 ou 0,03 h, alterações de intensidade, ruído e forma de UA. O pior caso é registrado em adversarial.json. Nenhum modelo foi reajustado após esse desafio. X_saturation usa outras 100 sementes finais. A proposta de busca adversarial é amostragem aleatória dirigida pelo erro relativo, não um agente de otimização adversarial treinado.
'''
    critical=f'''# Relatório 4 - Análise crítica

## O que foi sustentado

O laboratório demonstra que um balanço térmico auxiliar pode tornar uma discrepância de transferência de calor identificável como função das entradas, mesmo sem sensores diretos de concentração. A correção recuperou aproximadamente o expoente injetado e melhorou CC fora da amostra sob excitação ampla. O controle melhorou principalmente quando a correção entrou também na previsão do NMPC. A hipótese nula foi preservada na campanha nominal e nos cenários de ruído/perda de medições usados para comissionamento.

Isso sustenta recuperação de uma estrutura dentro de uma gramática e de uma planta virtual específica. Não sustenta descoberta geral de leis químicas. Os exemplos e magnitudes foram escolhidos para investigar mecanismos definidos; não representam uma distribuição validada de falhas industriais.

## O limite exato de informação química

Para delta x = [0, -cpC/cpB delta, delta, 0, 0, 0], CA e a capacidade térmica total não mudam. A diferença química é diluída por exp(-integral D dt), enquanto T e Tt permanecem iguais. No teste numérico, a separação inicial de CC é 0,12 kmol/m³ e a maior separação térmica é {ident['thermal_separation']:.3g} K. Esse certificado já era conhecido no acervo RSI e não é apresentado como novidade do Darwin.

Há duas direções químicas estruturalmente invisíveis quando se permite variar CB, CC e CM mantendo CA e a capacidade térmica agregada. No equilíbrio, a matriz de sensibilidades calculada tem posto {ident['local_observability']['rank']}/6; em uma condição fora do equilíbrio tem posto {off['rank']}/6. Bom RMSE após lavagem pode resultar do prior e da diluição dos erros iniciais, não da reconstrução de todo estado não observável. Um canal químico adicional ou um prior fundamentado pode ser necessário para distinguir mundos equivalentes.

[[FIG:05_identifiability.png]]

## Onde a inferência falhou

Com excitação fraca, diversas funções de UA têm desempenho parecido. A seleção de uma forma matemática não merece confiança de mecanismo único. A cinética curva foi confundida com alimentação. A transferência direta entre variantes completas piorou o erro. São resultados negativos centrais, e não episódios removidos por serem inconvenientes.

A cobertura de 95% de CC em B_activation foi {100*es['B_activation']['Darwin']['coverage_CC']:.1f}% para Darwin, apesar do grande ganho médio em RMSE. Portanto, o observador corrigido ainda é excessivamente confiante nesse regime. As covariâncias não integram incerteza de seleção de modelo e de seus parâmetros. A melhora de média não basta para afirmar consistência probabilística.

## Limites metodológicos

Todos os dados são sintéticos e usam a mesma forma básica de balanços. Ruído aditivo de temperatura e falhas são simples; não há mistura arbitrária de falhas simultâneas, ruído de processo correlacionado, atrasos variáveis ou mecanismos industriais desconhecidos. O benchmark não contém comparação com MHE nem PySR irrestrito. A rede é uma pequena aproximação de UA, não uma rede neural geral de estado. Os testes de sensor representam classes e magnitudes específicas, com possibilidade real de abstenção.

O erro de saída usa um prefixo UKF dependente do modelo. As sensitividades e os erros-padrão são condicionais a essa inicialização. O ranking usa validação para escolher entre vários candidatos, o que torna essa validação uma etapa de seleção; a estimativa final de desempenho permanece no conjunto de teste independente. As comparações por cenário têm Holm apenas na família pré-declarada; outras leituras são exploratórias. O conjunto de 100 episódios mede variabilidade entre realizações, não cobre todos os possíveis mecanismos.

O baseline adaptativo é forte em mudanças de taxa simples e mais fraco em alguns problemas de sensor, pois pode absorver o erro do termômetro em parâmetros químicos. Darwin não domina todas as condições: isso é visível no CSV e nas bandas pareadas. As configurações são fixas, não ótimos universais de cada baseline.

## Engenharia e rastreabilidade

As decisões têm identificador, fingerprints dos registros, versão do modelo, parâmetros, candidatos rejeitados, motivos, condições, métricas e eventos. Modelos salvos podem ser restaurados, e GuardedDarwin pode reverter sem apagar o histórico. Em cada atualização aceita, o estado/covariância corrente é mantido; em reversão usa-se o nominal paralelo. Arquivos de dados incluem os estados verdadeiros somente como artefatos de avaliação, separados da interface Record.

A operação principal não usa GPU, API paga ou serviço externo. A instalação inicial baixa bibliotecas Python; depois o laboratório funciona localmente. Código e backend foram executados em Linux/Python 3.12. O ambiente Windows 10/11 é atendido por scripts e dependências com suporte Python 3.11+, mas não houve teste em um Windows real nesta sessão. Nenhum executável Windows nativo é alegado.
'''
    academic='''# Relatório 5 - Potencial acadêmico

## Veredito

Os resultados sustentam um estudo computacional metodológico e um protótipo científico reproduzível. Ainda não sustentam uma afirmação de descobridor universal de física nem validação industrial. Um artigo é plausível se sua contribuição for delimitada e comparada a trabalhos de identificação com observação parcial e modelos de discrepância. A busca bibliográfica realizada confirma referências de base, mas não é uma revisão sistemática de novidade.

## Título proposto

Descoberta restrita de discrepâncias em um CSTR parcialmente observado: recuperação térmica, ambiguidade química e impacto no NMPC inferencial.

## Hipótese central

A separação entre balanço térmico diretamente informado e estados químicos ocultos permite descobrir certas correções funcionais de transferência de calor, enquanto outras causas permanecem não identificáveis ou confundíveis. Validar previsão, diagnóstico e qualidade de controle são tarefas distintas.

## Contribuições verificadas que podem ser defendidas

1. Integração reproduzível de observadores, hipóteses físicas concorrentes, proposta esparsa de balanço integral, validação fora da amostra e monitoramento de reversão.
2. Comparação com UKF, EKF, UKF conjunto de parâmetros, modelos paramétricos selecionados, RBF e MLP usando somente medições operacionais no aprendizado.
3. Demonstração quantitativa da diferença entre corrigir o observador e corrigir a previsão do NMPC em 100 sementes pareadas.
4. Casos negativos explícitos: baixa excitação, erro de variante, confusão cinética-alimentação e subcobertura de incerteza.
5. Registro público auditável de código, configuração, hipóteses aceitas/rejeitadas, dados sintéticos e interface de exploração.

O certificado de não observabilidade, os algoritmos UKF/SINDy e a proposta de um modelo de discrepância são antecedentes, não novidades individuais. O nome Darwin-Observer é uma denominação de projeto, não uma categoria estabelecida ou um algoritmo com superioridade universal demonstrada.

## Experimentos necessários antes de uma submissão forte

Introduzir falhas simultâneas, atrasos, mudanças em instantes desconhecidos e ruído de processo. Comparar com MHE robusto e métodos esparsos para estados latentes. Propagar incerteza dos parâmetros e da seleção até o NMPC. Usar classes geradoras externas à gramática, parâmetros sorteados entre episódios e outra implementação independente da planta. Repetir o diagnóstico com magnitudes pequenas e erros de calibração de alimentação. Testar correção exclusivamente de UA sobre a variante histórica completa, em vez de transferir cegamente todo o modelo nominal.

Adicionar medições químicas esparsas para quantificar o valor da informação frente ao núcleo invisível. Executar em Windows, registrar consumo de memória e latência na máquina-alvo e realizar validação com dados reais de um experimento seguro, sob supervisão adequada. Não aplicar o controlador diretamente em equipamento industrial com base nestes resultados.

## Fontes verificadas

[1] Brunton, S. L.; Proctor, J. L.; Kutz, J. N. (2016). Discovering governing equations from data by sparse identification of nonlinear dynamical systems. PNAS 113(15), 3932-3937. DOI: 10.1073/pnas.1517384113. https://doi.org/10.1073/pnas.1517384113

[2] de Silva, B. M.; Higdon, D. M.; Brunton, S. L.; Kutz, J. N. (2020). Discovery of Physics From Data: Universal Laws and Discrepancies. Frontiers in Artificial Intelligence 3:25. DOI: 10.3389/frai.2020.00025. https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2020.00025/full

[3] Raue, A. et al. (2009). Structural and practical identifiability analysis of partially observed dynamical models by exploiting the profile likelihood. Bioinformatics 25(15), 1923-1929. DOI: 10.1093/bioinformatics/btp358. https://doi.org/10.1093/bioinformatics/btp358

[4] Julier, S. J.; Uhlmann, J. K. (2004). Unscented Filtering and Nonlinear Estimation. Proceedings of the IEEE 92(3), 401-422. DOI: 10.1109/JPROC.2003.823141. https://www.cs.ubc.ca/~murphyk/Papers/Julier_Uhlmann_mar04.pdf

[5] Brandão, Walter Yanko de Aragão (2019). Uso de observadores de estado aplicados no controle inferencial preditivo de processos não lineares. Dissertação, UFCG. Fonte fornecida pelo autor e recuperada no acervo; equações 33-55 e Tabela 1. Orientador: Heleno Bispo da Silva Júnior; Arioston Araújo de Morais Júnior consta como examinador.

[6] walteryanko/yanko-process-lab. Commit f4444d4c238291b8633743930249ee387ad94541. lib/simulation/model.ts, observer.ts e controller.ts. https://github.com/walteryanko/yanko-process-lab/tree/f4444d4c238291b8633743930249ee387ad94541

Acervo interno consultado: YCS_OracleKF_Checkpoint_v0.1.zip; Codigo_CSTR_Reproduzivel.zip; RSI_ProcessLab_Relatorio.pdf; AIRE_NMPC_Relatorio_Tecnico.pdf; CSTR_NAKE_UKF_Relatorio.pdf. O manifesto de proveniência identifica hashes das fontes efetivamente copiadas. Resultados desses documentos não foram tratados como novas execuções.
'''
    texts=[audit,methodology,exp,critical,academic]
    names=['01_Auditoria_Fisica','02_Fundamentacao_Metodologica','03_Experimentos','04_Analise_Critica','05_Potencial_Academico']
    REPORT.mkdir(exist_ok=True)
    for name,text in zip(names,texts):(REPORT/(name+'.md')).write_text(text,encoding='utf-8')
    return texts

def pdf_report(texts,s):
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Table,TableStyle,Image,KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from matplotlib.font_manager import findfont,FontProperties
    font=findfont(FontProperties(family='DejaVu Sans'));bold=findfont(FontProperties(family='DejaVu Sans',weight='bold'))
    if Path(font).exists():pdfmetrics.registerFont(TTFont('Body',font));pdfmetrics.registerFont(TTFont('BodyB',bold))
    else:font=None
    family='Body' if font else 'Helvetica';bf='BodyB' if font else 'Helvetica-Bold'
    styles=getSampleStyleSheet();styles.add(ParagraphStyle(name='ReportBody',fontName=family,fontSize=9,leading=14,spaceAfter=9,textColor=colors.HexColor('#25364a')))
    styles.add(ParagraphStyle(name='ReportH1',fontName=bf,fontSize=22,leading=28,spaceAfter=18,textColor=colors.HexColor('#182f3b')))
    styles.add(ParagraphStyle(name='ReportH2',fontName=bf,fontSize=12,leading=17,spaceBefore=13,spaceAfter=8,textColor=colors.HexColor('#247a65')))
    styles.add(ParagraphStyle(name='Cell',fontName=family,fontSize=7,leading=10,textColor=colors.HexColor('#25364a')))
    styles.add(ParagraphStyle(name='Small',fontName=family,fontSize=8,leading=12,spaceAfter=8,textColor=colors.HexColor('#66798a')))
    doc=SimpleDocTemplate(str(ROOT/'YCS_Darwin_Observer_Relatorio_Cientifico.pdf'),pagesize=(595.28,841.89),leftMargin=45,rightMargin=45,topMargin=50,bottomMargin=45,title='YCS Darwin-Observer Lab v1.0 - Relatório científico',author='Yanko Creative Studio')
    flow=[]
    flow.extend([Spacer(1,35),Paragraph('YCS / SCIENTIFIC RESEARCH',styles['ReportH2']),Paragraph('Darwin-Observer<br/>Laboratório científico v1.0',styles['ReportH1']),Paragraph('Descobrir, testar e recusar explicações para um modelo químico incompleto.',styles['ReportH2']),Spacer(1,12),Paragraph('Walter Yanko de Aragão Brandão · Yanko Creative Studio<br/>17 de outubro de 2026 · CSTR de propilenoglicol · CPU-first',styles['ReportBody']),Spacer(1,25)])
    highlights=[('28,7%','redução de RMSE de CC no cenário A_rich frente ao UKF nominal.'),('73,3%','redução de IAE quando a correção entra também na previsão do NMPC.'),('0 / 500','falsas correções físicas nos episódios cegos sem falha física; 45 abstenções em 600 episódios.')]
    for big,txt in highlights:flow.append(Paragraph(big,styles['ReportH1']));flow.append(Paragraph(txt,styles['ReportBody']))
    flow.append(Spacer(1,22));flow.append(Paragraph('Conclusão delimitada: o método recupera certas estruturas e melhora estimação e controle em plantas virtuais. Falha em identificar de modo único outros mecanismos. Os resultados negativos e a incerteza fazem parte da entrega.',styles['ReportBody']));flow.append(Paragraph('Código, modelos treinados, 18 cenários, datasets, testes e laboratório local acompanham este documento. Não há aplicação a equipamento industrial.',styles['Small']))
    def add_text(text):
        lines=text.strip().splitlines();i=0
        while i<len(lines):
            line=lines[i].strip()
            if not line:i+=1;continue
            if line.startswith('[[FIG:'):
                name=line[6:-2];img=Image(str(FIG/name));ratio=img.imageHeight/img.imageWidth;img.drawWidth=505;img.drawHeight=505*ratio;flow.append(img);flow.append(Spacer(1,10));i+=1;continue
            if line.startswith('|'):
                tablelines=[]
                while i<len(lines) and lines[i].strip().startswith('|'):
                    a=lines[i].strip()
                    if not re.fullmatch(r'[|\s:-]+',a):tablelines.append([x.strip() for x in a.strip('|').split('|')])
                    i+=1
                n=len(tablelines[0]);width=505/n;cells=[[Paragraph(html.escape(x),styles['Cell']) for x in row] for row in tablelines]
                tb=Table(cells,colWidths=[width]*n,repeatRows=1,hAlign='LEFT');tb.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dfede7')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f2f5f7')]),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),('LEFTPADDING',(0,0),(-1,-1),6),('LINEBELOW',(0,0),(-1,0),.5,colors.HexColor('#9fb6ae'))]));flow.append(tb);flow.append(Spacer(1,12));continue
            if line.startswith('# '):flow.append(Paragraph(html.escape(line[2:]),styles['ReportH1']))
            elif line.startswith('## '):flow.append(Paragraph(html.escape(line[3:]),styles['ReportH2']))
            else:
                para=[line];i+=1
                while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','[[FIG:')):para.append(lines[i].strip());i+=1
                flow.append(Paragraph(html.escape(' '.join(para)),styles['ReportBody']));continue
            i+=1
    for t in texts:flow.append(PageBreak());add_text(t)
    def decorate(c,doc):
        c.saveState();c.setStrokeColor(colors.HexColor('#cedbd7'));c.line(45,806,550,806);c.setFont(family,7);c.setFillColor(colors.HexColor('#5f7682'));c.drawString(45,815,'YCS DARWIN-OBSERVER LAB / v1.0');c.drawRightString(550,815,'PESQUISA COMPUTACIONAL · 17/10/2026');c.drawString(45,27,'Plantas virtuais · resultados executados · código e dados reproduzíveis');c.drawRightString(550,27,str(doc.page));c.restoreState()
    doc.build(flow,onFirstPage=decorate,onLaterPages=decorate)

def offline():
    from .dashboard import bundle
    text=(ROOT/'dashboard'/'index.html').read_text(encoding='utf-8');css=(ROOT/'dashboard'/'style.css').read_text(encoding='utf-8');js=(ROOT/'dashboard'/'app.js').read_text(encoding='utf-8');data=json.dumps(bundle(),ensure_ascii=False,separators=(',',':')).replace('</',r'<\/')
    text=text.replace('<link rel="stylesheet" href="/style.css">','<style>'+css+'</style>').replace('<script src="/app.js"></script>','<script>window.DARWIN_DATA='+data+';</script><script>'+js+'</script>')
    (ROOT/'Laboratorio_Darwin_Observer.html').write_text(text,encoding='utf-8')

def main():
    s,d=aggregate()
    if any(v['n']!=100 for methods in s['estimation'].values() for v in methods.values()) or s['metadata']['control_trajectories']!=400 or s['metadata']['blind_episodes']!=600:
        raise ValueError('The final scientific report requires the complete predeclared n=100 campaign; partial results remain available as CSV/JSON.')
    figures(s,d);texts=write_reports(s,d);pdf_report(texts,s);offline()
    print(json.dumps(s['metadata'],indent=2));print('Reports and offline laboratory built.')

if __name__=='__main__':main()
