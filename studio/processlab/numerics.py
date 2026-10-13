import numpy as np
from scipy.integrate import solve_ivp


def jacobian(fun, x):
    x = np.asarray(x, dtype=float); cols = []
    for i in range(len(x)):
        h = 1e-5*max(abs(x[i]), 1.)
        delta = np.eye(len(x))[i]*h
        cols.append((np.asarray(fun(x+delta))-np.asarray(fun(x-delta)))/(2*h))
    return np.column_stack(cols)


def integrate(model, x, u, disturbance, dt, config, statistics=None):
    f = lambda t, y: model.rhs(y, u, disturbance)
    if config["solver"] == "RK4":
        count = max(8, int(np.ceil(dt/2))); h = dt/count; y = np.array(x, copy=True)
        for _ in range(count):
            a = f(0,y); b=f(0,y+h*a/2); c=f(0,y+h*b/2); d=f(0,y+h*c)
            y += h*(a+2*b+2*c+d)/6
            model.check(y)
        nfev = 4*count
    else:
        # A sample is not an integration step. Limit internal steps so long user
        # samples still resolve the fastest supported stirred-tank demonstrations.
        sol = solve_ivp(f, (0, dt), x, method=config["solver"], rtol=config["rtol"], atol=config["atol"], max_step=min(dt/4, 5.))
        if not sol.success:
            raise ValueError(f"ODE integration failed: {sol.message}")
        y = sol.y[:,-1]; nfev = sol.nfev
    model.check(y)
    if statistics is not None:
        statistics["nfev"] += nfev; statistics["integration_calls"] += 1
    return y


def covariance(P):
    P = (P+P.T)/2
    vals, vecs = np.linalg.eigh(P)
    if not np.isfinite(vals).all() or min(vals) < -1e-7*max(1., max(vals)):
        raise ValueError("Estimator covariance is not positive semidefinite")
    return (vecs*np.maximum(vals, 1e-12))@vecs.T
