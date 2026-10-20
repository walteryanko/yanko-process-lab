"""Generate figures, bilingual manuscripts, verified metrics and delivery manifest.
Requires pandoc and pdflatex for DOCX/PDF; compilation is actually executed.
Never fabricates a missing result.
"""
import sys,json,shutil,subprocess,hashlib,zipfile,platform
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np,pandas as pd
from pypdf import PdfReader
from model import *
import figures
import supplementary
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'results'
OUT=ROOT/'deliverables'/'YCS_PG_Information_Control_Frontier_v1.0_PARTIAL'
def table(df):
    # Native editable tables via Pandoc; no optional tabulate dependency.
    cols=list(df.columns)
    def value(x):
        if isinstance(x,(float,np.floating)):return f'{x:.5g}' if np.isfinite(x) else 'NA'
        return str(x).replace('|','/').replace('\n',' ').replace('_',' ')
    labels={'candidate':'Candidate','baseline':'Baseline','percent_improvement':'Gain (%)','mean_improvement':'IAE diff.','ci95_low':'CI lower','ci95_high':'CI upper','p_holm_primary':'Holm p','max_thermal_difference_K':'Max dT (K)','max_product_decay_error':'Product decay error','constant_input_max_thermal_difference':'Unexcited dT','excited_uncompensated_max_thermal_difference':'Excited dT','affine_kernel_max_thermal_difference':'Affine twin dT','affine_functional_rank':'Affine rank','quadratic_functional_rank':'Quadratic rank','derivative_check_error':'Derivative error','sufficient_rank4':'Rank 4 test','thermal_severity':'Thermal integral','decision_ms':'Decision ms','RMSE_CC':'RMSE CC'}
    return '| '+' | '.join(labels.get(str(k),str(k).replace('_',' ')) for k in cols)+' |\n| '+' | '.join(['---']*len(cols))+' |\n'+'\n'.join('| '+' | '.join(value(x) for x in row)+' |' for row in df.itertuples(index=False,name=None))+'\n'
def text(path,body):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(body,encoding='utf-8')
def verify():
    allrows=pd.concat([pd.read_csv(R/'episodes.csv'),pd.read_csv(R/'confirmation.csv')])
    index=allrows.set_index(['scenario','method','seed'])
    checks=[]
    for path in sorted((R/'trajectories').glob('*__*__*.npz')):
        bits=path.stem.split('__')
        if len(bits)!=3:continue
        scenario,method,seed=bits;key=(scenario,method,int(seed))
        if key not in index.index:continue
        record=index.loc[key];z=np.load(path);e=abs(z['x'][:,2]-z['reference'])
        iae=float(np.sum((e[1:]+e[:-1])*.5*np.diff(z['t'])))
        rmse=float(np.sqrt(np.sum((z['estimate'][:,2]-z['x'][:,2])**2)/len(z['t'])))
        q=z['u'][:,3]/U0[3];qm=1.3 if scenario=='saturation' else 3.
        checks.append(dict(scenario=scenario,method=method,seed=int(seed),iae_error=abs(iae-record.IAE),
             rmse_error=abs(rmse-record.RMSE_CC),bounds_ok=bool(np.all(q>=.05-1e-9)&np.all(q<=qm+1e-9)),
             slew_ok=bool(np.max(abs(np.diff(np.r_[1.,q])))<=.400001)))
    df=pd.DataFrame(checks);df.to_csv(R/'independent_metric_audit.csv',index=False)
    ok=len(df)==len(allrows) and df.iae_error.max()<1e-10 and df.rmse_error.max()<1e-10 and df.bounds_ok.all() and df.slew_ok.all()
    result=dict(trajectories_checked=len(df),trajectories_expected=len(allrows),
        max_iae_error=float(df.iae_error.max()),max_rmse_error=float(df.rmse_error.max()),pass_all=bool(ok))
    text(R/'independent_metric_audit.json',json.dumps(result,indent=2))
    if not ok:raise RuntimeError('independent metric or actuator audit failed')
    return result
