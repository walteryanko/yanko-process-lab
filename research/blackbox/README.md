# Fully learned dynamics in NMPC and NAKE: calibrated CSTR

This experiment extends the earlier open-loop `research/nake` comparison to
inferential closed-loop control. The physical plant is always the calibrated
six-state CSTR. The controlled variable is product concentration CC; the sole
manipulated variable is the coolant molar flow mw. Only T and Tt are measured.

## Four combinations

| Configuration | Predictor inside NMPC | State estimator predictor |
|---|---|---|
| physical_ukf | Physical balances | Physical UKF |
| physical_nake | Physical balances | Black-box NAKE |
| neural_ukf | Learned state transition | Physical UKF |
| neural_nake | Learned state transition | Black-box NAKE |

The network replaces the six-state prediction function, rather than emitting
control actions directly. The same SLSQP optimizer, objective and actuator
bounds apply to all configurations. An identity state skip and a fitted affine
map plus tanh MLP are learned from synthetic transitions; there are no reaction
or heat-transfer formulas in neural inference. The five learned substeps sum
to Ts=0.015h. One nominal training datum anchors the equilibrium.

The black-box NAKE uses this network to propagate sigma points. Its known
observation model selects T and Tt. A Joseph covariance correction preserves
positive semidefiniteness. The process covariance includes an independent
validation residual variance and is inflated using an EMA of **past** NIS/dof,
bounded from 1 to 25. It does not learn the Kalman gain, and is not a reproduction
of KalmanNet. It is also distinct from the earlier grey-box NAKE which adjusted
UA/k0. No simulator truth or physical parameters enter the online learned model.

## Historical tests and qualifications

The classic regulatory tests use FA -10%, FB +10%, T0 -10% in Fahrenheit and
Ta -20% in Fahrenheit at t4h, returning to nominal at t8h. Servo +10% follows
the same schedule. Severe NMPC tests use FA -15%, T0 -30% in Fahrenheit and
servo -20% at t4h; the last reference stays reduced. These correspond to
dissertation sections5.3.1 and5.3.2 and manuscript REV05.

Two thermal illustrations are reconstructed separately: Fig39 visually gives
approximately +20% servo at t3h (the text does not supply those numerical
values); Figs37-38 concern startup, whose six initial states are not stated.
We use a reactor initially filled with unreacted nominal feed at T0, with Tt=Ta.
Those assumptions appear in `protocol.json`; they are not claimed as recovered
Simulink settings.

Every case runs with and without the predicted T<=344K constraint. The source
uses an unspecified large penalty QR; this implementation instead uses hard
prediction inequalities. All runs retain mw bounds22.7--1366.2kmol/h. A 355.4K
plant event stops integration because the liquid-phase model lacks vaporization.
Incomplete runs cannot be credited for lower truncated IAE. Actual intrastep
temperature peaks and violation durations are measured independently. Nominal
prediction feasibility does not certify safety with neural error or noise.

Historical controller settings are retained: Ts=.015h, prediction horizon57,
move horizon6, weights.8/.2, and the normalized CC/mw objective. The final move
is held for the rest of the prediction horizon. Future disturbances and targets
are not previewed. SLSQP with exact sensitivities replaces MATLAB fmincon:
CasADi for the physical model, and an analytic neural chain rule compiled in C.
The independent NumPy neural evaluator verifies the compiled kernel.

Synthetic noise: unobserved independent1% Gaussian multiplicative disturbances
on each input per sample and additive sensor errors of1% nominal T/Tt in kelvin.
The four configurations share process/measurement draws and initial errors.
These runs reconstruct the documented protocol; exact historical random draws,
noise spectra, Simulink integrators and optimization tolerances were unavailable.

The effective enthalpy remains -84138.653537kJ/kmol, calibrated at the nominal
332.3K point. This is a single-point effective coefficient, not the identified
chemical enthalpy. All training labels and test plants use this adjusted model.

## Reproduce

Python with NumPy, SciPy, scikit-learn, CasADi, matplotlib and reportlab;
a C compiler is needed for CasADi JIT. Run from the repository root:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python research/blackbox/train.py --epochs 400
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -m unittest discover -s research/blackbox -p 'test_*.py' -v
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python research/blackbox/experiment.py --seeds 3 --workers 8
python research/blackbox/report.py --out /absolute/output/path
```

Weights are JSON, not pickle. Training excitation uses seeds6101/6111;
validation6201 and multistep validation6501; control tests8001--8003. Test
trajectories are never used to train the neural transition or select its weights.
Training rejection counts refer to synthetic samples outside the intended liquid
operating domain, not suppressed control-test failures. Raw run metrics and
all trajectories include optimizer failures, fallback use and stop reasons.

An additional 24-run diagnostic uses a 4K prediction margin in startup and
the thermal servo case. It was chosen by rounding up the independent57-step
validation maximum3.710K, not by optimizing control test results. Reproduce:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python research/blackbox/experiment.py --seeds 3 --workers 4 --cases thermal_servo startup --constraints on --margin 4
```

This leaves primary metrics unchanged and writes metrics_margin/protocol_margin.
It reports actual temperatures, the added tracking cost, solver statuses and
maximum-cooling fallbacks. An observed safe finite test set is not a formal
robustness or probabilistic guarantee.

Primary background: Revach etal., KalmanNet, IEEE TSP2022, arXiv2107.10043;
Shrivastava, Modeling and Control of CSTR using Model based Neural Network
Predictive Control, arXiv1208.3600; SciPy official SLSQP documentation. These
motivate the architectures; this code does not reproduce either publication.
