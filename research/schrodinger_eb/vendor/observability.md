# Observability, identifiability and actuator audit

**Scope:** calibrated reconstruction of the TFC first reactor, not a replication of the historical Aspen/Simulink trajectories. Time is hours; concentrations are kmol/m³. Numeric Q was calibrated, not recovered. All information calculations below condition on this model.

## Principal verified finding

The temperature-only **linearization is not fully observable at the nominal equilibrium**, but is **detectable**: its unobservable mode is stable. The nonlinear differential observability rank test is singular there. Because rank changes off equilibrium, this alone does not prove exact nonlinear indistinguishability; higher-order finite-amplitude information may exist. The result concerns the available local information, not an EKF-specific defect.

The stoichiometric matrix has rank 2 and ν3=ν1−ν2. Two moieties obey known-input washout equations:

- zA = CB + CEB + CDEB (aromatic rings).
- zE = CE + CEB + 2 CDEB (ethylene units).
- dz/dt = (moiety inflow − Fout z)/V; both share eigenvalue −Fout/V.

At nominal, Fout/V = 1.1474052 h⁻¹ and washout τ = 0.8715 h. A single scalar measurement cannot distinguish both members of that repeated eigenspace. The row-normalized Lie codistribution has singular values [2.103e+00 7.601e-01 8.146e-04 5.484e-08 7.135e-17]. Using derivatives through orders 5 and 7 preserves the rank deficit.

The differential test is O(x)=[dh; dLf h; ...; dLf⁴ h], evaluated with automatic differentiation. At an equilibrium f(x*)=0, its rows reduce to C, CA, ..., CA⁴. The two independent left eigenvectors given by the moieties share −Fout/V, so the associated eigenspace cannot be fully observed by a single scalar output.

At the tested nonstationary point the nonlinear Lie codistribution becomes full rank, while remaining ill conditioned. This satisfies the sufficient local weak observability rank condition there; it does not guarantee useful estimation from noisy temperature.

The two moieties provide independent **model and feed-history information**, even when temperature is uninformative. Known feed compositions and accurate initial conditions can therefore produce tiny nominal errors. Initial-state error decays on the dilution time scale. Persistent uncertainty in feed composition, model parameters or thermal closure is a different and harder problem.

An empirical central-difference Gramian was evaluated at four perturbation amplitudes (1e−4, 1e−3, 0.01, 0.05 times the scaling vector). Its convergence to the tangent sensitivity is recorded. Finite-amplitude curvature can produce a nonzero fifth singular value and reflects possible higher-order information; this does not overturn the exact equilibrium differential rank deficit.

## Thermochemical consistency ablation

Because ν3=ν1−ν2, constant-temperature enthalpies should obey ΔH3=ΔH1−ΔH2. The literal values give −205.5 versus −200 kcal/kmol. A diagnostic ablation sets ΔH3=−200 and adjusts Q by only -184.312 kcal/h to preserve the same equilibrium. The resulting temperature-only differential rank drops **4 to 3**, with three identical dilution eigenvalues. Its finite-horizon singular values are [2.5546e+03 4.9947e+01 4.4047e+00 1.1218e-12 7.6297e-14].

With this Hess closure, the enthalpy-like combination H=RHOC·T−27150·CEB−54100·CDEB has no reaction source and obeys another forced washout equation with the same −Fout/V. Along with the two chemical moieties, it yields three independent identical dilution modes; a scalar output leaves at least two directions unobservable in the equilibrium linearization.

Thus a tiny thermochemical closure difference sustains the weak fourth local information direction of the literal model. Source rounding, temperature reference and model approximations may explain it; the literal shared model remains unchanged. A claim of robust chemical identifiability based on that weak direction is not defensible.

## Practical information by chemical state

Whitened trajectory sensitivity: 101 independent T samples over 2 h, σT=0.1 K, dt=0.02 h. Scaling [0.1,7,3,0.6,50] is fixed for numerical comparisons. Singular values are [2.5547e+03 4.9951e+01 4.4024e+00 1.1250e-02 2.5003e-14]. The four concentrations all have nonzero projection on the null direction, so the **regular local Fisher matrix supplies no finite marginal bound** for their initial values without extra assumptions. A pseudoinverse must not be reported as finite certainty; this is not a theorem forbidding nonlinear Bayesian inference from finite excursions.

