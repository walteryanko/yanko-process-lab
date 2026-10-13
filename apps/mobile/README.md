# YCS ProcessLab Mobile — 0.1.0-beta.1

Native Android application, React Native 0.86.3 / Expo SDK 57 / Hermes / Skia.
This is an evaluation build until the Android installation/interaction evidence is obtained.
No WebView, Metro or external API is used for the core functionality.

## Development and build

Node 24, JDK 17, Android SDK and NDK as selected by the locked Expo/RN toolchain:

```sh
npm ci --prefix apps/mobile
npm test
node --test packages/scientific-core/tests/*.test.mjs
npm run typecheck --prefix apps/mobile
cd apps/mobile
npx expo prebuild --platform android --no-install
cd android
./gradlew :app:assembleRelease -PreactNativeArchitectures=arm64-v8a,x86_64
```

Supply `PROCESSLAB_KEYSTORE`, `PROCESSLAB_STORE_PASSWORD`, `PROCESSLAB_KEY_ALIAS`,
`PROCESSLAB_KEY_PASSWORD` outside Git. The workflow creates an **ephemeral evaluation
certificate** if repository signing secrets are absent. A release build is not the
same thing as a stable distribution identity. APKs with different certificates need
uninstall/reinstall: export projects first. Never commit keystores.

## Architecture

- `packages/scientific-core`: independent models, RK4, observers, bounded control,
  schema, deterministic replay checkpoints, fixtures and Node tests.
- `lib/simulation`: original TypeScript model/matrix/noise reused. The sole change
  is widening the TypeScript parameter type to allow its existing calibrated heat.
- `apps/mobile`: native views, Skia canvas/charts, Gesture Handler, SQLite WAL,
  Android document picker and file sharing; cooperative numerical work scheduling.
- `studio`: unchanged. Research equations/archives/history are preserved.

Simulation work is CPU-only in short JS slices; the native drawing thread is separate.
NMPC yields between candidate evaluations and can be cancelled before committing a
step. UI refresh is capped separately from integration. No native compute speedup or
60 FPS claim is made. Backgrounding pauses work and writes a checkpoint. Restore is
paused; it does not start an unattended background simulation.

## Recovered science

| Resource | Reuse / status |
|---|---|
| Original TS PG | Direct imports for calibrated and literal parameter sets |
| Original 2019 PG | Literal SI port of `research/beyond/vendor/pg_reference.py` |
| EB R1 | Literal port of `eb_reference.py`; independently checked against DOP853 |
| Matrix operations and noise | Original TypeScript imports |
| EKF / UKF | Generic RK4 predictors and Joseph measurement update; new mobile tuning |
| PID | Measured temperature, bounds, conditional integration anti-windup |
| Cascade | PG concentration estimate → thermal setpoint → measured-T PID |
| NMPC | Seven constant-input candidates; bounded horizon; feasibility/hold fallback |
| AIRE | Recovered/audited by Studio; not integrated into this APK |
| RSI | Named branch points at beyond research; no RSI implementation found |

The new observer/controller implementations do not claim bit-for-bit parity with
the old Euler observer, SQP research controllers or historical gains. The original
TS core tests remain intact; mobile model trajectories are compared separately.

### Scientific distinctions

- PG original nominal: 332.333618 K. Preserves the recovered Arrhenius offset and
  cooling-duty asymmetry. No fitted reaction heat.
- PG TS calibrated: 332.3 K, effective one-point reaction enthalpy calibration.
- PG TS table: 340.303489 K. Rounded table parameters retained.
- EB R1: Q0 reconstructed at 160 °C, thermal balance unreconciled; 165 °C is a study
  assumption. This is not the full Aspen plant or a validated safety controller.
- Flowsheet: constant-density liquid/tracer networks, no recycle or hydraulic solve.
  Source, sink, mixer, splitter, pump, valve, heater, cooler, exchanger, tank and
  first-order CSTR execute real balances. Pressure is only modeled in this network.

## Files, units and reproducibility

Seconds at mobile model boundaries; original chemical kinetics are converted from
hours. Units remain attached to values. Complete traces are retained for CSV, while
display paths are decimated. A mobile project separates science, graph and layout.
SQLite retains project, RNG, covariance, controller state, settings and events.
Unknown fields survive roundtrips. Desktop documents are preserved read-only with
the original payload; their unsupported solver/sensor contracts are never silently
converted. Saving a desktop document does not claim trajectory compatibility.

## Verification

`evidence/` contains actual local results. The Android Actions workflow installs the
release x86_64 APK into an Android emulator, disables Wi-Fi/data, verifies numerical
fixtures on Hermes, tests SQLite, checks rotation and process recovery, and captures
real portrait/landscape PNGs. The installable phone artifact is arm64-v8a. No physical
phone memory/battery/thermal measurements are claimed by emulator evidence.

## Current limits

No linear MPC, MHE, trained hybrid estimator, energy/signal connections as free
editor edges, general project-desktop migration, industrial certification or
background foreground-service simulation. Sensors/controllers are real panels, not
arbitrary instrumentation symbols in the equipment graph. QA does not yet cover
every multi-touch, keyboard, split-screen, reboot, accessibility or Android version.

## Quick use (pt-BR)

1. Instale o APK arm64, permitindo a instalação para o aplicativo que abre o arquivo.
2. Abra **CSTR** e toque em **▶**. O relógio mostra minutos simulados.
3. **⚡** altera a temperatura de alimentação; **Controle** ajusta PID/cascata/NMPC.
4. **Sensores** mostra concentração estimada, medições e covariância.
5. **Nova planta** permite mover equipamentos, conectar portas e editar parâmetros.
6. **Projetos** salva/abre/importa/exporta; **Ensaios** exporta CSV e compara execuções.
7. Gire o celular: o painel lateral aparece em landscape, preservando o motor.

Dependencies retain their upstream licenses; first-party mobile code is MIT under
the repository license. Numeric fixtures are generated test expectations, never
displayed as live simulation results.
