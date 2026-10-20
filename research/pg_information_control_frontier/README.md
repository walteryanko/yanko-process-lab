# YCS PG Information & Control Frontier
Scientific computational campaign, 20 October 2026.

Status is determined by results/execution.json and the executed test log, never by this README.
The campaign preserves the recovered six-state MATLAB process as M0. M1H/M1J/M2 are
explicit hypotheses, not experimentally reconciled physical property datasets.

## Reproduce
Python 3.12, CPU, no paid APIs:
python -m pip install -r research/pg_information_control_frontier/requirements.txt
python -m unittest discover -s research/pg_information_control_frontier/tests -v
python research/pg_information_control_frontier/src/experiments.py
python -m pip install -r research/pg_information_control_frontier/reproducibility/document_requirements.txt
python research/pg_information_control_frontier/src/reporting.py

Run commands from the repository root. Save the unittest transcript to
research/pg_information_control_frontier/results/tests.log before reporting.
The report builder requires Pandoc and pdflatex on PATH. On Windows, install
Pandoc and MiKTeX (including Portuguese Babel and recommended LaTeX packages).
On Ubuntu the executed workflow installs pandoc, texlive-latex-extra,
texlive-lang-portuguese and lmodern. The PowerShell helper is supplied but has
not been executed on the target Windows/Ryzen machine.

## Protocol
Frozen in configs/protocol.json before simulations. 14 fixed scenarios x 19 methods x
20 independent paired noise seeds = 5320 main trajectories; 400 confirmation trajectories;
18 grid sensitivity trajectories. Noise replicates do not represent 20 physical reactors.
Each episode lasts 0.9 h. Methods share the same actuator authority within a scenario.
The finite control grid uses two blocks and horizon 14. B1_continuous is an additional
SLSQP comparator in that same two-block class; it does not certify a global continuous optimum.
MHE is a six-step deterministic window with an approximate arrival prior.
Known inventory, true-state oracle, and chemical-sampling arms have extra information.

## Recovered provenance
M0: research/darwin-observer/vendor/thesis_original/modeloCT.m and vendor/legacy_model.py,
commit d2610a0723cbbaf00d3f4559242ba0efafb67771.
Dissertation pages 38-42 read from Dissertacao_WalterYanko.pdf.
Historical ICAC manuscript read, but branch research/icac-information-decision is absent
from the live branch listing and commit search returned no matching commit.
C01-C14 archives were located by filename; full bytes could not be recovered in this session.
The historical 0.951143 / 0.850912 / 0.358768 and 14.60% are NOT new results.

## Limits
No empirical Cp(T), analyzer dynamics, industrial plant data or target Ryzen timing.
Model alternatives change only declared physical closures.
No publication novelty claim is implied by generating manuscripts.
Full requested v1.0 cannot be called final without historical replay and stronger continuous
NMPC/MHE benchmarking. Delivered files must state their scope and remaining gaps.
