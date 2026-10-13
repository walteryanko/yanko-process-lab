import { Engine, metrics } from "../../../packages/scientific-core/engine";
import { newProject } from "../../../packages/scientific-core/project";
import {
  referenceChecks,
  scientificFingerprint,
} from "../../../packages/scientific-core/verification";
import fingerprint from "../../../packages/scientific-core/fixtures/node-fingerprint.json";
import { session } from "./session";
import { saveProject, loadProject, removeProject } from "./storage";
import { File, Paths } from "expo-file-system";
const yieldFrame = () => new Promise<void>((r) => setTimeout(r, 0));
export async function runDeviceVerification() {
  const started = performance.now();
  while (!session.ready && performance.now() - started < 10000)
    await new Promise((r) => setTimeout(r, 50));
  const references = referenceChecks(),
    fp = scientificFingerprint(),
    fingerprintError = Math.max(
      ...fp.map((v, i) => Math.abs(v - fingerprint.values[i])),
    );
  const cases = [];
  for (const id of [
    "pg-original",
    "pg-calibrated",
    "pg-table",
    "eb-reduced",
    "flowsheet",
  ] as const) {
    const p = newProject(id);
    p.science.settings.observer = "ukf";
    p.id = `device-qa-${id}`;
    const e = new Engine(p);
    for (let i = 0; i < 60 && !e.done; i++) {
      e.step();
      if (i % 5 === 0) await yieldFrame();
    }
    cases.push({
      model: id,
      error: e.error,
      steps: e.history.length - 1,
      metrics: metrics(e),
    });
  }
  const p = newProject();
  p.id = "device-qa-persistence";
  p.science.settings.controller = "pid";
  p.science.settings.setpoint += 1;
  const a = new Engine(p);
  for (let i = 0; i < 10; i++) a.step();
  await saveProject(p, a.checkpoint());
  const stored = await loadProject(p.id);
  if (!stored?.checkpoint) throw Error("SQLite perdeu checkpoint");
  const b = Engine.restore(stored.checkpoint);
  a.step();
  b.step();
  const persistence =
    JSON.stringify(a.last.x) === JSON.stringify(b.last.x) &&
    JSON.stringify(a.last.estimate) === JSON.stringify(b.last.estimate);
  await removeProject(p.id);
  await session.save();
  const hermes = !!(globalThis as any).HermesInternal;
  const result = {
    ok:
      hermes &&
      references.every((r) => r.ok) &&
      fingerprintError < 1e-6 &&
      persistence &&
      cases.every((c) => !c.error && c.steps === 60),
    hermes,
    references,
    fingerprintError,
    persistence,
    cases,
    elapsedMs: performance.now() - started,
    measuredOn: "Android runtime; performance.now; no desktop substitution",
  };
  const file = new File(Paths.document, "device-verification.json");
  file.write(JSON.stringify(result, null, 2));
  return result;
}
