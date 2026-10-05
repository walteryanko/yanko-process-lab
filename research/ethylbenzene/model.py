"""First ethylbenzene reactor from Brandao's UFPB TCC (2016), pp. 42-47.

This is a reconstruction of the printed ODEs, not the full Aspen flowsheet.
The kinetic time-unit correction is verified in the supplied Luyben paper.
Heat removal was unreported: infer an effective duty at the reconstructed
nominal point, retaining the printed constant heat capacities/densities.
"""
from pathlib import Path
import json
import numpy as np
from scipy.optimize import root, minimize_scalar

HERE=Path(__file__).resolve().parent
WEIGHTS=HERE/'weights'; RESULTS=HERE/'results'; NATIVE=HERE/'native_cache'
DT=.025  # h; 90 s, new study setting, not recovered from historical Simulink
V=200.
NU=np.array([[-1.,-1.,0.],[-1.,0.,-1.],[1.,-1.,2.],[0.,1.,-1.]])
MW=np.array([28.054,78.114,106.168,134.222])
K0=np.array([1.528e6,2.778e7,1000.])
E=np.array([17000.,20000.,15000.]); RGAS=1.987  # cal/mol/K, not kcal/mol/K
DH=np.array([-27150.,-26950.,-205.5])  # kcal/kmol
RHO=np.array([7.63446,10.8803,10.9014]); CP=np.array([236.32,265.80,273.50])
RHO_REACTOR=8.09685; CP_REACTOR=73.56
CAPACITY=V*RHO_REACTOR*CP_REACTOR
REC=np.array([.001198,10.8982,.002015,0.])
F0=np.array([82.59918,57.95784,88.92402]); TFEED=np.array([46.85,46.85,45.22])
TARGET_FRACTIONS=np.array([.0051,.6607,.2811,.0531])

def rates(x,multiplier=1.,time_factor=3600.):
    x=np.asarray(x)
    k=K0*time_factor*np.asarray(multiplier)*np.exp(-E/(RGAS*(x[...,4,None]+273.15)))
    return k*np.stack([x[...,0]*x[...,1],x[...,0]*x[...,2],x[...,1]*x[...,3]],axis=-1)

def concentrations_at_temperature(temp,time_factor=3600.):
    inflow=F0[0]*RHO[0]*np.array([1.,0,0,0])+F0[1]*RHO[1]*np.array([0,1.,0,0])+F0[2]*REC
    def fun(c):return (inflow-F0.sum()*c)/V+NU@rates(np.r_[c,temp],time_factor=time_factor)
    sol=root(fun,[.04,4.6,1.97,.37],tol=1e-11)
    if not sol.success and np.max(np.abs(fun(sol.x)))>1e-9:raise RuntimeError(sol.message)
    if np.min(sol.x)<=0:raise RuntimeError('Nonphysical equilibrium branch')
    return sol.x

_fit=minimize_scalar(lambda t:np.sum((concentrations_at_temperature(t)/concentrations_at_temperature(t).sum()-TARGET_FRACTIONS)**2),bounds=(155.,166.),method='bounded',options={'xatol':1e-11})
TNOM=float(_fit.x)
BASE=np.r_[concentrations_at_temperature(TNOM),TNOM]
Q0=float(np.dot(F0*RHO*CP,TFEED)-F0.sum()*RHO_REACTOR*CP_REACTOR*TNOM-V*np.dot(rates(BASE),DH))
U0=np.r_[F0,Q0,TFEED]
XS=np.array([.1,1.5,.75,.25,15.]); US=np.r_[F0*.3,Q0*.3,[5.,5.,5.]]
SUBSTEPS=8
STATE_NAMES=['CE','CB','CEB','CDEB','T_C']
INPUT_NAMES=['fE_m3_h','fB_m3_h','fRecycle_m3_h','Q_kcal_h','TE_C','TB_C','TRecycle_C']
T_LIMIT=165.  # imposed research limit; absent from the TCC
T_STOP=220.   # numerical domain guard; NOT a phase/safety limit

