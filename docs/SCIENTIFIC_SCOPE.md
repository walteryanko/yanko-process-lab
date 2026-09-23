# Scientific scope and reproducibility

The inspected implementation uses six coupled states for species concentrations and reactor/cooling-coil temperatures. Matrix routines support covariance propagation and correction in EKF and UKF observers. Controllers compare measured or estimated quantities with configured targets.

The upstream project documents a 2019 academic dissertation as methodological context. This package does not redistribute the dissertation, pages, plots or academic datasets. Before broad source publication, confirm attribution details, code ownership and permission for any material derived from that work. Equations and implementation provenance are reviewed separately from rights to the dissertation's expression and figures.

The nominal equilibrium produced by the implemented equations differs from the reference value. The tests preserve and expose that fact. A complete reproduction would require reconciling units, parameters, operating conditions, assumptions and optimizer differences against the source; that scientific reconciliation was not performed in this publication session.

Validation here establishes regression behavior for this numerical implementation. It does not establish estimator accuracy under arbitrary disturbances, global optimizer convergence, real-plant stability or industrial safety.
