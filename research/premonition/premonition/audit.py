from pathlib import Path
import json,platform,sys,hashlib,time
import numpy as np
from scipy.integrate import solve_ivp
from .physics import *
from .io import save,sha

def physical_audit(out):
    out=Path(out);root=Path(__file__).resolve().parents[1]
    pcal=TABLE.copy();T=332.3;x=mass_ss(T,TABLE_U,TABLE);r=TABLE[9]*np.exp(-TABLE[7]/TABLE[8]/T)*x[0]
    # Inverse energy balance follows the separate NAKE branch; never used in primary runs.
    pcal[10]-=heat(T,TABLE_U,TABLE)*TABLE[11]*np.dot(x[:4],TABLE[:4])/(r*TABLE[11])
    variants=[]
    for name,p,u in [('original_MATLAB_SI',P,U0),('tabled',TABLE,TABLE_U),('calibrated_332_3',pcal,TABLE_U)]:
        variants.append(dict(name=name,heat=p[10],R=p[8],arrhenius_offset_K=p[14],parameters=p,inputs=u,roots=equilibria(u,p)))
    src={p.name:sha(p) for p in (root/'vendor').iterdir() if p.is_file()}
    from .stability import observability
    points=[BASE,BASE+np.array([.1,.1,0,0,2,1]),BASE+np.array([.2,-.2,.1,0,5,-2])]
    ob=[dict(x=x,**observability(x,U0)) for x in points]
    env={m:__import__(m).__version__ for m in ['numpy','scipy','sklearn','numba','matplotlib']}
    result=dict(primary='original_MATLAB_SI',source_repo='https://github.com/walteryanko/yanko-process-lab',source_main_commit='f4444d4c238291b8633743930249ee387ad94541',source_historical_commit='b55a46cd182c70100b50ff5e6c98ba82ed96a5a8',source_reference_commit='88c40e65204fa6aa5bed02cc64fb15be79a53bb1',
      variants=variants,sources_sha256=src,observability=ob,ukf_changes='Historical alpha,beta,Q,R and Euler retained; initialized at nominal equilibrium with uncertain P0 for this campaign, not dissertation startup. Joseph covariance and SPD repair are numerical safeguards.',
      nmcp_identity='Port of ProcessLab main controller.ts (P57,M6,Qe0.8,Rdu0.2,coordinate search), with primary historical model; shared independent guard added. Not a MATLAB/fmincon binary reproduction.',
      other_research={'Oracle_KF_v01':'Audited; uses tabled model, pretrained weights incompatible with historical variant. No transfer or claimed gain.', 'NAKE':'Calibrated heat source audited; no mixing with primary model.', 'RSI':'Recovered branch aliases beyond-conventional-operation; no distinct recursive algorithm inferred.', 'Schrodinger_KF':'Branch reviewed; particle/transport ensemble uses tabled family. Not included as a primary estimator.', 'Quantum_Multiverse':'Checkpoint sources recovered and inspected; tabled family, not transferred.'},
      environment=dict(python=sys.version,platform=platform.platform(),libraries=env),industrial_use=False,limits=dict(study_K=344.,historical_K=355.4,exact_160F_K=(160-32)/1.8+273.15,meaning='Source study limit vs practical reagent evaporation constraint; not mathematical bifurcation thresholds'))
    save(out,result);return result
