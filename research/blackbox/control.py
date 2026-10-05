"""SISO NMPC with physical OR fully learned dynamics and exact derivatives.

Same cost, move horizon and bounds for both; only the prediction function
changes. SLSQP replaces historical MATLAB fmincon/SQP. No hidden plant state.
"""
from time import perf_counter
import numpy as np
import casadi as ca
from scipy.optimize import minimize
from common import *
from native import NativeNeuralEvaluator

PREDICTION_STEPS=57;CONTROL_STEPS=6
_STEPS={};_EVALUATIONS={}

def build_step(kind,network=None):
    if kind in _STEPS:return _STEPS[kind]
    x=ca.SX.sym('x',6);u=ca.SX.sym('u',6)
    if kind=='physical':
        p=P_ADJUSTED;fa,fb,fm,mw,t0,ta=ca.vertsplit(u)
        v=fa/p.rhoA+fb/p.rhoB+fm/p.rhoM
        r=p.k0*ca.exp(-p.E/(p.R*x[4]))*x[0]
        duty=mw*p.cpB*(ta-x[4])*(1-ca.exp(-p.UA/(mw*p.cpB)))
        dc=(ca.vertcat(fa,fb,0,fm)-v*x[:4])/p.V+ca.vertcat(-r,-r,r,0)
        capacity=p.V*ca.dot(x[:4],ca.DM([p.cpA,p.cpB,p.cpC,p.cpM]))
        dT=(duty-(fa*p.cpA+fb*p.cpB+fm*p.cpM)*(x[4]-t0)-p.dH*r*p.V)/capacity
        dTt=(mw*p.cpB*(ta-x[5])-duty)/(p.rhoB*p.Vt*p.cpB)
        rhs=ca.Function('physical_rhs',[x,u],[ca.vertcat(dc,dT,dTt)])
        z=x
        for _ in range(5):
            h=DT/5;a=rhs(z,u);b=rhs(z+h*a/2,u);c=rhs(z+h*b/2,u);d=rhs(z+h*c,u)
            z=z+h*(a+2*b+2*c+d)/6
    elif kind=='neural':
        n=network or NeuralTransition.load()
        f=ca.vertcat((x-ca.DM(BASE))/ca.DM(XS),(u-ca.DM(U_BASE))/ca.DM(US))
        affine=ca.DM(n.affine.T)@ca.vertcat(f,1.)
        a=(f-ca.DM(n.mean))/ca.DM(n.scale)
        for i,(w,b) in enumerate(zip(n.w,n.b)):
            a=ca.DM(w.T)@a+ca.DM(b)
            if i<len(n.w)-1:a=ca.tanh(a)
        zn=x+(affine+a*ca.DM(n.ys)+ca.DM(n.ym)-ca.DM(n.offset))*ca.DM(XS)
        sub=ca.Function('learned_substep',[x,u],[zn])
        # Keep substeps as MX calls to one shared kernel. SX expansion would
        # duplicate the network and its derivatives in generated C five times.
        x=ca.MX.sym('x',6);u=ca.MX.sym('u',6);z=x
        for _ in range(n.substeps):z=sub(z,u)
    else:raise ValueError(kind)
    step=ca.Function(kind+'_step',[x,u],[z])
    _STEPS[kind]=step
    return step

class CompiledTransition:
    def __init__(self,step):self.step=step;self.maps={}
    def __call__(self,x,u,p=None):
        x=np.asarray(x)
        if x.ndim==1:return np.asarray(self.step(x,u)).ravel()
        n=len(x)
        if n not in self.maps:self.maps[n]=self.step.map(n)
        return np.asarray(self.maps[n](x.T,np.tile(np.asarray(u)[:,None],(1,n)))).T

class BlackBoxNAKE(UKF):
    """Neural state predictor + unscented/Joseph correction + causal adaptive Q.

    Q includes a fixed validation residual variance. Only PREVIOUS innovations
    can inflate it. This is our research variant, not a KalmanNet reproduction.
    No neural gain is trained; temperature observation h(x) remains known.
    """
    def __init__(self,x0,model,network):
        self.base_q=Q_COMMON+network.q_model
        self.innovation_energy=1.;self.factor=1.
        super().__init__(x0,q=self.base_q,r=R_HISTORICAL,transition_model=model)
    def update(self,u,y):
        self.q0=self.base_q*self.factor
        result=super().update(u,y)
        nis,dof=result[2:]
        if dof:
            self.innovation_energy=.95*self.innovation_energy+.05*min(nis/dof,50.)
        self.factor=float(np.clip(self.innovation_energy,1.,25.))
        return result