def rhs(x,u,multiplier=1.):
    x=np.asarray(x);u=np.asarray(u)
    f=u[..., :3]; total=f.sum(axis=-1)
    inflow=f[...,0,None]*RHO[0]*np.array([1.,0,0,0])+f[...,1,None]*RHO[1]*np.array([0,1.,0,0])+f[...,2,None]*REC
    rr=rates(x,multiplier)
    dc=(inflow-total[...,None]*x[...,:4])/V+rr@NU.T
    heat=np.sum(f*RHO*CP*u[...,4:7],axis=-1)-total*RHO_REACTOR*CP_REACTOR*x[...,4]-V*(rr@DH)-u[...,3]
    return np.concatenate([dc,(heat/CAPACITY)[...,None]],axis=-1)

def transition(x,u,dt=DT,multiplier=1.,substeps=SUBSTEPS):
    x=np.asarray(x,dtype=float).copy();h=dt/substeps
    for _ in range(substeps):
        a=rhs(x,u,multiplier);b=rhs(x+h*a/2,u,multiplier)
        c=rhs(x+h*b/2,u,multiplier);d=rhs(x+h*c,u,multiplier)
        x+=h*(a+2*b+2*c+d)/6
    return x

def fraction(x):
    x=np.asarray(x);return x[...,2]/np.sum(x[...,:4],axis=-1)

def dump(path,data):
    def conv(x):
        if isinstance(x,np.ndarray):return x.tolist()
        if isinstance(x,np.generic):return x.item()
        if isinstance(x,Path):return str(x)
        raise TypeError(type(x))
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,default=conv,ensure_ascii=False,indent=2,allow_nan=False)+'\n')

def calibration_audit():
    c_minutes=concentrations_at_temperature(TNOM,time_factor=60.)
    return dict(source='TFC_WALTER_FINAL_imprimir.pdf, UFPB 2016, pp. 42-47 and Table 4.1 p.52',
      scope='first reactor only; downstream columns and second reactor are not dynamic models here',
      kinetic_time_factor=3600.,kinetic_unit_status='confirmed kmol/(s m3) in supplied Luyben 2011 p.656; printed TCC min label corrected',
      gas_constant='1.987 cal/mol/K; printed kcal is inconsistent with activation energies in cal/mol',
      nominal_state=BASE,nominal_fractions=BASE[:4]/BASE[:4].sum(),target_matlab_fractions=TARGET_FRACTIONS,
      literal_minutes_fractions=c_minutes/c_minutes.sum(),nominal_duty_kcal_h=Q0,nominal_duty_MW=Q0*4184/3.6e9,
      heat_capacity_status='printed constant energy-balance coefficients retained; effective Q inferred, not identified plant duty',
      steady_rhs=rhs(BASE,U0),temperature_limit_C=T_LIMIT,
      temperature_limit_status='new imposed research limit; no hard limit stated in TCC',
      manipulated_variables=dict(siso=['fE'],mimo=['fE','Q']),
      added_actuator='heat-removal duty supported by ASPEN/aspeneb.dynf R1_TC.OP -> R1.QR; ideal input and 0.6-1.4 bounds are new study assumptions',
      aspen_duty_warning='effective 25.24 MW of printed-ODE reconstruction differs from paper 10.3 MW and archive snapshots; not an Aspen thermodynamic reproduction',
      density_warning='printed constant reactor molar density and sum of computed concentrations differ; inherited reduced-model approximation retained',
      valve_flow_bounds='0.04-2.0 fE0, equal-percentage rangeability 50 and capacity factor 2 from TCC',
      sample_period_h=DT,original_Q_sample_period_Qcov_Rcov_PI_gains='not specified sufficiently to recover exactly')

if __name__=='__main__':
    dump(RESULTS/'calibration.json',calibration_audit());print(json.dumps(calibration_audit(),default=lambda x:x.tolist() if isinstance(x,np.ndarray) else x,indent=2))
