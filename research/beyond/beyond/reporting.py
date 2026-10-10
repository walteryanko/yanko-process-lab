"""Deterministic summaries and publication figures from saved numerical outputs."""
import json,platform,sys,importlib.metadata as md
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from beyond.models import get_model,ROOT
from beyond.common import RESULTS,FIGURES,dump,paired_ci

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,
    'axes.labelsize':9,'axes.titlesize':11,'figure.dpi':120,'savefig.dpi':220,'axes.grid':True,'grid.alpha':.18})
COLORS=['#264e70','#bb6a38','#26756a','#8b5269']
def save(fig,name):
    fig.savefig(FIGURES/(name+'.png'),bbox_inches='tight');fig.savefig(FIGURES/(name+'.pdf'),bbox_inches='tight');plt.close(fig)

def consolidate():
    a=pd.read_csv(RESULTS/'closedloop_PG.csv');b=pd.read_csv(RESULTS/'closedloop_EB.csv')
    assert len(a)==1088 and len(b)==1216,(len(a),len(b))
    c=pd.concat([a,b],ignore_index=True);c.to_csv(RESULTS/'closedloop.csv',index=False)
    v=pd.concat([pd.read_csv(RESULTS/f'region_validation_{k}.csv') for k in ['PG','EB']]);v.to_csv(RESULTS/'region_validation.csv',index=False)
    dump(RESULTS/'policy_selection.json',{k:json.loads((RESULTS/f'policy_selection_{k}.json').read_text()) for k in ['PG','EB']})
    rows=[]
    for kind,region in [('PG','fixed_feed_340K'),('EB','O2_robust')]:
        subset=c[(c.kind==kind)&(~c.transition)]
        for mode in ['direct','inferential']:
            d=subset[subset['mode']==mode]
            for metric in ['normalized_IAE','production_mean','feed_mean','heat_mean','cooling_square_mean','actuation_tv','violation_steps','estimation_RMSE','byproduct_mean','selectivity']:
                # Resample seed clusters: five scenario families sharing one seed
                # are NOT treated as five independent statistical observations.
                p=d.groupby(['seed','region'])[metric].mean().unstack();r=paired_ci(p[region],p.nominal)
                rows.append(dict(kind=kind,contrast=region,mode=mode,metric=metric,**r))
    pd.DataFrame(rows).to_csv(RESULTS/'operating_contrasts.csv',index=False)
    ident=pd.read_csv(RESULTS/'identification.csv');assert len(ident)==192
    # Early completed checkpoints predate addition of these diagnostic columns.
    if 'future_steady_solve_success' in ident:ident['future_steady_solve_success']=ident.future_steady_solve_success.fillna(ident.future_quality_error.notna())
    if 'decision_grid_has_feasible' in ident:
        for i,r in ident[ident.decision_grid_has_feasible.isna()].iterrows():
            z=np.load(RESULTS/f'identification_{r.kind}_{r.wave}_{int(r.seed)}.npz');ident.loc[i,'decision_grid_has_feasible']=bool(np.any(z['true_decision_cost'][:,3]))
    ident.to_csv(RESULTS/'identification.csv',index=False)
    rows=[]
    for (kind,case),d in ident.groupby(['kind','case']):
        for wave in ['step','prbs','sin']:
            for metric in ['decision_regret','robust_decision_regret','future_quality_error']:
                p=d.pivot(index='seed',columns='wave',values=metric).dropna()
                if metric=='future_quality_error':p=p**2
                rows.append(dict(kind=kind,case=case,wave=wave,metric='future_quality_MSE' if metric=='future_quality_error' else metric,**paired_ci(p[wave],p.constant)))
    pd.DataFrame(rows).to_csv(RESULTS/'identification_contrasts.csv',index=False)
    for filename,col,base,extra in [('sampling_control','strategy','none',['kind','delay_tau']),('adaptive','strategy','nominal',['kind'])]:
        data=pd.read_csv(RESULTS/(filename+'.csv'));rows=[]
        for key,d in data.groupby(extra):
            key=(key,) if not isinstance(key,tuple) else key
            for metric in ['normalized_IAE','production_mean','violation_steps']:
                p=d.pivot(index='seed',columns=col,values=metric)
                for name in p.columns.drop(base):rows.append(dict(zip(extra,key),contrast=name,metric=metric,**paired_ci(p[name],p[base])))
        pd.DataFrame(rows).to_csv(RESULTS/(filename+'_contrasts.csv'),index=False)
    c[~c.transition].groupby(['kind','mode','region']).agg(IAE=('normalized_IAE','mean'),
        production=('production_mean','mean'),thermal_failure_rate=('violation_steps',lambda a:np.mean(a>0)),
        worst_T=('Tmax','max'),mean_heat=('heat_mean','mean'),mean_feed=('feed_mean','mean'),
        chemical_RMSE=('estimation_RMSE','mean')).to_csv(RESULTS/'control_summary.csv')
    dump(RESULTS/'environment.json',dict(python=sys.version,platform=platform.platform(),
        dependencies={k:md.version(k) for k in ['numpy','scipy','pandas','matplotlib','casadi']},
        timing_warning='Wall times measured on a shared host with concurrent offline campaigns; no real-time or worst-case deadline certification'))

