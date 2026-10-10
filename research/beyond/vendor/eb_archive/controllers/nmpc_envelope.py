"""Exploratory NMPC after falsifying cold, positive-duty trajectories.

This is a new candidate, not a retrospective repair of the old benchmark.
Both manipulated inputs, horizon, solver and actuator limits match MIMO NMPC.
Changes: predicted temperature in [140.85, 170.85] degC, plus a small cost
around 160 degC. The lower bound is only a necessary direction-of-heat-flow
condition for 414 K steam. It does not validate UA, capacity or safety.

Inherited online solve/fallback is intentionally unchanged. It is not a
recursive-feasibility guarantee; failed solves and actual violations are saved.
"""
import os
import numpy as np
import casadi as ca
from controllers.control import NMPC, TMAX
from ethylbenzene_model.model import (
    build, STEP, DT, FMAX, Q0, NOMINAL_STROKE,
)

TMIN_ENVELOPE = 140.85
TTARGET = 160.0
TEMPERATURE_SCALE = 10.0
TEMPERATURE_WEIGHT = 0.10


class EnvelopeNMPC(NMPC):
    # Never reuse the less constrained parent problem from a shared cache.
    cache = {}

    def __init__(self, horizon=12):
        super().__init__(mimo=True, constrained=True, robust=False,
                         economic=False, adaptive_compute=False, horizon=horizon)

    def _build(self, n):
        key = (n, TMIN_ENVELOPE, TMAX, TTARGET, TEMPERATURE_WEIGHT)
        if key in self.cache:
            return self.cache[key]
        _, _, _, longstep, _ = build(dt=.10, substeps=12)
        nc = 4
        nm = 2
        v = ca.MX.sym('v', nm*nc)
        par = ca.MX.sym('par', 5+7+12+1+2+1)
        xx = par[:5]
        u = par[5:12]
        p = par[12:24]
        sp = par[24]
        last = par[25:27]
        # Margin is zero for this deterministic, non-robust candidate.
        margin = par[27]
        cost = 0
        g = []
        types = []
        for j in range(n):
            block = min(nc-1, j*nc//n)
            s = v[block*nm]
            cool = v[block*nm+1]
            uu = ca.MX(u)
            uu[0] = FMAX*50**(s-1)
            uu[3] = Q0*cool
            xx = STEP(xx, uu, p) if j == 0 else longstep(xx, uu, p)
            y = xx[2]/ca.sum1(xx[:4])
            weight = DT if j == 0 else .10
            cost += weight*((y-sp)/.025)**2
            cost += weight*.025*((s-NOMINAL_STROKE)/.2)**2
            cost += weight*.003*((cool-1)/.2)**2
            cost += weight*TEMPERATURE_WEIGHT*((xx[4]-TTARGET)/TEMPERATURE_SCALE)**2
            g.append(xx[4]+margin)
            types.append(0)
            if j == 0:
                g.extend([s-last[0], cool-last[1]])
                types.extend([1, 2])
                cost += .003*((s-last[0])/.025)**2
                cost += .001*((cool-last[1])/.025)**2
        cost += 2*((xx[2]/ca.sum1(xx[:4])-sp)/.025)**2
        cost += TEMPERATURE_WEIGHT*((xx[4]-TTARGET)/TEMPERATURE_SCALE)**2
        opts = {'ipopt.print_level':0, 'print_time':False, 'ipopt.sb':'yes',
                'ipopt.max_iter':55, 'ipopt.tol':1e-5,
                'ipopt.acceptable_tol':1e-3, 'ipopt.max_cpu_time':.7}
        if os.environ.get('EB_JIT') == '1':
            opts.update({'jit':True, 'compiler':'shell',
                         'jit_options':{'flags':['-O0']}})
        solver = ca.nlpsol('mpc_envelope', 'ipopt',
                          {'x':v, 'p':par, 'f':cost, 'g':ca.vertcat(*g)}, opts)
        lb = np.tile([.05,.75], nc)
        ub = np.tile([1.,1.25], nc)
        lbg = np.array([TMIN_ENVELOPE if typ==0 else -.045 if typ==1 else -.035
                        for typ in types])
        ubg = np.array([TMAX if typ==0 else .045 if typ==1 else .035
                        for typ in types])
        self.cache[key] = (solver, lb, ub, lbg, ubg)
        return self.cache[key]
