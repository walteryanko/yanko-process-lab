"""Paired PG estimator experiment. Synthetic, causal, CPU only."""
import argparse, csv, hashlib, itertools, json, os, platform, subprocess, sys, time, traceback, zipfile
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import lru_cache
from pathlib import Path
import numpy as np
import scipy
import casadi as ca
from scipy.optimize import least_squares
from scipy.special import logsumexp

ROOT=Path(__file__).resolve().parent
LAB=ROOT.parent/"darwin-observer"
sys.path.insert(0,str(LAB))
from darwin.physics import Model, NP, transition, STATE_NAMES, LEGACY_CP as CP, LEGACY_RHO as RHO, LEGACY_V as V, LEGACY_VT as VT, LEGACY_UA as UA
from darwin.observers import OnlineUKF
from darwin.thesis_cases import BY_KEY, U_NOM, T_LIMIT, Q_HIST, R_HIST, P_HIST, INPUT_STD, commanded, initial_state, observer_options, time_grid
from darwin.thesis_control import ThesisNMPC, compile_kernel
from darwin.thesis_experiments import advance

OUT=ROOT/"results"
CACHE=ROOT/".cache"
METHODS=("UKF_RK4","EKF","GM_EKF","MHE5")
H=np.eye(6)[4:6]
SCALE=np.array([1.,20.,1.,2.,1.,1.])
NOMINAL=Model(variant=1)
PROTOCOL=json.loads((ROOT/"PROTOCOL.json").read_text())

def write_json(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,allow_nan=False,ensure_ascii=False),encoding="utf-8")

def write_csv(path,rows):
    if not rows:return
    path.parent.mkdir(parents=True,exist_ok=True)
    fields=sorted(set().union(*(r.keys() for r in rows)))
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def sym_rhs(x,u):
    fa,fb,fm,mw,tf,tc=[u[i] for i in range(6)]
    flow=fa/RHO[0]+fb/RHO[1]+fm/RHO[2]
    rate=16.96e12*ca.exp(-75362.4/((1.987*4.1868)*(x[4]+.1833333333333333)))*x[0]
    q=mw*CP[1]*(tc-x[4])*(1-ca.exp(-UA/(mw*CP[1])))
    cap=V*ca.dot(x[:4],ca.DM(CP))
    sensible=(fa*CP[0]+fb*CP[1]+fm*CP[3])*(x[4]-tf)
    return ca.vertcat((ca.vertcat(fa,fb,0,fm)-flow*x[:4])/V+rate*ca.DM([-1,-1,1,0]),
        (q-sensible+83736.*rate*V)/cap,
        (mw*CP[1]*(tc-x[5])-q)/(RHO[1]*VT*CP[1]))

def sym_step(x,u,dt):
    z=x
    for _ in range(3):
        h=dt/3
        a=sym_rhs(z,u);b=sym_rhs(z+h*a/2,u);c=sym_rhs(z+h*b/2,u);d=sym_rhs(z+h*c,u)
        z=z+h*(a+2*b+2*c+d)/6
    return z

def step_function():
    x=ca.SX.sym("x",6);u=ca.SX.sym("u",6);dt=ca.SX.sym("dt")
    z=sym_step(x,u,dt)
    return ca.Function("pg_step_jac",[x,u,dt],[z,ca.jacobian(z,x)])

def mhe_function(n):
    z=ca.SX.sym("z",6*(n+1));par=ca.SX.sym("par",42+9*n)
    Z=ca.reshape(z,6,n+1);prior=par[:6];A=ca.reshape(par[6:42],6,6)
    U=ca.reshape(par[42:42+6*n],6,n)
    Y=ca.reshape(par[42+6*n:42+8*n],2,n);dt=par[42+8*n:]
    res=[A@(Z[:,0]-prior)]
    for j in range(n):
        res += [(Z[:,j+1]-sym_step(Z[:,j],U[:,j],dt[j]))/ca.DM(np.sqrt(Q_HIST)),
                (Z[4:6,j+1]-Y[:,j])/ca.DM(np.sqrt(R_HIST))]
    r=ca.vertcat(*res)
    return ca.Function("pg_mhe_"+str(n),[z,par],[r,ca.jacobian(r,z)])

