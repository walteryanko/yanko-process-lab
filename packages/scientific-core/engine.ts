import { SeededNoise } from "../../lib/simulation/engine.ts";
import { EstimatorState } from "./estimation.ts";
import { buildModel, rk4 } from "./models.ts";
import { validateProject, validateSettings } from "./project.ts";
import {
  type Project,
  type Sample,
  type Settings,
  type Model,
  copy,
  clamp,
  VERSION,
} from "./types.ts";
export type Checkpoint = {
  version: string;
  project: Project;
  initialProject: Project;
  x: number[];
  estimate: number[];
  cov: number[][];
  rng: number;
  history: Sample[];
  integral: number;
  previous: number;
  u: number;
  events: { t: number; patch: Partial<Settings> }[];
  done: boolean;
  error: string | null;
};
export class Engine {
  project: Project;
  initialProject: Project;
  model: Model;
  x: number[];
  estimator: EstimatorState;
  rng: SeededNoise;
  history: Sample[] = [];
  integral = 0;
  previous = 0;
  u: number;
  done = false;
  error: string | null = null;
  events: { t: number; patch: Partial<Settings> }[] = [];
  constructor(project: Project) {
    validateProject(project);
    this.project = copy(project);
    this.initialProject = copy(project);
    this.model = buildModel(this.project);
    const s = this.settings;
    this.x = [...(project.science.initial ?? this.model.x0)];
    this.model.check(this.x);
    this.rng = new SeededNoise(s.seed);
    this.estimator = new EstimatorState(this.model, s);
    this.u = s.manual;
    this.history = [this.sample(0, this.measure(this.x), "inicial", 0)];
  }
  get settings() {
    return this.project.science.settings;
  }
  get last() {
    return this.history[this.history.length - 1];
  }
  measure(x: number[]) {
    return this.settings.measurementIndices.map(
      (i) => x[i] + this.rng.normal() * this.settings.noise,
    );
  }
  sample(
    t: number,
    measured: number[],
    solver: string,
    computeMs: number,
  ): Sample {
    return {
      t,
      x: [...this.x],
      estimate: [...this.estimator.x],
      measured,
      sigma: this.estimator.cov.map((r, i) => Math.sqrt(r[i])),
      u: this.u,
      sp: this.settings.setpoint,
      disturbance: this.settings.disturbance,
      solver,
      computeMs,
    };
  }
  configure(patch: Partial<Settings>) {
    const next = { ...this.settings, ...patch };
    validateSettings(next, this.model);
    if (next.controller !== this.settings.controller) {
      this.integral = 0;
      this.previous = 0;
    }
    if (next.observer !== this.settings.observer)
      this.estimator.kind = next.observer;
    this.project.science.settings = next;
    this.events.push({ t: this.last.t, patch: copy(patch) });
  }
  *advance(): Generator<void, Sample, unknown> {
    if (this.done) return this.last;
    let sliceStart = performance.now(),
      activeMs = 0;
    const s = this.settings,
      m = this.model,
      dt = s.dt,
      limit = m.limit,
      [lo, hi] = m.bounds;
    let u = this.u,
      solver = "manual",
      integral = this.integral,
      previous = this.previous;
    try {
      if (s.controller === "manual") u = s.manual;
      else if (
        (s.controller === "nmpc" || s.controller === "cascade") &&
        s.observer === "off"
      ) {
        solver = "fallback · estimador desligado";
      } else if (s.controller === "pid" || s.controller === "cascade") {
        const channel = s.measurementIndices.indexOf(m.ti);
        if (channel < 0)
          throw Error("PID exige sensor da temperatura controlada");
        const setpoint =
          s.controller === "cascade"
            ? clamp(
                m.x0[m.ti] + 25 * (s.setpoint - this.estimator.x[m.qi]),
                m.x0[m.ti] - 20,
                m.limit,
              )
            : s.setpoint;
        const error = setpoint - this.last.measured[channel],
          inc = s.ki * error * dt,
          raw =
            m.u0 +
            s.kp * error +
            integral +
            inc +
            (s.kd * (error - previous)) / dt;
        if (
          (raw >= lo && raw <= hi) ||
          (raw > hi && inc < 0) ||
          (raw < lo && inc > 0)
        )
          integral += inc;
        previous = error;
        u = clamp(
          m.u0 +
            s.kp * error +
            integral +
            (s.kd * (error - this.previous)) / dt,
          lo,
          hi,
        );
        solver = s.controller;
      } else {
        // Bounded finite candidate search, explicitly not SQP and not robust MPC.
        let best = Infinity,
          chosen = this.u;
        for (const offset of [0, -0.16, 0.16, -0.06, 0.06, -0.02, 0.02]) {
          const candidate = clamp(this.u + offset * (hi - lo), lo, hi);
          let x = [...this.estimator.x],
            cost = 0.002 * ((candidate - this.u) / (hi - lo)) ** 2;
          try {
            for (let k = 0; k < s.horizon; k++) {
              x = rk4(m, x, candidate, dt, s.disturbance);
              if (x[m.ti] > limit) {
                cost = Infinity;
                break;
              }
              cost += ((x[m.ti] - s.setpoint) / 10) ** 2;
            }
          } catch {
            cost = Infinity;
          }
          if (cost < best) {
            best = cost;
            chosen = candidate;
          }
          activeMs += performance.now() - sliceStart;
          yield;
          sliceStart = performance.now();
        }
        u = chosen;
        solver = Number.isFinite(best)
          ? "NMPC · busca limitada"
          : "fallback · sem candidato viável";
      }
      const next = rk4(m, this.x, u, dt, s.disturbance),
        measured = this.measure(next);
      // Prediction uses the input held over [t,t+dt]; update consumes y(t+dt).
      this.estimator.update(u, measured, s);
      this.x = next;
      this.u = u;
      this.integral = integral;
      this.previous = previous;
      const sample = this.sample(
        this.last.t + dt,
        measured,
        solver,
        activeMs + performance.now() - sliceStart,
      );
      this.history.push(sample);
      if (sample.x[m.ti] >= limit) {
        this.done = true;
        this.error = `Limite de estudo: ${limit} ${m.units[m.ti]}. Simulação interrompida.`;
      }
      if (sample.t + 1e-9 >= s.duration || this.history.length >= 20001)
        this.done = true;
    } catch (e) {
      this.done = true;
      this.error = e instanceof Error ? e.message : String(e);
    }
    return this.last;
  }
  step() {
    const task = this.advance();
    let r = task.next();
    while (!r.done) r = task.next();
    return r.value;
  }
  checkpoint(): Checkpoint {
    return copy({
      version: VERSION,
      project: this.project,
      initialProject: this.initialProject,
      x: this.x,
      estimate: this.estimator.x,
      cov: this.estimator.cov,
      rng: this.rng.seed,
      history: this.history,
      integral: this.integral,
      previous: this.previous,
      u: this.u,
      events: this.events,
      done: this.done,
      error: this.error,
    });
  }
  static restore(c: Checkpoint) {
    if (c.version !== VERSION || !c.history?.length || c.history.length > 20001)
      throw Error("Checkpoint incompatível");
    const e = new Engine(c.project),
      n = e.x.length;
    e.model.check(c.x);
    if (
      c.estimate.length !== n ||
      c.cov.length !== n ||
      c.cov.some((r) => r.length !== n) ||
      [...c.estimate, ...c.cov.flat(), c.u, c.integral, c.previous, c.rng].some(
        (v) => !Number.isFinite(v),
      )
    )
      throw Error("Checkpoint numérico inválido");
    Object.assign(e, {
      initialProject: c.initialProject ?? copy(c.project),
      x: c.x,
      history: c.history,
      integral: c.integral,
      previous: c.previous,
      u: c.u,
      events: c.events,
      done: c.done,
      error: c.error,
    });
    e.estimator.x = c.estimate;
    e.estimator.cov = c.cov;
    e.rng.seed = c.rng;
    return e;
  }
}
export function metrics(e: Engine) {
  const samples = e.history.slice(1),
    m = e.model,
    qi = m.qi,
    ti = m.ti;
  let iae = 0,
    itae = 0,
    sse = 0,
    estimatedSamples = 0,
    overshoot = 0,
    violations = 0,
    previousTime = e.history[0].t,
    eventIndex = 0,
    observer = e.initialProject.science.settings.observer;
  const cascade = e.initialProject.science.settings.controller === "cascade" ||
    e.events.some((event) => event.patch.controller === "cascade");
  for (const s of samples) {
    while (eventIndex < e.events.length && e.events[eventIndex].t < s.t) {
      observer = e.events[eventIndex].patch.observer ?? observer;
      eventIndex++;
    }
    const dt = s.t - previousTime;
    previousTime = s.t;
    const err = s.sp - s.x[ti];
    iae += Math.abs(err) * dt;
    itae += s.t * Math.abs(err) * dt;
    if (observer !== "off") {
      sse += (s.x[qi] - s.estimate[qi]) ** 2;
      estimatedSamples++;
    }
    overshoot = Math.max(overshoot, s.x[ti] - s.sp);
    if (s.x[ti] > m.limit) violations++;
  }
  const stableTarget =
    samples.length > 0 && samples.every((s) => s.sp === samples[0].sp);
  const band = Math.max(
    0.1,
    0.02 * Math.abs((samples[0]?.sp ?? 0) - e.history[0].x[ti]),
  );
  const lastOutside = samples
    .map((s, i) => (Math.abs(s.x[ti] - s.sp) > band ? i : -1))
    .reduce((a, b) => Math.max(a, b), -1);
  const settling =
    stableTarget && samples.length - lastOutside >= 6
      ? (samples[lastOutside + 1]?.t ?? null)
      : null;
  return {
    rmse: estimatedSamples ? Math.sqrt(sse / estimatedSamples) : null,
    iae: cascade ? null : iae,
    itae: cascade ? null : itae,
    overshoot: cascade ? null : overshoot,
    settling: cascade ? null : settling,
    settlingBand: cascade ? null : band,
    violations,
    samples: samples.length,
    computeMs: samples.reduce((a, s) => a + s.computeMs, 0),
    peakStepMs: samples.reduce((a, s) => Math.max(a, s.computeMs), 0),
    note: cascade
      ? "Métricas térmicas indisponíveis em execuções que incluem cascata de concentração"
      : null,
  };
}
export function csv(e: Engine) {
  const m = e.model,
    headers = [
      "t_s",
      ...m.names.map((v, i) => `${v}_truth_${m.units[i]}`),
      ...m.names.map((v, i) => `${v}_estimate_${m.units[i]}`),
      ...e.settings.measurementIndices.map(
        (i) => `${m.names[i]}_measured_${m.units[i]}`,
      ),
      ...m.names.map((v) => `${v}_sigma`),
      `u_${m.inputUnit}`,
      "setpoint",
      "disturbance_K",
      "solver",
      "compute_ms",
    ];
  return [
    headers.join(","),
    ...e.history.map((s) =>
      [
        s.t,
        ...s.x,
        ...s.estimate,
        ...s.measured,
        ...s.sigma,
        s.u,
        s.sp,
        s.disturbance,
        `"${s.solver}"`,
        s.computeMs,
      ].join(","),
    ),
  ].join("\n");
}
