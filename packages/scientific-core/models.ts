import {
  BASE,
  TABLED_BASE,
  P,
  TABLED_P,
  NOMINAL,
  derivative,
  type State,
} from "../../lib/simulation/model.ts";
import { Flowsheet } from "./flowsheet.ts";
import { type Model, type Project, VERSION } from "./types.ts";
export const PG_X0 = [
  0.6070247319036959, 33.98910210720909, 2.2957646050793823, 3.6284866712288473,
  332.333618020444, 314.3975853301131,
];
export const EB_X0 = [
  0.037380854162926476, 4.632416401733355, 1.966908150395695,
  0.37244803185566633, 160,
];
export const EB_Q0 = 21828692.029215917;
const cu = 0.45359237 / 0.028316846592;
export const PG = {
  cp: [35, 18, 46, 19.5].map((v) => v * 4.1868),
  rho: [0.923, 3.45, 1.54].map((v) => v * cu),
  E: 32400 * 2.326,
  R: 1.987 * 4.1868,
  k0: 16.96e12,
  heat: 36000 * 2.326,
  V: (500 / 7.484) * 0.028316846592,
  Vt: 38.85 * 0.028316846592,
  UA: 16000 * 1.05505585262 * 1.8,
  FA: 80 * 0.45359237,
  FB: 1000 * 0.45359237,
  FM: 100 * 0.45359237,
  T0: (75 - 32) / 1.8 + 273.15,
  Ta: (60 - 32) / 1.8 + 273.15,
  offset: (460 - 459.67) / 1.8,
};
export function pgOriginalRhs(x: number[], u: number, d = 0) {
  const p = PG,
    v = p.FA / p.rho[0] + p.FB / p.rho[1] + p.FM / p.rho[2],
    r = p.k0 * Math.exp(-p.E / (p.R * (x[4] + p.offset))) * x[0];
  const q = u * p.cp[1] * (p.Ta - x[4]) * -Math.expm1(-p.UA / (u * p.cp[1])),
    cap = p.V * x.slice(0, 4).reduce((s, c, i) => s + c * p.cp[i], 0);
  const cp = p.FA * p.cp[0] + p.FB * p.cp[1] + p.FM * p.cp[3];
  return [
    (p.FA - v * x[0]) / p.V - r,
    (p.FB - v * x[1]) / p.V - r,
    r - (v * x[2]) / p.V,
    (p.FM - v * x[3]) / p.V,
    (q - cp * (x[4] - p.T0 - d) + p.heat * r * p.V) / cap,
    (u * p.cp[1] * (p.Ta - x[5]) - q) / (p.rho[1] * p.Vt * p.cp[1]),
  ].map((v) => v / 3600);
}
export function ebRhs(x: number[], u: number, d = 0) {
  const f = [82.59918, 57.95784, 88.92402],
    rho = [7.63446, 10.8803, 10.9014],
    cp = [236.32, 265.8, 273.5],
    k0 = [1.528e6, 2.778e7, 1e3],
    ea = [17000, 20000, 15000];
  const k = k0.map(
      (a, i) => a * 3600 * Math.exp(-ea[i] / (1.987 * (x[4] + 273.15))),
    ),
    r = [k[0] * x[0] * x[1], k[1] * x[0] * x[2], k[2] * x[1] * x[3]],
    out = f.reduce((s, v) => s + v, 0),
    rhoc = 8.09685 * 73.56;
  const feed = [
      f[0] * rho[0] + f[2] * 0.001198,
      f[1] * rho[1] + f[2] * 10.8982,
      f[2] * 0.002015,
      0,
    ],
    nu = [
      [-1, -1, 0],
      [-1, 0, -1],
      [1, -1, 2],
      [0, 1, -1],
    ];
  const dx = feed.map(
    (v, i) =>
      (v - out * x[i]) / 200 + nu[i].reduce((s, n, j) => s + n * r[j], 0),
  );
  dx.push(
    (f.reduce(
      (s, v, i) => s + v * rho[i] * cp[i] * ([46.85, 46.85, 45.22][i] + d),
      0,
    ) -
      out * rhoc * x[4] +
      200 * (27150 * r[0] + 26950 * r[1] + 205.5 * r[2]) -
      u) /
      (rhoc * 200),
  );
  return dx.map((v) => v / 3600);
}
export function buildModel(p: Project): Model {
  if (p.readOnlyReason) throw Error(p.readOnlyReason);
  const base = { version: VERSION, id: p.model };
  if (p.model === "flowsheet") {
    const f = new Flowsheet(p.graph),
      n = f.dynamic.length;
    if (!n)
      throw Error("Inclua ao menos um tanque ou CSTR para simulação dinâmica");
    if (n > 8) throw Error("Limite mobile: 8 equipamentos dinâmicos");
    return {
      ...base,
      label: "Planta líquida",
      names: f.dynamic.flatMap((k) => [`${k}.A`, `${k}.T`]),
      units: f.dynamic.flatMap(() => ["kg/kg", "K"]),
      x0: f.x0,
      ti: n * 2 - 1,
      qi: n * 2 - 2,
      measured: f.dynamic.map((_, i) => 2 * i + 1),
      scale: f.dynamic.flatMap(() => [0.1, 10]),
      u0: f.nodes.get(f.target!)!.parameters.duty,
      inputUnit: "W",
      inputLabel: "Potência",
      bounds: [0, 100000],
      limit: 373.15,
      maxStep: Math.min(
        1,
        ...f.dynamic.map(
          (k) => (1000 * f.nodes.get(k)!.parameters.volume) / 100,
        ),
      ),
      provenance:
        "Studio flowsheet: Cp=4180 J/(kg K), ρ=1000 kg/m³; RK4; balanços SI.",
      warning:
        "Sem equilíbrio de fases, reciclos ou solução hidráulica. Bomba/válvula têm ΔP prescrito.",
      rhs: (x, u, d) => f.evaluate(x, u, d).dx,
      check: (x) => {
        f.evaluate(x);
      },
    };
  }
  const eb = p.model === "eb-reduced",
    original = p.model === "pg-original",
    table = p.model === "pg-table";
  const x0 = eb ? EB_X0 : original ? PG_X0 : table ? TABLED_BASE : BASE;
  return {
    ...base,
    label: eb
      ? "Etilbenzeno · R1"
      : original
        ? "PG · original"
        : table
          ? "PG · tabela literal"
          : "PG · calibrado",
    x0: [...x0],
    names: eb
      ? ["C_E", "C_B", "C_EB", "C_DEB", "T1"]
      : ["C_A", "C_B", "C_C", "C_M", "T", "T_t"],
    units: eb
      ? ["kmol/m³", "kmol/m³", "kmol/m³", "kmol/m³", "°C"]
      : ["kmol/m³", "kmol/m³", "kmol/m³", "kmol/m³", "K", "K"],
    ti: 4,
    qi: 2,
    measured: eb ? [4] : [4, 5],
    scale: eb ? [0.03, 5, 2, 0.4, 10] : [0.6, 34, 2.3, 3.6, 10, 10],
    u0: eb ? EB_Q0 : original ? 453.59237 : NOMINAL.mw,
    inputUnit: eb ? "kcal/h" : "kmol/h",
    inputLabel: eb ? "Calor retirado" : "Refrigerante",
    bounds: eb ? [EB_Q0 * 0.75, EB_Q0 * 1.25] : [22.7, 1366.2],
    limit: eb ? 165 : 355.4,
    maxStep: eb ? 2 : 3.6,
    provenance: eb
      ? "Porta literal de research/beyond/vendor/eb_reference.py. Q0 e XSS calculados no arquivo original."
      : original
        ? "Porta SI de pg_reference.py e modeloCT.m (2019), incluindo offset de Arrhenius e assimetria térmica."
        : "Reutiliza lib/simulation/model.ts sem alterar equações.",
    warning: eb
      ? "R1 reduzido. Q0 calibrado em 160 °C; balanço térmico não reconciliado; limite 165 °C é hipótese de estudo."
      : original
        ? "332,3336 K nominal; não equivale à tabela literal nem à calibração. Simulação de pesquisa."
        : table
          ? "340,3035 K nominal; entalpia tabelada. Não é o modelo executável recuperado."
          : "332,3 K nominal; entalpia efetiva ajustada em um ponto. Não representa recuperação do parâmetro físico.",
    rhs: eb
      ? ebRhs
      : original
        ? pgOriginalRhs
        : (x, u, d) =>
            derivative(
              x as State,
              { ...NOMINAL, mw: u, t0: NOMINAL.t0 + d },
              table ? TABLED_P : P,
            ).map((v) => v / 3600),
    check: (x) => {
      if (
        x.length !== x0.length ||
        x.some((v) => !Number.isFinite(v)) ||
        x.slice(0, 4).some((v) => v < -1e-9) ||
        x[4] < (eb ? -20 : 150) ||
        x[4] > (eb ? 350 : 600) ||
        (!eb && (x[5] < 150 || x[5] > 600))
      )
        throw Error(
          "Estado fora do domínio numérico; último ponto válido preservado",
        );
    },
  };
}
export function rk4(
  m: Model,
  x: number[],
  u: number,
  dt: number,
  d = 0,
  maxStep = m.maxStep,
) {
  if (
    !Number.isFinite(dt) ||
    dt <= 0 ||
    maxStep <= 0 ||
    !Number.isFinite(u) ||
    u < m.bounds[0] ||
    u > m.bounds[1]
  )
    throw Error("Passo/entrada inválidos");
  const n = Math.ceil(dt / maxStep);
  if (n > 10000) throw Error("Orçamento de integração excedido");
  const h = dt / n;
  let y = [...x];
  const add = (a: number[], b: number[], s: number) =>
    a.map((v, i) => v + s * b[i]);
  for (let j = 0; j < n; j++) {
    const a = m.rhs(y, u, d),
      b = m.rhs(add(y, a, h / 2), u, d),
      c = m.rhs(add(y, b, h / 2), u, d),
      e = m.rhs(add(y, c, h), u, d);
    y = y.map((v, i) => v + (h * (a[i] + 2 * b[i] + 2 * c[i] + e[i])) / 6);
    m.check(y);
  }
  return y;
}
