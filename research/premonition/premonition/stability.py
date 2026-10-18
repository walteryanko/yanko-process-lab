from pathlib import Path
import numpy as np
from scipy.optimize import root
from scipy.integrate import solve_ivp
from scipy.linalg import expm
from .physics import *
from .continuation import arclength,normal_form_tests,classify_crossings
from .io import save,csv_write

def spectrum(x,u,p=P):return np.linalg.eigvals(jacobian(x,u,p))
def reactive_alpha(x,u,p=P):
    J=jacobian(x,u,p);a=np.array([[J[0,0],J[0,4]],[J[4,0]+J[4,1]-J[4,2],J[4,4]]])
    return float(np.linalg.eigvals(a).real.max())

def observability(x,u,p=P,horizon=57):
    A=jacobian(x,u,p);S=np.diag(SCALE);A=np.linalg.solve(S,A@S);H=np.eye(6)[[4,5]]@S
    F=expm(A*DT);O=np.vstack([H@np.linalg.matrix_power(F,k) for k in range(horizon)])
    s=np.linalg.svd(O,compute_uv=False)
    return dict(singular_values=s,rank=int(np.sum(s>s[0]*1e-8)),condition=float(s[0]/max(s[-1],1e-30)),note='local finite-horizon, scaled state, two thermal outputs')

def refine_fold(guess,key=4,u=U0,p=P):
    def fun(z):
        uu=u.copy();uu[key]=z[1];h=1e-3
        return [heat(z[0],uu,p),(heat(z[0]+h,uu,p)-heat(z[0]-h,uu,p))/(2*h)]
    sol=root(fun,guess,tol=1e-10);T,v=sol.x;uu=u.copy();uu[key]=v
    h=.001;hh=1e-3
    up=uu.copy();um=uu.copy();up[key]+=hh;um[key]-=hh
    fp=(heat(T,up,p)-heat(T,um,p))/(2*hh)
    ftt=(heat(T+h,uu,p)-2*heat(T,uu,p)+heat(T-h,uu,p))/h**2
    x=mass_ss(T,uu,p);eig=spectrum(x,uu,p)
    return dict(T=float(T),parameter=float(v),key=key,x=x,residual=float(np.linalg.norm(fun(sol.x))),parameter_derivative=fp,second_T_derivative=ftt,eig_real=eig.real,eig_imag=eig.imag,
        verified=bool(np.linalg.norm(fun(sol.x))<1e-7 and abs(fp)>1e-5 and abs(ftt)>1e-5 and min(abs(eig))<1e-5))

