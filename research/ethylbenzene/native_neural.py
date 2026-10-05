"""Exact learned-MLP chain rule in small C loops, checked against CasADi.

No reaction, enthalpy or physical derivative is embedded in this kernel.
This optimization changes evaluation cost, not weights or the NLP problem.
"""
import ctypes,hashlib,subprocess
import numpy as np
from model import BASE,U0,XS,US,SUBSTEPS,NATIVE,T_LIMIT

KERNEL=r'''
static void substep(const double *x,const double *u,double *out,double der[5][7]) {
 double f[12],a[WIDTH],an[WIDTH],d[WIDTH][7]={{0}},dn[WIDTH][7];
 for(int j=0;j<5;j++)f[j]=(x[j]-BASE[j])/XS[j];
 for(int j=0;j<7;j++)f[j+5]=(u[j]-UBASE[j])/US[j];
 for(int j=0;j<12;j++)a[j]=(f[j]-MEAN[j])/SCALE[j];
 for(int j=0;j<5;j++)d[j][j]=1/(XS[j]*SCALE[j]);
 d[5][5]=1/(US[0]*SCALE[5]);d[8][6]=1/(US[3]*SCALE[8]);
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
 for(int i=0;i<5;i++){
  double inc=AFFINE[12*5+i]+a[i]*YS[i]+YM[i]-OFFSET[i];
  for(int j=0;j<12;j++)inc+=f[j]*AFFINE[j*5+i];out[i]=x[i]+XS[i]*inc;
  for(int s=0;s<7;s++){
   double v=s<5?AFFINE[s*5+i]/XS[s]:(s==5?AFFINE[5*5+i]/US[0]:AFFINE[8*5+i]/US[3]);
   der[i][s]=XS[i]*(v+d[i][s]*YS[i])+(s==i?1:0);
  }
 }
}
static void step(const double *x,const double *u,double *out,double a[5][5],double b[5][2]){
 double z[5],next[5],d[5][7],na[5][5],nb[5][2];
 for(int i=0;i<5;i++){z[i]=x[i];b[i][0]=b[i][1]=0;for(int j=0;j<5;j++)a[i][j]=(i==j);}
 for(int k=0;k<SUBSTEPS;k++){
  substep(z,u,next,d);
  for(int i=0;i<5;i++){
   for(int v=0;v<2;v++){nb[i][v]=d[i][5+v];for(int m=0;m<5;m++)nb[i][v]+=d[i][m]*b[m][v];}
   for(int j=0;j<5;j++){na[i][j]=0;for(int m=0;m<5;m++)na[i][j]+=d[i][m]*a[m][j];}
  }
  for(int i=0;i<5;i++){z[i]=next[i];for(int v=0;v<2;v++)b[i][v]=nb[i][v];for(int j=0;j<5;j++)a[i][j]=na[i][j];}
 }
 for(int i=0;i<5;i++)out[i]=z[i];
}
void evaluate(const double *q,const double *theta,int nmv,int constrained,double *cost,double *grad,double *con,double *jac){
 int nd=4*nmv;int nc=2*nd+(constrained?40:0);
 double x[5],u[7],next[5],a[5][5],b[5][2],s[5][8]={{0}},sn[5][8];
 for(int i=0;i<5;i++)x[i]=theta[i];for(int i=0;i<7;i++)u[i]=theta[5+i];
 for(int i=0;i<nd;i++)grad[i]=0;for(int i=0;i<nc*nd;i++)jac[i]=0;*cost=0;
 for(int k=0;k<40;k++){
  int j=k/5;if(j>3)j=3;u[0]=q[j*nmv]*UBASE[0];u[3]=(nmv==2?q[j*nmv+1]:1.)*UBASE[3];
  step(x,u,next,a,b);
  for(int i=0;i<5;i++)for(int c=0;c<nd;c++){
   sn[i][c]=(c==j*nmv?b[i][0]*UBASE[0]:0)+(nmv==2&&c==j*nmv+1?b[i][1]*UBASE[3]:0);
   for(int m=0;m<5;m++)sn[i][c]+=a[i][m]*s[m][c];
  }
  double total=next[0]+next[1]+next[2]+next[3];double ex=(next[2]/total-theta[12])/.02;
  double et=(next[4]-theta[13])/5.;*cost+=.8*ex*ex+(nmv==2?.2*et*et:0);
  for(int c=0;c<nd;c++){
   double dtotal=sn[0][c]+sn[1][c]+sn[2][c]+sn[3][c];
   double dxe=(sn[2][c]*total-next[2]*dtotal)/(total*total);
   grad[c]+=1.6*ex*dxe/.02+(nmv==2?.4*et*sn[4][c]/5.:0);
   if(constrained)jac[k*nd+c]=-sn[4][c]/5.;
  }
  if(constrained)con[k]=(TLIMIT-next[4])/5.;
  for(int i=0;i<5;i++){x[i]=next[i];for(int c=0;c<nd;c++)s[i][c]=sn[i][c];}
 }
 int first=constrained?40:0;
 for(int j=0;j<4;j++)for(int v=0;v<nmv;v++){
  int pos=j*nmv+v;double du=q[pos]-(j?q[pos-nmv]:theta[14+v]);
  *cost+=.03*du*du;grad[pos]+=.06*du;if(j)grad[pos-nmv]-=.06*du;
  double limit=v==0?.12:.08;int rminus=first+j*2*nmv+v;int rplus=rminus+nmv;
  con[rminus]=limit-du;con[rplus]=limit+du;
  jac[rminus*nd+pos]=-1.;jac[rplus*nd+pos]=1.;
  if(j){jac[rminus*nd+pos-nmv]=1.;jac[rplus*nd+pos-nmv]=-1.;}
 }
}
'''

