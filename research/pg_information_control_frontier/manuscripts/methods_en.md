# Introduction

Inferential quality control relies on the information carried by measured variables and on the predictions used to choose actions. A smaller concentration RMSE need not reduce closed-loop loss. This study audits a six-state propylene-glycol CSTR before evaluating additional estimation or control complexity. Two questions are separated: whether temperature-only measurements leave a demonstrable chemical ambiguity, and whether explicitly representing that ambiguity improves control against equally informed comparators.

The recovered internal ICAC study already reported calorimetrically indistinguishable states and decision conflicts. Its numerical percentages are historical evidence, not reproduced findings of this campaign. The current branch and complete raw ICAC archive were unavailable. This manuscript therefore reports an independent computational core, with remaining publication requirements explicitly identified.

# Related work

Nonlinear observability and identifiability theory distinguish information loss from numerical estimation difficulty [@hermann1977; @villaverde2016]. Reactor concentration ambiguity is not new: nonmonotone kinetic examples already motivate detectable output-feedback designs [@schaum2007]. Empirical trajectory methods can reveal weak directions without proving a global structural result [@lall2002].

Constrained MHE and output-feedback MPC have established assumptions and stability frameworks [@rao2003; @rawlings2017]. Regret-optimal measurement feedback has a different benchmark in existing linear-control results [@goel2021]. Decision-aware prediction and dual control also precede this study [@elmachtoub2022; @klenske2016]. Recent belief-space approaches treat input-dependent observations or latent parameter risk [@cao2026; @enwerem2026]; those preprints do not establish reactor performance. The present candidate contribution is a traced, model-specific heat-capacity classification and its connection to finite-horizon decision experiments.

# Physical process model

The historical source is Brandão's dissertation and recovered executable MATLAB model [@brandao2019]. The reaction is A+B to C, with methanol M treated as inert, constant reactor volume and a level-controlled outlet. Concentrations are kmol/m3, temperatures K, time h and heat kJ. Let
$$v=F_A/\rho_A+F_B/\rho_B+F_M/\rho_M,\quad D=v/V,\quad
r=k_0\exp[-E/(R(T+0.183333333333))]C_A.$$
The balances are
$$\dot C_A=F_A/V-DC_A-r,\qquad \dot C_B=F_B/V-DC_B-r,$$
$$\dot C_C=-DC_C+r,\qquad\dot C_M=F_M/V-DC_M.$$
With $W=\sum_i c_{p,i}C_i$ and $F_{cp}=F_Ac_{p,A}+F_Bc_{p,B}+F_Mc_{p,M}$,
$$Q=m_wc_{p,B}(T_a-T)[1-e^{-UA/(m_wc_{p,B})}],$$
$$\dot T=\frac{Q+F_{cp}(T_0-T)-\Delta H_r rV}{VW},\qquad
\dot T_t=\frac{m_wc_{p,B}(T_a-T_t)-Q}{\rho_BV_tc_{p,B}}.$$
Only $T,T_t$ are measured. The sole optimized input is $m_w=q\,453.59237$ kmol/h; current feeds are known, future disturbances are not. The historical asymmetry is retained: $T_t$ does not enter $Q$.

The executable enthalpy is -83736 kJ/kmol; the dissertation table instead lists -91556.90. The archive's rounded imperial conversion and Fahrenheit offset are preserved as benchmark conventions, not new physical findings. The public Fogler example also contains a temperature correction to reaction heat, but at different operating conditions [@fogler_examples]. It does not justify replacing the dissertation constants without calibration.

A related teaching case uses excess-water first-order kinetics and models the liquid as nonideal [@chan2004]. This supports retaining the historical kinetic approximation as a benchmark, while showing why ideal-mixture calorimetry alone cannot establish physical equivalence in a real reactor.

## Explicit physical alternatives

M1H adds Kirchhoff consistency: $\Delta H_r(T)=\Delta H_r(T_r)+\int_{T_r}^T(c_{p,C}-c_{p,A}-c_{p,B})\,d\theta$, with the historical enthalpy assumed to refer to nominal $T_r=332.333618020$ K. This reference is not independently known. M1J also uses $Q=G(T_t-T)$ and the existing jacket storage balance. The conductance $G=m_{w0}c_{p,B}[\exp(UA/(m_{w0}c_{p,B}))-1]$ matches nominal stationary cooling, rather than asserting that coil UA and mixed-jacket conductance are identical.

M2L and M2Q use $c_{p,i}(T)=a_i+b_i(T-T_r)+c_i(T-T_r)^2$, where $a_i$ are historical capacities. Relative slopes are (0.0015,0.0002,0.0025,0.0010) per K; relative curvatures are (0.000010,0.000002,0.000016,-0.000003) per K squared. M2L sets all curvatures to zero. Feed sensible enthalpies and reaction enthalpy are integrated consistently. These are synthetic sensitivity models. They are not calibrated physical-property correlations, and no one is called the validated M1 of the original research request.

