# NAKE research experiment on the existing six-state CSTR

This research module continues the existing Yanko Process Lab equations. It
uses the explicitly calibrated effective enthalpy documented in
`docs/EQUILIBRIUM_ADJUSTMENT.md`. It does not replace the web application's
observer or its controller and does not deploy the separately hosted site.

## Run and reproduce

From the repository root, Python 3.10+ and Node 24 for the parity test:

```sh
python -m pip install -r research/nake/requirements.txt
python -m unittest discover -s research/nake -p 'test_*.py' -v
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python research/nake/experiment.py --seeds 8 --steps 160
python research/nake/equilibrium_validation.py
python research/nake/report.py
npm test
```

The complete experiment trains from scratch. For inference only, NumPy/SciPy
and the portable JSON weights suffice; sklearn is used offline for training.
Do not use untrusted pickle files: model weights are plain JSON and the forward
pass is independently checked against the training implementation.

## Precisely defined variants

| Name | Model | Process covariance |
|---|---|---|
| ukf_published | adjusted balances | historical published Q |
| ukf_tuned | adjusted balances | bounded grid tuning using training only |
| nake_q | adjusted balances | MLP adapts six diagonal Q elements |
| nake_dynamics | MLP adjusts UA and k0 in balances | same fixed Q as ukf_tuned |
| nake_hybrid | MLP adjusts UA and k0 in balances | MLP adapts six diagonal Q elements |

Both neural mechanisms use the SAME trained tanh MLP (26 -> 32 -> 24 -> 8).
Dynamics correction is structured parameter correction, not an unconstrained
six-state black-box dynamics replacement. This is a prototype defined here,
not a reproduction of KalmanNet and not a claim that NAKE is a new method.
It uses a causal window-statistics MLP, **not an LSTM**. NAKE is a working name.

Features are estimated prior states, present commanded inputs, input changes,
and statistics of the previous 12 normalized innovations plus their exponential
moving average. No current measurement is reused in prediction, no future
measurement, hidden true concentration or simulator parameter enters online
inference. The UKF measurement step sees T and Tt only. Missing measurements
are masked (one-sensor update or prediction only).

The MLP learns offline log-UA/log-k0 corrections and log Q ratios from simulated
labels. UA/k0 labels are known simulator parameters; Q labels are bounded
one-step nominal-model squared error divided by tuned Q. Those labels are a
heuristic covariance teacher, **not a covariance-identification theorem**.
Q has positive bounded diagonal values; UA/k0 scales are bounded to 0.7–1.3
and smoothed. Residual mismatch may bias means, so coverage/NEES/NIS are also
reported. R stays fixed: Q-adaptation alone is not a sensor-noise estimator.

## Protocol

36 training trajectories (seeds 100–135), six separate validation trajectories
(500–505), and eight independent test seeds (900–907) for each of nine regimes.
Each has 160 samples, Ts = 0.015 h (2.4 h total). Whole trajectories form splits.
Each estimator sees the same commands, noise, missing-data pattern and initial
estimate on each test trajectory. Test data and weights are never mixed.
MLP fitting uses 5760 simulated training samples, without an internal shuffled
validation split; the explicit six-trajectory validation is reported separately.

Q tuning uses a fixed nine-candidate grid on a predeclared training subset,
minimizing six-state normalized RMSE; it is a bounded, coarse baseline tuning,
not the original paper's SQP optimum nor a globally optimal UKF baseline.
The adjusted published Q baseline is retained as a separate comparison.

The sensor calibration is a declared **synthetic assumption**: independent
Gaussian standard deviations 0.35 K and 0.30 K. It differs from the historical
web demo's 1% sensor-noise choice. Variable-noise tests multiply these by three
without informing the estimators. There is no independent additive state-noise
in the simulated plant; Q models parameter/discretization uncertainty.

All research variants share UKF alpha=0.2, beta=2, kappa=0, scaled-coordinate
covariances, identical P0, and an exact linear T/Tt update with Joseph covariance.
Plant truth uses DOP853 with tight tolerances; filtering uses RK4. The existing
web/CLI observer remains Euler-based; do not compare this benchmark's scores
to that observer as if their integration and noise settings were identical.

Regimes: matched nominal, startup, feed steps, coolant steps, UA -12%, k0 +10%,
noise x3, partial/complete sensor dropout, and combined out-of-training-range
UA -20% / k0 +18% with feed/noise changes. Input ranges and parameter changes
are experimental scenarios, not validated industrial operating envelopes.

Outputs include six-state RMSE/MAE, CC interval coverage, NEES/NIS,
latency, covariance repairs, failure counts and thermal excursions. Statistics
aggregate by independent seed, not by treating time samples as independent.
Reported paired bootstrap intervals describe this small simulation sample.
No NMPC closed-loop comparison, MATLAB execution, plant experiment or full
original-Simulink recovery is claimed in this session.

References: Brandão (2019), *Uso de observadores de estado aplicados no controle
inferencial preditivo de processos não lineares*, equations 33–55 and Tables
1–2. Julier & Uhlmann (2004), *Unscented Filtering and Nonlinear Estimation*,
DOI 10.1109/JPROC.2003.823141. Revach et al. (2022), *KalmanNet: Neural Network
Aided Kalman Filtering for Partially Known Dynamics*, arXiv:2107.10043.
Original thesis/paper files are not redistributed with this code.