For a transparent local linear-Gaussian Bayesian illustration, chemistry has independent 20% initial priors and temperature has 0.2 K prior SD. The table reports posterior uncertainty about the **initial** composition; it is not online filter RMSE and must not be read as a limit on current-state accuracy after washout.

| State | Prior SD | Posterior initial SD | Prior SD reduction |
|---|---:|---:|---:|
|CE|0.00747617|0.00487443|34.80%|
|CB|0.926483|0.670347|27.65%|
|CEB|0.393382|0.368006|6.45%|
|CDEB|0.0744896|0.0740345|0.61%|
|T|0.2|0.0860003|57.00%|

For contrast, propagating that initial uncertainty through the exact, noise-free dynamics to t=2 h gives current CEB SD 0.03277 without temperature updates and 0.02801 with its history. The model itself removes much of the initial uncertainty by stable washout. This calculation excludes continuous process noise and parameter/feed uncertainty.

The linearized modal time constants are approximately 46 s, 27 min and 52 min. They are coupled chemical/thermal modes, not a justification for freezing chemistry while updating temperature. Multi-rate estimation requires validated sensor bandwidth and noise correlation before fast samples can be counted as independent information.

## Operating map and active sensing

The 81-cell map sweeps T=140–180°C and ethylene feed 0.8–1.2 nominal, recalibrating duty to each equilibrium. These are mathematical information probes, **not approved safe operating points**. Equilibrium rank loss persists. CEB and especially CDEB are much less informed than aggregate reaction activity.

A supplementary 147-cell map varies ethylene, benzene and recycle separately across the same range; every row also stores conversion, all concentrations, reaction-heat intensity, recalibrated Q and the local Euler stability limit.

| Excitation | Rank | Smallest singular | Initial CEB SD | Max T (°C) | Max CEB excursion |
|---|---:|---:|---:|---:|---:|
|constant|4|2.5e-14|0.368|160.000|0|
|ethylene_2pct|5|0.00982|0.367|160.204|0.001683|
|ethylene_5pct|5|0.00955|0.3646|160.510|0.004192|
|two_feed_2pct|5|0.00955|0.3672|160.249|0.001984|
|benzene_50pct|5|0.0858|0.3588|167.025|0.09456|
|recycle_minus50pct|5|0.0765|0.3805|160.000|0.138|

Small known-input dither can lift rank but rank restoration alone is not an industrial benefit. Its posterior CEB information gain must be traded against temperature and production excursions. These are active-sensing experiments, **not a proved dual-control algorithm**.

## Parameter identifiability and thermal residual interpretation

At constant nominal temperature, each log pre-exponential factor and activation-energy shift enter only through log k0−ΔE/(RT). Their sensitivity columns are collinear (cosine −1). Estimating all six independently from this operating point is unjustified. Estimate effective k(Tref), then add activation-energy variation only if a sufficiently broad thermal experiment supports it.

A multiplicative reaction-heat correction and an additive thermal bias have collinear first-order effects at equilibrium (cosine +1). Effective heat capacity is locally unidentifiable at exact equilibrium because dT/dt=0. Fresh-benzene and recycle-benzene composition errors also have collinear effects with fixed flow proportions. This explains why tuning a single Q to match a steady state cannot identify whether the discrepancy came from thermodynamics, kinetics or omitted dynamics.

The identifiability output includes 12-parameter sensitivity cosines and singular spectra under equilibrium, small dither and the historical benzene disturbance. These diagnostics support estimating only a small, identifiable subset; the full joint 17-state/parameter problem has severe confounding.

## What one additional sensor can accomplish

A second measurement of the same perfectly mixed temperature, or ΔT to an already known feed temperature, adds precision but no structural rank. Outlet flow is already the sum of model inputs. Pressure has no measurement equation in this constant-density model. Real second-position temperature and coolant dynamics require an expanded model before their value can be quantified.