def campaign_A(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);rows=[];curves={};folds=[]
    specs=[('mw','u',3,22.7,1366.2,600.),('T0','u',4,275.,325.,15.),('FA','u',0,U0[0]*.6,U0[0]*1.4,15.),('FB','u',1,U0[1]*.7,U0[1]*1.3,150.),('FM','u',2,U0[2]*.5,U0[2]*1.5,30.),('UA','p',13,P[13]*.5,P[13]*1.5,15000.),('k0','p',9,P[9]*.7,P[9]*1.3,P[9]*.3),('E','p',7,P[7]*.98,P[7]*1.02,P[7]*.02)]
    for name,kind,key,lo,hi,sc in specs:
        def up(v):
            u=U0.copy();p=P.copy()
            if kind=='u':u[key]=v
            else:p[key]=v
            return u,p
        def F(z):
            u,p=up(z[1]);return np.array([heat(z[0],u,p)/10])
        u,p=up(lo);initial=equilibria(u,p)[0]
        branch=arclength(F,[initial[4],lo],[20.,sc],ds=.025,steps=650,direction=1,stop=lambda z:z[1]>hi+sc*.01 or z[1]<lo-sc*.05 or z[0]<250 or z[0]>430)
        rr=[];es=[]
        for T,val in branch['points']:
            u,p=up(val);x=mass_ss(T,u,p);eig=spectrum(x,u,p);es.append(eig)
            rr.append(dict(parameter=float(val),T=float(T),CC=x[2],alpha=eig.real.max(),reactive_alpha=reactive_alpha(x,u,p),stable=bool(eig.real.max()<0),residual=float(np.linalg.norm(rhs(x,u,p)/SCALE)),eig_real=eig.real,eig_imag=eig.imag))
        candidates=classify_crossings(branch['points'],es)
        curves[name]=dict(rows=rr,failures=branch['failures'],candidates=candidates,range=[lo,hi],kind=kind,key=key)
        if kind=='u':
            for c in candidates:
                if c['type']=='fold_candidate':
                    f=refine_fold(np.mean([c['left'],c['right']],axis=0),key)
                    if f['verified'] and lo<=f['parameter']<=hi and not any(a['axis']==name and abs(a['parameter']-f['parameter'])<1e-5 for a in folds):folds.append(dict(axis=name,**f))
        # Multi-start/bracketing grid independently checks disconnected roots.
        for val in np.linspace(lo,hi,121):
            u,p=up(val);xx=equilibria(u,p)
            for n,x in enumerate(xx):
                e=spectrum(x,u,p)
                rows.append(dict(axis=name,parameter=val,root=n,nroots=len(xx),T=x[4],CC=x[2],alpha=e.real.max(),reactive_alpha=reactive_alpha(x,u,p),residual=np.linalg.norm(rhs(x,u,p)),stable=bool(e.real.max()<0),near_axis=abs(e.real.max())<.1))
    # A joint LHS-style random screen is exploratory, not an exhaustive guarantee.
    rng=np.random.default_rng(651);joint=[]
    for k in range(400):
        u=U0.copy();p=P.copy();u[3]=rng.uniform(22.7,1366.2);u[4]=rng.uniform(285,315);u[0]*=rng.uniform(.8,1.2);u[1]*=rng.uniform(.8,1.2);p[13]*=rng.uniform(.7,1.3);p[9]*=rng.uniform(.8,1.2)
        for x in equilibria(u,p):
            e=spectrum(x,u,p);joint.append(dict(case=k,u=u,p=p,T=x[4],alpha=e.real.max(),imag_at_max=e[np.argmax(e.real)].imag))
    # Local predictions verified dynamically on all three nominal-feed-295 roots.
    u=U0.copy();u[4]=295.;checks=[];basins=[]
    for i,x in enumerate(equilibria(u)):
        A=jacobian(x,u);e,V=np.linalg.eig(A);idx=np.argmax(e.real);d=V[:,idx].real;d=.02*d/np.linalg.norm(d/SCALE)
        for sign in [-1,1]:
            sol=solve_ivp(lambda t,z:rhs(z,u),[0,3.],x+sign*d,rtol=1e-9,atol=1e-10,t_eval=np.linspace(0,3,301))
            checks.append(dict(root=i,stable=bool(e.real.max()<0),sign=sign,t=sol.t,T=sol.y[4],distance=np.linalg.norm((sol.y.T-x)/SCALE,axis=1),success=sol.success))
    for T in np.linspace(290,345,31):
        x=mass_ss(T,u);sol=solve_ivp(lambda t,z:rhs(z,u),[0,6],x,rtol=1e-8,atol=1e-9)
        basins.append(dict(initial_T=T,final_T=sol.y[4,-1],success=sol.success))
    fold,hopf=normal_form_tests()
    audit=dict(model='MATLAB2019_SI',base=BASE,parameters=asdict(Parameters()),inputs=U0,base_eig=spectrum(BASE,U0),base_observability=observability(BASE,U0),folds=folds,
       scan_points=len(rows),joint_equilibria=len(joint),max_residual=max(r['residual'] for r in rows),normal_forms=dict(fold_crossed=bool(fold['points'][:,0].min()<0),fold_min_parameter=fold['points'][:,1].min(),hopf_mu_range=[hopf['points'][:,2].min(),hopf['points'][:,2].max()]),
       note='No global exclusion of Hopf. Negative results limited to sampled domain; fold labels require refinement.')
    save(out/'map.json',curves);csv_write(out/'equilibria.csv',rows);save(out/'joint_screen.json',joint);save(out/'audit.json',audit);save(out/'local_validation.json',checks);csv_write(out/'basins.csv',basins)
    return audit