def landscapes():
    df=pd.read_csv(RESULTS/'landscape.csv');sel=json.loads((RESULTS/'selected_regions.json').read_text())
    for kind,a in df.groupby('kind'):
        fig,axes=plt.subplots(2,2,figsize=(7.2,5.5),constrained_layout=True)
        items=[('production','Produção líquida (kmol/h)'),('sensitivity_relative','Sensibilidade / qualidade nominal'),
               ('posterior_quality_relative','Desvio posterior / qualidade nominal'),('information_fraction','Redução relativa pela informação')]
        for ax,(metric,label) in zip(axes.flat,items):
            im=ax.scatter(a.feed_ratio,a.temperature,c=a[metric],cmap='viridis',s=33,marker='s',linewidths=0,
                norm=LogNorm() if kind=='PG' and metric=='sensitivity_relative' else None)
            ax.set(xlabel='Alimentação / nominal',ylabel='Temperatura (K)' if kind=='PG' else 'Temperatura (°C)',title=label)
            fig.colorbar(im,ax=ax,shrink=.9)
            nominal=a[a['index']==-1].iloc[0];ax.plot(nominal.feed_ratio,nominal.temperature,'r*',ms=11)
        fig.suptitle(kind+' | regiões estacionárias do modelo declarado',fontsize=12)
        save(fig,'landscape_'+kind)
    fig,axs=plt.subplots(1,2,figsize=(7.3,3.1),constrained_layout=True)
    for ax,(kind,a) in zip(axs,df.groupby('kind')):
        ax.scatter(a.sensitivity_relative,a.economic_proxy,c='0.8',s=13,label='Todos os pontos')
        p=a[a.pareto];ax.scatter(p.sensitivity_relative,p.economic_proxy,c=COLORS[0],s=20,label='Pareto de três critérios')
        ax.set(xlabel='Sensibilidade relativa',ylabel='Benefício econômico substituto',title=kind);ax.legend(fontsize=7)
        if kind=='PG':ax.set_xscale('log')
    save(fig,'pareto')