A hypothetical independent calorimetry observation (1% noise on reaction heat) improves some observable combinations but cannot remove the equilibrium chemical null mode. Measuring actual heat duty and feed temperatures can reduce nuisance uncertainty. The following comparison has explicit assumed prior reductions and does not establish a hardware-specific sensor winner.

| Sensor assumption | Initial CEB SD | SD reduction |
|---|---:|---:|
|T only|0.36801|6.45%|
|duplicate_temperature|0.35279|10.32%|
|reaction_calorimetry|0.36185|8.02%|
|T, unknown heat/feed-T bias|0.38256|2.75%|
|T + heat-duty equivalent sensor|0.38256|2.75%|
|T + combined feed-T sensors|0.38255|2.75%|
|T + heat-duty and feed-T sensors|0.38245|2.78%|

## Input authority and interaction

fC1 denotes recycle; fR1 denotes dependent reactor outlet = fE+fB+fC1 and is not an additional independent manipulated variable. The shared implementation input vector stores recycle at index 2. The Q input is heat removal in this sign convention.

| Input | CEB elasticity (or relative response per 1 K feed T) | CDEB elasticity | T response to +1% input (or +1 K feed T) |
|---|---:|---:|---:|
|fE|0.4217|1.4597|1.2514|
|fB|-0.0839|-0.6558|0.1852|
|recycle fC1|-0.1287|-1.0058|0.2797|
|Q removal|-0.2973|0.3813|-1.7347|
|TEfeed|0.0020|-0.0026|1.1843|
|TBfeed|0.0023|-0.0029|1.3320|
|TCfeed|0.0036|-0.0046|2.1070|

The fE choice has strong CEB authority, but also increases temperature and DEB. Benzene and recycle have nearly parallel local effects and must not be counted as independent powerful directions. The CEB/CDEB/T versus fE/fB/Q RGA is:

```
[[-3.5431  1.9889  2.5542]
 [ 2.3064 -1.8562  0.5498]
 [ 2.2366  0.8673 -2.104 ]]
```

Large interaction entries caution against independent loop pairing. Dynamic RGA and scaled controllability are retained in JSON. Q authority is a mathematical hypothetical; the historical actuator/heat-exchanger model is not available.

## Discretization audit

The fastest nominal mode is approximately -77.9398 h⁻¹; local explicit-Euler stability requires dt < 0.02566 h, and positivity/accuracy may require much smaller steps. The actual historical sample interval is not inferred from this bound.

Audit scenario: perturbed positive initial state, +50% benzene constant input, duration 1 h; DOP853 rtol=1e−11/atol=1e−12 reference. CPU is a single-run local measurement, not a controller benchmark.

| Integrator | dt (h) | max CEB error | max T error | failure | negative chemistry |
|---|---:|---:|---:|---|---|
|Euler|0.02|0.0015|0.129|False|False|
|Euler|0.01|0.000731|0.0396|False|False|
|Euler|0.005|0.000363|0.0145|False|False|
|Euler|0.001|7.23e-05|0.00253|False|False|
|RK4_8_substeps|0.02|1.06e-08|7.9e-07|False|False|
|CVODES|0.02|1.17e-09|7.7e-09|False|False|
|collocation|0.02|2.66e-11|1.97e-09|False|False|
|Radau|adaptive|1.45e-09|1.34e-08|False|False|
|BDF|adaptive|1.28e-08|6.84e-08|False|False|
|DOP853|adaptive|8.09e-10|5.94e-08|False|False|

## Reproducibility and evidence limits

- All nonlinear and one-step Jacobians were checked against central differences at nominal and transient points; numerical errors are saved in JSON.
- CSV and JSON retain scalings, noise assumptions, priors, nominal vectors, per-state metrics, map, correlations and model SHA256.
- No empirical temperature-only output establishes full composition observability with arbitrary unknown kinetics/feed/thermal parameters.
- No observer architecture can fix information that the measurements and trusted balances do not contain.
- Equilibrium local rank/detectability and stoichiometric invariants: evidence A **within the reconstructed equations**. Practical information and dither tradeoffs: evidence B, conditional numerical experiments. Sensor hardware and plant-wide conclusions remain hypotheses pending model and data.
