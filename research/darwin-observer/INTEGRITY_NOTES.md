# Integrity notes

- Primary model: ProcessLab tabulated six-state PG, commit f4444d4c238291b8633743930249ee387ad94541.
- A complete historical variant is separately implemented and numerically checked against recovered source. No thermodynamic parameter mixing.
- Discovery receives Record(inputs, measurements, seed, dt), never Episode.truth or hidden-law metadata.
- Training and validation episodes have distinct seeds. Main test episodes are independent of both. No new model was fitted from final main-test results.
- Blind diagnosis uses a causal prefix/validation/future partition within a single episode. Its correction starts only at sample 91; it is not counted as a separate full-episode blind commissioning result.
- All reported trajectories are synthetic. Metrics are calculated from files produced by the runner, not hand-entered demonstrations.
- Profile likelihood and local sensitivity ranks are conditional diagnostics. They do not establish globally unique physical explanations.
- The adaptive baseline estimates UA and reaction-rate multipliers. It is not an ideal all-parameter oracle.
- Model uncertainty is not fully propagated into reported Gaussian covariance intervals. Coverage can be poor despite low RMSE.
- Constraint monitoring and fallback are simulation protections, not certified industrial safeguards.
- C_noise has 44 ambiguous classifications; H0 has one ambiguous classification. No incorrect conclusive classifications occurred in these six tested categories, but this is not a universal diagnostic guarantee.
- Main control runs did not require fallback. Negative tests and separate online ablations exercise and log reversions.
- Removing individual gates in the ablation runner relaxes the acceptance policy as well as ranking. Those results are exploratory, not clean causal estimates of one mechanism in isolation.
- The Windows launchers are prepared; the executed validation platform was Linux/Python 3.12.14.
- Browser screenshots were used only for internal visual inspection and are not part of the deliverable package.
- Release hardening adds an explicit domain check for every planned NMPC move and predicted reactor temperature. All 100 corrected-control episodes were replayed to compare trajectories and decisions exactly; the release verification JSON records the result. Original campaign timing columns predate this added check and are not a benchmark of the final release on Windows.