def compile_function(fun):
    if os.name=="nt":return  # CasADi graph evaluation remains available without gcc.
    CACHE.mkdir(parents=True,exist_ok=True)
    name=fun.name();lib=CACHE/(name+".so")
    if lib.exists():return
    old=Path.cwd()
    try:
        os.chdir(CACHE);fun.generate(name+".c")
        subprocess.run(["gcc","-O3","-fPIC","-shared",name+".c","-o",name+".so","-lm"],check=True)
    finally:os.chdir(old)

def prepare():
    compile_function(step_function())
    for n in range(1,6):compile_function(mhe_function(n))
    if os.name!="nt":compile_kernel()
    # Warm Numba outside episode timings.
    transition(initial_state(BY_KEY["OL_FA"]),U_NOM,np.zeros(NP),.015,3,1)
    warm=OnlineUKF(NOMINAL,**observer_options(initial_state(BY_KEY["OL_FA"])))
    warm.update(U_NOM,initial_state(BY_KEY["OL_FA"])[4:6],.015)

@lru_cache(maxsize=1)
def step_jac():
    path=CACHE/"pg_step_jac.so"
    return ca.external("pg_step_jac",str(path)) if path.exists() else step_function()

@lru_cache(maxsize=5)
def mhe_graph(n):
    path=CACHE/("pg_mhe_"+str(n)+".so")
    return ca.external("pg_mhe_"+str(n),str(path)) if path.exists() else mhe_function(n)

def psd(p):
    p=(p+p.T)/2
    val=np.linalg.eigvalsh(p)[0]
    return p+np.eye(len(p))*max(0.,1e-12-val)

def predict(x,p,u,dt):
    xp,F=step_jac()(x,u,dt)
    xp=np.asarray(xp).ravel();F=np.asarray(F)
    return xp,psd(F@p@F.T+np.diag(Q_HIST))

def gaussian_update(xp,pp,y,rdiag):
    S=H@pp@H.T+np.diag(rdiag)
    innovation=np.asarray(y)-H@xp
    K=np.linalg.solve(S,(pp@H.T).T).T
    xn=xp+K@innovation;A=np.eye(6)-K@H
    pn=psd(A@pp@A.T+K@np.diag(rdiag)@K.T)
    ll=-.5*(np.linalg.slogdet(S)[1]+innovation@np.linalg.solve(S,innovation)+2*np.log(2*np.pi))
    return xn,pn,float(ll)

def mixture_update(xp,pp,y,epsilon=.05,kappa=10.):
    means=[];covs=[];logs=[]
    for bits in itertools.product((0,1),repeat=2):
        probability=np.prod([epsilon if b else 1-epsilon for b in bits])
        if probability<=0:continue
        rd=R_HIST*np.array([kappa*kappa if b else 1. for b in bits])
        m,p,ll=gaussian_update(xp,pp,y,rd)
        means.append(m);covs.append(p);logs.append(np.log(probability)+ll)
    weights=np.exp(np.asarray(logs)-logsumexp(logs))
    mean=sum(w*m for w,m in zip(weights,means))
    covariance=sum(w*(p+np.outer(m-mean,m-mean)) for w,m,p in zip(weights,means,covs))
    return mean,psd(covariance)

class EKF:
    def __init__(self,x0,robust=False):
        self.x=x0.copy();self.P=np.diag(P_HIST);self.robust=robust
        self.fallbacks=0;self.budget_hits=0
    def update(self,u,y,dt):
        xp,pp=predict(self.x,self.P,u,dt)
        if self.robust:self.x,self.P=mixture_update(xp,pp,y)
        else:self.x,self.P,_=gaussian_update(xp,pp,y,R_HIST)
        return self.x.copy()

