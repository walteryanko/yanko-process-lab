"""Dimensionally restricted expression grammar and STLSQ weak discovery.

Expressions modify positive physical coefficients, never six arbitrary state
derivatives. A sparse weak jacket balance uses only measured T and Tt.
"""
import numpy as np
import sympy as sp
from .physics import CP,RHO,VT,UA,U0,NP,Model,correction,BASE,simulate,in_domain

def stlsq(A,b,threshold=.05,ridge=1e-5,iterations=8):
    scale=np.linalg.norm(A,axis=0);scale=np.maximum(scale,1e-10);An=A/scale
    c=np.linalg.solve(An.T@An+ridge*np.eye(An.shape[1]),An.T@b)
    for _ in range(iterations):
        keep=np.abs(c)>threshold*max(np.max(np.abs(c)),1e-12)
        if not np.any(keep):return np.zeros(A.shape[1])
        c[~keep]=0;c[keep]=np.linalg.lstsq(An[:,keep],b,rcond=1e-8)[0]
    return c/scale

def weak_jacket(records,block=8):
    """Integral residual versus conductance dictionary (not noisy derivatives).
    This produces proposals, subsequently refit using full output error.
    G(mw)=mw*cp*(1-exp(-UA/(mw*cp))); linearize at nominal UA.
    """
    A=[];b=[]
    for rec in records:
        z=rec.measurements;u=rec.inputs;dt=rec.dt
        for start in range(0,len(u)-block+1,block):
            end=start+block
            if not np.all(np.isfinite(z[start:end+1])):continue
            T=(z[start:end,0]+z[start+1:end+1,0])/2
            Tt=(z[start:end,1]+z[start+1:end+1,1])/2;w=u[start:end,3];ta=u[start:end,5]
            v=w/U0[3];F=np.column_stack([np.ones(block),v-1,np.log(v),(v-1)**2,1/v-1,np.sqrt(v)-1])
            G=w*CP[1]*(-np.expm1(-UA/(w*CP[1])))
            residual=RHO[1]*VT*CP[1]*(z[end,1]-z[start,1])-dt*np.sum(w*CP[1]*(ta-Tt)+G*(T-ta))
            sensitivity=UA*np.exp(-UA/(w*CP[1]))*(T-ta)
            A.append(dt*np.sum(F*sensitivity[:,None],axis=0));b.append(residual)
    if len(A)<8:return dict(coefficients=[0.]*6,terms=[],rows=len(A),condition=None)
    A=np.array(A);b=np.array(b);c=stlsq(A,b,threshold=.15,ridge=.01)
    return dict(coefficients=c.tolist(),terms=np.flatnonzero(abs(c)>.01).tolist(),rows=len(A),condition=float(np.linalg.cond(A)))

def equations(model):
    p=model.params;v,T,t=sp.symbols('v T t',positive=True)
    f=[1,v-1,sp.log(v),(v-1)**2,1/v-1,sp.sqrt(v)-1]
    expo=sum(float(p[j])*f[j] for j in range(6) if abs(p[j])>1e-10)
    kin=float(p[6])+float(p[7])*10*(340/T-1)
    entries=[('UA_eff',30385.6*sp.exp(expo),'kJ/(h K)'),('k_eff',16.96e12*sp.exp(-75362.4/(8.314*T)+kin),'h^-1'),
             ('measurement_T',T+float(p[10]),'K'),('bias_Tt',float(p[11])+float(p[12])*t,'K')]
    if abs(p[8])>1e-10:entries.append(('heat_release',91556.9*sp.exp(float(p[8])),'kJ/kmol'))
    if abs(p[9])>1e-10:entries.append(('FA_eff',sp.Symbol('FA')*sp.exp(float(p[9])),'kmol/h'))
    if abs(p[13])>1e-10:entries.append(('capacity_eff',sp.Symbol('capacity_nominal')*sp.exp(float(p[13])),'kJ/K'))
    if abs(p[14])>1e-10:entries.append(('Tfeed_eff',sp.Symbol('Tfeed')+float(p[14]),'K'))
    result=[]
    for n,e,u in entries:
        simple=sp.simplify(e)
        result.append(dict(name=n,expression=str(simple),latex=sp.latex(simple),sympy=sp.sstr(simple),mathml=sp.printing.mathml(simple,printer='presentation'),unit=u))
    return result

def physical_check(model,stress=True):
    # Bounds are evaluated over the deployment domain, not just training points.
    factors=[]
    for mw in np.linspace(150,1250,17):
        for t in np.linspace(295,350,12):
            x=BASE.copy();x[4]=t;u=U0.copy();u[3]=mw
            factors.append(correction(x,u,model.params))
    a=np.array(factors);ok=bool(np.all(np.isfinite(a)) and a[:,0].min()>=.25 and a[:,0].max()<=3. and a[:,1].min()>=.1 and a[:,1].max()<=8.)
    reason='positive bounded coefficient grammar' if ok else 'coefficient extrapolation outside allowed envelope'
    if ok and stress:
        for mw in (220.,453.6,1050.):
            u=np.tile(U0,(400,1));u[:,3]=mw
            path=simulate(BASE,u,model.params,.015,3,model.variant)
            if not in_domain(path):ok=False;reason='long integration left physical domain';break
    return dict(valid=ok,reason=reason,ua_range=a[:,0].min().item() if np.all(np.isfinite(a)) else None,
                ua_max=a[:,0].max().item() if np.all(np.isfinite(a)) else None,
                mass_conservation='reaction stoichiometry [-1,-1,+1,0] unchanged',
                dimensionless_arguments=True)
