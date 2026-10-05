"""Check all Table-2 points independently of the single nominal calibration.
Branch selected by nearest reported temperature, explicitly best-case diagnostic.
"""
import csv,json
from pathlib import Path
from dataclasses import replace
import numpy as np
from cstr import equilibria
from estimator import *
DATA={'fa':[298.2,301.7,332.3,349.,361.4],'fb':[357.4,345.3,332.3,302.2,299.9],
'fm':[336.2,334.4,332.3,329.6,308.3],'mw':[342.2,336.4,332.3,328.8,325.0],
't0':[281.4,290.7,332.3,345.3,354.3],'ta':[293.7,299.4,332.3,338.2,342.7]}
rows=[]
for key,temperatures in DATA.items():
 for factor,target in zip([.5,.75,1.,1.25,1.5],temperatures):
  u=U_BASE.copy();j=['fa','fb','fm','mw','t0','ta'].index(key)
  if j<4:u[j]*=factor
  else:u[j]=(((u[j]-273.15)*1.8+32)*factor-32)/1.8+273.15
  for name,p0 in [('tabled',P_TABLE),('calibrated',P_ADJUSTED)]:
   p=replace(p0,FB=u[1],FM=u[2],T0=u[4]);us=u[[0,3,5]]
   roots=equilibria(us,p)
   z=min(roots,key=lambda z:abs(z['x'][4]-target))
   rows.append(dict(input=key,factor=factor,model=name,reported_T=target,computed_T=z['x'][4],
     error_K=z['x'][4]-target,stable=z['stable'],root_count=len(roots),
     max_residual=float(max(abs(rhs6(z['x'],u,p))))))
root=Path(__file__).resolve().parent/'results'
with (root/'historical_equilibria.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,rows[0].keys(),lineterminator='\n');w.writeheader();w.writerows(rows)
summary={}
for name in ['tabled','calibrated']:
 r=[x for x in rows if x['model']==name and x['factor']!=1]
 errors=np.array([x['error_K'] for x in r]);summary[name]=dict(RMSE_K=float(np.sqrt(np.mean(errors**2))),max_absolute_error_K=float(max(abs(errors))),non_nominal_points=len(r))
summary['branch_selection']='Nearest reported root; best-case diagnostic, not a continuation forecast'
(root/'historical_validation.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
