| Question | Evidence class | Conclusion |
| --- | --- | --- |
| Q1 | Demonstrated mathematically | M0 has a two-dimensional chemical indistinguishability class; six free states are not fully observable. |
| Q2 | Partially supported | Constant-Cp ambiguity survives consistent reaction enthalpy and reciprocal jacket; physically calibrated M1 remains unavailable. |
| Q3 | Demonstrated mathematically | The sufficient invisible subspace is orthogonal to the functional span of CpB,CpC,CpM, with deltaCA=0. |
| Q4 | Demonstrated mathematically | Half separation is an instantaneous two-world lower bound; the integrated bound is distinct. |
| Q5 | Experimentally supported | Finite-class costs show when chemical ambiguity changes actions; no global continuous optimum certificate. |
| Q6 | Experimentally supported | The claimed reliability is contradicted: zero-RMSE state reference and better-RMSE estimator-only adaptation can have worse IAE. |
| Q7 | Experimentally supported | Predictor sharing reduced mean IAE by 39.91% versus estimator-only correction, with independent confirmation. |
| Q8 | Inconclusive | Incremental ambiguity gains of 0.63%/0.66% have CIs including zero; the 10% target was not met. |
| Q9 | Experimentally supported | Adverse heat-transfer/property regimes and denser-grid checks are retained; no uniform robust advantage. |
| Q10 | Partially supported | Only the declared CC sampling schedules/noises/delay approximation were tested; no globally optimal sensor frequency. |
| Q11 | Demonstrated mathematically | Exact indistinguishable-pair bounds apply independently of estimator architecture under stated information. |
| Q12 | Partially supported | Proof transfers to the same dilution/kinetic/calorimetric structure; numerical gains do not transfer automatically. |



# Ablation, falsification and interpretation

The common-information comparisons separate point versus representative decisions, estimator-only versus predictor-sharing adaptation, and a denser finite grid. Exact inventory and chemical sampling are additional-information arms. A better result there cannot be attributed solely to a more sophisticated algorithm.

The core structural result is insensitive to replacing one-way coil coupling with a reciprocal jacket while retaining constant heat capacities. Synthetic property dependence can break the particular two-species compensation, but tiny output differences may remain undetectable at realistic sensor precision. The numerical rank map is a grid of initial states, not a map of feasible steady operating points. The Fisher matrix corresponding to independent Gaussian measurement noise is the sensitivity Gram matrix; no calibrated posterior coverage guarantee follows from its singular values.

The expected-cost proposition provides a stronger null case: symmetric exact chemical twins only add a plan-independent variance term to the quadratic cost. P1 therefore has no theoretical action advantage over the point policy under those assumptions. The post-protocol audit checks this identity on nine plan/reference/horizon combinations.

Positive grid regret establishes conflict within the stated candidate class. Grid minimax is not a lower bound on all causal controllers. The state-informed reference may have a smaller loss, but unreachable references and physical cooling limits remain. The initial failed numerical effect-size expectation is retained: a thermal difference of 9.516165278e-7 K did not exceed an arbitrary 1e-6 K threshold. The implementation test was replaced by an exact capacity identity, while scientific separability is reported without imposing a favorable outcome.

# Limitations and publication readiness

Historical 0.951143, 0.850912, 0.358768 and 14.60% outcomes have identified documentary sources but were not replayed under their original protocols. The current finite-grid two-block NMPC, fixed PI and short-window MHE do not establish comparison against the strongest available baselines. Longer horizons, six-move continuous optimization, systematic tuning on development data, additional sensor variables and model-family closed-loop stress tests remain.

Beyond the explicitly derived M0 quotient minor, full-model Lie-derivative sweeps, practical lower-bound calibration, genuine chemical-analyzer dynamics, interval safety between samples, rigorous recovery margins and target-Ryzen timings remain unexecuted. MHE covariance is inherited from its UKF arrival approximation; its coverage is diagnostic only. Full NEES is not reported because full covariance histories were not saved. Decision timing excludes some sensor-scheduling calculations; total episode time is separately available. No on-spec production or economic loss is claimed because no commercial specification or prices were defined. The code is a simulator study, not an industrial trial.

The article is not ready for submission as a claim of a superior controller. Its defensible research direction is the structural classification and reproducible decision audit, subject to physical property validation, a fuller novelty review and independent technical review.

# Conclusions

The recovered model places a specific information limit on chemical reconstruction that cannot be cured by estimator architecture alone. Reciprocal jacket dynamics are insufficient to remove this ambiguity under constant heat capacities. Whether that ambiguity matters for control depends on the objective, feasibility and action class. The accompanying data show the realized outcomes of the declared comparisons, including negative cases. They support a bounded computational research contribution while leaving the full original campaign incomplete.

# Scientific claims audit

