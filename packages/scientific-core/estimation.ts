import {
  diag,
  zeros,
  cholesky,
  multiply,
  transpose,
  plus,
  symmetrize,
  type Matrix,
} from "../../lib/simulation/matrix.ts";
import { rk4 } from "./models.ts";
import { type Model, type Estimator, type Settings } from "./types.ts";
// Public estimator API has no true-state argument. Only causal applied input and measured channels.
export class EstimatorState {
  x: number[];
  cov: Matrix;
  model: Model;
  kind: Estimator;
  constructor(model: Model, s: Settings) {
    this.model = model;
    this.kind = s.observer;
    this.x = model.x0.map((v, i) => v + s.initialOffset * model.scale[i]);
    this.cov = diag(model.scale.map((v) => (v * 0.04) ** 2));
  }
  update(u: number, y: number[], settings: Settings) {
    if (this.kind === "off") return;
    const m = this.model,
      n = this.x.length,
      dt = settings.dt;
    const transition = (x: number[]) => rk4(m, x, u, dt, settings.disturbance);
    const q = diag(
      m.scale.map((v) => ((v * 0.0005) ** 2 * settings.qScale * dt) / 54),
    );
    let xp: number[], pp: Matrix;
    if (this.kind === "ekf") {
      xp = transition(this.x);
      const f = zeros(n);
      for (let j = 0; j < n; j++) {
        const h = Math.max(1e-7, Math.abs(this.x[j]) * 1e-6),
          a = [...this.x],
          b = [...this.x];
        a[j] += h;
        b[j] -= h;
        const aa = transition(a),
          bb = transition(b);
        for (let i = 0; i < n; i++) f[i][j] = (aa[i] - bb[i]) / (2 * h);
      }
      pp = plus(multiply(multiply(f, this.cov), transpose(f)), q);
    } else {
      const alpha = 0.6,
        scale = alpha * alpha * n,
        wm = [1 - n / scale, ...Array(2 * n).fill(1 / (2 * scale))],
        wc = [wm[0] + 1 - alpha * alpha + 2, ...wm.slice(1)],
        l = cholesky(this.cov),
        pts = [this.x];
      for (let j = 0; j < n; j++)
        for (const sign of [1, -1])
          pts.push(this.x.map((v, i) => v + sign * Math.sqrt(scale) * l[i][j]));
      const transformed = pts.map(transition);
      xp = Array(n).fill(0);
      pp = zeros(n);
      for (let k = 0; k < transformed.length; k++)
        for (let i = 0; i < n; i++) xp[i] += wm[k] * transformed[k][i];
      for (let k = 0; k < transformed.length; k++)
        for (let i = 0; i < n; i++)
          for (let j = 0; j < n; j++)
            pp[i][j] +=
              wc[k] * (transformed[k][i] - xp[i]) * (transformed[k][j] - xp[j]);
      pp = plus(pp, q);
    }
    // Independent linear sensors; sequential Joseph updates equal a joint Gaussian update.
    const r = Math.max(1e-8, settings.noise ** 2) * settings.rScale;
    settings.measurementIndices.forEach((j, k) => {
      if (!Number.isFinite(y[k])) throw Error("Medição não finita");
      const s = pp[j][j] + r,
        K = pp.map((row) => row[j] / s),
        innovation = y[k] - xp[j];
      xp = xp.map((v, i) => v + K[i] * innovation);
      const a = diag(Array(n).fill(1));
      for (let i = 0; i < n; i++) a[i][j] -= K[i];
      pp = plus(
        multiply(multiply(a, pp), transpose(a)),
        K.map((ki) => K.map((kj) => ki * r * kj)),
      );
    });
    if (
      xp.some((v) => !Number.isFinite(v)) ||
      pp.flat().some((v) => !Number.isFinite(v))
    )
      throw Error("Estimador sem convergência");
    pp = symmetrize(pp);
    cholesky(pp);
    this.x = xp;
    this.cov = pp;
  }
}