class MHE:
    """Only measurements through the current sample enter the MAP window."""
    def __init__(self,x0):
        self.x=x0.copy();self.P=np.diag(P_HIST);self.ekf=EKF(x0)
        self.inputs=[];self.ys=[];self.dts=[];self.priors=[(x0.copy(),self.P.copy())]
        self.previous=None;self.fallbacks=0;self.budget_hits=0
    def update(self,u,y,dt):
        self.inputs.append(np.asarray(u).copy());self.ys.append(np.asarray(y).copy());self.dts.append(float(dt))
        self.ekf.update(u,y,dt)
        self.priors.append((self.ekf.x.copy(),self.ekf.P.copy()))
        n=min(5,len(self.inputs));prior,P=self.priors[-n-1]
        A=np.linalg.solve(np.linalg.cholesky(psd(P)),np.eye(6))
        us=np.asarray(self.inputs[-n:]);ys=np.asarray(self.ys[-n:]);dts=np.asarray(self.dts[-n:])
        pars=np.r_[prior,A.reshape(-1,order="F"),us.ravel(),ys.ravel(),dts]
        if self.previous is not None and len(self.previous)==n+1:
            warm=np.vstack([self.previous[1:],np.asarray(step_jac()(self.previous[-1],us[-1],dts[-1])[0]).ravel()])
        else:
            warm=[prior]
            for uu,dd in zip(us,dts):warm.append(np.asarray(step_jac()(warm[-1],uu,dd)[0]).ravel())
            warm=np.asarray(warm)
        lo=np.tile([0.,0.,0.,0.,250.,250.],n+1)
        hi=np.tile([np.inf,np.inf,np.inf,np.inf,400.,400.],n+1)
        z0=np.clip(warm.ravel(),lo+1e-10,hi-1e-10);graph=mhe_graph(n)
        memo=[None,None]
        def evaluate(z):
            if memo[0] is None or not np.array_equal(z,memo[0]):
                r,j=graph(z,pars);memo[:]=[z.copy(),(np.asarray(r).ravel(),np.asarray(j))]
            return memo[1]
        try:
            opt=least_squares(lambda z:evaluate(z)[0],z0,jac=lambda z:evaluate(z)[1],
                bounds=(lo,hi),x_scale=np.tile(SCALE,n+1),max_nfev=5,ftol=1e-6,xtol=1e-6,gtol=1e-6)
            self.budget_hits+=int(opt.status==0)
            if not np.all(np.isfinite(opt.x)) or not np.all(np.isfinite(opt.fun)):raise FloatingPointError("MHE nonfinite")
            self.previous=opt.x.reshape(n+1,6);self.x=self.previous[-1].copy()
            information=opt.jac.T@opt.jac+np.eye(len(opt.x))*1e-12
            covariance=np.linalg.pinv(information,hermitian=True)
            self.P=psd(covariance[-6:,-6:])
        except (ValueError,FloatingPointError,np.linalg.LinAlgError):
            self.fallbacks+=1;self.x=self.ekf.x.copy();self.P=self.ekf.P.copy();self.previous=None
        # Bounded history; retain sufficient arrival posterior.
        if len(self.inputs)>5:
            self.inputs=self.inputs[-5:];self.ys=self.ys[-5:];self.dts=self.dts[-5:];self.priors=self.priors[-6:]
        return self.x.copy()

def make_observer(method,x0):
    if method=="UKF_RK4":return OnlineUKF(NOMINAL,**observer_options(x0))
    if method=="EKF":return EKF(x0)
    if method=="GM_EKF":return EKF(x0,robust=True)
    if method=="MHE5":return MHE(x0)
    raise ValueError(method)

def noise_data(scenario,seed,condition):
    n=len(time_grid(scenario.hours))-1
    rng=np.random.default_rng(seed)
    inp=rng.normal(size=(int(scenario.hours/.1)+3,6))*INPUT_STD
    measurement=rng.normal(size=(n+1,2))*np.sqrt(R_HIST)
    generator=np.random.default_rng(seed+10000000)
    mask=generator.uniform(size=measurement.shape)<.05
    gross=generator.normal(size=measurement.shape)*np.sqrt(R_HIST)*np.sqrt(99.)
    if condition=="contaminated":measurement=measurement+mask*gross
    elif condition=="gaussian":mask=np.zeros_like(mask)
    else:raise ValueError(condition)
    digest=hashlib.sha256(inp.tobytes()+measurement.tobytes()+mask.tobytes()).hexdigest()
    return inp,measurement,mask,digest

