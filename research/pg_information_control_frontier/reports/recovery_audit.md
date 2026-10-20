# Recovery audit and historical status

Reference date: 20 October 2026. Repository default main was f4444d4c238291b8633743930249ee387ad94541.
New campaign starts from d2610a0723cbbaf00d3f4559242ba0efafb67771, which preserves the Darwin/thesis sources.

| Material | Recovery | Scope |
|---|---|---|
| Dissertation, Dissertacao_WalterYanko.pdf | Text read, pp.38–42 | Original balances, sensors, heat exchange and parameter table. 92-page PDF; not all pages reread. |
| modeloCT.m | Full original source recovered | Literal six-state historical dynamics |
| modeloFun_KF.m, NMPC_Fmincon.m, model/observer archive | Present in traced Git tree | Some prior audit content and NMPC reconstruction read; original MATLAB runtime not executed |
| Simulink package | Filename located, bytes unavailable locally | No Simulink execution |
| Relatorio_CSTR_Propilenoglicol.pdf | Relevant physical and attribution pages read | Historical values, units, seeds and caveats established |
| ICAC_Manuscrito_PT.pdf | Full five-page manuscript read | Historical twin and decision claims |
| research/icac-information-decision | Absent from live branch listing; commit search found no ICAC match | Code and full raw reproduction unavailable |
| PG C01–C14 | Timeline in Relatorio_Campanhas_PG_EB_Arioston.pdf read | Some C02/C03/C04/C12 code survives on beyond branch; no full 14-campaign replay |
| Darwin complete/thesis | Code and source manifest recovered from Git | Existing outputs are inherited evidence, not new execution |
| Darwin reduced branch | Audit-only checkpoint recovered | It explicitly reports zero new trajectories; not a completed reduced-model campaign |
| PG_Darwin_Reduced_Pilot_v0.1 | Report read; package identified | Independent PI/EKF pilot, tabulated variant; not equivalent to historical NMPC |
| PG Model Fidelity v0.8 | Current RESULTADOS.md v8 read | 1792 reported episodes, oracle parameter interpolation; not causal online identification |
| New frontier | Independent implementation with parity test | Its numbers are not substitutions for the historical protocols |

| Historical result | Reported value | New exact reproduction | Divergence / status |
|---|---|---|---|
| ICAC twin product gap | 0.426449 kmol/m3 | Not reproduced at that historical endpoint | Construction/protocol raw files inaccessible; new .4/.8 twin experiments use declared different initial conditions |
| Instantaneous lower bound | 0.213225 kmol/m3 | Analytic half-gap rule verified; rounded historical scalar inherited | 0.426449/2=0.2132245 before rounding |
| Nominal predictor hidden mismatch IAE | 0.951143 kmol h/m3 | Not rerun | Original 6 h, 400-step protocol differs from new 0.9 h episodes |
| Estimator-only correction IAE | 0.850912 | Not rerun | Source: PG report pp.55–57; 20 seeds 270201–270220 |
| Estimator+predictor correction IAE | 0.358768 | Not rerun | Same historical mismatch contrast; no new historical validation claim |
| ICAC B1 relative IAE | -14.60% | Not rerun | Manuscript reports six holdout seeds, different horizon/objective; not pooled with new data |

## Physical changes
The table's reaction heat is -91556.90 kJ/kmol; the executable uses -36000 Btu/lbmol,
converted in the recovered archive to -83736 kJ/kmol. M0 uses the latter. The historical
Fahrenheit +460 Arrhenius convention becomes Kelvin +0.183333333333.
Replacing it silently by exact absolute temperature would change the benchmark.

M1H adds a Kirchhoff correction with an ASSUMED reference enthalpy at nominal T.
This is thermodynamically consistent within the chosen ideal-mixture model but is not
a physically calibrated reconciliation. M1J adds a reciprocal lumped jacket, with
conductance selected to match the original nominal stationary coil duty.
M2L and M2Q use declared synthetic slopes/curvatures of species Cp(T). They are
sensitivity/falsification families, not measured property correlations.

The initial test run had 17 passes and one failed effect-size expectation. The full record
and scientific interpretation are preserved in initial_test_failure.md.

## Unexecuted central requirements
Exact historical C08/ICAC replay; all C01–C14 raw audits; validated physical-property M1;
full continuous 57-step/6-move strong baseline; fully tuned MHE; CPU timing on the target
Ryzen; prospective Lie-derivative symbolic rank sweep; independent human theoretical review.
These gaps prohibit labeling the entire requested v1.0 FINAL complete.