def produce_document(stem,body,title_,language,number,doctype='article'):
    src=OUT/'07_LATEX_SOURCE';src.mkdir(exist_ok=True)
    md=src/(stem+'.md')
    date_label='20 de outubro de 2026' if language.startswith('pt') else '20 October 2026'
    pre=f'---\ntitle: "{title_}"\nauthor: "Walter Yanko de Aragão Brandão"\ndate: "{date_label}"\nlang: "{language}"\nfontsize: 11pt\ngeometry: margin=24mm\ncolorlinks: true\n---\n\n'
    text(md,pre+body)
    common=['pandoc',md.name,'--standalone','--citeproc','--bibliography=references.bib','--number-sections','--lua-filter=compact_tables.lua']
    log=[]
    def run(args):
        s=subprocess.run(args,cwd=src,text=True,encoding='utf-8',errors='replace',stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        log.append('COMMAND: '+' '.join(args)+'\n'+s.stdout)
        if s.returncode:raise RuntimeError('document command failed: '+' '.join(args)+'\n'+s.stdout[-4000:])
    run(common+['-o',stem+'.tex'])
    run(common+['-o',stem+'.docx'])
    run(['pdflatex','-interaction=nonstopmode','-halt-on-error',stem+'.tex'])
    run(['pdflatex','-interaction=nonstopmode','-halt-on-error',stem+'.tex'])
    text(OUT/'12_REPRODUCIBILITY'/(stem+'_build.log'),'\n'.join(log))
    pdf=src/(stem+'.pdf');docx=src/(stem+'.docx')
    reader=PdfReader(pdf);pages=len(reader.pages)
    with zipfile.ZipFile(docx) as z:
        if z.testzip() is not None:raise RuntimeError('DOCX ZIP integrity failure')
        xml=ET.fromstring(z.read('word/document.xml'))
        ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
        docx_tables=len(xml.findall('.//w:tbl',ns));docx_equations=len(xml.findall('.//m:oMath',ns))
        docx_images=len([n for n in z.namelist() if n.startswith('word/media/')])
        if stem in ['Article_EN','Artigo_PTBR'] and (docx_tables<9 or docx_equations<10 or docx_images<16):raise RuntimeError('DOCX lacks required tables/equations/figures')
    previews=OUT/'12_REPRODUCIBILITY/PDF_PREVIEWS';previews.mkdir(exist_ok=True)
    target_pages={1}
    for j,page in enumerate(reader.pages):
        txt=page.extract_text() or ''
        if 'Numerical results' in txt or 'Resultados numéricos' in txt:target_pages.add(j+1);break
    for page in target_pages:
        proc=subprocess.run(['pdftoppm','-f',str(page),'-singlefile','-scale-to','1500','-png',str(pdf),str(previews/f'{stem}_page_{page}')],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        if proc.returncode:raise RuntimeError('PDF preview rendering failed')
    if pages<2 or sum(len(p.extract_text() or '') for p in reader.pages)<1500:raise RuntimeError('PDF text/page validation failed')
    shutil.copy2(pdf,OUT/f'{number}_{stem}.pdf');shutil.copy2(docx,OUT/f'{number}_{stem}.docx')
    return dict(stem=stem,pages=pages,pdf_compiled=True,docx_created=True,docx_tables=docx_tables,docx_equations=docx_equations,docx_images=docx_images)

def main():
    if not (R/'execution.json').exists():raise RuntimeError('No completed execution ledger: refusing final-looking report.')
    execution=json.loads((R/'execution.json').read_text())
    audit=verify()
    supplementary.main()
    figures.main()
    OUT.mkdir(parents=True,exist_ok=True)
    for folder in ['07_LATEX_SOURCE','09_RESULTS/raw','09_RESULTS/processed','09_RESULTS/statistical_tests','09_RESULTS/tables',
        '10_CODE/research','11_TESTS','12_REPRODUCIBILITY','13_VISUAL_LAB','14_NEGATIVE_RESULTS','15_BIBLIOGRAPHY_REVIEW']:
        (OUT/folder).mkdir(parents=True,exist_ok=True)
    shutil.copytree(OUT/'08_FIGURES',OUT/'07_LATEX_SOURCE/figures',dirs_exist_ok=True)
    shutil.copy2(ROOT/'manuscripts/references.bib',OUT/'07_LATEX_SOURCE/references.bib')
    shutil.copy2(ROOT/'manuscripts/compact_tables.lua',OUT/'07_LATEX_SOURCE/compact_tables.lua')
    data=pd.read_csv(R/'episodes.csv');contrasts=pd.read_csv(R/'contrasts.csv')
    confirm=pd.read_csv(R/'confirmation_contrasts.csv');twins=pd.read_csv(R/'twins.csv');dec=pd.read_csv(R/'decisions.csv')
    mean=data.groupby(['scenario','method'])[['IAE','RMSE_CC','Tmax','thermal_severity','fallback','decision_ms','samples']].mean().reset_index()
    primary=contrasts[(contrasts.scenario=='FINITE_SUITE')&contrasts.apply(lambda r:[r.candidate,r.baseline] in
        [['P2_regret','B1_ukf'],['P3_adaptive_regret','B2_both'],['B2_both','B2_estimator']],axis=1)].drop_duplicates(['candidate','baseline'])
    primary=primary[['candidate','baseline','percent_improvement','mean_improvement','ci95_low','ci95_high','p_holm_primary']]
    selected=mean[(mean.scenario.isin(['nominal','inventory_plus','kinetic','combined']))&
        (mean.method.isin(['B1_ukf','B1_continuous','B2_estimator','B2_both','B4_mhe','P2_regret','P3_adaptive_regret']))]
    adverse=contrasts[(contrasts.baseline=='B1_ukf')&(contrasts.mean_improvement<0)&(contrasts.scenario!='FINITE_SUITE')].sort_values('percent_improvement').head(12)
    adverse=adverse[['scenario','candidate','percent_improvement','ci95_low','ci95_high']]
    parms=pd.DataFrame([
        ['V',V,'m3'],['Vt',VT,'m3'],['UA',UA,'kJ/(h K)'],['CpA',CP[0],'kJ/(kmol K)'],
        ['CpB',CP[1],'kJ/(kmol K)'],['CpC',CP[2],'kJ/(kmol K)'],['CpM',CP[3],'kJ/(kmol K)'],
        ['E',75362.4,'kJ/kmol'],['R',1.987*4.1868,'kJ/(kmol K)'],['k0',16.96e12,'1/h'],
        ['DeltaH',-83736.,'kJ/kmol'],['FA',U0[0],'kmol/h'],['FB',U0[1],'kmol/h'],['FM',U0[2],'kmol/h'],
        ['mw0',U0[3],'kmol/h'],['T0',U0[4],'K'],['Ta',U0[5],'K']],columns=['Parameter','Value','Unit'])
    x0=equilibrium();D=dilution(U0)
    snapshots=dict(nominal_state=x0.tolist(),dilution=float(D),residence_minutes=float(60/D),
        worst_IAE_bound_delta08=float(.8*(1-np.exp(-D*.9))/(2*D)),
        positive_grid_conflicts=int(np.sum(dec.regret>1e-10)),grid_cases=len(dec),
        maximum_sampled_T=float(data.Tmax.max()))
    text(R/'scientific_summary.json',json.dumps(snapshots,indent=2))
    supp=json.loads((R/'supplementary_audit.json').read_text())
    lie=pd.read_csv(R/'local_lie_quotient.csv')
    tests=(R/'tests.log').read_text()
    testok='OK' in tests and 'FAILED' not in tests
    if not testok:raise RuntimeError('Latest scientific tests did not pass')
    enabs=f"""# Abstract

This computational study examines information and decision limits in a recovered six-state propylene-glycol reactor model. An exact two-dimensional chemical equivalence class exists with constant species heat capacities and first-order kinetics. Restoring reciprocal jacket feedback does not eliminate it. A functional heat-capacity span characterizes a sufficient surviving ambiguity, while temperature-dependent property examples test practical separability. The executed main suite contains {execution['episodes']} trajectories, with {execution['confirmation']} independent-seed confirmation trajectories and {execution['grid_sensitivity']} grid-sensitivity checks. At nominal dilution, a two-world initial product separation of 0.8 kmol/m3 yields a worst-world 0.9-hour tracking lower bound of {snapshots['worst_IAE_bound_delta08']:.6f} kmol h/m3. Finite-grid decision conflict is positive in {snapshots['positive_grid_conflicts']} of {len(dec)} examined cases. Incremental ambiguity-control mean gains were 0.63% and 0.66%, with paired confidence intervals including zero; predictor sharing reduced IAE by 39.91% versus estimator-only adaptation. These outcomes do not establish superiority over all continuous NMPC designs. The physical alternatives remain uncalibrated and historical ICAC scalar results were not independently replayed. Accordingly this is a partial research manuscript, not a completed submission-ready validation.
"""
    ptabs=f"""# Resumo

Este estudo computacional investiga limites de informação e decisão em um modelo recuperado de reator de propilenoglicol de seis estados. Existe uma classe química exatamente indistinguível de dimensão dois sob capacidades caloríficas constantes e cinética de primeira ordem. Acrescentar realimentação térmica da camisa não a elimina. O posto funcional das capacidades caloríficas caracteriza uma ambiguidade suficiente remanescente; exemplos com propriedades dependentes de temperatura examinam a separabilidade prática. A suíte principal executou {execution['episodes']} trajetórias, com {execution['confirmation']} trajetórias de confirmação em sementes independentes e {execution['grid_sensitivity']} verificações de grade. Na diluição nominal, separação inicial de produto de 0,8 kmol/m3 implica limite inferior de {snapshots['worst_IAE_bound_delta08']:.6f} kmol h/m3 para o pior IAE entre dois mundos em 0,9 h. Há conflito decisório positivo em {snapshots['positive_grid_conflicts']} dos {len(dec)} casos finitos examinados. Os ganhos médios adicionais por ambiguidade foram 0,63% e 0,66%, com intervalos pareados incluindo zero; compartilhar a correção com o preditor reduziu IAE em 39,91% frente à correção somente do estimador. Não se demonstrou superioridade sobre todo NMPC contínuo. As alternativas físicas não foram calibradas, e os números históricos ICAC não foram reproduzidos independentemente. Trata-se de manuscrito parcial de pesquisa, ainda não validado para submissão.
"""
    paramsEN='\n# Parameters and initial condition\n\n'+table(parms)+'\nNominal equilibrium: '+', '.join(f'{v:.9f}' for v in x0)+'.\n'
    paramsPT='\n# Parâmetros e condição inicial\n\n'+table(parms)+'\nEquilíbrio nominal: '+', '.join(f'{v:.9f}' for v in x0)+'.\n'
    nrEN='\n# Numerical results\n\nCompleted execution and paired comparisons are shown below. Positive improvement favors the first method. The finite-suite CI resamples 20 paired seed clusters and is conditional on the chosen scenarios.\n\n'+table(primary)+'\n## Model and information experiments\n\n'+table(twins)+'\n## Input-dependent local rank and surviving affine-property twins\n\n'+table(lie)+'\n\n'+table(pd.DataFrame([supp])[['constant_input_max_thermal_difference','excited_uncompensated_max_thermal_difference','affine_kernel_max_thermal_difference','affine_functional_rank','quadratic_functional_rank']])+'\n## Selected absolute metrics\n\n'+table(selected[['scenario','method','IAE','RMSE_CC','Tmax','fallback']])+'\n## Independent confirmation\n\n'+table(confirm[(confirm.scenario=='FINITE_SUITE')&(confirm.baseline.isin(['B1_ukf','B2_both','B2_estimator']))][['candidate','baseline','percent_improvement','ci95_low','ci95_high']].drop_duplicates().head(10))+'\n## Adverse outcomes retained\n\n'+table(adverse)
    nrPT='\n# Resultados numéricos\n\nAs comparações abaixo provêm da execução. Melhoria positiva favorece o primeiro método. O IC da suíte reamostra 20 sementes pareadas e é condicional aos cenários escolhidos.\n\n'+table(primary)+'\n## Experimentos físicos e informacionais\n\n'+table(twins)+'\n## Posto local dependente da entrada e gêmeos remanescentes com propriedades afins\n\n'+table(lie)+'\n\n'+table(pd.DataFrame([supp])[['constant_input_max_thermal_difference','excited_uncompensated_max_thermal_difference','affine_kernel_max_thermal_difference','affine_functional_rank','quadratic_functional_rank']])+'\n## Métricas absolutas selecionadas\n\n'+table(selected[['scenario','method','IAE','RMSE_CC','Tmax','fallback']])+'\n## Confirmação independente\n\n'+table(confirm[(confirm.scenario=='FINITE_SUITE')&(confirm.baseline.isin(['B1_ukf','B2_both','B2_estimator']))][['candidate','baseline','percent_improvement','ci95_low','ci95_high']].drop_duplicates().head(10))+'\n## Resultados adversos preservados\n\n'+table(adverse)
    overall=data.groupby('method').mean(numeric_only=True)
    p2=primary[primary.candidate=='P2_regret'].iloc[0]
    p3=primary[primary.candidate=='P3_adaptive_regret'].iloc[0]
    corr=primary[primary.candidate=='B2_both'].iloc[0]
    inv=mean[mean.scenario=='inventory_plus'].set_index('method')
    gain_sample=100*(inv.loc['B1_ukf','IAE']-inv.loc['P5_initial','IAE'])/inv.loc['B1_ukf','IAE']
    maxpi=data[data.method=='B0_PI'].Tmax.max()
    ccontinuous=100*overall.loc['B1_continuous','solver_failure']
    interpretationEN=f"""
## What the executed results do and do not establish

The mean additional benefit of P2 is {p2.percent_improvement:.3f}% over B1; its paired absolute IAE difference is {p2.mean_improvement:.6f}, with 95% CI [{p2.ci95_low:.6f}, {p2.ci95_high:.6f}] kmol h/m3. P3 adds {p3.percent_improvement:.3f}% over the adapted predictor, CI [{p3.ci95_low:.6f}, {p3.ci95_high:.6f}] in absolute IAE units. Both intervals include zero. Independent confirmation also fails to establish an additional benefit. The exploratory 10% ambiguity-control target was not met.

By contrast, sharing causal parameter estimates with the predictor reduced finite-suite mean IAE from {overall.loc['B2_estimator','IAE']:.6f} to {overall.loc['B2_both','IAE']:.6f}, a {corr.percent_improvement:.2f}% reduction. This is an attribution result for the declared models and finite suite, not a new universal controller result. Estimator-only adaptation itself worsened IAE relative to B1, despite a smaller mean RMSE.

P1 and B1 have exactly equal IAE throughout the main suite, consistent with the expected-cost proposition. The denser nine-point grid gives adverse mean P2 differences in all three checked scenarios, with only three validation seeds; it does not rescue the positive claim.

The true-state reference has zero estimation RMSE but mean IAE {overall.loc['B5_true_state','IAE']:.6f}, versus B1's {overall.loc['B1_ukf','IAE']:.6f}. It still uses the nominal predictor and finite-horizon quadratic objective, so it is not a certified lower bound on attainable IAE. This provides an explicit counterexample to treating lower estimation RMSE as a sufficient guarantee of better tracking.

One initial chemical sample reduced inventory-plus mean IAE by {gain_sample:.2f}%. Four periodic samples produced the same mean IAE there, while reducing estimation RMSE slightly. Across the entire mismatched-model suite, the implemented chemical-sampling policies did not improve mean IAE. This is realized algorithm performance, not negative optimal value of free information: an optimally designed policy with additional optional information could always ignore it.

The fixed PI achieved favorable average tracking at the cost of a maximum sampled temperature of {maxpi:.3f} K, exceeding the study limit by {maxpi-TLIMIT:.3f} K. Its raw IAE gain therefore fails the safety criterion. B1_continuous reported solver failures on {ccontinuous:.3f}% of decisions and used the declared fallback. Zero trajectory aborts does not mean zero optimizer failures or zero thermal exceedances. These adverse outcomes are retained.

The data establish neither a uniform controller winner nor substantial incremental engineering gain from ambiguity handling. They support a model-specific information result, a useful predictor-correction ablation and falsification of several plausible but incorrect performance shortcuts.
"""
    interpretationPT=f"""
## Interpretação dos resultados executados

P2 apresentou ganho médio adicional de {p2.percent_improvement:.3f}% frente a B1; diferença absoluta pareada de IAE {p2.mean_improvement:.6f}, com IC95% [{p2.ci95_low:.6f}, {p2.ci95_high:.6f}] kmol h/m3. P3 acrescentou {p3.percent_improvement:.3f}% frente ao preditor adaptado, com IC95% [{p3.ci95_low:.6f}, {p3.ci95_high:.6f}] em unidades absolutas de IAE. Ambos incluem zero. A confirmação independente também não estabeleceu benefício adicional. A meta exploratória de 10% para controle por ambiguidade não foi atingida.

Compartilhar as estimativas paramétricas causais com o preditor reduziu o IAE médio de {overall.loc['B2_estimator','IAE']:.6f} para {overall.loc['B2_both','IAE']:.6f}, redução de {corr.percent_improvement:.2f}%. É atribuição dentro desta suíte e destes modelos, não demonstração de controlador universal novo. A adaptação somente do estimador piorou o IAE frente a B1, apesar de RMSE médio menor.

P1 e B1 possuem IAE exatamente igual em toda a suíte principal, consistente com a proposição de custo esperado. A grade de nove pontos produziu diferenças médias adversas para P2 nos três cenários de sensibilidade, com apenas três sementes; não resgatou a hipótese positiva.

A referência informada do estado tem RMSE zero, porém IAE médio {overall.loc['B5_true_state','IAE']:.6f}, contra {overall.loc['B1_ukf','IAE']:.6f} de B1. Ela mantém preditor nominal e objetivo quadrático de horizonte finito; portanto não é limite inferior certificado do IAE atingível. É contraexemplo explícito à suposição de que RMSE menor garante tracking melhor.

Uma amostra química inicial reduziu o IAE médio de inventory-plus em {gain_sample:.2f}%. Quatro amostras periódicas deram o mesmo IAE nesse cenário e RMSE discretamente menor. Na suíte completa com mismatch, as políticas de amostragem implementadas não melhoraram o IAE médio. Isso é desempenho realizado dos algoritmos, não valor ótimo negativo da informação gratuita: uma política otimamente projetada poderia ignorar informação opcional adicional.

O PI fixo obteve tracking médio favorável, mas alcançou temperatura amostrada máxima de {maxpi:.3f} K, excedendo o limite do estudo em {maxpi-TLIMIT:.3f} K. Seu ganho bruto de IAE falha no critério de segurança. B1_continuous registrou falha do solver em {ccontinuous:.3f}% das decisões e acionou a contingência prevista. Ausência de aborto de trajetória não equivale à ausência de falhas do otimizador ou de violações térmicas.

Os dados não estabelecem vencedor uniforme nem ganho substancial adicional de engenharia por representar ambiguidade. Sustentam um resultado informacional específico do modelo, a ablação útil da correção do preditor e a falsificação de interpretações simplistas de desempenho.
"""
    nrEN+=interpretationEN
    nrPT+=interpretationPT
    questions=[
    ['Q1','Demonstrated mathematically','M0 has a two-dimensional chemical indistinguishability class; six free states are not fully observable.'],
    ['Q2','Partially supported','Constant-Cp ambiguity survives consistent reaction enthalpy and reciprocal jacket; physically calibrated M1 remains unavailable.'],
    ['Q3','Demonstrated mathematically','The sufficient invisible subspace is orthogonal to the functional span of CpB,CpC,CpM, with deltaCA=0.'],
    ['Q4','Demonstrated mathematically','Half separation is an instantaneous two-world lower bound; the integrated bound is distinct.'],
    ['Q5','Experimentally supported','Finite-class costs show when chemical ambiguity changes actions; no global continuous optimum certificate.'],
    ['Q6','Experimentally supported','The claimed reliability is contradicted: zero-RMSE state reference and better-RMSE estimator-only adaptation can have worse IAE.'],
    ['Q7','Experimentally supported','Predictor sharing reduced mean IAE by 39.91% versus estimator-only correction, with independent confirmation.'],
    ['Q8','Inconclusive','Incremental ambiguity gains of 0.63%/0.66% have CIs including zero; the 10% target was not met.'],
    ['Q9','Experimentally supported','Adverse heat-transfer/property regimes and denser-grid checks are retained; no uniform robust advantage.'],
    ['Q10','Partially supported','Only the declared CC sampling schedules/noises/delay approximation were tested; no globally optimal sensor frequency.'],
    ['Q11','Demonstrated mathematically','Exact indistinguishable-pair bounds apply independently of estimator architecture under stated information.'],
    ['Q12','Partially supported','Proof transfers to the same dilution/kinetic/calorimetric structure; numerical gains do not transfer automatically.']]
    claims=pd.DataFrame(questions,columns=['Question','Evidence class','Conclusion'])
    tableclaims=table(claims)
    classes_pt={'Demonstrated mathematically':'Demonstrada matematicamente','Experimentally supported':'Sustentada experimentalmente','Partially supported':'Parcialmente sustentada','Inconclusive':'Inconclusiva'}
    claims_pt=claims.copy();claims_pt['Evidence class']=claims_pt['Evidence class'].map(classes_pt)
    claims_pt['Conclusion']=[
        'M0 possui classe química bidimensional indistinguível; seis estados livres não são completamente observáveis.',
        'A ambiguidade com Cp constante persiste com entalpia consistente e camisa recíproca; M1 físico calibrado permanece ausente.',
        'O núcleo suficiente é ortogonal ao espaço funcional de CpB, CpC e CpM, com diferença em CA igual a zero.',
        'Metade da separação limita o erro instantâneo no problema de dois mundos; o limite integrado é distinto.',
        'Custos na classe finita determinam quando a ambiguidade altera ações; não há certificado de ótimo contínuo global.',
        'Contraexemplos executados contradizem a confiabilidade geral: menor RMSE, inclusive zero, pode acompanhar IAE maior.',
        'O compartilhamento com o preditor reduziu IAE médio em 39,91% contra correção somente do estimador, com confirmação independente.',
        'Ganhos adicionais de 0,63%/0,66% possuem IC incluindo zero; a meta exploratória de 10% não foi atingida.',
        'Regimes adversos são preservados nas tabelas e em contrasts.csv.',
        'Somente os esquemas declarados de medição de CC foram testados; frequência globalmente ótima não foi estabelecida.',
        'Os limites para gêmeos exatos independem da arquitetura do estimador sob as hipóteses declaradas.',
        'A prova transfere para a mesma estrutura de diluição, cinética e calorimetria; ganhos numéricos não se generalizam automaticamente.']
    claims_pt.columns=['Questão','Classe de evidência','Conclusão']
    tableclaimsPT=table(claims_pt)
    discussionEN=r"""
# Ablation, falsification and interpretation

The common-information comparisons separate point versus representative decisions, estimator-only versus predictor-sharing adaptation, and a denser finite grid. Exact inventory and chemical sampling are additional-information arms. A better result there cannot be attributed solely to a more sophisticated algorithm.

The core structural result is insensitive to replacing one-way coil coupling with a reciprocal jacket while retaining constant heat capacities. Synthetic property dependence can break the particular two-species compensation, but tiny output differences may remain undetectable at realistic sensor precision. The numerical rank map is a grid of initial states, not a map of feasible steady operating points. The Fisher matrix corresponding to independent Gaussian measurement noise is the sensitivity Gram matrix; no calibrated posterior coverage guarantee follows from its singular values.

The expected-cost proposition provides a stronger null case: symmetric exact chemical twins only add a plan-independent variance term to the quadratic cost. P1 therefore has no theoretical action advantage over the point policy under those assumptions. The post-protocol audit checks this identity on nine plan/reference/horizon combinations.

Positive grid regret establishes conflict within the stated candidate class. Grid minimax is not a lower bound on all causal controllers. The state-informed reference may have a smaller loss, but unreachable references and physical cooling limits remain. The initial failed numerical effect-size expectation is retained: a thermal difference of 9.516165278e-7 K did not exceed an arbitrary 1e-6 K threshold. The implementation test was replaced by an exact capacity identity, while scientific separability is reported without imposing a favorable outcome.

# Limitations and publication readiness

Historical 0.951143, 0.850912, 0.358768 and 14.60% outcomes have identified documentary sources but were not replayed under their original protocols. The current finite-grid two-block NMPC, fixed PI and short-window MHE do not establish comparison against the strongest available baselines. Longer horizons, six-move continuous optimization, systematic tuning on development data, additional sensor variables and model-family closed-loop stress tests remain.

Beyond the explicitly derived M0 quotient minor, full-model Lie-derivative sweeps, practical lower-bound calibration, genuine chemical-analyzer dynamics, interval safety between samples, rigorous recovery margins and target-Ryzen timings remain unexecuted. MHE covariance is inherited from its UKF arrival approximation; its coverage is diagnostic only. Full NEES is not reported because full covariance histories were not saved. Decision timing excludes some sensor-scheduling calculations; total episode time is separately available. No on-spec production or economic loss is claimed because no commercial specification or prices were defined. The code is a simulator study, not an industrial trial.

The article is not ready for submission as a claim of a superior controller. Its defensible research direction is the structural classification and reproducible decision audit, subject to physical property validation, a fuller novelty review and independent technical review.

# Conclusions

The recovered model places a specific information limit on chemical reconstruction that cannot be cured by estimator architecture alone. Reciprocal jacket dynamics are insufficient to remove this ambiguity under constant heat capacities. Whether that ambiguity matters for control depends on the objective, feasibility and action class. The accompanying data show the realized outcomes of the declared comparisons, including negative cases. They support a bounded computational research contribution while leaving the full original campaign incomplete.

# Scientific claims audit

"""
    discussionPT=r"""
# Ablação, falsificação e interpretação

As comparações com a mesma informação separam decisão pontual e por representantes, correção somente do estimador e compartilhamento com o preditor, além de grade mais densa. Inventário exato e amostragem química fornecem informação adicional; seu eventual ganho não pode ser atribuído apenas à sofisticação algorítmica.

O resultado estrutural persiste ao substituir a serpentina assimétrica por camisa recíproca mantendo capacidades caloríficas constantes. A dependência sintética de propriedades pode desfazer a compensação específica entre duas espécies, mas as diferenças térmicas podem permanecer pequenas diante do ruído. O mapa numérico utiliza uma grade de estados iniciais, não pontos estacionários fisicamente viáveis. Para ruído gaussiano independente, a Fisher correspondente é o produto da sensibilidade transposta pela sensibilidade; seus valores singulares não certificam cobertura posterior.

A proposição do custo esperado fornece um caso nulo mais forte: gêmeos exatos e simétricos acrescentam apenas um termo de variância independente do plano ao custo quadrático. P1 não possui vantagem teórica na ação sobre a política pontual nessas condições. A auditoria suplementar verifica a identidade em nove combinações de horizonte e referência.

Regret positivo na grade demonstra conflito nessa classe. Seu valor minimax não limita inferiormente todo controlador causal. Um oráculo informado do estado pode reduzir perda, mas referências inalcançáveis e limites de refrigeração permanecem. Preserva-se a expectativa experimental inicialmente refutada: diferença térmica de 9.516165278e-7 K não ultrapassou o corte arbitrário 1e-6 K. A verificação de implementação foi substituída por identidade exata de capacidade térmica, sem exigir resultado favorável na separabilidade científica.

# Limitações e condição para publicação

Os números históricos 0.951143, 0.850912, 0.358768 e 14.60% possuem fontes documentais identificadas, mas seus protocolos não foram reexecutados. O NMPC de dois blocos, PI fixo e MHE curto desta campanha não representam os melhores baselines disponíveis. Permanecem horizontes maiores, otimização contínua de seis movimentos, sintonia sistemática em desenvolvimento, outras variáveis químicas medidas e stress tests fechados nas famílias físicas.

Além do menor explícito de Lie no quociente M0, não foram concluídos mapas completos de derivadas de Lie, calibração de limites estatísticos práticos, dinâmica real de analisadores, segurança entre amostras, margens rigorosas de recuperação e tempos no Ryzen. A covariância atribuída ao MHE vem da aproximação UKF de chegada; sua cobertura é apenas diagnóstica. Não se informa NEES completo porque os históricos de covariância completa não foram salvos. Tempos decisórios excluem parte da programação das amostras; tempos totais dos episódios estão registrados. Não se afirma produção dentro de especificação nem perda econômica, pois não foram definidos limites comerciais ou preços. Trata-se de simulação, sem ensaio industrial.

O artigo ainda não está pronto para submissão como demonstração de um controlador superior. O caminho defensável é a classificação estrutural e a auditoria reproduzível de decisão, após validação de propriedades físicas, revisão mais abrangente de originalidade e revisão técnica independente.

# Conclusões

O modelo recuperado impõe um limite informacional específico que não desaparece com a troca da arquitetura do estimador. Realimentação da camisa é insuficiente para removê-lo quando as capacidades caloríficas são constantes. A importância para o controle depende do objetivo, da viabilidade e da classe de ações. Os dados documentam as comparações executadas e seus casos negativos, sustentando uma contribuição computacional delimitada e mantendo explícita a incompletude da missão integral.

# Auditoria das conclusões

"""
    cap=json.loads((OUT/'08_FIGURES/captions.json').read_text())
    gallery='\n# Figures from executed data\n\n'+'\n\n'.join(f'![Figure {i}. {cap[str(i)]}](figures/Figure_{i:02d}.png)' for i in range(1,17))
    en=enabs+'\n\n'+(ROOT/'manuscripts/methods_en.md').read_text()+paramsEN+'\n'+(ROOT/'reports/theory_en.md').read_text()+nrEN+discussionEN+tableclaims+gallery+'\n# References\n\n'
    pt=ptabs+'\n\n'+(ROOT/'manuscripts/methods_pt.md').read_text()+paramsPT+'\n'+(ROOT/'reports/theory_pt.md').read_text()+nrPT+discussionPT+tableclaimsPT+gallery.replace('# Figures from executed data','# Figuras dos dados executados')+'\n# Referências\n\n'
    builds=[]
    builds.append(produce_document('Article_EN',en,'Information and Decision Limits in Inferential Predictive Control of a Nonlinear Propylene Glycol Reactor','en-US','03'))
    builds.append(produce_document('Artigo_PTBR',pt,'Limites de Informação e Decisão no Controle Preditivo Inferencial de um Reator Não Linear de Propilenoglicol','pt-BR','05'))
    # Canonical individual filenames and requested aliases.
    shutil.copy2(OUT/'03_Article_EN.docx',OUT/'04_ARTICLE_EN.docx')
    shutil.copy2(OUT/'05_Artigo_PTBR.docx',OUT/'06_ARTICLE_PTBR.docx')
    report=pt+'\n# Auditoria da recuperação\n\n'+(ROOT/'reports/recovery_audit.md').read_text()+'\n# Revisão bibliográfica crítica\n\n'+(ROOT/'reports/literature_review.md').read_text()+'\n# Configuração congelada\n\n~~~json\n'+(ROOT/'configs/protocol.json').read_text()+'\n~~~\n# Registro de testes\n\n~~~\n'+tests+'\n~~~\n# Verificação independente de métricas\n\n~~~json\n'+json.dumps(audit,indent=2)+'\n~~~\n# Todos os cenários: médias por método\n\n'+table(mean)
    builds.append(produce_document('Scientific_Research_Report',report,'Relatório técnico estendido: PG Information and Control Frontier — núcleo parcial','pt-BR','02'))
    shutil.copy2(OUT/'02_Scientific_Research_Report.docx',OUT/'Relatorio_Tecnico_Completo.docx')
    executive=f"""# Resultado e escopo

Foram executadas {execution['episodes']} trajetórias principais, {execution['confirmation']} confirmações e {execution['grid_sensitivity']} verificações de grade. Esta entrega documenta o núcleo computacional e permanece PARCIAL frente à missão integral. A auditoria recalculou IAE e RMSE em {audit['trajectories_checked']} arquivos de trajetória. O histórico completo ICAC e o modelo físico calibrado M1 não foram recuperados.

A contribuição matemática mais útil é separar as dependências físicas necessárias para a ambiguidade. Com cinética de primeira ordem em A e capacidades caloríficas constantes, duas direções químicas podem permanecer invisíveis às temperaturas. Tornar a camisa recíproca não remove esse núcleo. Propriedades independentes dependentes de temperatura podem reduzir esse núcleo, sem necessariamente fornecer sinal mensurável no tempo útil ao controle.

\\newpage

# Resultados de controle

Melhoria positiva favorece o candidato. As diferenças são pareadas por semente e condicionadas à suíte finita, com modelos e limites compartilhados. Não equivalem a uma conclusão industrial.

{table(primary)}

Os ganhos adicionais de P2 e P3 foram 0,63% e 0,66%, com IC incluindo zero, sem confirmação de benefício. O ganho de 39,91% vem de compartilhar a correção paramétrica com o preditor. O PI teve IAE favorável, mas excedeu amplamente a temperatura limite; informação química ajudou no inventário incerto, sem ganho uniforme sob mismatch.

O confronto contínuo utiliza a mesma parametrização curta de dois blocos. Ainda falta a comparação com o NMPC histórico de horizonte 57 e seis movimentos, além da sintonia competitiva do PI/MHE. A meta exploratória de 10% não deve ser lida como promessa ou como critério suficiente de publicação.

\\newpage

# Contraexemplos e perguntas para discussão

{table(adverse.head(6))}

Perguntas centrais para colaboradores: quais correlações experimentais Cp(T) devem substituir as hipóteses? Qual é a informação inicial realmente disponível sobre os inventários? O ganho de cada contraste persiste quando horizonte, solver e orçamento são equiparados ao baseline histórico? Qual sensor adicional pode ser instalado e qual seu atraso real?

\\newpage

# Decisão científica e próximo gate

A limitação do modelo histórico está demonstrada sob hipóteses explícitas. Uma limitação universal do reator físico não está demonstrada. O valor de informação depende do objetivo e da autoridade de atuação. O artigo não deve reivindicar nova teoria geral, melhor controlador universal ou validação industrial.

O pacote fornece código, dados, figuras, fontes LaTeX, PDF compilado, DOCX, revisão dirigida e registro das lacunas. Para promover a versão a FINAL: recuperar e reexecutar ICAC/C08; obter propriedades físicas e dinâmica de analisadores; concluir baselines contínuos fortes; revisar causalidade/identificabilidade com especialista; confirmar regimes novos; e só então decidir o periódico e a submissão.
"""
    builds.append(produce_document('EXECUTIVE_SUMMARY',executive,'Síntese executiva para discussão científica — PG Frontier','pt-BR','01'))
    text(OUT/'16_SCIENTIFIC_CLAIMS_AUDIT.md',tableclaims+'\n\n'+discussionEN)
    shutil.copy2(ROOT/'reports/literature_review.md',OUT/'15_BIBLIOGRAPHY_REVIEW/literature_review.md')
    shutil.copy2(ROOT/'reports/recovery_audit.md',OUT/'12_REPRODUCIBILITY/recovery_audit.md')
    shutil.copy2(ROOT/'reports/document_build_failure_1.md',OUT/'12_REPRODUCIBILITY/document_build_failure_1.md')
    shutil.copy2(ROOT/'reproducibility/google_docs.json',OUT/'12_REPRODUCIBILITY/google_docs.json')
    provenance=dict(historical_model_commit='d2610a0723cbbaf00d3f4559242ba0efafb67771',frozen_execution_commit='a57be15bdddbe0c2447a9eb21bce7f6b5b63d37c',data_workflow_run=39499177732,build_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),pandoc=subprocess.check_output(['pandoc','--version'],text=True).splitlines()[0])
    text(OUT/'12_REPRODUCIBILITY/git_provenance.json',json.dumps(provenance,indent=2))
    shutil.copy2(ROOT/'reports/initial_test_failure.md',OUT/'14_NEGATIVE_RESULTS/initial_test_failure.md')
    adverse.to_csv(OUT/'14_NEGATIVE_RESULTS/adverse_contrasts.csv',index=False)
    for p in R.glob('*'):
        if p.is_file():
            target='statistical_tests' if 'contrast' in p.name or 'audit' in p.name else 'tables'
            shutil.copy2(p,OUT/'09_RESULTS'/target/p.name)
    shutil.copytree(R/'trajectories',OUT/'09_RESULTS/raw/trajectories',dirs_exist_ok=True)
    code=OUT/'10_CODE/research/pg_information_control_frontier'
    for name in ['src','tests','configs','reports','manuscripts','reproducibility']:
        shutil.copytree(ROOT/name,code/name,ignore=shutil.ignore_patterns('__pycache__'),dirs_exist_ok=True)
    for name in ['README.md','requirements.txt','pyproject.toml']:shutil.copy2(ROOT/name,code/name)
    vendor=OUT/'10_CODE/research/darwin-observer/vendor';vendor.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT.parent/'darwin-observer/vendor/legacy_model.py',vendor/'legacy_model.py')
    shutil.copy2(ROOT.parent/'darwin-observer/vendor/thesis_original/modeloCT.m',vendor/'modeloCT.m')
    shutil.copytree(ROOT/'tests',OUT/'11_TESTS',ignore=shutil.ignore_patterns('__pycache__'),dirs_exist_ok=True)
    shutil.copy2(R/'tests.log',OUT/'11_TESTS/tests.log')
    readme=f"""# YCS PG Information & Control Frontier v1.0 — PARTIAL
Author: Walter Yanko de Aragão Brandão. Date: 20 October 2026.

Executed core: {execution['episodes']} main + {execution['confirmation']} confirmation trajectories.
Tests: latest 18 passed; initial failed scientific cutoff retained. Independent metrics: {audit['trajectories_checked']} trajectories.
PDFs were compiled with pdflatex, DOCX generated with Pandoc. This is a partial scientific manuscript, not a submission or a claim of complete v1.0.

Start with 01_EXECUTIVE_SUMMARY.pdf. Articles: 03_Article_EN.pdf and 05_Artigo_PTBR.pdf.
All 16 figures are generated from executed data. 09_RESULTS contains actual trajectories and tables.
10_CODE contains a scoped reproducible project; see its README.
13_VISUAL_LAB is a lightweight offline data viewer, not a new simulation engine.

Critical gaps: original ICAC/C08 replay, calibrated M1, strong 57/6 continuous baseline,
fully tuned MHE, full NEES, target Ryzen timing, full novelty review and human expert review. A supplementary 60-digit local quotient audit is included.
No industrial safety, global optimality or universal novelty is claimed.
"""
    text(OUT/'00_README_START_HERE.md',readme)
    text(OUT/'12_REPRODUCIBILITY/document_builds.json',json.dumps(builds,indent=2))
    # Clean intermediary TeX outputs; keep source, figures and compilation logs.
    for ext in ['.aux','.out','.log','.toc']:
        for p in (OUT/'07_LATEX_SOURCE').glob('*'+ext):p.unlink()
    # Embed true summary data in an offline viewer without remote dependencies.
    summaries=mean.to_json(orient='records')
    html='''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>PG Frontier — resultados executados</title><style>body{font:16px system-ui;margin:2rem;max-width:1100px;background:#f4f7f8;color:#173749}select{font:inherit;padding:.5rem}table{border-collapse:collapse;width:100%;font-size:13px}td,th{padding:.6rem;border-bottom:1px solid #ccd7dc;text-align:right}td:first-child{text-align:left}img{max-width:100%}header{padding:1rem;background:white;border-radius:12px}a{color:#185f8a}</style>
<header><h1>PG Information & Control Frontier</h1><p>Núcleo computacional parcial. Dados reais de simulação; sem garantias industriais.</p></header>
<h2>Arena dos controladores</h2><label>Cenário <select id="s"></select></label><div id="table"></div>
<h2>Explorar evidências</h2><select id="fig"></select><p id="caption"></p><img id="plot" alt="Figura científica executada">
<script>const data=DATA;const captions=CAP;
const scenarios=[...new Set(data.map(x=>x.scenario))];
const s=document.getElementById('s');for(const v of scenarios)s.add(new Option(v,v));
function draw(){const rows=data.filter(x=>x.scenario===s.value).sort((a,b)=>a.IAE-b.IAE);
document.getElementById('table').innerHTML='<table><thead><tr><th>Método</th><th>IAE</th><th>RMSE</th><th>T máx.</th><th>Contingência</th><th>ms decisão</th><th>Amostras</th></tr></thead><tbody>'+rows.map(x=>'<tr><td>'+x.method+'</td>'+['IAE','RMSE_CC','Tmax','fallback','decision_ms','samples'].map(k=>'<td>'+Number(x[k]).toPrecision(5)+'</td>').join('')+'</tr>').join('')+'</tbody></table>';}
s.onchange=draw;draw();const f=document.getElementById('fig');for(const k in captions)f.add(new Option(k+' — '+captions[k],k));
function pic(){document.getElementById('plot').src='../08_FIGURES/Figure_'+f.value.padStart(2,'0')+'.png';document.getElementById('caption').textContent=captions[f.value];}f.onchange=pic;pic();</script></html>'''
    text(OUT/'13_VISUAL_LAB/index.html',html.replace('DATA',summaries).replace('CAP;',json.dumps(cap)+';'))
    manifest=[]
    for p in sorted(OUT.rglob('*')):
        if not p.is_file():continue
        manifest.append(dict(path=str(p.relative_to(OUT)),type=p.suffix,status='created',
            size=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
            origin='executed frozen protocol or explicitly cited documentary/analytical material',
            reproduce='python src/reporting.py; simulations: python src/experiments.py',
            known_errors='See 00_README_START_HERE.md and scientific claims audit'))
    for meta in json.loads((ROOT/'reproducibility/google_docs.json').read_text()).values():
        manifest.append(dict(path=meta['url'],type='GoogleDoc',status=meta['status'],size=None,sha256=None,origin='Native document with verified tables and figures from executed data',reproduce='Recreate from Article_EN.md or Artigo_PTBR.md using native Docs operations',known_errors=meta['equations']))
    text(OUT/'17_DELIVERY_MANIFEST.json',json.dumps(dict(status='PARTIAL_CORE_EXECUTED',execution=execution,
        metrics_audit=audit,documents=builds,artifacts=manifest),indent=2))
    def archive(path,paths):
        with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for p in paths:
                if p.is_file():z.write(p,OUT.name+'/'+str(p.relative_to(OUT)))
        return dict(name=path.name,bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    zippath=OUT.parent/(OUT.name+'.zip')
    delivery=[archive(zippath,OUT.rglob('*'))]
    if zippath.stat().st_size>90*1024**2:
        zippath.unlink()
        datafolders={'09_RESULTS','10_CODE','11_TESTS','12_REPRODUCIBILITY'}
        datafiles=[p for p in OUT.rglob('*') if p.is_file() and p.relative_to(OUT).parts[0] in datafolders]
        docfiles=[p for p in OUT.rglob('*') if p.is_file() and p.relative_to(OUT).parts[0] not in datafolders]
        delivery=[archive(OUT.parent/(OUT.name+'_CODE_DATA.zip'),datafiles),
                  archive(OUT.parent/(OUT.name+'_MANUSCRIPTS.zip'),docfiles)]
    if any(a['bytes']>99*1024**2 for a in delivery):raise RuntimeError('Archive requires further splitting before GitHub delivery')
    text(ROOT/'deliverables/delivery_status.json',json.dumps(dict(folder=OUT.name,archives=delivery,
        documents=builds,manifest_entries=len(manifest)),indent=2))
    print(json.dumps(builds),flush=True)
if __name__=='__main__':main()
