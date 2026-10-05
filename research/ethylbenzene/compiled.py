"""CasADi-generated native kernels; no chemical RHS in neural kernels.

Both controller prediction and estimator transitions use exact derivatives
of their own model. Compile once; processes then share the local .so cache.
"""
import ctypes, hashlib, json, os, subprocess
from pathlib import Path
import numpy as np
import casadi as ca
from model import *
from networks import NeuralTransition

HORIZON=40; MOVES=4; BLOCK=5

def symbolic_steps(net):
    x=ca.SX.sym('x',5);u=ca.SX.sym('u',7);f=u[:3];total=ca.sum1(f)
    inflow=ca.vertcat(f[0]*RHO[0]+f[2]*REC[0],f[1]*RHO[1]+f[2]*REC[1],f[2]*REC[2],0)
    k=ca.DM(K0*3600)*ca.exp(-ca.DM(E)/(RGAS*(x[4]+273.15)))
    rr=k*ca.vertcat(x[0]*x[1],x[0]*x[2],x[1]*x[3])
    dc=(inflow-total*x[:4])/V+ca.DM(NU)@rr
    heat=ca.dot(f*ca.DM(RHO*CP),u[4:7])-total*RHO_REACTOR*CP_REACTOR*x[4]-V*ca.dot(rr,ca.DM(DH))-u[3]
    fun=ca.Function('chemical_rhs',[x,u],[ca.vertcat(dc,heat/CAPACITY)])
    z=x;h=DT/SUBSTEPS
    for _ in range(SUBSTEPS):
        a=fun(z,u);b=fun(z+h*a/2,u);c=fun(z+h*b/2,u);d=fun(z+h*c,u);z+=h*(a+2*b+2*c+d)/6
    physical=ca.Function('physical',[x,u],[z])
    feat=ca.vertcat((x-ca.DM(BASE))/ca.DM(XS),(u-ca.DM(U0))/ca.DM(US))
    a=(feat-ca.DM(net.mean))/ca.DM(net.scale)
    for i,(w,b) in enumerate(zip(net.w,net.b)):
        a=ca.DM(w.T)@a+ca.DM(b)
        if i<len(net.w)-1:a=ca.tanh(a)
    inc=ca.DM(net.affine.T)@ca.vertcat(feat,1)+a*ca.DM(net.ys)+ca.DM(net.ym-net.offset)
    sub=ca.Function('neural_substep',[x,u],[x+inc*ca.DM(XS)])
    xm=ca.MX.sym('x',5);um=ca.MX.sym('u',7);zm=xm
    for _ in range(SUBSTEPS):zm=sub(zm,um)
    neural=ca.Function('neural',[xm,um],[zm])
    return dict(physical=physical,neural=neural)

