"""Portable MLP and genuine LSTM, with NumPy BPTT and Adam training.

LSTM gates: input, forget, candidate, output. No random reservoir or MLP
is called LSTM. Only past estimator features are consumed online.
"""
import json
from pathlib import Path
import numpy as np
from scipy.special import expit
from model import BASE, U0, XS, US, WEIGHTS, SUBSTEPS

class NeuralTransition:
    def __init__(self,data):
        self.data=data;self.w=[np.array(x) for x in data['weights']];self.b=[np.array(x) for x in data['biases']]
        self.affine=np.array(data['affine']);self.mean=np.array(data['mean']);self.scale=np.array(data['scale'])
        self.ym=np.array(data['target_mean']);self.ys=np.array(data['target_scale']);self.offset=np.array(data['offset'])
        self.q_model=np.array(data['q_model'])
    def substep(self,x,u):
        x=np.asarray(x);u=np.asarray(u)
        f=np.concatenate([(x-BASE)/XS,(np.broadcast_to(u,x.shape[:-1]+(7,))-U0)/US],axis=-1)
        a=(f-self.mean)/self.scale
        for i,(w,b) in enumerate(zip(self.w,self.b)):
            a=a@w+b
            if i<len(self.w)-1:a=np.tanh(a)
        inc=np.concatenate([f,np.ones(f.shape[:-1]+(1,))],axis=-1)@self.affine+a*self.ys+self.ym-self.offset
        return x+inc*XS
    def __call__(self,x,u):
        z=np.array(x,copy=True)
        for _ in range(SUBSTEPS):z=self.substep(z,u)
        return z
    @classmethod
    def load(cls,path=None):return cls(json.loads(Path(path or WEIGHTS/'transition.json').read_text()))

class LSTM:
    def __init__(self,n_input=17,n_hidden=16,n_output=5,seed=4301):
        rng=np.random.default_rng(seed);self.n=n_hidden
        self.p={'W':rng.normal(0,.15,(n_input+n_hidden,4*n_hidden)),
                'b':np.r_[np.zeros(n_hidden),np.ones(n_hidden),np.zeros(2*n_hidden)],
                'V':rng.normal(0,.1,(n_hidden,n_output)),'d':np.zeros(n_output)}
        self.mean=np.zeros(n_input);self.scale=np.ones(n_input);self.ym=np.zeros(n_output);self.ys=np.ones(n_output)
    def forward(self,x,cache=False):
        batch,length,_=x.shape;h=np.zeros((batch,self.n));c=h.copy();cs=[]
        for t in range(length):
            z=np.c_[x[:,t],h];a=z@self.p['W']+self.p['b'];n=self.n
            i=expit(a[:,:n]);f=expit(a[:,n:2*n]);g=np.tanh(a[:,2*n:3*n]);o=expit(a[:,3*n:]);cn=f*c+i*g
            hn=o*np.tanh(cn)
            if cache:cs.append((z,i,f,g,o,c,cn))
            h=hn;c=cn
        out=h@self.p['V']+self.p['d']
        return (out,cs,h) if cache else out
    def loss_grad(self,x,y):
        out,cs,h=self.forward(x,True);e=out-y;loss=float(np.mean(e**2));dy=2*e/e.size
        grads={k:np.zeros_like(v) for k,v in self.p.items()};grads['V']=h.T@dy;grads['d']=dy.sum(0)
        dh=dy@self.p['V'].T;dc=np.zeros_like(dh);n=self.n
        for z,i,f,g,o,cp,c in reversed(cs):
            tc=np.tanh(c);do=dh*tc;dc=dc+dh*o*(1-tc**2)
            di=dc*g;df=dc*cp;dg=dc*i;dc=dc*f
            da=np.c_[di*i*(1-i),df*f*(1-f),dg*(1-g*g),do*o*(1-o)]
            grads['W']+=z.T@da;grads['b']+=da.sum(0);dh=(da@self.p['W'].T)[:,-n:]
        return loss,grads
    def fit(self,x,y,xv,yv,epochs=150,batch_size=128,rate=.003,seed=4311):
        self.mean=x.mean((0,1));self.scale=np.maximum(x.std((0,1)),1e-5)
        self.ym=y.mean(0);self.ys=np.maximum(y.std(0),.2)
        a=np.clip((x-self.mean)/self.scale,-8,8);b=(y-self.ym)/self.ys
        av=np.clip((xv-self.mean)/self.scale,-8,8);bv=(yv-self.ym)/self.ys
        m={k:np.zeros_like(v) for k,v in self.p.items()};v={k:np.zeros_like(w) for k,w in self.p.items()}
        rng=np.random.default_rng(seed);step=0;best=float('inf');bp=None;history=[]
        for epoch in range(epochs):
            order=rng.permutation(len(a));losses=[]
            for j in range(0,len(a),batch_size):
                ix=order[j:j+batch_size];loss,g=self.loss_grad(a[ix],b[ix]);losses.append(loss);step+=1
                norm=np.sqrt(sum(np.sum(t*t) for t in g.values()));fac=min(1.,5./max(norm,1e-9))
                for k in self.p:
                    gg=g[k]*fac;m[k]=.9*m[k]+.1*gg;v[k]=.999*v[k]+.001*gg**2
                    self.p[k]-=rate*(m[k]/(1-.9**step))/(np.sqrt(v[k]/(1-.999**step))+1e-8)
            score=float(np.mean((self.forward(av)-bv)**2))
            if score<best:best=score;bp={k:z.copy() for k,z in self.p.items()};self.epoch=epoch+1
            if (epoch+1)%10==0:history.append(dict(epoch=epoch+1,train_loss=float(np.mean(losses)),validation_loss=score))
            if (epoch+1)%50==0:print('LSTM epoch',epoch+1,'validation',round(score,5),flush=True)
        self.p=bp;return history
    def predict(self,sequence):
        x=np.asarray(sequence);single=x.ndim==2
        if single:x=x[None]
        ans=self.forward(np.clip((x-self.mean)/self.scale,-8,8))*self.ys+self.ym
        return ans[0] if single else ans
    def export(self):
        return dict(parameters=self.p,hidden=self.n,mean=self.mean,scale=self.scale,target_mean=self.ym,target_scale=self.ys,
                    gate_order=['input','forget','candidate','output'],epoch=self.epoch,
                    architecture='genuine LSTM with trained recurrent weights, trained by BPTT/Adam; last-output regression')
    @classmethod
    def load(cls,path=None):
        d=json.loads(Path(path or WEIGHTS/'lstm_q.json').read_text());s=cls(len(d['mean']),d['hidden'],len(d['target_mean']))
        s.p={k:np.array(v) for k,v in d['parameters'].items()};s.mean=np.array(d['mean']);s.scale=np.array(d['scale'])
        s.ym=np.array(d['target_mean']);s.ys=np.array(d['target_scale']);s.epoch=d['epoch'];return s