def compile_kernel(net):
    def array(name,values):return 'static const double '+name+'[]={' + ','.join(format(v,'.17g') for v in np.asarray(values).ravel())+'};\n'
    dims=[net.w[0].shape[0]]+[w.shape[1] for w in net.w]
    source='#include <math.h>\n'+f'#define WIDTH {max(dims)}\n#define LAYERS {len(net.w)}\n#define SUBSTEPS {SUBSTEPS}\n#define TLIMIT {T_LIMIT:.17g}\n'
    source+='static const int DIMS[]={'+','.join(str(v) for v in dims)+'};\n'
    for name,val in [('BASE',BASE),('UBASE',U0),('XS',XS),('US',US),('MEAN',net.mean),('SCALE',net.scale),('YS',net.ys),('YM',net.ym),('OFFSET',net.offset),('AFFINE',net.affine)]:source+=array(name,val)
    for i,(w,b) in enumerate(zip(net.w,net.b)):source+=array(f'W{i}',w)+array(f'B{i}',b)
    source+='static const double *WEIGHTS[]={'+','.join(f'W{i}' for i in range(len(net.w)))+'};\n'
    source+='static const double *BIASES[]={'+','.join(f'B{i}' for i in range(len(net.b)))+'};\n'
    source+=KERNEL;folder=NATIVE/('fast_'+hashlib.sha256(source.encode()).hexdigest()[:16]);lib=folder/'kernel.so'
    if not lib.exists():
        folder.mkdir(parents=True,exist_ok=True);(folder/'kernel.c').write_text(source)
        subprocess.run(['cc','-O3','-std=c99','-fPIC','-shared',str(folder/'kernel.c'),'-lm','-o',str(lib)],check=True,capture_output=True)
    return lib

class NativeNeuralEvaluator:
    def __init__(self,network,mode,constrained):
        self.nmv=1 if mode=='siso' else 2;self.constrained=int(constrained);self.nd=4*self.nmv;self.nc=2*self.nd+(40 if constrained else 0)
        self.dll=ctypes.CDLL(str(compile_kernel(network)));self.fn=self.dll.evaluate;self.ptr=ctypes.POINTER(ctypes.c_double)
        self.fn.argtypes=[self.ptr,self.ptr,ctypes.c_int,ctypes.c_int,self.ptr,self.ptr,self.ptr,self.ptr];self.fn.restype=None
    def __call__(self,q,theta):
        q=np.ascontiguousarray(q,dtype=float);theta=np.ascontiguousarray(theta,dtype=float)
        if q.shape!=(self.nd,) or theta.shape!=(16,):raise ValueError('Invalid neural NMPC input shape')
        obj=np.empty(1);grad=np.empty(self.nd);con=np.empty(self.nc);jac=np.empty((self.nc,self.nd))
        p=lambda a:a.ctypes.data_as(self.ptr)
        self.fn(p(q),p(theta),self.nmv,self.constrained,p(obj),p(grad),p(con),p(jac));return [obj,grad,con,jac]
