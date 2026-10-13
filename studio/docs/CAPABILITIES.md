# Capability matrix

| Capability | Implemented | Verification / limitation |
|---|---|---|
| Flowsheet editor | Yes | Drag, connect, inspect, undo/redo, save/reopen; browser tested |
| Executable physical networks | Yes | Acyclic constant-property liquid/tracer systems |
| Material / energy streams | Yes | Typed ports and required-connection validation |
| Source, sink, mixer, splitter | Yes | Mass and energy balance tests |
| Tank and first-order CSTR | Yes | Analytic transient/steady tests; constant density |
| Pump, valve | Limited | Prescribed pressure change; no flow/pressure network coupling |
| Heater, cooler, utility exchanger | Limited | Specified duty / infinite utility temperature |
| Steady and dynamic solve | Yes | RK4, RK45, DOP853, BDF, Radau; no general DAE |
| Sensor corruption and delay | Yes | Gaussian noise, drift, bias, quantization, dropout, saturation, lag |
| Thermal and chemical clocks | Yes | Collection/arrival timestamps, delayed replay, no future access |
| EKF / UKF | Yes | Covariance/innovation reporting, numerical local observability |
| MHE | Experimental | Five-transition deterministic single shooting; EKF companion covariance |
| PID | Yes | Measured T, anti-windup, bounded input and slew |
| NMPC | Experimental | SLSQP, estimated state, discrete constraints, bounded hold on failure |
| PG original | Yes | Direct archived adapter; independent imperial/SI verification |
| TS table and calibrated PG | Preserved | Original code/tests, not GUI models |
| EB reduced R1 | Yes, limited | Preserved model with unresolved energy balance; not Aspen full plant |
| AIRE | Audit only | Original source recovered and selected tests reproduced; no product integration |
| RSI | No | Reports recovered; code absent from named research branch |
| Research Studio | Partial | Manifest, export, local observability, CLI benchmark; no autonomous code generation |
| CSV / JSON | Yes | Native persistence and portable definitions; runtime setpoint replay CLI |
| Model schema | v1 | Structural JSON schema + semantic Python validation; future versions rejected |
| Unit conversion | Yes | Pint at boundaries; declared native units retained in PG/EB adapters |
| Undo / redo | Yes | Editor changes; not a scientific trajectory rollback |
| Autosave | No | Explicit save with previous version backup; no background recovery journal |
| Windows installer | Yes | NSIS build and actual per-user installation passed on Windows Server 2022 CI |
| Windows application startup | Yes, CI host | All five frozen scenarios and installed WebView2 interface passed; target Windows 10 untested |
| Low-end laptop performance | NOT measured | CPU-only design; shared Linux host timings only |
| Distillation / recycle / phase equilibrium | No | Explicit unsupported scope |
| FMI / DWSIM / MATLAB / Aspen import | No | No universal compatibility claim |
| Cascade / linear / robust / economic control | No | Historical source preserved where present, not product modes |
| Industrial safety certification | No | Simulation and research only |

The exact verified installer build and evidence are recorded in `WINDOWS_VALIDATION.md`.
Windows 10 and the target i5 laptop have not been tested. This remains a research
checkpoint; the full product scope and target-hardware acceptance are not complete.
