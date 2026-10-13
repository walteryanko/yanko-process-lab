# Recovery and scientific reconciliation — 13 October 2026

## Repository evidence

| Reference | Commit found | Contents/status |
|---|---|---|
| main | f4444d4c238291b8633743930249ee387ad94541 | Original TypeScript numerical core |
| research/nake-calibrated-equilibrium | f9ad5c7743094681eb66a78b47936eae0cf5cb48 | Adjusted equilibrium, NAKE/black-box work |
| research/ethylbenzene-combinations | 16aaafb63572d62e0e3341e26d8317b0651bdde0 | EB reconstructed model, comparison and results |
| research/beyond-conventional-operation-20261010 | 88c40e65204fa6aa5bed02cc64fb15be79a53bb1 | PG/EB source archives, models, campaigns |
| research/rsi-processlab-20261011 | 88c40e65204fa6aa5bed02cc64fb15be79a53bb1 | Same commit as beyond; no RSI code directory |

Implementation branch: `work/ycs-processlab-studio-20261013`, based on `88c40e6`.
No history or historical result files were overwritten. There were no tags returned
by the actual `git ls-remote` inventory. Full Git clone recovered the Latin-1 original
MATLAB file, including its original bytes; text-only connector decoding could not.

## Assets

| Asset | Origin and path | Classification | Reproduction scope |
|---|---|---|---|
| PG MATLAB | Walter Yanko, 2019; research/beyond/provenance/pg_modeloCT.m | VERIFIED source recovery | Literal equations and units checked against independent imperial RHS |
| PG Python | research/beyond/vendor/pg_reference.py | VERIFIED numerical translation | Equilibrium, derivative parity, thermal ambiguity and integration |
| TS PG | lib/simulation/model.ts | VERIFIED as its own implementation | Existing 11 tests preserved and executed |
| EB Python R1 | research/beyond/vendor/eb_reference.py | PARTIALLY VERIFIED / thermally INCONSISTENT | Archived equations, nominal equilibrium and stoichiometry, not full plant |
| PG/EB campaigns | research/beyond | PARTIALLY VERIFIED | Existing 15 scientific gates executed; entire campaigns not rerun |
| AIRE | AIRE_NMPC_Reproducivel.zip, user scientific archive (213,580,036 bytes) | PARTIALLY VERIFIED | Restored source, 18 estimation/observability tests and independent PG validation rerun |
| RSI | RSI_ProcessLab_Relatorio.pdf and RSI_ProcessLab_Manuscrito.pdf | UNAVAILABLE source in inspected branch | Reports read; no genuine recursive superiority established; not integrated |
| Aspen full plant | Historical reports/archived references | UNAVAILABLE executable validation | No Aspen engine present; no claim of two-reactor/column/recycle reproduction |

The AIRE package was recovered in an isolated analysis directory. It was not merged
into this public repository because it includes additional scientific materials,
private source documents and no verified package-wide redistribution license.
Only newly computed validation evidence and provenance are added. The original
package remains the authority for the AIRE equations and experiments.

The report names and recovered branch contents differ materially for RSI. The product
does not pretend that the missing research implementation is integrated. AIRE is
also not silently substituted by the new generic MHE/NMPC in this application.

## PG discrepancy: three deliberately separate parameter sets

| Variant | Nominal T (K) | Reaction enthalpy (kJ/kmol) | Meaning |
|---|---:|---:|---|
| Recovered executable original | 332.333618 | -83736 | Converted from MATLAB -36000 Btu/lbmol |
| Literal TS table | 340.303489 | -91556.9 | Rounded table constants and no original Arrhenius offset |
| Adjusted TS | 332.3 | -84138.653537 | Earlier one-point effective-enthalpy calibration |

The source uses R = 1.987×4.1868 = 8.3191716, T_F+460 = T_K+0.183333…,
exact unit conversions, V=(500/7.484)×0.028316846592 m³ and source feed values.
The table/TS variant uses rounded constants, R=8.314 and its table enthalpy.
These differences change equilibrium. The recovered executable needs no fitting
to reach approximately 332.3336 K, Tt=314.3976 K, CC=2.295765 kmol/m³.

The original heat-exchange duty depends on reactor T and coolant inlet, not Tt.
That asymmetry and its observability consequences are preserved. A generic jacket
equation would define a different model. The original code and thesis also disagree
on certain UKF Q entries; new estimator settings are not described as exact historical
filter reproduction. The product defaults to 54 s (0.015 h) for PG.

## EB remains unreconciled

The recovered five-state R1 is (CE, CB, CEB, CDEB, T1). Time h, T1 °C, kinetics K,
concentrations kmol/m³, energy kcal. Quality is CEB/sum(C), not product concentration.
Q0 is a reconstructed duty calibrated at 160 °C, not recovered Aspen output.
For enthalpies [-27150,-26950,-205.5], -DH1+DH2+DH3=-5.5 kcal/kmol.
Closing that Hess cycle alone does not reconcile the constant-property thermal model.
The 165 °C upper boundary is a research assumption, not a certified plant constraint.

## What was not claimed

No MATLAB/Simulink or Aspen execution; no chemical-plant validation; no complete
historical campaign replication; no proven RSI superiority; no generalized observer
observability; no guaranteed NMPC safety; no benchmark on the user's laptop.
Checksums and fresh numerical evidence are in `studio/evidence/`.
