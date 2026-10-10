"""Operating windows and priors expressed in fixed physical coordinates."""
import numpy as np
import pandas as pd
from beyond.models import get_model
from beyond.common import RESULTS,frame,dump,pareto
from beyond.spectra import information

def point_metrics(m,x,u):
    A=np.array(m.fx(x,u,m.p0));B=np.array(m.fu(x,u,m.p0));G=np.array(m.fp(x,u,m.p0))
    eig=np.linalg.eigvals(A);g=np.array(m.qgrad(x)).ravel();Xp=-np.linalg.solve(A,G);Xu=-np.linalg.solve(A,B)
    sensitivity=g@Xp*m.pscale
    authority=g@Xu[:,m.controls]*m.u0[m.controls]
    prod=m.production(x,u);feed=u[0]/m.u0[0];cool=u[m.cidx]/m.u0[m.cidx]
    if m.kind=='PG':byproduct=0;selectivity=1;utility=.02*cool**2
    else:byproduct=sum(u[:3])*x[3];selectivity=prod/(prod+byproduct);utility=.02*cool
    economic=prod/m.prod0-.60*feed-utility-(.20*byproduct/m.prod0 if m.kind=='EB' else 0)
    # A quality deadband of +/-2% of NOMINAL quality is fixed across the map.
    return dict(quality=float(m.quality(x)),production=prod,byproduct=byproduct,selectivity=selectivity,
        heat=m.duty(x,u),feed_ratio=feed,cooling_ratio=cool,economic_proxy=economic,
        sensitivity_sd=float(np.linalg.norm(sensitivity)),sensitivity_relative=float(np.linalg.norm(sensitivity)/m.q0),
        gain_feed=float(authority[0]/m.q0),gain_cooling=float(authority[1]/m.q0),
        authority=float(np.linalg.norm(authority)/m.q0),stability_abscissa=float(max(eig.real)),
        thermal_margin=m.tmax-x[4],temperature=float(x[4]),
        heat_transfer_ratio=float((u[3]/m.u0[3])/((x[4]-m.tmin)/(160-m.tmin))) if m.kind=='EB' else 1.)

def run():
    rows=[];points={}
    for kind in ['PG','EB']:
        m=get_model(kind);idx=0
        temps=np.linspace(320,m.tmax-.5,15) if kind=='PG' else np.linspace(145,164.5,15)
        for fr in np.linspace(.7,1.3,15):
            for T in temps:
                try:x,u=m.operating_point(fr,T)
                except (ValueError,RuntimeError):continue
                if not m.feasible(x,u):continue
                r=point_metrics(m,x,u)
                if r['stability_abscissa']>=0:continue
                # EB necessary cooling direction enforced; capacity is separately reported.
                U=np.tile(u,(int(np.ceil(3*m.tau/m.dt)),1))
                info,X,data=information(m,x,U)
                # Sensitivity to the fixed physical prior, with states AND parameters uncertain.
                r.update(info);r.update(kind=kind,index=idx)
                r['posterior_quality_relative']=r['current_quality_posterior_sd']/m.q0
                r['prior_quality_relative']=r['current_quality_prior_sd']/m.q0
                r['information_fraction']=r['current_quality_information_reduction']
                rows.append(r);points[f'{kind}_{idx}']={'x':x,'u':u};idx+=1
        nominal=point_metrics(m,m.x0,m.u0);nominal.update(kind=kind,index=-1)
        info,_,_=information(m,m.x0,np.tile(m.u0,(int(np.ceil(3*m.tau/m.dt)),1)))
        nominal.update(info);nominal['posterior_quality_relative']=info['current_quality_posterior_sd']/m.q0
        nominal['prior_quality_relative']=info['current_quality_prior_sd']/m.q0
        nominal['information_fraction']=info['current_quality_information_reduction']
        rows.append(nominal);points[f'{kind}_-1']={'x':m.x0,'u':m.u0}
        print(kind,'landscape',idx,'points',flush=True)
    df=pd.DataFrame(rows);df['negative_economic']=-df.economic_proxy;df['pareto']=False;selected={}
    for kind,grp in df.groupby('kind'):
        m=get_model(kind)
        # Price proxy is declared, not calibrated to industrial monetary cost.
        # Productive region: >=90% nominal throughput. At least 2 K margin.
        eligible=grp[(grp.production>=.9*m.prod0)&(grp.thermal_margin>=2)]
        e=eligible.copy()
        e['joint_score']=-e.economic_proxy+4*e.posterior_quality_relative+2*e.sensitivity_relative+.01/(e.thermal_margin)
        if e.empty:raise RuntimeError('No productive robust operating window')
        selected[kind]={
          'nominal':-1,
          'O1_economic':int(eligible.loc[eligible.economic_proxy.idxmax(),'index']),
          'O2_robust':int(eligible.loc[eligible.sensitivity_relative.idxmin(),'index']),
          'O3_information':int(eligible.loc[eligible.posterior_quality_relative.idxmin(),'index']),
          'O4_joint':int(e.loc[e.joint_score.idxmin(),'index'])}
        df.loc[grp.index,'pareto']=pareto(grp,['negative_economic','posterior_quality_relative','sensitivity_relative'])
    df.to_csv(RESULTS/'landscape.csv',index=False);dump(RESULTS/'operating_points.json',points)
    dump(RESULTS/'selected_regions.json',selected)
    print(selected,flush=True)
if __name__=='__main__':run()