class NMPC:
    def __init__(self,step,constrained=False,margin=0.,network=None):
        self.constrained=constrained;self.margin=margin;self.previous=1.;self.warm=np.ones(CONTROL_STEPS)
        self.bounds=[(MW_MIN/U_BASE[3],MW_MAX/U_BASE[3])]*CONTROL_STEPS
        if network is not None:
            self.evaluate=NativeNeuralEvaluator(network,margin);return
        key=(step.name(),margin)
        if key in _EVALUATIONS:
            self.evaluate=_EVALUATIONS[key];return
        q=ca.MX.sym('q',CONTROL_STEPS);theta=ca.MX.sym('theta',14)
        # theta: estimated states, known commanded inputs, current CC target, previous mw/mw0.
        sx=ca.MX.sym('sx',6);su=ca.MX.sym('su',6);sz=step(sx,su)
        local=ca.Function('local_sensitivities',[sx,su],[sz,ca.jacobian(sz,sx),ca.jacobian(sz,su)[:,3]])
        # Propagate only the six decision sensitivities, rather than building
        # a horizon Jacobian against all 342 exogenous input entries.
        state=theta[:6];sens=ca.MX.zeros(6,CONTROL_STEPS)
        obj=0.;gradient=ca.MX.zeros(CONTROL_STEPS,1);cons=[];jacrows=[]
        for k in range(PREDICTION_STEPS):
            j=min(k,CONTROL_STEPS-1);u=theta[6:12]
            command=ca.vertcat(u[:3],q[j]*U_BASE[3],u[4:])
            state,a,b=local(state,command)
            sens=a@sens+b@ca.DM(np.eye(CONTROL_STEPS)[j:j+1])*U_BASE[3]
            error=(state[2]-theta[12])/theta[12]
            obj+=.8*error**2;gradient+=1.6*error*sens[2,:].T/theta[12]
            cons.append((T_LIMIT-margin-state[4])/10.);jacrows.append(-sens[4,:]/10.)
        du=ca.vertcat(q[0]-theta[13],q[1:]-q[:-1])
        obj+=.2*ca.sumsqr(du);gradient+=ca.gradient(.2*ca.sumsqr(du),q)
        con=ca.vertcat(*cons);jacobian=ca.vertcat(*jacrows)
        # JIT compiles the full rollout and derivative calls, avoiding Python finite differences.
        self.evaluate=ca.Function('nmpc_eval',[q,theta],[obj,gradient,con,jacobian],
                {'jit':True,'jit_options':{'flags':'-O3'}})
        _EVALUATIONS[key]=self.evaluate

    def step(self,x,u,reference):
        theta=np.r_[x,u,reference,self.previous];cache={}
        def calc(q):
            if 'q' not in cache or not np.array_equal(cache['q'],q):
                cache.update(q=q.copy(),v=[np.asarray(v) for v in self.evaluate(q,theta)])
            return cache['v']
        start=perf_counter();guess=np.r_[self.warm[1:],self.warm[-1]]
        constraints=[]
        if self.constrained:
            constraints=[dict(type='ineq',fun=lambda q:calc(q)[2].ravel(),jac=lambda q:calc(q)[3])]
        sol=minimize(lambda q:float(calc(q)[0].item()),guess,jac=lambda q:calc(q)[1].ravel(),
          method='SLSQP',bounds=self.bounds,constraints=constraints,
          options={'maxiter':60,'ftol':1e-8,'disp':False})
        v=calc(sol.x);feasible=(not self.constrained or float(v[2].min())>=-1e-6)
        finite=bool(np.isfinite(sol.fun) and np.all(np.isfinite(sol.x)) and np.all(np.isfinite(v[2])))
        fallback=not(finite and feasible)
        if fallback:
            # Identical transparent policy in both models; no physics substitute for neural prediction.
            candidate=np.full(CONTROL_STEPS,MW_MAX/U_BASE[3] if self.constrained else self.previous)
            cv=calc(candidate);self.warm=candidate
            predicted_Tmax=T_LIMIT-self.margin-10.*float(cv[2].min())
        else:
            self.warm=sol.x.copy();predicted_Tmax=T_LIMIT-self.margin-10.*float(v[2].min())
        self.previous=float(self.warm[0]);duration=perf_counter()-start
        return self.previous*U_BASE[3],dict(solver_success=bool(sol.success),solver_status=int(sol.status),
            solver_feasible=bool(feasible),fallback=fallback,iterations=int(sol.nit),
            predicted_Tmax=float(predicted_Tmax),latency_ms=1000*duration)

class NeuralEvaluator:
    """Identical NMPC problem with exact analytic NumPy neural sensitivities."""
    def __init__(self,network,margin):self.network=network;self.margin=margin
    def __call__(self,q,theta):
        state=theta[:6].copy();u=theta[6:12].copy();reference=theta[12]
        sens=np.zeros((6,CONTROL_STEPS));cost=0.;gradient=np.zeros(CONTROL_STEPS);cons=[];jac=[]
        for i in range(PREDICTION_STEPS):
            j=min(i,CONTROL_STEPS-1);u[3]=q[j]*U_BASE[3]
            state,a,b=self.network.step_with_sensitivities(state,u)
            sens=a@sens;sens[:,j]+=b*U_BASE[3]
            error=(state[2]-reference)/reference;cost+=.8*error**2
            gradient+=1.6*error*sens[2]/reference
            cons.append((T_LIMIT-self.margin-state[4])/10.);jac.append(-sens[4].copy()/10.)
        du=np.diff(np.r_[theta[13],q]);cost+=.2*np.sum(du**2)
        gradient+=.4*du;gradient[:-1]-=.4*du[1:]
        return [np.asarray(cost),gradient[:,None],np.asarray(cons)[:,None],np.asarray(jac)]
