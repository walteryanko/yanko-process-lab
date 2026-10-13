"""Offline, budgeted experiments. Truth is used only for retrospective scoring.

Search = seeded logarithmic exploration followed by shrinking pattern search.
The winner is selected on training only, then compared on two untouched seeds.
This is a local computational study, not a global optimum or plant autotuner.
"""
import copy
import csv
import io
import json
import math
import threading
import time
import uuid
from datetime import datetime, timezone
import numpy as np
from .schema import canonical
from .models import build_model
from .simulation import Simulation
from .storage import atomic_json, atomic_bytes


class Interrupted(Exception):
    pass


def integer(value, low, high, name):
    number = float(value)
    if not math.isfinite(number) or number != int(number) or not low <= number <= high:
        raise ValueError(f"{name}: use an integer from {low} to {high}")
    return int(number)


def options(project, payload):
    c = project["experiment"]
    out = {"steps": integer(payload.get("steps", min(80, int(c["duration"]/c["dt"]))), 4, 200, "Passos"),
           "time_budget_s": integer(payload.get("time_budget_s", 90), 5, 600, "Tempo de cálculo"),
           "budget": integer(payload.get("budget", 8), 3, 24, "Candidatos"),
           "target": payload.get("target", "controller")}
    if out["target"] not in ("controller", "observer", "joint"):
        raise ValueError("Unknown tuning target")
    return out


def criterion(result, model, target):
    """Dimensionless score; all terms are disclosed in the saved report."""
    if result["status"] != "completed":
        return {"score": 1e6, "feasible": False, "reason": result["error"] or result["status"]}
    rows = result["rows"]; duration = max(result["time"], 1e-9)
    norm = max(.05, abs(rows[0]["setpoint"])*.05) if result["manifest"]["project"]["experiment"]["control_target"] == "quality" else 5.
    tracking = result["metrics"]["iae"] / (duration*norm)
    moves = np.diff([r["input"] for r in rows])/(model.bounds[1]-model.bounds[0])
    effort = float(np.mean(moves**2))
    failures = result["controller"]["optimizer_failures"]/max(1, len(rows)-1)
    control = tracking + .02*effort + .2*failures
    observer = None
    if rows[-1]["estimate"] is not None:
        delta = (np.array([r["estimate"] for r in rows])-np.array([r["truth"] for r in rows]))/model.scale
        state = float(np.mean(np.sqrt(np.mean(delta**2, axis=0))))
        quality_norm = .05 if getattr(model, "kind", None) == "eb" else model.scale[model.qidx]
        quality = result["metrics"]["quality_rmse"]/quality_norm
        coverage = float(np.mean(result["metrics"]["empirical_2sd_coverage"]))
        observer = state + quality + .05*max(0., .9-coverage)
    score = control if target == "controller" else observer if target == "observer" else control + observer
    if score is None or not math.isfinite(score):
        raise ValueError("Criterion requires a finite observer estimate")
    return {"score": float(score), "feasible": True, "tracking": tracking, "normalized_move_energy": effort,
            "optimizer_failure_fraction": failures, "control_score": control, "observer_score": observer}


def search_space(project, target):
    c = project["experiment"]; m = build_model(project); space = []
    if target in ("controller", "joint"):
        if c["controller"] == "manual":
            raise ValueError("Selecione PID ou NMPC antes de sintonizar o controlador.")
        if c["controller"] == "pid":
            kp = max(abs(c["kp"]), (m.bounds[1]-m.bounds[0])/50)
            ki = max(abs(c["ki"]), kp/max(20*c["dt"], 1))
            space += [("kp", kp*.1, kp*4, False), ("ki", ki*.03, ki*8, False),
                      ("kd", 0., max(abs(c["kd"])*3, kp*c["dt"]*.3), True)]
        else:
            space += [("move_weight", .001, 10., False), ("horizon", 2., min(12., max(6., c["horizon"])), True)]
    if target in ("observer", "joint"):
        if c["observer"] == "none":
            raise ValueError("Selecione EKF, UKF ou MHE antes de sintonizar o sensor virtual.")
        space += [("q_scale", .001, 100., False), ("r_scale", .05, 20., False)]
    return space


