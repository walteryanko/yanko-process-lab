import copy
import csv
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from processlab.api import API
from processlab.laboratory import Interrupted, options, search_space
from processlab.scenarios import scenarios
from processlab.schema import canonical
from processlab.simulation import Simulation


class LaboratoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.examples = scenarios()

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.api = API(self.directory.name)
        self.project = copy.deepcopy(self.examples[1])

    def run_job(self, **kwargs):
        p = kwargs.pop("project", self.project)
        payload = {"project": p, "kind": "tuning", "options": {"steps": 12, "budget": 4, "time_budget_s": 90}, **kwargs}
        started = self.api.request("lab_start", payload)
        self.assertTrue(started["ok"], started)
        self.api.laboratory.worker.join(100)
        self.assertFalse(self.api.laboratory.worker.is_alive(), "Worker did not finish")
        report = self.api.request("lab_read", {"id": started["data"]["id"]})
        self.assertTrue(report["ok"], report)
        return report["data"]

    def test_seeded_search_repeats_and_holdout_is_separate(self):
        a = self.run_job(); b = self.run_job()
        self.assertEqual(a["status"], "completed", a["error"])
        self.assertEqual(a["candidates"], b["candidates"])
        self.assertEqual(a["validation"], b["validation"])
        self.assertFalse(set(a["training_seeds"]) & set(a["validation_seeds"]))
        self.assertEqual(a["source_project"], self.project)
        scores = [c["score"] if c["feasible"] else float("inf") for c in a["candidates"]]
        self.assertEqual(a["training_winner"], scores.index(min(scores)))
        for run_a, run_b in zip(a["runs"], b["runs"]):
            self.assertEqual(run_a["result"]["rows"], run_b["result"]["rows"])

    def test_pid_improvement_and_stale_project_apply_guard(self):
        r = self.run_job(options={"steps": 60, "budget": 8, "time_budget_s": 90})
        self.assertTrue(r["validation"]["accepted"], r.get("conclusion"))
        self.assertGreater(r["validation"]["improvement_fraction"], .1)
        applied = self.api.laboratory.apply(r["id"], self.project)
        self.assertEqual(applied["experiment"]["kp"], r["recommendation"]["kp"])
        self.assertEqual(self.project["experiment"]["kp"], 7000)
        changed = copy.deepcopy(self.project); changed["experiment"]["setpoint"] += 1
        with self.assertRaisesRegex(ValueError, "mudou"): self.api.laboratory.apply(r["id"], changed)

    def test_no_validation_gain_never_creates_recommendation(self):
        # Same score for every completed candidate: acceptance must stay false.
        from processlab.laboratory import criterion
        def tied(result, model, target):
            metrics = criterion(result, model, target); metrics["score"] = 1.
            return metrics
        with patch("processlab.laboratory.criterion", side_effect=tied): r = self.run_job()
        self.assertIsNone(r["recommendation"])
        self.assertFalse(r["validation"]["accepted"])
        with self.assertRaises(ValueError): self.api.laboratory.apply(r["id"], self.project)

    def test_observer_and_joint_tuning_adjust_only_requested_parameters(self):
        for target, expected in (("observer", {"q_scale", "r_scale"}), ("joint", {"kp", "ki", "kd", "q_scale", "r_scale"})):
            r = self.run_job(options={"steps": 8, "budget": 3, "time_budget_s": 90, "target": target})
            self.assertEqual(r["status"], "completed", r["error"])
            self.assertEqual(set(r["candidates"][1]["parameters"]), expected)
            self.assertTrue(all(c["feasible"] for c in r["candidates"]))

    def test_ukf_mhe_and_nmpc_tuning_execute(self):
        for observer in ("ukf", "mhe"):
            p = copy.deepcopy(self.project); p["experiment"]["observer"] = observer
            r = self.run_job(project=p, options={"steps": 4, "budget": 3, "time_budget_s": 90, "target": "observer"})
            self.assertEqual(r["status"], "completed", r["error"])
            self.assertTrue(all(c["feasible"] for c in r["candidates"]))
        p = copy.deepcopy(self.examples[4])
        r = self.run_job(project=p, options={"steps": 4, "budget": 3, "time_budget_s": 90})
        self.assertEqual(r["status"], "completed", r["error"])
        self.assertEqual(set(r["search_bounds"]), {"horizon", "move_weight"})
        for run in r["runs"]:
            self.assertTrue(all(0 <= row["input"] <= 100000 for row in run["result"]["rows"]))

    def test_comparison_preserves_active_simulation_and_replays(self):
        self.api.request("reset", self.project); self.api.request("advance", {"count": 2})
        before = copy.deepcopy(self.api.request("inspect")["data"]["rows"])
        variants = [{"label": "PID", "experiment": {}}, {"label": "Manual", "experiment": {"controller": "manual"}}]
        r = self.run_job(kind="comparison", variants=variants)
        self.assertEqual(r["status"], "completed")
        self.assertEqual(before, self.api.request("inspect")["data"]["rows"])
        self.assertNotEqual(r["runs"][0]["result"]["rows"], r["runs"][1]["result"]["rows"])
        for run in r["runs"]:
            self.assertEqual(run["result"]["rows"], Simulation.replay(run["result"])["rows"])
        csv_result = self.api.laboratory.export(r["id"], "csv")
        rows = list(csv.reader(io.StringIO(csv_result["csv"])))
        self.assertEqual(len(rows), 1+sum(len(run["result"]["rows"]) for run in r["runs"]))
        self.assertTrue(Path(csv_result["path"]).is_file())
        reopened = API(self.directory.name)
        self.assertEqual(reopened.laboratory.history(self.project["id"])[0]["id"], r["id"])
        self.assertEqual(reopened.laboratory.read(r["id"]), r)

    def test_cancellation_keeps_configuration_and_prevents_apply(self):
        started = self.api.request("lab_start", {"project": self.project, "options": {"steps": 200, "budget": 24, "time_budget_s": 90}})
        self.assertTrue(started["ok"])
        self.api.request("lab_cancel"); self.api.laboratory.worker.join(30)
        r = self.api.laboratory.read(started["data"]["id"])
        self.assertEqual(r["status"], "cancelled"); self.assertIsNone(r["recommendation"])
        self.assertEqual(r["source_project"], self.project)

    def test_budget_exhaustion_saves_partial_without_recommendation(self):
        with patch.object(self.api.laboratory, "_check", side_effect=Interrupted("budget_exhausted")):
            r = self.run_job()
        self.assertEqual(r["status"], "budget_exhausted"); self.assertIsNone(r["recommendation"])
        self.assertEqual(r["runs"], [])

    def test_rejects_invalid_limits_and_unavailable_strategies(self):
        for opts in ({"steps": 201}, {"budget": 2}, {"time_budget_s": 0}, {"target": "unknown"}, {"steps": float("nan")}):
            with self.assertRaises(ValueError): options(self.project, opts)
        p = copy.deepcopy(self.project); p["experiment"]["controller"] = "manual"
        with self.assertRaises(ValueError): search_space(p, "controller")
        p["experiment"]["observer"] = "none"
        with self.assertRaises(ValueError): search_space(p, "observer")
        p["experiment"]["move_weight"] = -1
        with self.assertRaises(ValueError): canonical(p)
        with self.assertRaises(ValueError): self.api.laboratory.read("../escape")
        response = self.api.request("lab_start", {"project": self.project, "kind": "comparison", "variants": [{"label": "X", "experiment": {"typo": 12}}]})
        self.assertFalse(response["ok"])


if __name__ == "__main__": unittest.main(verbosity=2)