# Estimation and control architectures

B1 uses a six-state UKF and nominal predictive model. B2_estimator augments the UKF with log kinetic and heat-transfer factors, while retaining a nominal predictor. B2_both shares the same estimated factors with the predictor. Neither receives true parameters. B0 is a documented fixed PI using the inferred product, with gains 4 and 2 and antiwindup. It is not a reproduced optimally tuned historical cascade.

B3_assumed_inventory imposes nominal initial inventories. B3_known_inventory receives exact initial inventories once, and therefore has additional information. The reduced state is $(C_C,T,T_t)$; conserved totals follow their feed/dilution equations. B4 is a deterministic six-step MHE with an approximate arrival prior, no process-noise decision variables and 18 function-evaluation budget. B5 uses the true current state only as a diagnostic oracle, with nominal predictive parameters.

P1 evaluates mean cost of three representatives. P2 minimizes their largest regret. P3 combines this rule with causal parameter adaptation. P4 uses the robust action when representative first actions differ by at least 0.2 nominal coolant units; otherwise it applies the adapted nominal policy. The representatives are a UKF point and calorimetrically compensated product offsets of plus/minus $0.4e^{-\int Ddt}$. They are not a certified set enclosure or a posterior sample; a finite set cannot represent every possible physical state.

P5 variants retain nominal control and add chemical samples: initial only; four periodic samples; event-triggered with quota four; three-step delay; higher measurement noise; or up to eight frequent samples. Immediate product samples have standard deviation 0.03 kmol/m3, the noisy case 0.15. Delayed innovations are transported approximately with dilution and an explicit variance increment; a full out-of-sequence smoother is not implemented. Event requests use available belief width and previous action disagreement, never future measurements.

The standard policy enumerates at most 25 two-block sequences: the first action lasts three steps and the second eleven. Candidate increments are five equally spaced values from -0.4 to 0.4. All methods in each scenario share $0.05\le q\le3$ and step change at most 0.4; saturation cases use the same lower maximum 1.3 for all methods. The sampled constraint is $T\le344.261111$ K. A no-common-feasible-plan event triggers an explicitly logged least-violation fallback; no safety guarantee is inferred.

The dimensionless horizon cost is
$$J=\sum_{j=1}^{14}\left[0.8\left(\frac{C_{C,j}-r_k}{2.295764605}\right)^2+
1000\left(\frac{\max(T_j-344.261111,0)}{160/1.8}\right)^2\right]
+0.2[(q_1-q_{\rm prev})^2+(q_2-q_1)^2].$$
This cost is not IAE. B1_continuous additionally optimizes the same two-block problem using SLSQP, initialized by the grid solution; it is a local numerical comparator, not the full historical 57-step/six-move NMPC.

# Experimental methodology

The frozen protocol specifies 14 scenarios, 19 methods and 20 paired seeds per combination. Sixty intervals of 0.015 h give 0.9 h per trajectory. Scenarios include nominal operation, reference changes, kinetic and heat-transfer errors, signed inventory ambiguity, current feed disturbances, heat-capacity error, correlated noise, sensor dropout, saturation, combined perturbations, a state outside the representative prior and an unreachable reference. Hypothetical structural-physics variants are analyzed separately from the M0 control benchmark.

The UKF prior standard deviations are (0.15,0.8,0.4,0.3,0.5,0.5); process covariance diagonal is (2e-6,2e-5,2e-6,1e-7,0.015,0.006). Temperature-noise standard deviations are (1.385,1.062)/1.8 K. Adaptive log factors have initial variance 0.15 squared, process variance 1e-5 and bounds [-0.5,0.5]. UKF alpha=0.5 and beta=2. No tuning uses held-out outcomes.

Main seeds are 4100–4119. Confirmation seeds 8100–8119 address four declared scenarios and five relevant methods. Validation seeds 101–103 evaluate a denser grid. Development seed 11 is used for short runtime checks. Noise trajectories are matched across methods. Bootstrap units are paired seeds; finite-suite means first average each seed across the fixed scenario list. Uncertainty describes this finite suite, not an industrial population. Three primary contrasts receive Holm adjustment; other contrasts remain exploratory.

The plant uses RK4 with 12 substeps, compared against SciPy DOP853 with rtol 2e-11 and atol 1e-12. Prediction uses three substeps; filtering uses four. Physical state trajectories are not clipped. Filter positivity and covariance repairs are logged. Scalar metrics are independently recalculated from saved trajectories. Timing is from a Linux hosted CPU, without evidence of performance on the target Ryzen system.