def encode(params, space):
    return np.array([(params[k]-a)/(b-a) if linear else math.log(max(params[k], a)/a)/math.log(b/a)
                     for k, a, b, linear in space])


def decode(vector, space):
    params = {}
    for z, (key, a, b, linear) in zip(np.clip(vector, 0, 1), space):
        value = a+(b-a)*float(z) if linear else a*(b/a)**float(z)
        params[key] = int(round(value)) if key == "horizon" else float(value)
    return params


class Laboratory:
    """One background worker per application; polling never holds the simulation lock."""
    def __init__(self, storage):
        self.storage = storage; self.lock = threading.RLock(); self.job = None
        self.cancel_event = threading.Event(); self.worker = None

    def start(self, payload):
        project = canonical(payload["project"]); model = build_model(project)
        if not len(model.x0):
            raise ValueError("O laboratório dinâmico requer pelo menos um tanque ou CSTR.")
        kind = payload.get("kind", "tuning")
        if kind not in ("tuning", "comparison"):
            raise ValueError("Unknown laboratory experiment")
        opts = options(project, payload.get("options", {}))
        if kind == "tuning": search_space(project, opts["target"])
        variants = payload.get("variants", [])
        if kind == "comparison":
            if not isinstance(variants, list) or not 1 <= len(variants) <= 6:
                raise ValueError("Compare from one to six experimental cases")
            labels = set()
            for v in variants:
                if not isinstance(v.get("label"), str) or not 1 <= len(v["label"]) <= 100:
                    raise ValueError("Every case needs a short label")
                if not v["label"].strip() or v["label"].strip() in labels:
                    raise ValueError("Use nomes diferentes e não vazios para os ensaios.")
                labels.add(v["label"].strip())
                if not isinstance(v.get("experiment"), dict) or set(v["experiment"])-set(project["experiment"]):
                    raise ValueError("Unknown experiment settings")
                canonical({**project, "experiment": {**project["experiment"], **v["experiment"]}})
        with self.lock:
            if self.worker and self.worker.is_alive():
                raise ValueError("Já existe um cálculo no laboratório. Aguarde ou cancele.")
            self.cancel_event = threading.Event()
            self.job = {"id": uuid.uuid4().hex, "project_id": project["id"], "kind": kind, "status": "running",
                        "progress": 0., "message": "Preparando experimento", "completed_evaluations": 0,
                        "started": time.monotonic(), "error": None}
            self.worker = threading.Thread(target=self._work, args=(project, kind, opts, copy.deepcopy(variants)), daemon=True)
            self.worker.start()
            return self.status()

    def status(self):
        with self.lock:
            if not self.job: return None
            return {k: v for k, v in self.job.items() if k != "started"} | {"elapsed_s": time.monotonic()-self.job["started"] if self.job["status"] == "running" else self.job["elapsed_s"]}

    def cancel(self):
        self.cancel_event.set()
        return self.status()

    def _check(self):
        if self.cancel_event.is_set(): raise Interrupted("cancelled")
        if time.monotonic() >= self.deadline: raise Interrupted("budget_exhausted")

    def _run(self, project, label, report, retain=True):
        self._check()
        with self.lock: self.job["message"] = label
        sim = Simulation(project)
        while sim.status not in ("completed", "failed", "constraint_stop"):
            self._check(); sim.advance(1)
        self._check()
        result = sim.snapshot()
        with self.lock:
            self.job["completed_evaluations"] += 1
            self.job["progress"] = min(.99, self.job["completed_evaluations"]/self.total)
        if retain: report["runs"].append({"label": label, "result": result})
        return result

    def _work(self, source, kind, opts, variants):
        job_id = self.job["id"]
        report = {"schema_version": 1, "id": job_id, "kind": kind, "project_id": source["id"],
                  "project_name": source["name"], "created_utc": datetime.now(timezone.utc).isoformat(),
                  "source_project": source, "options": opts, "runs": [], "candidates": [], "recommendation": None,
                  "scope": "Offline synthetic experiment. Truth is retrospective scoring only; no plant connection. Time budget checked between integration/control steps."}
        self.deadline = time.monotonic()+opts["time_budget_s"]
        status = "completed"; error = None
        try:
            if kind == "comparison":
                self.total = len(variants)
                for v in variants:
                    p = copy.deepcopy(source); p["experiment"].update(v["experiment"])
                    p["experiment"]["duration"] = opts["steps"]*p["experiment"]["dt"]
                    self._run(canonical(p), v["label"], report)
            else: self._tune(source, opts, report)
        except Interrupted as exc:
            status = str(exc); report["recommendation"] = None
        except Exception as exc:
            status = "failed"; error = str(exc); report["recommendation"] = None
        elapsed = time.monotonic()-self.job["started"]
        report.update(status=status, error=error, elapsed_s=elapsed)
        try:
            atomic_json(self._path(job_id), report)
            summary = {k: report[k] for k in ("id", "kind", "project_id", "project_name", "created_utc", "status", "elapsed_s")}
            summary.update(run_count=len(report["runs"]), accepted=bool(report["recommendation"]))
            atomic_json(self.storage.root/"laboratory"/"index"/(job_id+".json"), summary)
        except Exception as exc:
            status = "failed"; error = "Não foi possível salvar o experimento: "+str(exc)
        with self.lock:
            self.job.update(status=status, error=error, elapsed_s=elapsed, progress=1. if status == "completed" else self.job["progress"], message=status)

    def _tune(self, source, opts, report):
        target = opts["target"]; space = search_space(source, target); c = source["experiment"]
        project = copy.deepcopy(source); project["experiment"]["duration"] = opts["steps"]*c["dt"]
        base = {key: c[key] for key, *_ in space}; best = dict(base); rng = np.random.default_rng(c["seed"])
        train = c["seed"]; validation = [(train+104729) % 2**32, (train+209759) % 2**32]
        report.update(algorithm="Seeded log-space exploration + shrinking coordinate pattern search, v1",
                      training_seeds=[train], validation_seeds=validation,
                      search_bounds={key: [a, b] for key, a, b, _ in space},
                      scoring={"control": "IAE/(duration*target_scale) + 0.02*mean(normalized_input_moves²) + 0.2*optimizer_failure_fraction",
                               "observer": "mean(state_RMSE/state_scale) + quality_RMSE/quality_scale + 0.05*max(0,0.90-mean_2sd_coverage)",
                               "joint": "control + observer", "target_scale": "5 K or max(0.05, 5% of quality setpoint)",
                               "acceptance": "At least 1% mean validation improvement; neither seed >5% worse; both runs complete. Holdout never guides search."})
        self.total = opts["budget"]+4
        model = build_model(project); best_score = float("inf"); winner = 0
        report["scoring"].update(state_scale=model.scale.tolist(),
                                 quality_scale=.05 if getattr(model,"kind",None)=="eb" else float(model.scale[model.qidx]),
                                 input_span=float(model.bounds[1]-model.bounds[0]))
        for i in range(opts["budget"]):
            self._check()
            if i == 0: params = dict(base)
            elif i <= max(2, opts["budget"]//2):
                # Seeded logarithmic exploration; include a lower-noise, no-D PID candidate.
                z = rng.random(len(space))
                if i == 1:
                    z = np.clip(encode(base, space)+np.array([.16 if key in ("kp", "ki") else -.2 for key, *_ in space]), 0, 1)
                params = decode(z, space)
                if "kd" in params and i % 2: params["kd"] = 0.
            else:
                z = encode(best, space); coordinate = (i-opts["budget"]//2-1) % len(space)
                z[coordinate] += (.25*(1-i/(opts["budget"]+1)))*(1 if i % 2 else -1)
                params = decode(z, space)
            candidate = copy.deepcopy(project); candidate["experiment"].update(params, seed=train)
            try:
                result = self._run(canonical(candidate), f"Treino · candidato {i+1}/{opts['budget']}", report, retain=i == 0)
                metrics = criterion(result, model, target)
            except (ValueError, FloatingPointError, np.linalg.LinAlgError, OverflowError) as exc:
                metrics = {"score": 1e6, "feasible": False, "reason": str(exc)}
            report["candidates"].append({"index": i, "parameters": params, **metrics})
            if metrics["feasible"] and metrics["score"] < best_score:
                best_score = metrics["score"]; best = params; winner = i
        report["training_winner"] = winner
        pairs = []
        for seed in validation:
            pair = {"seed": seed}
            for name, params in (("baseline", base), ("candidate", best)):
                p = copy.deepcopy(project); p["experiment"].update(params, seed=seed)
                result = self._run(canonical(p), f"Validação {seed} · {'original' if name == 'baseline' else 'candidato'}", report)
                pair[name] = criterion(result, model, target)
            pairs.append(pair)
        mean_base = float(np.mean([p["baseline"]["score"] for p in pairs]))
        mean_best = float(np.mean([p["candidate"]["score"] for p in pairs]))
        improvement = (mean_base-mean_best)/max(mean_base, 1e-12)
        accepted = winner != 0 and improvement >= .01 and all(p["baseline"]["feasible"] and p["candidate"]["feasible"] and p["candidate"]["score"] <= p["baseline"]["score"]*1.05 for p in pairs)
        report["validation"] = {"pairs": pairs, "baseline_score": mean_base, "candidate_score": mean_best,
                                "improvement_fraction": improvement, "accepted": accepted}
        report["recommendation"] = best if accepted else None
        report["conclusion"] = "Ganho confirmado nas duas sementes de validação. Revise e aplique se adequado ao estudo." if accepted else "Nenhum ganho validado suficiente. A configuração original foi mantida."

    def _path(self, id):
        if not isinstance(id, str) or len(id) != 32 or any(c not in "0123456789abcdef" for c in id):
            raise ValueError("Invalid laboratory record ID")
        return self.storage.root/"laboratory"/(id+".json")

    def read(self, id):
        return json.loads(self._path(id).read_text("utf-8"))

    def history(self, project_id):
        self.storage.path(project_id)
        records = []
        for path in (self.storage.root/"laboratory"/"index").glob("*.json"):
            try:
                item = json.loads(path.read_text("utf-8"))
                if item["project_id"] == project_id: records.append(item)
            except (ValueError, OSError, KeyError): continue
        return sorted(records, key=lambda x: x["created_utc"], reverse=True)[:50]

    def apply(self, id, project):
        record = self.read(id); current = canonical(project)
        if record["status"] != "completed" or not record.get("recommendation"):
            raise ValueError("Este estudo não tem uma recomendação validada.")
        if current != record["source_project"]:
            raise ValueError("O projeto mudou desde a sintonia. Reabra a configuração do estudo ou execute uma nova busca.")
        current["experiment"].update(record["recommendation"])
        current["last_tuning_record"] = id
        return canonical(current)

    def export(self, id, format):
        record = self.read(id)
        if format == "json": return {"path": str(self._path(id)), "record": record}
        if format != "csv": raise ValueError("Use JSON or CSV")
        out = io.StringIO(newline=""); writer = csv.writer(out)
        writer.writerow(["case", "seed", "time_s", "temperature_truth", "temperature_estimate", "temperature_unit", "quality_truth", "quality_estimate", "input", "input_unit", "setpoint"])
        for run in record["runs"]:
            r = run["result"]; ti = r["metadata"]["temperature_index"]
            for row in r["rows"]:
                writer.writerow([run["label"], r["manifest"]["project"]["experiment"]["seed"], row["t"], row["truth"][ti], row["estimate"][ti] if row["estimate"] else "", r["metadata"]["units"][ti], row["quality_truth"], row["quality_estimate"], row["input"], r["metadata"]["input_unit"], row["setpoint"]])
        path = self.storage.root/"exports"/(id+"-laboratory.csv"); content = out.getvalue()
        atomic_bytes(path, content.encode("utf-8")); return {"path": str(path), "csv": content}
