"""Compile the learned MLP chain rule and six-decision rollout to a C kernel.

Only learned constants and generic network/chain-rule operations are embedded.
No chemical balances are available to this kernel. The NumPy evaluator remains
an independent reference, and tests compare values and derivatives with it.
"""
import ctypes,hashlib,subprocess,tempfile
from pathlib import Path
import numpy as np
from common import BASE,U_BASE,XS,US

_CACHE={}
KERNEL=r'''
static void substep(const double *x,const double *u,double *out,double der[6][7]) {
 double f[12],a[WIDTH],an[WIDTH],d[WIDTH][7]={{0}},dn[WIDTH][7];
 for(int j=0;j<6;j++){f[j]=(x[j]-BASE[j])/XS[j];f[j+6]=(u[j]-UBASE[j])/US[j];}
 for(int j=0;j<12;j++)a[j]=(f[j]-MEAN[j])/SCALE[j];
 for(int j=0;j<6;j++)d[j][j]=1/(XS[j]*SCALE[j]);
 d[9][6]=1/(US[3]*SCALE[9]);
 for(int l=0;l<LAYERS;l++){
  int ni=DIMS[l],no=DIMS[l+1];
  for(int i=0;i<no;i++){
   an[i]=BIASES[l][i];for(int s=0;s<7;s++)dn[i][s]=0;
   for(int j=0;j<ni;j++){
    double w=WEIGHTS[l][j*no+i];an[i]+=w*a[j];
    for(int s=0;s<7;s++)dn[i][s]+=w*d[j][s];
   }
   if(l<LAYERS-1){an[i]=tanh(an[i]);double v=1-an[i]*an[i];for(int s=0;s<7;s++)dn[i][s]*=v;}
  }
  for(int i=0;i<no;i++){a[i]=an[i];for(int s=0;s<7;s++)d[i][s]=dn[i][s];}
 }
 for(int i=0;i<6;i++){
  double inc=AFFINE[12*6+i]+a[i]*YS[i]+YM[i]-OFFSET[i];
  for(int j=0;j<12;j++)inc+=f[j]*AFFINE[j*6+i];out[i]=x[i]+XS[i]*inc;
  for(int s=0;s<7;s++){
   double v=s<6?AFFINE[s*6+i]/XS[s]:AFFINE[9*6+i]/US[3];
   der[i][s]=XS[i]*(v+d[i][s]*YS[i])+(s==i?1:0);
  }
 }
}
static void step(const double *x,const double *u,double *out,double a[6][6],double *b){
 double z[6],next[6],d[6][7],na[6][6],nb[6];
 for(int i=0;i<6;i++){z[i]=x[i];b[i]=0;for(int j=0;j<6;j++)a[i][j]=(i==j);}
 for(int k=0;k<SUBSTEPS;k++){
  substep(z,u,next,d);
  for(int i=0;i<6;i++){
   nb[i]=d[i][6];for(int m=0;m<6;m++)nb[i]+=d[i][m]*b[m];
   for(int j=0;j<6;j++){na[i][j]=0;for(int m=0;m<6;m++)na[i][j]+=d[i][m]*a[m][j];}
  }
  for(int i=0;i<6;i++){z[i]=next[i];b[i]=nb[i];for(int j=0;j<6;j++)a[i][j]=na[i][j];}
 }
 for(int i=0;i<6;i++)out[i]=z[i];
}
void evaluate(const double *q,const double *theta,double margin,double *cost,double *grad,double *con,double *jac){
 double x[6],u[6],next[6],a[6][6],b[6],s[6][6]={{0}},sn[6][6];
 for(int i=0;i<6;i++){x[i]=theta[i];u[i]=theta[i+6];grad[i]=0;}*cost=0;
 for(int k=0;k<57;k++){
  int j=k<6?k:5;u[3]=q[j]*UBASE[3];step(x,u,next,a,b);
  for(int i=0;i<6;i++)for(int c=0;c<6;c++){
   sn[i][c]=c==j?b[i]*UBASE[3]:0;for(int m=0;m<6;m++)sn[i][c]+=a[i][m]*s[m][c];
  }
  double error=(next[2]-theta[12])/theta[12];*cost+=.8*error*error;
  for(int c=0;c<6;c++){grad[c]+=1.6*error*sn[2][c]/theta[12];jac[k*6+c]=-sn[4][c]/10.;}
  con[k]=(344.-margin-next[4])/10.;
  for(int i=0;i<6;i++){x[i]=next[i];for(int c=0;c<6;c++)s[i][c]=sn[i][c];}
 }
 for(int i=0;i<6;i++){
  double du=q[i]-(i?q[i-1]:theta[13]);*cost+=.2*du*du;grad[i]+=.4*du;
  if(i)grad[i-1]-=.4*du;
 }
}
'''

def compile_kernel(network):
    n=network
    def array(name,values):
        a=np.asarray(values).ravel()
        return 'static const double '+name+'[]={' + ','.join(format(v,'.17g') for v in a)+'};\n'
    text='#include <math.h>\n'
    dims=[n.w[0].shape[0]]+[w.shape[1] for w in n.w]
    text+=f'#define WIDTH {max(dims)}\n#define LAYERS {len(n.w)}\n#define SUBSTEPS {n.substeps}\n'
    text+='static const int DIMS[]={'+','.join(str(v) for v in dims)+'};\n'
    for name,values in [('BASE',BASE),('UBASE',U_BASE),('XS',XS),('US',US),('MEAN',n.mean),('SCALE',n.scale),
          ('YS',n.ys),('YM',n.ym),('OFFSET',n.offset),('AFFINE',n.affine)]:text+=array(name,values)
    for i,(w,b) in enumerate(zip(n.w,n.b)):text+=array(f'W{i}',w)+array(f'B{i}',b)
    text+='static const double *WEIGHTS[]={'+','.join(f'W{i}' for i in range(len(n.w)))+'};\n'
    text+='static const double *BIASES[]={'+','.join(f'B{i}' for i in range(len(n.b)))+'};\n'
    text+=KERNEL;key=hashlib.sha256(text.encode()).hexdigest()
    if key not in _CACHE:
        tmp=tempfile.TemporaryDirectory(prefix='cstr_neural_');folder=Path(tmp.name)
        source=folder/'kernel.c';lib=folder/'kernel.so';source.write_text(text)
        subprocess.run(['cc','-O3','-std=c99','-fPIC','-shared',str(source),'-lm','-o',str(lib)],check=True,capture_output=True)
        dll=ctypes.CDLL(str(lib));function=dll.evaluate
        ptr=ctypes.POINTER(ctypes.c_double);function.argtypes=[ptr,ptr,ctypes.c_double,ptr,ptr,ptr,ptr];function.restype=None
        _CACHE[key]=(tmp,dll,function)
    return _CACHE[key][2]

class NativeNeuralEvaluator:
    def __init__(self,network,margin):self.fn=compile_kernel(network);self.margin=margin
    def __call__(self,q,theta):
        q=np.ascontiguousarray(q,dtype=np.float64);theta=np.ascontiguousarray(theta,dtype=np.float64)
        if q.shape!=(6,) or theta.shape!=(14,):raise ValueError('Expected six moves and fourteen problem parameters')
        obj=np.empty(1);grad=np.empty(6);con=np.empty(57);jac=np.empty((57,6))
        ptr=ctypes.POINTER(ctypes.c_double)
        p=lambda a:a.ctypes.data_as(ptr)
        self.fn(p(q),p(theta),self.margin,p(obj),p(grad),p(con),p(jac))
        return [obj,grad[:,None],con[:,None],jac]
