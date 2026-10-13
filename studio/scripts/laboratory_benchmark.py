"""Reproducible 0.2 demonstrations, with no claim about a user's target hardware."""
import copy
import json
import platform
import tempfile
from pathlib import Path
from processlab.api import API
from processlab.scenarios import scenarios
from processlab.storage import atomic_json


def main():
    cases = []
    examples = scenarios()
    definitions = [('tank-pid', 1, 'controller', 60, 8, {}),
                   ('tank-ekf-noisy', 1, 'observer', 60, 8, {'sensor_sigma': .8}),
                   ('pg-ukf', 2, 'observer', 12, 4, {}),
                   ('eb-ekf', 3, 'observer', 8, 4, {})]
    with tempfile.TemporaryDirectory() as directory:
        api = API(directory)
        for name, index, target, steps, budget, changes in definitions:
            p = copy.deepcopy(examples[index]); p['experiment'].update(changes)
            start = api.request('lab_start', {'project': p, 'kind': 'tuning', 'options': {'target': target, 'steps': steps, 'budget': budget, 'time_budget_s': 90}})
            assert start['ok'], start
            api.laboratory.worker.join(110)
            assert not api.laboratory.worker.is_alive()
            report = api.laboratory.read(start['data']['id'])
            assert report['status'] == 'completed', report.get('error')
            case = {'case': name, 'options': report['options'], 'source_project': report['source_project'],
                    'validation': report['validation'], 'recommendation': report['recommendation'],
                    'elapsed_s': report['elapsed_s'], 'engine_manifest': report['runs'][0]['result']['manifest']}
            cases.append(case)
            print(json.dumps({'case': name, 'elapsed_s': report['elapsed_s'], 'validation': report['validation']['improvement_fraction'], 'accepted': bool(report['recommendation'])}), flush=True)
    atomic_json(Path(__file__).resolve().parents[1]/'evidence/laboratory-benchmark.json', {'version': '0.2.0', 'platform': platform.platform(), 'scope': 'Runtime host only, not target-laptop performance. PG/EB short execution demonstrations, not accuracy validation.', 'cases': cases})


if __name__ == '__main__': main()