def run_trial(scenario_key,method,thermal,seed,condition,save=True):
    s=BY_KEY[scenario_key];times=time_grid(s.hours);n=len(times)-1
    inp,noise,mask,digest=noise_data(s,seed,condition)
    x=initial_state(s);obs=make_observer(method,x)
    ctl=None if s.kind=="open" else ThesisNMPC(thermal)
    truth=np.empty((n+1,6));estimate=truth.copy();measurements=np.empty((n+1,2))
    truth[0]=x;estimate[0]=x;measurements[0]=x[4:6]+noise[0]
    controls=np.empty(n);latency=np.empty(n);solver_ok=np.ones(n,dtype=bool)
    solver_fallback=np.zeros(n,dtype=bool);solver_ms=np.zeros(n)
    references=np.array([commanded(s,t)[1] for t in times])
    peak=x[4];over=0.;dose=0.;start=time.perf_counter()
    for k in range(n):
        u,sp=commanded(s,times[k])
        if ctl:
            refs=np.array([commanded(s,times[k]+(j+1)*.015)[1] for j in range(57)])
            u[3],info=ctl.action(estimate[k],u,sp,NOMINAL,refs)
            solver_ok[k]=info["solver_success"];solver_fallback[k]=info["fallback"];solver_ms[k]=info["solver_ms"]
        controls[k]=u[3]
        x,pk,ov,ex,_=advance(x,s,times[k],times[k+1],u[3],inp)
        peak=max(peak,pk);over+=ov;dose+=ex
        measurements[k+1]=x[4:6]+noise[k+1]
        before=time.perf_counter()
        updated=obs.update(u,measurements[k+1],times[k+1]-times[k])
        estimate[k+1]=updated[0] if method=="UKF_RK4" else updated
        latency[k]=1000*(time.perf_counter()-before);truth[k+1]=x
        if not np.all(np.isfinite(estimate[k+1])) or not np.all(np.isfinite(x)):
            raise FloatingPointError("Nonfinite episode")
        if np.min(x[:4])<-1e-8 or np.min(estimate[k+1,:4])<-1e-8:
            raise FloatingPointError("Negative concentration")
    error=estimate-truth;tracking=truth[:,2]-references
    row=dict(scenario=scenario_key,method=method,thermal="open" if not ctl else ("soft" if thermal else "none"),
        seed=seed,noise=condition,pair_noise_sha256=digest,n_samples=n+1,contaminated_sensor_samples=int(mask.sum()),
        RMSE_est_CC=float(np.sqrt(np.mean(error[:,2]**2))),
        IAE_track_CC=float(np.trapezoid(np.abs(tracking),times)) if ctl else None,
        T_peak_K=float(peak),T_above_limit_h=float(over),thermal_excess_Kh=float(dose),
        observer_mean_ms=float(np.mean(latency)),observer_p95_ms=float(np.percentile(latency,95)),
        observer_max_ms=float(np.max(latency)),observer_fallbacks=int(getattr(obs,"fallbacks",0)),
        mhe_budget_hits=int(getattr(obs,"budget_hits",0)),solver_success_fraction=float(solver_ok.mean()),
        solver_fallbacks=int(solver_fallback.sum()),solver_mean_ms=float(solver_ms.mean()),
        seconds=float(time.perf_counter()-start))
    for j,name in enumerate(STATE_NAMES):row["RMSE_est_"+name]=float(np.sqrt(np.mean(error[:,j]**2)))
    if save:
        directory=OUT/"trajectories";directory.mkdir(parents=True,exist_ok=True)
        name=f"{scenario_key}_{row['thermal']}_{condition}_{method}_{seed}.npz"
        np.savez_compressed(directory/name,t=times,truth=truth,estimate=estimate,measurements=measurements,
            reference=references,mw=controls,observer_ms=latency,contamination_mask=mask,solver_ok=solver_ok)
        row["trajectory"]="trajectories/"+name
    return row

def task(args):
    try:return dict(ok=True,row=run_trial(*args))
    except Exception:return dict(ok=False,task=list(args),error=traceback.format_exc())

