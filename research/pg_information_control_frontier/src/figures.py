from pathlib import Path
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'results'
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':120,'savefig.dpi':300})
F=ROOT/'deliverables'/'YCS_PG_Information_Control_Frontier_v1.0_PARTIAL'/'08_FIGURES'
F.mkdir(parents=True,exist_ok=True)
CAPTIONS={}
def finish(fig,i,title):
    fig.suptitle(title,fontsize=12)
    fig.tight_layout()
    fig.savefig(F/f'Figure_{i:02d}.png',bbox_inches='tight');fig.savefig(F/f'Figure_{i:02d}.pdf',bbox_inches='tight')
    plt.close(fig);CAPTIONS[i]=title
def trace(s,m,seed=4100):return np.load(R/'trajectories'/f'{s}__{m}__{seed}.npz')
def main():
    d=pd.read_csv(R/'episodes.csv');c=pd.read_csv(R/'contrasts.csv')
    fig,ax=plt.subplots(figsize=(8,4));ax.axis('off')
    boxes=[(.05,.55,.25,.25,'Chemical reactor\nCA, CB, CC, CM, T, Tt'),
           (.39,.55,.23,.25,'Sensors\nT, Tt + noise'),
           (.72,.55,.24,.25,'State belief\nUKF / MHE / inventories'),
           (.39,.08,.27,.25,'Decision\nNominal / expected / regret')]
    for x,y,w,h,t in boxes:
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.015',fc='#e8f1f5',ec='#35637c'))
        ax.text(x+w/2,y+h/2,t,ha='center',va='center')
    for a,b in [((.30,.67),(.39,.67)),((.62,.67),(.72,.67)),((.84,.55),(.64,.32)),((.39,.20),(.17,.55))]:
        ax.annotate('',xy=b,xytext=a,arrowprops={'arrowstyle':'->','color':'#35637c'})
    ax.text(.2,.24,'coolant flow',ha='center');ax.text(.7,.37,'chemical samples: separate information arm',fontsize=8,ha='center')
    finish(fig,1,'Physical process and available information')
    fig,ax=plt.subplots(3,1,figsize=(7,7),sharex=True)
    z=np.load(R/'trajectories/twins_0.npz')
    for lab,color in [('a','#247ba0'),('b','#e07a5f')]:
        ax[0].plot(z['t'],z[lab][:,2],label=lab,color=color)
        ax[1].plot(z['t'],z[lab][:,4],label='T '+lab,color=color)
        ax[2].plot(z['t'],z[lab][:,5],label='Tt '+lab,color=color)
    ax[0].set_ylabel('CC (kmol/m3)');ax[1].set_ylabel('T (K)');ax[2].set_ylabel('Tt (K)');ax[2].set_xlabel('Time (h)');ax[0].legend()
    finish(fig,2,'Distinct chemical inventories, identical historical thermal outputs')
    o=pd.read_csv(R/'observability.csv')
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for ax,exc in zip(axes,[False,True]):
        z=o[(o.epsilon==.0001)&(o.excited==exc)].pivot(index='variant',columns='T_initial',values='rank_1e6')
        im=ax.imshow(z,vmin=0,vmax=6,cmap='viridis',aspect='auto')
        ax.set_xticks(range(len(z.columns)),[f'{a:.1f}' for a in z.columns]);ax.set_yticks(range(len(z.index)),[a.split('_')[0] for a in z.index])
        ax.set_xlabel('Initial reactor temperature (K)')
        ax.set_title('Excited input' if exc else 'Constant nominal input')
        fig.colorbar(im,ax=ax,label='Numerical rank, relative tol 1e-6')
    finish(fig,3,'Finite-horizon sensitivity map (initial-state grid, not equilibrium map)')
    ss=pd.read_csv(R/'singular_values.csv');fig,ax=plt.subplots(figsize=(7,4))
    for v,g in ss[(abs(ss.T_initial-332.33361802)<1e-6)&(ss.excited==True)&(ss.epsilon==.0001)].groupby('variant'):
        ax.semilogy(range(1,7),np.maximum(g[[f's{i}' for i in range(1,7)]].values[0],1e-14),'-o',label=v.split('_')[0])
    ax.set_xlabel('Singular-value index');ax.set_ylabel('Noise-whitened, state-scaled sensitivity');ax.legend()
    finish(fig,4,'Singular spectra; a numerical floor does not prove observability')
    fig,ax=plt.subplots(figsize=(7,4))
    for kind in ['ukf','adaptive','reduced','mhe']:
        z=np.load(R/'trajectories'/f'estimation_{kind}.npz')
        worst=np.maximum(abs(z['estimate'][:,2]-z['a'][:,2]),abs(z['estimate'][:,2]-z['b'][:,2]))
        ax.plot(z['t'],worst,label=kind)
    ax.plot(z['t'],z['lower'],'k--',label='half-separation lower bound')
    ax.set_xlabel('Time (h)');ax.set_ylabel('Worst of two absolute errors (kmol/m3)');ax.legend()
    finish(fig,5,'One shared measurement stream: estimation error and two-world bound')
    fig,ax=plt.subplots(figsize=(7,4))
    g=d.groupby(['scenario','method'])[['RMSE_CC','IAE']].mean().reset_index()
    for m in ['B1_ukf','B2_estimator','B2_both','P2_regret','P3_adaptive_regret']:
        s=g[g.method==m];ax.scatter(s.RMSE_CC,s.IAE,label=m,alpha=.7)
    ax.set_xlabel('CC estimation RMSE (kmol/m3)');ax.set_ylabel('IAE (kmol h/m3)');ax.legend(fontsize=8)
    finish(fig,6,'Estimation error and tracking loss across fixed scenarios')
    dec=pd.read_csv(R/'decisions.csv');fig,ax=plt.subplots(figsize=(7,4))
    s=dec[(dec.horizon==14)&(dec.reference==2.1)]
    for col in ['action_low','action_high','robust_action']:ax.plot(s.width,s[col],'-o',label=col)
    ax.set_xlabel('Prior half-width (kmol/m3)');ax.set_ylabel('First coolant action / nominal');ax.legend()
    finish(fig,7,'World-conditioned and minimax-regret actions (finite action class)')
    fig,ax=plt.subplots(figsize=(7,4))
    for h,g in dec[dec.reference==2.1].groupby('horizon'):ax.plot(g.width,g.regret,'-o',label=f'H={h}')
    ax.set_xlabel('Prior half-width (kmol/m3)');ax.set_ylabel('Minimum worst regret (dimensionless)');ax.legend()
    finish(fig,8,'Decision ambiguity versus prior width and prediction horizon')
    methods=['B1_ukf','B2_both','P2_regret','P3_adaptive_regret','B5_true_state']
    for i,scenario,title in [(9,'servo','Servo tracking'),(10,'feed','Regulatory response to known current feed disturbance')]:
        fig,ax=plt.subplots(figsize=(7,4))
        for m in methods:
            z=trace(scenario,m);ax.plot(z['t'],z['x'][:,2],label=m)
        ax.step(z['t'],z['reference'],'k--',where='post',label='reference')
        ax.set_xlabel('Time (h)');ax.set_ylabel('CC (kmol/m3)');ax.legend(fontsize=8)
        finish(fig,i,title+'; paired seed 4100')
    fig,axs=plt.subplots(2,1,figsize=(7,6),sharex=True)
    for m in methods:
        z=trace('kinetic',m);axs[0].plot(z['t'],z['x'][:,2],label=m);axs[1].plot(z['t'],z['x'][:,4])
    axs[0].set_ylabel('CC');axs[1].set_ylabel('T (K)');axs[1].set_xlabel('Time (h)');axs[0].legend(fontsize=8)
    finish(fig,11,'Concentration and temperature under hidden kinetic mismatch')
    fig,axs=plt.subplots(2,1,figsize=(7,6),sharex=True)
    for m in methods:
        z=trace('combined',m);axs[0].step(z['t'][:-1],z['u'][:,3]/453.59237,label=m,where='post')
        axs[1].plot(z['t'],z['x'][:,4])
    axs[0].set_ylabel('Coolant / nominal');axs[1].axhline(344.261111,color='k',ls='--')
    axs[1].set_ylabel('T (K)');axs[1].set_xlabel('Time (h)');axs[0].legend(fontsize=8)
    finish(fig,12,'Actuation and sampled thermal constraint under combined perturbations')
    s=c[(c.scenario=='FINITE_SUITE')&(c.candidate.isin(['B2_both','P1_expected','P2_regret','P3_adaptive_regret','P5_initial','P5_periodic']))&(c.baseline=='B1_ukf')].drop_duplicates(['candidate','baseline'])
    fig,ax=plt.subplots(figsize=(8,4))
    ax.errorbar(s.mean_improvement,np.arange(len(s)),
        xerr=[s.mean_improvement-s.ci95_low,s.ci95_high-s.mean_improvement],fmt='o')
    ax.set_yticks(np.arange(len(s)),s.candidate);ax.axvline(0,color='k',ls='--')
    ax.set_xlabel('Paired IAE improvement over B1; 95% seed-cluster bootstrap CI')
    finish(fig,13,'Finite-suite contrasts: positive differences favor the candidate')
    s=d[(d.scenario=='inventory_plus')&(d.method.str.startswith('P5')|d.method.eq('B1_ukf'))].groupby('method')[['IAE','samples']].mean()
    fig,ax=plt.subplots(figsize=(8,4));ax.bar(np.arange(len(s)),s.IAE,color='#247ba0')
    ax.set_xticks(np.arange(len(s)),[f'{m}\n{n:.0f} samples' for m,n in zip(s.index,s.samples)],rotation=30,ha='right')
    ax.set_ylabel('IAE (kmol h/m3)')
    finish(fig,14,'Value of additional chemical measurements: inventory-plus scenario')
    s=d.groupby('method')[['IAE','thermal_severity','cooling_effort','decision_ms']].mean()
    s=s.sort_values('IAE');fig,axs=plt.subplots(1,4,figsize=(12,8),sharey=True)
    metrics=[('IAE','Mean IAE','#247ba0'),('thermal_severity','Thermal exceedance\nintegral (K h)','#b74a48'),
             ('cooling_effort','Coolant effort\nintegral q squared (h)','#21857a'),('decision_ms','Decision time (ms)','#7d5e9b')]
    for ax,(column,label,color) in zip(axs,metrics):
        ax.scatter(s[column],np.arange(len(s)),color=color,s=28)
        ax.set_xlabel(label);ax.grid(axis='x',alpha=.25)
        ax.tick_params(axis='x',labelsize=8)
    axs[0].set_yticks(np.arange(len(s)),[m.replace('_',' ') for m in s.index],fontsize=8)
    axs[0].invert_yaxis()
    axs[1].set_xscale('symlog',linthresh=1e-6)
    axs[3].set_xscale('log')
    finish(fig,15,'Tracking, sampled safety, effort and computing trade-offs')
    p=d.groupby(['scenario','method']).IAE.mean().unstack()
    z=p.apply(lambda col:100*(p.B1_ukf-col)/p.B1_ukf)
    fig,ax=plt.subplots(figsize=(12,6));im=ax.imshow(z,cmap='RdBu',vmin=-30,vmax=30,aspect='auto')
    ax.set_xticks(range(len(z.columns)),z.columns,rotation=60,ha='right',fontsize=7);ax.set_yticks(range(len(z)),z.index)
    fig.colorbar(im,ax=ax,label='IAE improvement versus B1 (%) clipped at +/-30 for display')
    finish(fig,16,'Regime map: favorable and adverse mean differences')
    (F/'captions.json').write_text(__import__('json').dumps(CAPTIONS,indent=2))
if __name__=='__main__':main()
