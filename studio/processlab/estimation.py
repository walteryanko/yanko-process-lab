"""EKF/UKF and bounded-window deterministic MHE; delayed events replay from collection time.

No method accepts the simulator's physical state. Covariances are approximations,
not calibrated confidence or safety certificates.
"""
import numpy as np
from scipy.optimize import least_squares
from .numerics import jacobian, covariance, integrate


class Observer:
    def __init__(self, model, config):
        self.model, self.c = model, config
        self.x = model.x0.copy()
        # Initial prior is defined solely by the project, not a copy of the perturbed truth.
        self.x += config["initial_estimate_offset"]*model.scale
        self.P = np.diag((model.scale*.2)**2)
        self.Q = np.diag((model.scale*.002)**2)*config["q_scale"]
        self.priors = [(self.x.copy(),self.P.copy())]; self.posts = []
        self.inputs = []; self.events = {}; self.innovations = []
        self.event_ids = set()
        self.diagnostics = {"replayed_steps":0,"mhe_nonconvergence":0,"mhe_fallbacks":0,"covariance_condition":0.}

    def transition(self, x, u, d):
        return integrate(self.model,x,u,d,self.c["dt"],self.c)

    def sigma(self,x,P):
        n = len(x); alpha=.5; lam=alpha**2*n-n
        s = np.linalg.cholesky(covariance(P)*(n+lam))
        points=np.vstack([x,x+s.T,x-s.T]); wm=np.full(2*n+1,1/(2*(n+lam)));wc=wm.copy()
        wm[0]=lam/(n+lam);wc[0]=wm[0]+(1-alpha**2+2)
        return points,wm,wc

    def predict(self,x,P,u,d):
        f=lambda z:self.transition(z,u,d)
        if self.c["observer"] == "ukf":
            pts,wm,wc=self.sigma(x,P); values=np.array([f(z) for z in pts]); mean=wm@values
            diff=values-mean; return mean,covariance((diff.T*wc)@diff+self.Q)
        F=jacobian(f,x);return f(x),covariance(F@P@F.T+self.Q)

    def measurement(self,x,event):
        return x[self.model.measurement_indices] if event["kind"] == "thermal" else np.array([self.model.quality(x)])

    def update(self,x,P,event):
        h=lambda z:self.measurement(z,event); y=np.asarray(event["values"])
        R=np.diag(event["variance"])*self.c["r_scale"]
        if self.c["observer"] == "ukf":
            pts,wm,wc=self.sigma(x,P); ypts=np.array([h(z) for z in pts]); yp=wm@ypts
            dy=ypts-yp;S=(dy.T*wc)@dy+R;cross=((pts-x).T*wc)@dy
            K=np.linalg.solve(S,cross.T).T;Pn=P-K@S@K.T
        else:
            H=jacobian(h,x);yp=h(x);S=H@P@H.T+R;K=np.linalg.solve(S,H@P).T
            A=np.eye(len(x))-K@H;Pn=A@P@A.T+K@R@K.T
        innovation=y-yp
        self.innovations.append({"sample":event["sample"],"arrival":event["arrival"],"kind":event["kind"],"nis":float(innovation@np.linalg.solve(S,innovation)),"innovation":innovation.tolist()})
        xn=x+K@innovation
        self.model.check(xn)
        return xn,covariance(Pn)

    def advance(self,u,d):
        self.inputs.append((float(u),float(d)))
        self.x,self.P=self.predict(self.x,self.P,u,d)
        self.priors.append((self.x.copy(),self.P.copy()))

    def assimilate(self,step,arrivals):
        if len(self.posts) <= step:
            self.posts.append((self.x.copy(),self.P.copy()))
        accepted=[]
        for e in arrivals:
            if e["arrival"] > step or e["sample"] > step:
                raise ValueError("Future measurement rejected")
            event_id=e.get("id",f"{e['kind']}-{e['sample']}")
            if event_id in self.event_ids:continue
            self.event_ids.add(event_id);accepted.append(e)
            self.events.setdefault(e["sample"],[]).append(e)
        start=min((e["sample"] for e in accepted),default=step)
        x,P=(v.copy() for v in self.priors[start])
        self.innovations=[]
        for k in range(start,step+1):
            if k>start:
                x,P=self.predict(x,P,*self.inputs[k-1]);self.priors[k]=(x.copy(),P.copy())
            for event in sorted(self.events.get(k,[]),key=lambda e:(e["kind"],e["arrival"])):
                x,P=self.update(x,P,event)
            self.posts[k]=(x.copy(),P.copy())
        self.x,self.P=x,P;self.diagnostics["replayed_steps"]+=step-start
        if self.c["observer"] == "mhe" and step > 0:
            self._mhe(step)
        self.diagnostics["covariance_condition"]=float(np.linalg.cond(self.P))

    def _mhe(self,step):
        # Single-shooting, constant parameters, no process noise decision variables.
        first=max(0,step-5);prior,P=self.priors[first];L=np.linalg.cholesky(covariance(P));scale=self.model.scale
        def residual(z,ret_state=False):
            x=prior+z*scale;rs=[np.linalg.solve(L,x-prior)]
            for k in range(first,step+1):
                if k>first:x=self.transition(x,*self.inputs[k-1])
                for e in self.events.get(k,[]):
                    rs.append((self.measurement(x,e)-e["values"])/np.sqrt(np.array(e["variance"])*self.c["r_scale"]))
            return x if ret_state else np.concatenate(rs)
        try:
            sol=least_squares(residual,np.zeros(len(prior)),max_nfev=12,ftol=1e-5,xtol=1e-5,gtol=1e-5)
            candidate=residual(sol.x,True);self.model.check(candidate)
            if not sol.success:self.diagnostics["mhe_nonconvergence"]+=1
            if np.sum(sol.fun**2) <= np.sum(residual(np.zeros(len(prior)))**2):
                self.x=candidate
                # Covariance remains the EKF arrival companion, explicitly marked.
                self.posts[step]=(self.x.copy(),self.P.copy())
        except (ValueError,np.linalg.LinAlgError,FloatingPointError):
            self.diagnostics["mhe_fallbacks"]+=1

    def observability(self,u,d=0):
        n=len(self.x);A=jacobian(lambda z:self.transition(z,u,d),self.x)
        H=np.eye(n)[self.model.measurement_indices];rows=[];power=np.eye(n)
        for _ in range(n):rows.append(H@power);power=power@A
        O=np.vstack(rows)*self.model.scale
        sv=np.linalg.svd(O,compute_uv=False);tol=max(O.shape)*sv[0]*1e-8
        return {"singular_values":sv.tolist(),"rank":int(np.sum(sv>tol)),"states":n,"threshold":float(tol),"scope":"Local thermal linearization, scaled state, numerical rank; not global observability"}
