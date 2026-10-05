# Ethylbenzene TFC: causal neural estimation and SISO/MIMO NMPC

This module implements the **first reactor** studied in Walter Yanko de
Aragao Brandao's UFPB TFC (2016). It is a new, reproducible Python study of
the five-state reduced model, not a run of the complete Aspen flowsheet.
The original `TFC.zip` was inspected without changing it. See
`results/source_manifest.json` for the archive hash and verified contents.
Original third-party papers, simulator binaries and teaching files are not
redistributed in this repository.

## Source recovery and equilibrium

The source is `TFC_WALTER_FINAL_imprimir.pdf`, pp. 42-47 and Table 4.1,
with the reaction document and Aspen export supplied in `TFC.zip`.
The supplied Luyben (2011) article, p. 656, explicitly gives reaction rates
in kmol/(s m3). The TFC's `min` label is corrected to seconds, then converted
to hours. The gas constant is 1.987 **cal**/(mol K), consistent with E in
cal/mol; the printed `kcal` label is corrected.

The TFC says Q was adjusted but does not report that value. A temperature
is fitted to the four reported MATLAB mole fractions, then an effective
constant heat-removal duty closes the printed energy balance. The nominal
point is approximately 160.876 C and xEB=0.281108. The heat-removal duty is
approximately **25.241 MW**. This is an effective reduced-model parameter,
not the 10.3 MW physical duty in Luyben's flowsheet. Printed constant heat
capacities and densities are retained. Their inconsistency with the sum of
the simulated concentrations is recorded. This study does not repair or
identify a full thermodynamic property model.

The original Aspen export connects `R1_TC.OP` to `R1.QR`, supporting thermal
actuation. MIMO uses an ideal heat-removal input with assumed limits of
0.6-1.4 times the reduced-model duty. The ethylene valve uses 0.04-2.0 times
its nominal flow, consistent with equal-percentage rangeability 50 and
capacity factor 2. The normal per-sample move limits are 0.12 and 0.08.

No hard temperature limit was identified in the TFC. **165 C is a research
assumption**, compared with the restriction disabled. The 220 C guard is
a numerical-domain stop, not a boiling-point or certified safety limit.

## Twenty useful combinations including a validation-tuned UKF baseline

| Estimator | State predictor | Online uncertainty |
|---|---|---|
| UKF | Printed physical balances | Fixed diagonal Q |
| LSTM-UKF | Physical balances | Genuine trained LSTM predicts bounded positive Q factors |
| NAKE-BB | Trained MLP dynamics | Validation residual variance + previous NIS EWMA |
| LSTM-NAKE | Trained MLP dynamics | Separate genuine trained LSTM predicts bounded positive Q factors |

Each is crossed with physical or blackbox NMPC prediction, and SISO or
MIMO control: 4 x 2 x 2 = 16. NAKE is a project working name. The Kalman
gain is computed from the UKF covariance; it is not learned and this is
not a KalmanNet reproduction. An LSTM-Q network changes uncertainty, not
the state-transition equations. A neural model has no physical-RHS residual
online. Known temperature observation remains h(x)=T in every estimator.

Four additional combinations use a **constant validation-tuned UKF Q**.
`tuning.py` evaluates factors 0.25, 1, 4, 16, 64 and 100 on 16 independently
seeded validation trajectories, minimizing normalized xEB and temperature
RMSE after the initial transient. One fixed Q is then used in every test
regime. The selected factor is recorded in `results/tuning_ukf.json`.
Total: 20 configurations, 720 closed-loop runs and 75 paired observer runs.
Comparisons report both nominal-Q and validation-tuned UKF baselines.

The blackbox is an affine learned increment plus a 12-48-48-5 tanh MLP,
composed over eight substeps. The nominal equilibrium anchor comes from
the training source. Both LSTMs use 17 causal features, a 12-sample window,
16 recurrent cells and five outputs. Recurrent weights and gates are
trained by actual BPTT/Adam in NumPy. JSON weights allow portable inference.

SISO tracks xEB with fE. MIMO tracks xEB **and temperature** with fE and Q.
MIMO therefore adds a thermal objective as well as an actuator. Results
report composition error, temperature and effort separately; a direct
SISO/MIMO ranking cannot isolate a change in the solver alone.

## Tests and information boundaries

Six closed-loop cases each last 10 h. The original regulatory steps are
preserved: +50% benzene and -50% recycle at 5 h. New tests are +/-10% xEB
servo steps at 3 h, return at 7 h, a 20% unobserved cooling-efficiency loss,
and a kinetic/input-noise/sensor-dropout stress case. Initial true state
is the reconstructed steady point, with a common biased estimate. Historical
startup is not included in the score because its source Q, covariance
matrices, integration step and PI gains were not recoverable exactly.

Three independently seeded noise sequences are paired across every
configuration. Commanded inputs are known; actual noisy inputs, kinetics,
heat-removal efficiency and true concentrations never enter the controller
or observer. Future disturbance schedules are not previewed. Offline
training uses state labels, as explicitly declared; held-out control runs
never train or select any network.

The plant uses independent DOP853 integration with dense temperature
monitoring at 21 points per sample. Controllers use native physical and
neural prediction with exact gradients and SLSQP. The neural C chain rule
is checked against an independent CasADi evaluator. The prediction
horizon is 40 samples (1 h), four moves with five-sample early blocks, and
the last move held. Sampling is 0.025 h (90 s), a new setting. Both prediction
models use the same horizon, bounds and solver settings within each mode.

