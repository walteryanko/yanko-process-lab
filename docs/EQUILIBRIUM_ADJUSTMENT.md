# Effective-enthalpy calibration at the historical nominal point

The literal Table-1 parameters and equations 33–55 of Brandão (2019) give
T = 340.3034893843503 K. At the reported Table-2 nominal point 332.3 K,
with stationary species balances, the energy balance gives dT/dt =
32.964619919720086 K/h. Therefore the table and nominal result cannot both
be stationary for that literal implementation.

The user authorized using adjusted calculations. The default numerical core
now uses an **effective reaction enthalpy**, calibrated to that ONE reported
nominal temperature. All other table parameters and nominal inputs remain fixed.

For a positive heat release H = -DeltaH, let v = sum(F_i/rho_i),
k = k0 exp(-E/(RT)), CA = FA/(v+Vk), and
Qcool = mw cpB (Ta-T)[1-exp(-UA/(mw cpB))]. Then:

H_eff = [(FA cpA + FB cpB + FM cpM)(T-T0) - Qcool] / (Vk CA).

At 332.3 K, DeltaH_eff = -84138.65353748415 kJ/kmol. Its magnitude is
8.1023346821% lower than the table's -91556.9 kJ/kmol. This is a single-point
calibrated effective coefficient, NOT proof of the true chemical enthalpy,
NOT identification of the original Simulink implementation, and NOT full
historical reproduction. Other uncertain inputs/parameters could also fit
this single temperature. The PDF and source manuscript repeat the original
enthalpy; no documentary correction to that value was found.

The newly calculated six-state equilibrium is:

| State | Adjusted value | Units |
|---|---:|---|
| CA | 0.6246448243276402 | kmol/m³ |
| CB | 34.02657223082452 | kmol/m³ |
| CC | 2.2809146409391614 | kmol/m³ |
| CM | 3.633950405595394 | kmol/m³ |
| T | 332.3 | K |
| Tt | 314.4906748250958 | K |

Species and Tt were recomputed from their balances, rather than copied from
historical results. All six derivative residuals are below 1e-8 in their
respective physical units. The nominal Jacobian has negative real eigenvalues.
An independent DOP853 integration and RK4 step halving agree within 1.1e-10
in the largest physical state difference in the documented 0.6 h test.

`TABLED_P` / `TABLED_BASE` retain the original TypeScript model, accessible
through the optional parameter arguments. `P` / `BASE` select the explicitly
adjusted variant. `equilibria()` exposes all detected roots in 250–430 K and
`equilibrium(..., hint)` chooses the nearest branch; branch stability must be
checked separately. Root scans are finite-resolution, not formal proofs of
exhaustive root isolation.

The research comparison uses the same adjusted plant and nominal model.
Synthetic UA and k0 mismatches are deliberately introduced only in stated
regimes. See `research/nake/results/calibration.json` and
`historical_validation.json` for numerical evidence. Non-nominal points in
the historical table are checked independently and are not used to fit the
calibration. Previous MV/RGA/NMPC reports based on the literal table should
not be reinterpreted as adjusted-model results.