def summarize(rows,failures,tasks):
    groups=defaultdict(list);failed=defaultdict(int);scheduled=defaultdict(int)
    for sc,m,th,seed,no in tasks:scheduled[(sc,"open" if BY_KEY[sc].kind=="open" else ("soft" if th else "none"),no,m)]+=1
    for r in rows:groups[(r["scenario"],r["thermal"],r["noise"],r["method"])].append(r)
    for f in failures:
        sc,m,th,seed,no=f["task"];failed[(sc,"open" if BY_KEY[sc].kind=="open" else ("soft" if th else "none"),no,m)]+=1
    aggregate=[];paired=[];metrics=["RMSE_est_CC","IAE_track_CC","T_peak_K","T_above_limit_h","observer_mean_ms","observer_p95_ms","solver_success_fraction","observer_fallbacks","solver_fallbacks","mhe_budget_hits"]
    boot=np.random.default_rng(20261020)
    for key in sorted(scheduled):
        sc,th,no,m=key;data=groups[key]
        out=dict(scenario=sc,thermal=th,noise=no,method=m,scheduled=scheduled[key],completed=len(data),failed=failed[key])
        for metric in metrics:
            vals=[r[metric] for r in data if r.get(metric) is not None]
            out[metric]=float(np.mean(vals)) if vals else None
        aggregate.append(out)
        if m=="UKF_RK4":continue
        base={r["seed"]:r for r in groups[(sc,th,no,"UKF_RK4")]}
        for metric in ("RMSE_est_CC","IAE_track_CC","T_above_limit_h"):
            pairs=[(base[r["seed"]][metric],r[metric]) for r in data if r["seed"] in base and r.get(metric) is not None]
            if not pairs:continue
            pairs=np.array(pairs);delta=pairs[:,1]-pairs[:,0]
            sample=boot.choice(delta,size=(2000,len(delta)),replace=True).mean(axis=1)
            paired.append(dict(scenario=sc,thermal=th,noise=no,method=m,metric=metric,n_paired=len(delta),
                expected=scheduled[key],mean_delta=float(delta.mean()),CI95_lo=float(np.percentile(sample,2.5)),
                CI95_hi=float(np.percentile(sample,97.5)),baseline_mean=float(pairs[:,0].mean()),
                method_mean=float(pairs[:,1].mean())))
    write_csv(OUT/"summary.csv",aggregate);write_csv(OUT/"paired.csv",paired)
    result=dict(protocol=PROTOCOL,scheduled=len(tasks),completed=len(rows),failed=len(failures),groups=aggregate,paired=paired)
    write_json(OUT/"results.json",result)
    report=["# PG Estimator Benchmark v0.1 — resultados exploratórios",
        "",f"Episódios previstos: {len(tasks)}; concluídos: {len(rows)}; falhas: {len(failures)}.",
        "IAE só é apresentado para malha fechada. Unidade de CC: kmol/m³ (= mol/L); IAE: kmol h/m³.",
        "Térmico soft significa penalização QR=1000, não restrição rígida.",
        "Oito sementes por célula; IC bootstrap pareado exploratório. Tempos incluem execução no runner, não Windows.",
        "", "|Cenário|Térmico|Ruído|Método|n/falhas|RMSE CC|IAE CC|T pico K|T acima h|Obs ms|",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|"]
    def fmt(v):return "—" if v is None else f"{v:.6g}"
    for r in aggregate:report.append("|"+"|".join([r["scenario"],r["thermal"],r["noise"],r["method"],
        f"{r['completed']}/{r['failed']}"]+[fmt(r.get(k)) for k in ["RMSE_est_CC","IAE_track_CC","T_peak_K","T_above_limit_h","observer_mean_ms"]])+"|")
    report+=["","## Limitações","Simulação sintética com planta nominal, receitas conhecidas e covariâncias históricas.",
        "GM_EKF não reproduz o DDR-EKF publicado. MHE não herda automaticamente garantias teóricas de outro algoritmo.",
        "Não há sintonia posterior com os testes. Falhas e uso de fallback devem acompanhar qualquer ranking.",
        "As trajetórias reais dos métodos divergem em malha fechada; o ruído exógeno permanece pareado.",
        "Os valores médios de T pico não substituem o pior episódio; consulte metrics.csv.",
        "A rotina MHE possui limite de avaliações, que pode interromper a solução antes da convergência.",
        "Não foram testados sensores ausentes, erros de parâmetros da planta ou inventários iniciais incertos nesta campanha."]
    (OUT/"REPORT.md").write_text("\n".join(report)+"\n",encoding="utf-8")
    print(json.dumps(dict(scheduled=len(tasks),completed=len(rows),failed=len(failures),groups=aggregate),ensure_ascii=False),flush=True)
    return result

def plots(rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    keys=sorted({(r["scenario"],r["thermal"],r["noise"]) for r in rows})
    for sc,th,no in keys:
        candidates=[r for r in rows if (r["scenario"],r["thermal"],r["noise"])==(sc,th,no)]
        seed=min(r["seed"] for r in candidates)
        fig,ax=plt.subplots(3,1,figsize=(10,9),sharex=True)
        for r in candidates:
            if r["seed"]!=seed:continue
            a=np.load(OUT/r["trajectory"]);t=a["t"]
            ax[0].plot(t,a["truth"][:,2],label=r["method"]+" real")
            ax[1].plot(t,a["estimate"][:,2]-a["truth"][:,2],label=r["method"])
            ax[2].plot(t,a["truth"][:,4],label=r["method"])
        if th!="open":ax[0].plot(t,a["reference"],"k--",label="reference")
        ax[2].axhline(T_LIMIT,color="red",linestyle="--",label="160 F")
        ax[0].set_ylabel("CC [mol/L]");ax[1].set_ylabel("Estimation error [mol/L]");ax[2].set_ylabel("T [K]");ax[2].set_xlabel("Time [h]")
        for panel in ax:panel.grid(alpha=.25);panel.legend(fontsize=8,ncol=3)
        fig.suptitle(f"{sc} / {th} / {no} / seed {seed}");fig.tight_layout()
        fig.savefig(OUT/f"trajectory_{sc}_{th}_{no}.png",dpi=150);plt.close(fig)

def package():
    target=OUT/"PG_Estimator_Benchmark_v0.1.zip"
    repo=ROOT.parents[1]
    with zipfile.ZipFile(target,"w",zipfile.ZIP_DEFLATED) as z:
        for p in sorted(ROOT.rglob("*")):
            if p.is_file() and ".cache" not in p.parts and "__pycache__" not in p.parts and p!=target:
                z.write(p,p.relative_to(repo))
        for folder in ("darwin","vendor"):
            for p in sorted((LAB/folder).rglob("*.py")):
                if "__pycache__" not in p.parts:z.write(p,p.relative_to(repo))
        z.write(LAB/"requirements.txt",(LAB/"requirements.txt").relative_to(repo))
        for name in ("LICENSE","LICENSE_SCOPE.md","THIRD_PARTY_NOTICES.md"):
            z.write(repo/name,name)
    print("PACKAGE",target.name,target.stat().st_size,hashlib.sha256(target.read_bytes()).hexdigest(),flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--workers",type=int,default=2);ap.add_argument("--replicates",type=int,default=8);args=ap.parse_args()
    if args.replicates!=PROTOCOL["replicates"]:raise ValueError("Change and preregister protocol before changing test size.")
    OUT.mkdir(parents=True,exist_ok=True);write_json(OUT/"protocol.json",PROTOCOL);prepare()
    tasks=[]
    for i,sc in enumerate(PROTOCOL["scenarios"]):
        for th in ([False] if BY_KEY[sc].kind=="open" else [False,True]):
            for no in PROTOCOL["noises"]:
                for m in METHODS:
                    for j in range(args.replicates):tasks.append((sc,m,th,700000+i*1000+j,no))
    write_json(OUT/"scheduled_tasks.json",[list(t) for t in tasks])
    rows=[];failures=[];start=time.perf_counter()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures={pool.submit(task,t):t for t in tasks}
        for future in as_completed(futures):
            try:a=future.result()
            except Exception:a=dict(ok=False,task=list(futures[future]),error=traceback.format_exc())
            if a["ok"]:rows.append(a["row"])
            else:failures.append(a)
            done=len(rows)+len(failures)
            if done%8==0 or done==len(tasks):
                write_csv(OUT/"metrics.csv",rows);write_json(OUT/"failures.json",failures)
                print(f"PROGRESS {done}/{len(tasks)} failures={len(failures)} seconds={time.perf_counter()-start:.1f}",flush=True)
    rows.sort(key=lambda r:(r["scenario"],r["thermal"],r["noise"],r["method"],r["seed"]))
    write_csv(OUT/"metrics.csv",rows);write_json(OUT/"failures.json",failures)
    summarize(rows,failures,tasks);plots(rows)
    write_json(OUT/"runtime.json",dict(python=sys.version,platform=platform.platform(),numpy=np.__version__,scipy=scipy.__version__,
        casadi=ca.__version__,seconds=time.perf_counter()-start,workers=args.workers,commit=os.getenv("GITHUB_SHA")))
    package()
    if failures:raise SystemExit("Episodes failed; results and failures preserved. No silent exclusion.")

if __name__=="__main__":main()