def evaluator(step,mode,constrained):
    nmv=1 if mode=='siso' else 2;nd=MOVES*nmv
    q=ca.MX.sym('q',nd);theta=ca.MX.sym('theta',16)
    a=ca.MX.sym('a',5);b=ca.MX.sym('b',7);nextx=step(a,b)
    jac=ca.jacobian(nextx,b)
    local=ca.Function(step.name()+'_sens',[a,b],[nextx,ca.jacobian(nextx,a),jac[:,[0,3]]])
    state=theta[:5];sens=ca.MX.zeros(5,nd);cost=0;grad=ca.MX.zeros(nd,1);cons=[];cj=[]
    unit=np.eye(nd)
    for k in range(HORIZON):
        j=min(k//BLOCK,MOVES-1);qe=q[j*nmv];qq=1. if nmv==1 else q[j*nmv+1]
        cmd=ca.vertcat(qe*F0[0],theta[6:8],qq*Q0,theta[9:12])
        state,aa,bb=local(state,cmd)
        sens=aa@sens+bb[:,0]@ca.DM(unit[j*nmv:j*nmv+1])*F0[0]
        if nmv==2:sens+=bb[:,1]@ca.DM(unit[j*nmv+1:j*nmv+2])*Q0
        total=ca.sum1(state[:4]);xe=state[2]/total;ex=(xe-theta[12])/.02
        dx=(sens[2,:]*total-state[2]*ca.sum1(sens[:4,:]))/(total*total)
        cost+=.8*ex**2;grad+=1.6*ex*dx.T/.02
        if nmv==2:
            et=(state[4]-theta[13])/5.;cost+=.2*et**2;grad+=.4*et*sens[4,:].T/5.
        if constrained:
            cons.append((T_LIMIT-state[4])/5.);cj.append(-sens[4,:]/5.)
    # Per-move increments include the previous physically issued command.
    moves=ca.reshape(q,nmv,MOVES)
    previous=theta[14:14+nmv];du=ca.horzcat(moves[:,0]-previous,moves[:,1:]-moves[:,:-1])
    penalty=.03*ca.sumsqr(du);cost+=penalty;grad+=ca.gradient(penalty,q)
    # Bound the changes, including the first executed move. Emergency fallback is logged separately.
    lim=ca.DM([.12] if nmv==1 else [.12,.08])
    for j in range(MOVES):
        cons.extend([lim-du[:,j],lim+du[:,j]])
        cj.extend([ca.jacobian(lim-du[:,j],q),ca.jacobian(lim+du[:,j],q)])
    return ca.Function(f'eval_{step.name()}_{mode}_{int(constrained)}',[q,theta],
                       [cost,ca.densify(grad),ca.vertcat(*cons),ca.densify(ca.vertcat(*cj))])

def compile_models():
    net=NeuralTransition.load();version='eb-v3-h40-m4-block5'
    sig=hashlib.sha256((json.dumps(net.data,sort_keys=True)+version+json.dumps(calibration_audit(),default=lambda v:v.tolist() if isinstance(v,np.ndarray) else v)).encode()).hexdigest()[:16]
    folder=NATIVE/sig;lib=folder/'kernels.so'
    if not lib.exists():
        folder.mkdir(parents=True,exist_ok=True);steps=symbolic_steps(net)
        old=Path.cwd();os.chdir(folder)
        try:
            gen=ca.CodeGenerator('kernels.c',{'with_header':True})
            for kind,step in steps.items():
                gen.add(step)
                x=ca.MX.sym('x',5,11);u=ca.MX.sym('u',7)
                gen.add(ca.Function(kind+'_batch',[x,u],[step.map(11)(x,ca.repmat(u,1,11))]))
                for mode in ['siso','mimo']:
                    for constrained in [False,True]:gen.add(evaluator(step,mode,constrained))
            gen.generate()
            subprocess.run(['cc','-O3','-fPIC','-shared','kernels.c','-lm','-o','kernels.so'],check=True,capture_output=True)
            dump(folder/'manifest.json',dict(casadi_version=ca.__version__,signature=sig,source_version=version))
        finally:os.chdir(old)
    return lib

class NativeFunction:
    def __init__(self,lib,name,input_shapes,output_shapes):
        self.lib=lib;self.fun=getattr(lib,name);self.fun.restype=ctypes.c_int
        ptr=ctypes.POINTER(ctypes.c_double);iptr=ctypes.POINTER(ctypes.c_longlong)
        self.fun.argtypes=[ctypes.POINTER(ptr),ctypes.POINTER(ptr),iptr,ptr,ctypes.c_int]
        work=getattr(lib,name+'_work');work.argtypes=[iptr,iptr,iptr,iptr]
        sizes=[ctypes.c_longlong() for _ in range(4)];work(*[ctypes.byref(x) for x in sizes])
        self.iw=np.zeros(max(sizes[2].value,1),dtype=np.int64);self.w=np.zeros(max(sizes[3].value,1))
        self.narg=max(sizes[0].value,len(input_shapes));self.nres=max(sizes[1].value,len(output_shapes));self.ptr=ptr
        self.ins=input_shapes;self.outs=[np.zeros(s,order='F') for s in output_shapes]
        self.res=(ptr*self.nres)(*[z.ctypes.data_as(ptr) for z in self.outs])
    def __call__(self,*args):
        aa=[np.array(a,dtype=float,order='F',copy=True).reshape(s,order='F') for a,s in zip(args,self.ins)]
        arg=(self.ptr*self.narg)(*[z.ctypes.data_as(self.ptr) for z in aa])
        rc=self.fun(arg,self.res,self.iw.ctypes.data_as(ctypes.POINTER(ctypes.c_longlong)),self.w.ctypes.data_as(self.ptr),0)
        if rc:raise RuntimeError(f'native kernel status {rc}')
        return [z.copy() for z in self.outs]

class Models:
    def __init__(self,libpath=None,fast_neural=True):
        self.lib=ctypes.CDLL(str(libpath or compile_models()));self.steps={};self.batches={};self.evaluators={}
        for kind in ['physical','neural']:
            self.steps[kind]=NativeFunction(self.lib,kind,[(5,),(7,)],[(5,)])
            self.batches[kind]=NativeFunction(self.lib,kind+'_batch',[(5,11),(7,)],[(5,11)])
            for mode in ['siso','mimo']:
                nmv=1 if mode=='siso' else 2;nd=nmv*MOVES
                for con in [False,True]:
                    nc=2*nd+(HORIZON if con else 0)
                    self.evaluators[kind,mode,con]=NativeFunction(self.lib,f'eval_{kind}_{mode}_{int(con)}',[(nd,),(16,)],[(1,),(nd,),(nc,),(nc,nd)])
        if fast_neural:
            from native_neural import NativeNeuralEvaluator
            net=NeuralTransition.load()
            for mode in ['siso','mimo']:
                for con in [False,True]:self.evaluators['neural',mode,con]=NativeNeuralEvaluator(net,mode,con)
    def transition(self,kind,x,u):
        x=np.asarray(x)
        if x.ndim==1:return self.steps[kind](x,u)[0]
        return self.batches[kind](x.T,u)[0].T

if __name__=='__main__':print(compile_models())