def spectra_figures():
    df=pd.read_csv(RESULTS/'spectra.csv');fig,axs=plt.subplots(1,2,figsize=(7.2,3),constrained_layout=True)
    for ax,kind in zip(axs,['PG','EB']):
        a=df[df.kind==kind];baseline=a[a.wave=='constant'].iloc[0].common_target_posterior_sd
        for mode,color in zip(['feed','cool'],COLORS):
            b=a[(a.wave=='sin')&(a['mode']==mode)].sort_values('period_tau')
            ax.semilogx(b.period_tau,b.common_target_posterior_sd/baseline,'o-',color=color,label='Alimentação' if mode=='feed' else 'Refrigeração')
        ax.axhline(1,color='0.3',ls='--',lw=1);ax.set(title=kind,xlabel='Período / tempo de residência',ylabel='Desvio posterior / sem excitação');ax.legend(fontsize=7)
    save(fig,'spectra_information')
    rows=[];fig,axs=plt.subplots(2,2,figsize=(7.2,5.2),constrained_layout=True)
    for j,kind in enumerate(['PG','EB']):
        m=get_model(kind)
        for mode,color in zip(['feed','cool'],COLORS):
            values=[]
            for _,r in df[(df.kind==kind)&(df.wave=='sin')&(df['mode']==mode)].iterrows():
                raw=np.load(RESULTS/f'spectrum_{kind}_{int(r["case"])}.npz');U=raw['U'];X=raw['X'];ii=np.arange(len(U))>=len(U)//2
                omega=2*np.pi/r.period;t=np.arange(len(U))*m.dt
                design=lambda tt:np.c_[np.ones(len(tt)),np.sin(omega*tt),np.cos(omega*tt),np.sin(2*omega*tt),np.cos(2*omega*tt)]
                by=np.linalg.lstsq(design(t[ii]+m.dt),X[1:,4][ii],rcond=None)[0];idx=0 if mode=='feed' else m.cidx
                bu=np.linalg.lstsq(design(t[ii]),U[ii,idx]/m.u0[idx],rcond=None)[0]
                gain=np.hypot(by[1],by[2])/np.hypot(bu[1],bu[2]);phase=np.angle(complex(by[1],by[2])/complex(bu[1],bu[2]))
                rows.append(dict(kind=kind,mode=mode,period_tau=r.period_tau,samples_per_period=r.period/m.dt,empirical_gain_K_per_relative_input=gain,empirical_phase_rad=phase,
                    second_to_first_harmonic=np.hypot(by[3],by[4])/np.hypot(by[1],by[2]),scope='sampled empirical harmonics, actual timestamps; no ZOH deconvolution'))
                if r.period/m.dt>=8:values.append((r.period_tau,gain,phase))
            v=np.array(sorted(values));axs[0,j].loglog(v[:,0],v[:,1],'o-',color=color,label=mode);axs[1,j].semilogx(v[:,0],v[:,2]*180/np.pi,'o-',color=color)
        axs[0,j].set(title=kind,ylabel='Ganho térmico (K / entrada relativa)');axs[0,j].legend(fontsize=7)
        axs[1,j].set(xlabel='Período / tempo de residência',ylabel='Fase empírica (graus)')
    pd.DataFrame(rows).to_csv(RESULTS/'frequency_response.csv',index=False);save(fig,'frequency_response')

def periodic_figure():
    df=pd.read_csv(RESULTS/'periodic.csv');fig,axs=plt.subplots(1,2,figsize=(7.2,3.4),constrained_layout=True)
    for ax,kind in zip(axs,['PG','EB']):
        a=df[(df.kind==kind)&df.valid]
        im=ax.scatter(a.gain_vs_nominal_percent,a.gain_vs_stationary_percent,c=a.period_tau,cmap='viridis',s=25)
        ax.axhline(0,color='0.4',lw=1);ax.axvline(0,color='0.4',lw=1);ax.set(title=kind+' | somente trajetórias admissíveis',xlabel='Ganho sobre nominal (%)',ylabel='Ganho sobre estacionário comparável (%)');fig.colorbar(im,ax=ax,label='Período / residência',shrink=.8)
    save(fig,'periodic_comparison')

def controls_figure():
    df=pd.read_csv(RESULTS/'closedloop.csv');df=df[(~df.transition)&(df['mode']=='direct')]
    fig,axs=plt.subplots(1,2,figsize=(7.2,3.5),constrained_layout=True)
    for ax,kind in zip(axs,['PG','EB']):
        a=df[df.kind==kind].groupby('region').agg(error=('normalized_IAE','mean'),production=('production_mean','mean'),failure=('violation_steps',lambda x:np.mean(x>0)))
        for label in ['O2_robust','O3_information','O4_joint'] if kind=='EB' else ['O3_information']:
            a=a.drop(label)
        im=ax.scatter(a.production,a.error,c=a.failure,cmap='YlOrRd',vmin=0,vmax=.35,s=80,edgecolors='black',linewidth=.5)
        for name,r in a.iterrows():
            text={'nominal':'Nominal','fixed_feed_337K':'337 K','fixed_feed_340K':'340 K','O1_economic':'O1','O2_robust':'O2/O3','O4_joint':'O4','feed1.0_T158':'158°C','feed1.0_T162':'162°C','feed0.9_T160':'0,9 feed'}.get(name,name)
            offset=(3,5)
            if kind=='EB':
                text='O1 a O4' if name=='O1_economic' else text
                offset={'nominal':(-22,23),'feed1.0_T158':(-38,-16),'feed1.0_T162':(3,10)}.get(name,(3,5))
            ax.annotate(text,(r.production,r.error),xytext=offset,textcoords='offset points',fontsize=7,
                arrowprops=dict(arrowstyle='-',lw=.45,color='.4') if kind=='EB' and name.startswith(('nominal','feed1')) else None)
        ax.set(title=kind+' | mesmo PI térmico',xlabel='Produção líquida média (kmol/h)',ylabel='IAE / (qualidade nominal × horizonte)');ax.margins(.18)
    fig.colorbar(im,ax=axs,shrink=.8,label='Fração de trajetórias com violação');save(fig,'control_tradeoffs')

