"""Post-protocol physical/analytical audit; does not alter frozen control results."""
from pathlib import Path
import json
import numpy as np,pandas as pd
import mpmath as mp
from model import *
from control import candidates,costs
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results'
def main():
    mp.mp.dps=60
    cv=lambda z:mp.mpf(str(float(z)))
    vol=cv(V);D=cv(dilution(U0));q=cv(U0[0])/vol
    cp=[cv(z) for z in CP];fcp=sum(cv(U0[j])*cp[i] for j,i in [(0,0),(1,1),(2,3)])
    c=fcp/vol;n=cp[2]-cp[0]-cp[1];mw=cv(U0[3]);ua=cv(UA);ta=cv(U0[5]);tf=cv(U0[4])
    k=lambda T:mp.mpf('16.96e12')*mp.exp(-mp.mpf('75362.4')/(mp.mpf('1.987')*mp.mpf('4.1868')*(T+mp.mpf(11)/60)))
    a=lambda T:(mw*cp[1]*(ta-T)*(1-mp.exp(-ua/(mw*cp[1])))+fcp*(tf-T))/vol
    b=lambda T:mp.mpf(83736)*k(T)
    g=lambda A,W,T:(a(T)+b(T)*A)/W
    lf=lambda A,W,T:(b(T)*q+D*a(T)-b(T)*k(T)*A)/W+(a(T)+b(T)*A)*(mp.diff(a,T)+mp.diff(b,T)*A-c-n*k(T)*A)/W**2
    tt=mp.findroot(lambda T:a(T)+b(T)*q/(D+k(T)),(mp.mpf(331),mp.mpf(334)))
    aa=q/(D+k(tt));ww=(c+n*k(tt)*aa)/D
    rows=[]
    for temp in [mp.mpf(315),mp.mpf(325),tt,mp.mpf(340),mp.mpf(348)]:
        A=aa;W=ww
        direct=mp.diff(lambda z:g(z,W,temp),A)*mp.diff(lambda z:lf(A,z,temp),W)-mp.diff(lambda z:g(A,z,temp),W)*mp.diff(lambda z:lf(z,W,temp),A)
        formula=-b(temp)*(b(temp)*q+(D+k(temp))*a(temp))/W**3+(a(temp)+b(temp)*A)*(-b(temp)*mp.diff(a,temp)+b(temp)*c+a(temp)*mp.diff(b,temp)-a(temp)*n*k(temp))/W**4
        assert abs(direct-formula)<mp.mpf('1e-45')
        rows.append(dict(T=float(temp),determinant=str(formula),derivative_check_error=str(abs(direct-formula)),
            sufficient_rank4=bool(abs(formula)>mp.mpf('1e-30'))))
    pd.DataFrame(rows).to_csv(OUT/'local_lie_quotient.csv',index=False)
    assert abs(mp.mpf(rows[2]['determinant']))<mp.mpf('1e-40')
    x=equilibrium();U=np.tile(U0,(60,1))
    x_b=x.copy();x_b[2]+=.4 # deliberately NOT heat-capacity compensated
    a0=rollout(x,U,np.zeros(3),0,12);b0=rollout(x_b,U,np.zeros(3),0,12)
    varied=U.copy();varied[:,3]*=1+.25*np.sin(np.arange(60)*.3)
    a1=rollout(x,varied,np.zeros(3),0,12);b1=rollout(x_b,varied,np.zeros(3),0,12)
    # Construct the surviving affine-Cp kernel, not just the earlier B/C twin.
    slopes=CP*np.array([.0015,.0002,.0025,.001])
    basis=np.cross(CP[1:],slopes[1:]);basis*=.4/basis[1]
    delta=np.r_[0.,basis,0.,0.]
    assert min((x+delta)[:4])>0
    ca=rollout(x,varied,np.zeros(3),3,12);cb=rollout(x+delta,varied,np.zeros(3),3,12)
    quad=np.vstack([CP[1:],slopes[1:],(CP*np.array([.00001,.000002,.000016,-.000003]))[1:]])
    summary=dict(precision_decimal_digits=60,Lie_formula_verified=True,nominal_quotient_singular=True,
        constant_input_uncompensated_product_gap=.4,
        constant_input_max_thermal_difference=float(np.max(abs(a0[:,4:]-b0[:,4:]))),
        excited_uncompensated_max_thermal_difference=float(np.max(abs(a1[:,4:]-b1[:,4:]))),
        affine_kernel_difference=delta.tolist(),
        affine_kernel_max_thermal_difference=float(np.max(abs(ca[:,4:]-cb[:,4:]))),
        affine_functional_rank=int(np.linalg.matrix_rank(quad[:2])),
        quadratic_functional_rank=int(np.linalg.matrix_rank(quad)),
        conclusion='Specific-twin breakup does not eliminate every affine-Cp twin; rank is local and input-dependent.')
    assert summary['constant_input_max_thermal_difference']<1e-8
    assert summary['affine_kernel_max_thermal_difference']<1e-8
    assert summary['excited_uncompensated_max_thermal_difference']>1e-5
    (OUT/'supplementary_audit.json').write_text(json.dumps(summary,indent=2))
    np.savez_compressed(OUT/'trajectories/supplementary_twins.npz',constant_a=a0,constant_b=b0,excited_a=a1,excited_b=b1,affine_a=ca,affine_b=cb)
    expected_rows=[]
    plans=candidates(1.,3.,21);states=np.array([twin(x,-.4),x,twin(x,.4)])
    for horizon in [4,14,57]:
        for reference in [2.1,float(x[2]),2.5]:
            J,VV=costs(states,plans,U0,np.zeros(3),reference,1.,horizon)
            constant=J.mean(axis=0)-J[1]
            expected_rows.append(dict(horizon=horizon,reference=reference,
                offset_range=float(np.ptp(constant)),same_minimizer=bool(np.argmin(J.mean(axis=0))==np.argmin(J[1])),
                max_constraint_difference=float(np.max(abs(VV-VV[1])))))
    assert max(r['offset_range'] for r in expected_rows)<1e-10
    assert all(r['same_minimizer'] for r in expected_rows)
    pd.DataFrame(expected_rows).to_csv(OUT/'expected_cost_equivalence.csv',index=False)
    summary['expected_cost_equivalence_cases']=len(expected_rows)
    summary['expected_cost_equivalence_pass']=True
    (OUT/'supplementary_audit.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
