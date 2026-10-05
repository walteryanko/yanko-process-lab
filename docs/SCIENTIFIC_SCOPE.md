# Scientific scope and reproducibility

The inspected implementation uses six coupled states for species concentrations and reactor/cooling-coil temperatures. Matrix routines support covariance propagation and correction in EKF and UKF observers. Controllers compare measured or estimated quantities with configured targets.

The upstream project documents a 2019 academic dissertation as methodological context. This package does not redistribute the dissertation, pages, plots or academic datasets. Before broad source publication, confirm attribution details, code ownership and permission for any material derived from that work. Equations and implementation provenance are reviewed separately from rights to the dissertation's expression and figures.

The literal table yields 340.303489 K rather than the reported 332.3 K. In the current patch, the default uses a transparently calibrated effective enthalpy at the single historical nominal point; the literal variant is retained. This resolves nominal mathematical stationarity but does not identify the true enthalpy or recover the original Simulink model. See EQUILIBRIUM_ADJUSTMENT.md.

The research module tests five UKF/neural variants on the calibrated equations. Its neural model is a trained causal window-statistics MLP, not an LSTM or a reproduction of KalmanNet. Only synthetic data is used. Q tuning and neural labels use training trajectories exclusively. Nine regimes and disjoint seeds expose both improvements and deteriorations. Published Q is a historical tuning reused on the adjusted model; an additional coarse training-only retuning is provided. R is fixed and can be mismatched in noise tests. No uniform superiority, industrial accuracy, general uncertainty calibration or closed-loop NMPC improvement is established.

Validation here establishes regression behavior for this numerical implementation. It does not establish estimator accuracy under arbitrary disturbances, global optimizer convergence, real-plant stability or industrial safety.