def decision_figure():
    df=pd.read_csv(RESULTS/'identification.csv');df=df[df['case']=='correct_family'];fig,axs=plt.subplots(2,2,figsize=(7.2,5.1),constrained_layout=True)
    order=['constant','step','prbs','sin'];labels=['Constante','Degrau','PRBS','Senoide']
    for j,kind in enumerate(['PG','EB']):
        a=df[df.kind==kind];g=a.groupby('wave');rmse=g.future_quality_error.apply(lambda x:np.sqrt(np.mean(x*x))).reindex(order)
        axs[0,j].bar(labels,rmse,color=COLORS);axs[0,j].set(title=kind,ylabel='RMSE da qualidade futura')
        vals=g.decision_regret.mean().reindex(order);axs[1,j].bar(labels,vals,color=COLORS);axs[1,j].set(ylabel='Arrependimento médio da decisão')
    fig.suptitle('Validação não linear | 16 sementes pareadas | 17 ações futuras',fontsize=11)
    save(fig,'decision_value')

def complements_figure():
    fig,axs=plt.subplots(1,2,figsize=(7.2,3.1),constrained_layout=True);m=get_model('PG')
    for name,color in zip(['constant','frontloaded','backloaded'],COLORS):
        r=np.load(RESULTS/f'forgetting_{name}.npz');t=np.arange(len(r['A']))*m.dt;axs[0].semilogy(t,abs(r['B'][:,2]-r['A'][:,2]),label=name,color=color)
    axs[0].axhline(.04*m.q0,ls='--',color='0.3',label='Largura da especificação');axs[0].set(xlabel='Tempo (h)',ylabel='Separação de composição (kmol/m³)',title='PG | esquecimento sem identificação');axs[0].legend(fontsize=6)
    a=np.load(RESULTS/'twins_EB_1.0.npz');t=np.arange(len(a['A']))*.02
    axs[1].plot(t,(a['B'][:,4]-a['A'][:,4])/.1,label='ΔT / ruído térmico',color=COLORS[0]);axs[1].plot(t,get_model('EB').quality(a['B'])-get_model('EB').quality(a['A']),label='Δ fração molar EB',color=COLORS[1]);axs[1].set(xlabel='Tempo (h)',title='EB | gêmeos aproximados');axs[1].legend(fontsize=7)
    save(fig,'chemical_twins')

def final_figures():
    d=pd.read_csv(RESULTS/'same_quality_contrasts.csv');fig,axs=plt.subplots(1,2,figsize=(7.2,3.1),constrained_layout=True)
    for ax,metric,label in zip(axs,['normalized_IAE','production_mean'],['Diferença de IAE normalizado','Diferença de produção (kmol/h)']):
        a=d[d.metric==metric].sort_values(['kind','region'])
        for i,(_,r) in enumerate(a.iterrows()):
            ax.errorbar(r.difference,i,xerr=[[r.difference-r.low],[r.high-r.difference]],fmt='o',capsize=3,color=COLORS[0] if r.kind=='PG' else COLORS[1])
        ax.axvline(0,color='.4',ls='--',lw=1);ax.set(yticks=range(len(a)),yticklabels=[r.kind+' '+r.region.split('_')[-1] for _,r in a.iterrows()],xlabel=label)
    fig.suptitle('Mesma qualidade | mesmo PI | IC95% pareado por semente',fontsize=11);save(fig,'same_quality')
    data=json.loads((RESULTS/'observability_spectra.json').read_text());fig,ax=plt.subplots(figsize=(6.8,3),constrained_layout=True)
    for row,color in zip([r for r in data if r['kind']=='EB' and r['type']=='finite_record'],COLORS):
        ax.semilogy(range(1,6),row['singular_values'],'o-',color=color,label='Histórico' if row['variant']=='historical' else 'Ciclo de Hess fechado')
    ax.set(xticks=range(1,6),xlabel='Índice do valor singular',ylabel='Valor singular do registro normalizado',title='EB | entalpia inconsistente acrescenta uma direção local espúria');ax.legend(fontsize=8);save(fig,'hess_observability')

def run():
    consolidate();landscapes();spectra_figures();periodic_figure();controls_figure();decision_figure();complements_figure();final_figures()
if __name__=='__main__':run()
