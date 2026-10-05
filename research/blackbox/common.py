"""Shared protocol. All neural inference is independent of the physical RHS."""
from pathlib import Path
import sys,json
import numpy as np

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'nake'))
from estimator import BASE,U_BASE,XS,US,DT,P_ADJUSTED,Q_PUBLISHED,UKF,transition,rhs6

WEIGHTS=ROOT/'weights';RESULTS=ROOT/'results'
R_HISTORICAL=np.diag((.01*BASE[4:])**2)
Q_COMMON=Q_PUBLISHED*np.array([1,1,1,1,4,4])
MW_MIN=22.7;MW_MAX=1366.2;T_LIMIT=344.;T_STOP=355.4
STATE_NAMES=['CA','CB','CC','CM','T','Tt']

def dump(path,obj):
    def default(v):
        if isinstance(v,np.ndarray):return v.tolist()
        if isinstance(v,np.generic):return v.item()
        raise TypeError(type(v).__name__)
    Path(path).write_text(json.dumps(obj,indent=2,ensure_ascii=False,default=default,allow_nan=False)+'\n')

def cold_state():
    # Filled feed mixture; no product initially. Not specified numerically in source.
    p=P_ADJUSTED;v=U_BASE[0]/p.rhoA+U_BASE[1]/p.rhoB+U_BASE[2]/p.rhoM
    return np.r_[U_BASE[:3][[0,1]]/v,0.,U_BASE[2]/v,U_BASE[4],U_BASE[5]]

class NeuralTransition:
    """12 -> hidden layers -> 6 increments; identity skip, no balance residual.

    The equilibrium offset is learned from the nominal training datum, and
    subtracted in every implementation (NumPy and CasADi). This anchors one
    point without supplying reaction/heat-transfer formulas to the model.
    """
    def __init__(self,data):
        self.data=data
        self.mean=np.asarray(data['mean']);self.scale=np.asarray(data['scale'])
        self.ym=np.asarray(data['target_mean']);self.ys=np.asarray(data['target_scale'])
        self.w=[np.asarray(w) for w in data['weights']]
        self.b=[np.asarray(b) for b in data['biases']]
        self.offset=np.asarray(data['equilibrium_offset'])
        self.q_model=np.asarray(data['validation_error_variance'])
        self.affine=np.asarray(data.get('affine_weights',np.zeros((13,6))))
        self.substeps=int(data.get('substeps',1))
    @classmethod
    def load(cls,path=WEIGHTS/'transition_mlp.json'):return cls(json.loads(Path(path).read_text()))
    def increments(self,x,u):
        x=np.asarray(x);u=np.broadcast_to(u,x.shape)
        f=np.concatenate([(x-BASE)/XS,(u-U_BASE)/US],axis=-1)
        affine=np.concatenate([f,np.ones((*f.shape[:-1],1))],axis=-1)@self.affine
        a=(f-self.mean)/self.scale
        for i,(w,b) in enumerate(zip(self.w,self.b)):
            a=a@w+b
            if i<len(self.w)-1:a=np.tanh(a)
        return affine+a*self.ys+self.ym-self.offset
    def __call__(self,x,u,p=None):
        z=np.array(x,dtype=float,copy=True)
        for _ in range(self.substeps):z=z+self.increments(z,u)*XS
        return z
    def step_with_sensitivities(self,x,u):
        """Exact MLP chain rule for six state directions and the coolant input.

        Small dense matrix products avoid computing derivatives for exogenous
        inputs that are held fixed inside this SISO optimization.
        """
        z=np.asarray(x).copy();a_total=np.eye(6);b_total=np.zeros(6)
        affine_j=np.c_[self.affine[:6].T/XS,self.affine[9]/US[3]]
        for _ in range(self.substeps):
            f=np.r_[(z-BASE)/XS,(u-U_BASE)/US]
            value=(f-self.mean)/self.scale
            jac=np.zeros((12,7));jac[np.arange(6),np.arange(6)]=1/(XS*self.scale[:6])
            jac[9,6]=1/(US[3]*self.scale[9])
            for i,(w,b) in enumerate(zip(self.w,self.b)):
                value=value@w+b;jac=w.T@jac
                if i<len(self.w)-1:
                    value=np.tanh(value);jac*=1-value[:,None]**2
            increment=np.r_[f,1.]@self.affine+value*self.ys+self.ym-self.offset
            derivative=(affine_j+jac*self.ys[:,None])*XS[:,None]
            a=np.eye(6)+derivative[:,:6];b=derivative[:,6]
            z=z+increment*XS;a_total=a@a_total;b_total=a@b_total+b
        return z,a_total,b_total
