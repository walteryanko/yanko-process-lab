# Critical literature review — 20 October 2026

This is a targeted, source-verified review, not an exhaustive systematic review.
No worldwide novelty claim is justified by this search. Publisher metadata, author-hosted
manuscripts and institutional records were preferred. Paywalls and inaccessible pages were recorded.

| Topic | Verified antecedent | Relation and limit of the present contribution |
|---|---|---|
| Nonlinear observability | Hermann and Krener (1977), DOI 10.1109/TAC.1977.1101601 | Local rank conditions are established. Here exact PG symmetry is proved directly; finite numerical rank is not called structural proof. IEEE page had a robot gate. |
| Reactor indistinguishability | Schaum, Moreno, Díaz-Salgado and Alvarez, IFAC DYCOPS 2007 | Nonmonotone kinetics already produce concentration ambiguity with thermal sensing. Our PG construction instead uses calorimetric compensation and shared dilution. |
| Identifiability | Villaverde, Barreiro and Papachristodoulou (2016), DOI 10.1371/journal.pcbi.1005153 | State augmentation and Lie-derivative identifiability are established; this campaign does not invent that analysis. |
| Empirical reduction/information | Lall, Marsden and Glavaski (2002), DOI 10.1002/rnc.657 | Trajectory sensitivity and empirical reduction have long precedents. Our finite-horizon singular spectra are diagnostic, not an exact global Gramian theorem. |
| MHE | Rao, Rawlings and Mayne (2003), DOI 10.1109/TAC.2002.808470 | Constrained deterministic estimation has stability conditions. The six-step implementation here does not establish those conditions or represent a fully tuned best-in-class MHE. |
| Output-feedback MPC | Rawlings, Mayne and Diehl, second-edition textbook, author site | Standard foundations and implementation reference. State error, model error and constraints interact; new guarantees are not inferred from trajectory plots. |
| Regret under measurements | Goel and Hassibi, PMLR 144 (2021), 1270–1280 | Prior regret-optimal linear control compares to an offline benchmark. Here the comparator knows the initial chemical world but uses the same finite action class; these regret definitions are different. |
| Decision-focused prediction | Elmachtoub and Grigas (2022), DOI 10.1287/mnsc.2020.3922 | Prediction error and decision loss need not align. No novelty is claimed for that principle. Our setting is dynamic inferential control. |
| Dual control | Klenske and Hennig, JMLR 17(127), 2016 | Actions may change learning. The present scenario controller does not optimize future observation distributions, so it is not a full dual controller. |
| Belief MPC, recent | Cao et al., arXiv:2604.24663 (2026), preprint | Linear dynamics, bilinear sensing and input-dependent Kalman covariance. Its favorable synthetic results do not establish gains for this nonlinear reactor. |
| Latent-risk planning, recent | Enwerem, Baras and Belta, arXiv:2604.03868 v2 (2026), preprint | Measured state with latent parameters, CVaR and MPPI. Our ambiguity is chemical state with thermal observations; no CVaR guarantee is imported. |
| Reactor physics | Brandão dissertation (2019), pp. 30–32; recovered modeloCT.m | Original six-state equations and sensors. Table/coded enthalpies differ; M0 follows code and preserves its Arrhenius offset. |
| Reaction enthalpy correction | Fogler, UMich living example 12-4 | The public code contains a temperature correction from reaction Cp difference. It supports checking Kirchhoff consistency, not importing its different operating point or enthalpy as a calibrated replacement. |

Searches also covered set-membership nonlinear MPC (Canale, DOI 10.1002/rnc.2878;
publisher full text was inaccessible), inferential control, information-constrained control,
value of chemical sampling and chemical-reactor observability. Coverage of the entire
2025–2026 literature and full-text comparisons remains incomplete.

## Claim-by-claim originality assessment

1. Two invisible chemical modes in the constant-Cp PG model: case-specific construction,
   already present in recovered internal ICAC material; not a new discovery of this campaign.
2. Persistence under a reciprocal jacket and consistent temperature-dependent reaction
   enthalpy: explicit extension of that construction; potentially useful audit result.
3. Dimension controlled by the span of species heat-capacity functions: candidate compact
   structural characterization. Priority not established; compare against general quotient
   systems, reaction invariants and structural-identifiability literature before claiming novelty.
4. Half-separation estimation bound and convex regret bound: elementary consequences of
   known inequalities, not independent major theoretical novelty.
5. Controller superiority: must be determined by paired test and confirmation data, including
   adverse regimes, stronger continuous baselines, safety and computation.
6. Publication: a reproducible negative or mixed result may be valuable. Submission readiness
   still requires recovered historical replay, better physical properties, stronger baselines and
   independent expert review.

All bibliography entries are in manuscripts/references.bib. Preprints are explicitly labeled.
