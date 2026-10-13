# ProcessLab Studio 0.1.0 — architecture and scope

This is an executable research baseline, not the complete target industrial simulator.
It evolves the same repository from `88c40e65204fa6aa5bed02cc64fb15be79a53bb1`.
The original TypeScript code and research directories are unchanged.

## Decisions

React 19 + TypeScript + React Flow 12 provide the editor. Python 3.12, NumPy,
SciPy, Pint and the archived CasADi EB implementation are the numerical source
of truth. The UI never integrates physical equations. Plot refresh is independent
of physical sampling; each API batch advances a specified number of samples.

For this baseline, pywebview + the Windows WebView2 renderer replace the suggested
Tauri shell. This removes an additional Rust process supervisor and loopback API
from the packaged desktop. PyInstaller bundles Python and required packages;
NSIS makes a per-user installer. Tauri was suggested, not required by the mission.
No browser runtime or numerical interpreter is fetched during a simulation.
Windows needs the Microsoft Edge WebView2 runtime and .NET Framework supported
by pywebview. Installer does not silently download them. Desktop startup validation
on the Windows runner is distinct from validation on Windows 10 and the target laptop.

Native transport is the pywebview JSON bridge. Browser development uses a separate
loopback-only HTTP adapter with a random 256-bit token, Host/Origin checks, no CORS,
2 MB request limit and static path confinement. No hardware interfaces or dynamic
user code execution are implemented.

## Modules

| Module | Responsibility |
|---|---|
| schema / units | Schema v1, allowed enums, SI conversions, finite values |
| flowsheet | Typed ports, acyclic compile order, streams and conservation |
| models | Direct archived PG/EB adapters, seconds ↔ native hours |
| numerics | RK4 / adaptive RK / BDF / Radau, failure reporting |
| sensors | Simulated acquisition, corruption and event arrival |
| estimation | EKF, UKF, deterministic-window MHE; delayed replay |
| control | Measured-temperature PID; estimated-state NMPC |
| simulation | Physical clock and orchestration, immutable output rows |
| storage / api | Atomic local files and serialized requests |
| desktop / server | Native host and authenticated development host |

## Physical limitations

The flowsheet package is a specified-flow, constant-density liquid/tracer system:
rho=1000 kg/m³, Cp=4180 J/(kg K), temperature 273.15–373.15 K. Properties are assumed,
not a validated real-substance equation of state. A/B have equal molecular mass.
Tank volume is fixed and outflow equals inflow. CSTR reaction is first-order A→B
with constant k and specified heat release. It is not the historical PG model.

Mixer conserves mass, tracer and sensible energy; outlet pressure is minimum inlet
pressure, with no hydraulic convergence. Splitter preserves composition and T.
Pump uses a prescribed pressure rise and efficiency, adds dissipative heat; valve
uses a prescribed drop converted to heat. These units do not solve pressure/flow
coupling. The utility exchanger has an infinite constant-temperature utility and
effectiveness 1-exp(-UA/(m Cp)); it is not a two-stream exchanger. Heater/cooler add
specified duty. An energy source can connect to the heat port. The manipulated
input, when applied to a dynamic unit, is TOTAL duty, overriding its static duty
plus any energy source (not additive).

All material outlets must terminate in a sink; branching requires a splitter.
Cycles/recycles, phase changes, flashes, columns, general DAEs, FMI and material
species databases are explicitly unsupported. Instrumentation is configured through
the sensor/control panels, not arbitrary graphical signal wiring.

## Estimation and control limits

EKF uses numerical discrete Jacobians and Joseph updates. UKF uses scaled sigma
points (alpha=.5, beta=2). Q is per-sample, not a continuous spectral density.
P0 and Q are scaled diagonal priors; users can change prior offset and Q/R multipliers.
Sensor bias/lag/saturation are emulated but not estimated; resulting mismatch is real.
No post hoc truth correction is applied. Delayed measurements are assimilated at
collection time through deterministic replay of known inputs and received events.

MHE is a new single-shooting window of five transitions, deterministic model,
initial-state decisions, at most 12 residual evaluations. It is not the AIRE MHE.
The EKF companion provides the arrival distribution and displayed covariance;
failed optimization falls back explicitly. Covariance coverage is descriptive per
simulation, not a calibrated claim. Local observability is scaled, numerical,
thermal-only linearization; a finite numerical rank does not prove global observability.

PID controls measured temperature with conditional integration anti-windup and
limited slew. Missing observations hold the last action. NMPC uses estimated states,
SciPy SLSQP with max 25 iterations and normalized moves, input/rate bounds and
predicted thermal constraints at sample points. A failed/infeasible solve holds the
last bounded input. Neither fallback nor discrete constraints guarantee plant safety.
Cascade, linear MPC, economic/robust NMPC and neural modules are not implemented.

## Project/API contract

Projects contain `schema_version:1`, stable `id`, `name`, `model`, `nodes`, `edges`,
optional `control_equipment`, and `experiment`. Each node has `id`, `kind`, `label`,
`parameters`, and independent `layout:{x,y}`. Each edge has `id`, `source`, `target`,
`source_port`, `target_port`, `kind` (material or energy). Ports are from the catalog.
Bare physical parameter numbers have catalog units; `{value,unit}` is converted by
Pint. Research adapters preserve their declared concentration/temperature units.
Time at every product boundary is seconds. Unsupported versions fail; there is no
earlier product schema to migrate.

`API.request(method,payload)` returns `{ok:true,data}` or `{ok:false,error,type}`.
Methods: bootstrap, validate, steady, reset, advance, inspect, setpoint, observability,
save, open and export. `advance` has at most 20 samples per call; reading never advances.
Project writes close the temporary handle before os.replace, including on Windows.
Existing project content is backed up. Export preserves definition, time-stamped
measurements, truth, estimates, controls, metrics, solver settings and environment.

Documentation consulted: https://reactflow.dev/api-reference/react-flow and
https://pywebview.flowrl.com/guide/freezing.html (13 October 2026).