Q is diagonal and positive by construction; posterior covariance uses
Joseph correction. Covariance repairs and concentration projections are
counted. Missing temperature measurements skip correction. Infeasible
constrained optimization invokes an explicitly logged emergency policy:
minimum fE and maximum Q for MIMO, minimum fE and fixed Q for SISO. It can
override normal move-rate limits. Unconstrained infeasibility holds the
previous command. Feasible candidates with failed solver status are retained
and counted separately. Predicted feasibility is not actual-plant safety.

Full IAE/ISE/ITAE and IAE after the scheduled event are retained. Rankings
use complete paired runs only and always disclose censored/failed runs.
The open-loop observer benchmark uses common truth trajectories to separate
estimation performance from controller-induced trajectory changes. Three
seeds support a preliminary comparison, not an experimental plant claim.

## Comparison with the original TFC control

The original Tables 4.1–4.4 are transcribed in `results/tfc_published.json`;
the original FKE equilibrium and published observer MAE/RMSE are included.
Figures 4.4, 4.7 and 4.8 are approximately digitized with recorded masks,
axis calibration, pixel uncertainty and embedded-image hashes. Occluded
segments remain missing. These are contextual historical results, not
recovered raw time series. The supplied sensitivity spreadsheets are
static parameter sweeps, not dynamic PI/EKF recordings.

The original Table 4.3 gives **larger closed-loop IAE and ISE** for the
benzene step, although its discussion claims improvement. These values
are preserved. Figure 4.8 has an ambiguous loop legend; colors and source
labels are preserved instead of silently swapping traces.

`baseline.py` adds a reconstructed PI + EKF architecture to the **identical
new plant, initial bias, measurement noise, seeds, sampling and actuator
bounds**: 18 closed-loop and 15 paired observer runs, all complete. EKF Q
is selected using the independent validation protocol (factor 64). PI
gains follow the TFC relay/Ziegler–Nichols recipe on a separate nominal
noise-free run: Kcu=45.878237, Tu=0.15 h, Kc=20.853744 and Ti=0.125 h.
The equal-percentage valve, new slew limit and anti-windup are explicit.
The chosen valve bounds imply nominal signal 82.28%, rather than the
78.5175% printed in the TFC; its inconsistent flow/signal specifications
are not claimed exactly reproduced.

Improvement is scored only against this reconstructed PI/EKF reference.
Physical SISO NMPC with validation-tuned UKF reduces paired post-event IAE
by 16.4% (benzene) and 97.9% (recycle), but increases servo error by 7–11%.
The large recycle gain includes oscillation of the reconstructed PI and
depends on its new tuning. Neural prediction and neural estimation are
not uniformly better. MIMO introduces a second actuator/objective; the
165 C restriction is absent from the original PI. These design changes
are flagged in every comparison. Temperature is reported separately.

Historical startup, numerical PI gains, initial covariance, Q/R and
sampling were not recovered, so **no causal percentage improvement over
the native TFC execution is claimed**. Descriptive full-window IAE/ISE/ITAE
and observer errors are retained side by side. All 7,200 PI samples were
reintegrated; state/metric errors and paired observer-truth error were zero.
See [the Portuguese comparison](results/COMPARACAO_TFC.md),
`improvement_vs_pi.csv/json` and `historical_audit.json`.

Recorded `q` and `cov_diagonal` arrays have physical state units squared
(concentration squared for the first four states, temperature squared
for the fifth). Normalization by XS is internal to covariance propagation.

## Reproduction

Requires Python 3.11+ and a C compiler such as `cc`.

```bash
python -m pip install -r research/ethylbenzene/requirements.txt
cd research/ethylbenzene
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python train.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -m unittest discover -p 'test_*.py' -v
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python experiment.py --workers 6
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python experiment.py --openloop --workers 6
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python tuning.py --workers 6
python audit.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python baseline.py --workers 3
python historical.py --output /absolute/path/for/reports
python report.py --output /absolute/path/for/reports
```

`train.py --stage transition` and `--stage lstm` can run separately. Compiled
kernels are cached by model and source signature. Run checkpoints are
signature-checked before reuse. `experiment.py --smoke` runs all 16 combinations
on the original benzene test. Full results and weights are versioned; raw
traces are supplied separately to avoid inflating the Git repository.
Pass `--source-pdf /path/to/TFC_WALTER_FINAL_imprimir.pdf` to `historical.py`
to redo digitization; otherwise it uses the versioned digitized CSV.
Historical source PDFs remain private. Nine numerical tests cover this
module, including EKF derivative/prediction and PI anti-windup reversal.

## References

Brandao, W. Y. A. (2016), *Uso de sensores virtuais como observadores de
estado aplicados na dinamica e controle de processos quimicos lineares e
nao lineares*, UFPB.

Luyben, W. L. (2011), *Design and control of the ethyl benzene process*,
AIChE Journal 57(3), 655-670. DOI: 10.1002/aic.12289.

Julier and Uhlmann (2004), *Unscented Filtering and Nonlinear Estimation*,
DOI: 10.1109/JPROC.2003.823141.

Hochreiter and Schmidhuber (1997), *Long Short-Term Memory*,
DOI: 10.1162/neco.1997.9.8.1735.

Revach et al. (2022), *KalmanNet: Neural Network Aided Kalman Filtering
for Partially Known Dynamics*, arXiv:2107.10043. Related work, not a
reproduced architecture in this module.
