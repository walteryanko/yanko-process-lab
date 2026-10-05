"""Source-grounded disturbances; unspecified items explicitly reconstructed."""
from common import *

CASES={
 'servo_plus10':dict(label='Servo +10%',group='servo',duration=12.,on=4.,off=8.,sp=1.10,source='section 5.3.1, Fig33, printed p65'),
 'fa_minus10':dict(label='FA -10%',group='regulatory',duration=12.,on=4.,off=8.,index=0,factor=.90,source='section 5.3.1, Fig29, p63'),
 'fb_plus10':dict(label='FB +10%',group='regulatory',duration=12.,on=4.,off=8.,index=1,factor=1.10,source='section 5.3.1, Fig30, p64'),
 't0_minus10F':dict(label='T0 -10% °F',group='regulatory',duration=12.,on=4.,off=8.,index=4,factor=.90,fahrenheit=True,source='section 5.3.1, Fig31, p64'),
 'ta_minus20F':dict(label='Ta -20% °F',group='regulatory',duration=12.,on=4.,off=8.,index=5,factor=.80,fahrenheit=True,source='section 5.3.1, Fig32, p65'),
 'fa_minus15':dict(label='FA -15%',group='severe regulatory',duration=12.,on=4.,off=8.,index=0,factor=.85,source='section 5.3.2.2, Fig34, p68-69'),
 't0_minus30F':dict(label='T0 -30% °F',group='severe regulatory',duration=12.,on=4.,off=8.,index=4,factor=.70,fahrenheit=True,source='section 5.3.2.2, Fig35, p69'),
 'servo_minus20':dict(label='Servo -20%',group='severe servo',duration=12.,on=4.,off=None,sp=.80,source='section 5.3.2.2, Fig36, p70; holds new target'),
 'thermal_servo':dict(label='Servo +20% / limite',group='thermal servo',duration=6.,on=3.,off=None,sp=1.20,source='Fig39, p72: amplitude +20% and t3h inferred approximately from axes, not specified in text'),
 'startup':dict(label='Partida fria',group='startup',duration=3.,on=None,off=None,source='Figs37-38, p71-72; filled feed initial mixture reconstructed, source does not state six initial values'),
}
CONFIGS={
 'physical_ukf':dict(label='NMPC físico + UKF',controller='physical',estimator='ukf'),
 'physical_nake':dict(label='NMPC físico + NAKE-BB',controller='physical',estimator='nake'),
 'neural_ukf':dict(label='NMPC neural + UKF',controller='neural',estimator='ukf'),
 'neural_nake':dict(label='NMPC neural + NAKE-BB',controller='neural',estimator='nake'),
}

def inputs(case,t):
    c=CASES[case];u=U_BASE.copy();sp=BASE[2]
    active=c['on'] is not None and t>=c['on'] and (c['off'] is None or t<c['off'])
    if active:
        if 'sp' in c:sp*=c['sp']
        if 'index' in c:
            j=c['index']
            if c.get('fahrenheit'):
                f=(u[j]-273.15)*1.8+32.;u[j]=(f*c['factor']-32.)/1.8+273.15
            else:u[j]*=c['factor']
    return u,sp
