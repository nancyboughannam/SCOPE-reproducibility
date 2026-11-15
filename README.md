# SCOPE: reproducible edge–cloud orchestration experiments

Research code and archived results for **Stability-Aware Multi-Timescale Orchestration for IoE Edge–Cloud Systems**.

This publication snapshot contains the original corrected predictors, the λ-calibration evidence, the completed main study, RANDOM as a main baseline, the separate EXP3 routing comparison, and the completed planning-interval (ΔT) study. It provides both **figure regeneration from archived data** and **fresh simulation runs**. Experimental retrained predictors are not substituted for the models behind these results.

## Quick start

Clone the repository, then run the setup script in **Terminal**:

```bash
git clone --depth 1 https://github.com/nancyboughannam/SCOPE-reproducibility.git
cd SCOPE-reproducibility
bash SETUP.sh
```

Prerequisites: Git and **Python 3.11 or 3.12**. Simulations additionally require **JDK 21 or newer**. Figure export requires **MATLAB R2020a or newer** and the **Times New Roman** font. See [installation and troubleshooting](docs/REPRODUCIBILITY.md) for interpreter selection and platform notes. No IDE is required.

`SETUP.sh` creates a local `.venv`, installs the pinned scientific dependencies, checks archive integrity, and recomputes the statistical summaries. Wait for `SETUP COMPLETE`.

### Regenerate the paper figures without running simulations

In **MATLAB**, change to your clone and run:

```matlab
cd(fullfile(getenv('HOME'),'Documents','SCOPE-reproducibility')) % change to your actual clone path
RUN_MATLAB
```

This reads only the archived paper tables. It exports 40 panels as vector PDF, 300 dpi PNG and editable FIG files into a new `outputs/figures_...` folder. RANDOM appears in the main comparisons. Existing figure folders are preserved. The two dense main legends are placed below the curves.

Then return to **Terminal**, in the repository folder:

```bash
bash ZIP_RESULTS.sh archived
```

The review ZIP is written to `packages/`. On macOS, Finder opens with the ZIP selected. Verified PDF exports are also available immediately in [results/figures](results/figures).

### Run fresh simulations

Check the full pipeline with a small execution test first:

```bash
bash RUN_SIMULATION.sh --profile smoke
```

For the full paper protocol:

```bash
bash RUN_SIMULATION.sh
```

The script compiles isolated Java classes, starts and stops the required local Python services, performs static calibration, runs all policies including RANDOM, checks paired workloads, and exports CSV summaries. **Do not launch Flask or Java manually.** On macOS it uses `caffeinate`; keep the laptop plugged in with the lid open.

Full reproduction performs **637 simulations**: 27 λ-calibration runs, 40 static-calibration runs, 400 guard-on study runs, 50 additional edge-first EXP3 runs, and 120 ΔT runs. The final main table contains 400 scenarios: the 350 unaffected results plus the 50 edge-first EXP3 results. Each full simulation represents 60 minutes, with a 3-minute warm-up. Wall-clock time depends on hardware; no unmeasured completion-time estimate is promised.

Results are saved under `reruns/paper/`; smoke results use `reruns/smoke/`. Press **Ctrl+C once**, wait for `STOPPED`, and repeat the same command to resume. Completed jobs are verified and skipped. Interrupted attempts are retained in separate folders. Ports 5002 and 5003 must be free; unrelated services are never killed.

When `SIMULATIONS COMPLETE` appears, use **MATLAB**:

```matlab
cd(fullfile(getenv('HOME'),'Documents','SCOPE-reproducibility')) % your clone path
RUN_MATLAB('rerun')
```

Then use **Terminal**:

```bash
bash ZIP_RESULTS.sh rerun
```

Smoke results are execution checks, not paper results; the publication exporter rejects them.

## What is reproduced

| Paper component | Archived data | Reproduction/export |
|---|---|---|
| Corrected original predictor table (Table 4) | `FLaskAPIs/scope_candidate_xgboost_results/` | `.venv/bin/python reproduce.py table4` |
| λ-calibration table (Table 6) | `results/lambda_calibration/` | `.venv/bin/python reproduce.py calibration-table` |
| Main failures and service-time figures, including RANDOM | `results/v5_guard_off/` | `RUN_MATLAB`; `scope/main/` |
| ΔT figure: failures and service time | `results/delta_t/` | `RUN_MATLAB`; `delta_t/` |
| Static control across all loads | `results/v5_guard_off/` | `scope/static_control/` |
| Hard-only, soft-cost and performance-only ablations | `results/v5_guard_off/` | `scope/ablations/` |
| Workload shift and matched frozen control | `results/v5_guard_off/` | `scope/adaptation/` |
| QoE, utilization, delay decomposition and all controls | `results/v5_guard_off/` | `scope/supplementary/` |
| EXP3 guard-on versus edge-first comparison | Both `v5_guard_*` folders | `scope/exp3_routing_ablation/` |

See [experiment definitions and metric interpretation](docs/EXPERIMENTS.md), [data dictionary and figure map](docs/DATA_AND_FIGURES.md), and [provenance](docs/PROVENANCE.md). Figure/table numbering can change during manuscript revision; the mapping above identifies the experiments and output filenames.

## Frozen protocol

- Main iterations: **3401–3410**, with 600, 900, 1200, 1500 and 1800 vehicles.
- SCOPE: **λ = 0.01**, **Rmax = 0.15**, planning interval **60 s**, `deadline_guard_v1` routing.
- Main EXP3: `edge_first_v1`; the guard-on comparison is retained separately.
- Static calibration: iterations **3201–3202**, separated from evaluation.
- λ calibration: **0, 0.01, 0.05**, iterations **3301–3303**, with steady and shifted workloads and matched frozen controls.
- ΔT: **15, 30, 60 and 90 s**, iterations **3601–3610**; steady 900, steady 1800, and a 1200-vehicle workload shift.
- Original predictor split: training iterations 3002–3005 and 3009–3010; validation 3001 and 3008; test 3006 and 3007.

Iteration identifiers are not the literal random seeds: the simulator uses `20260828 + iteration`. No new model fitting occurs during simulation reproduction.

Means and two-sided 95% Student-t intervals use ten simulation iterations as replicates. Paired tests and Holm adjustments are supplied separately. Service, processing and network times describe **completed tasks only**; they must be interpreted together with task failures. Static is a calibrated control. The EXP3 routing and ΔT analyses are post-confirmation analyses and are labeled accordingly.

## Repository layout

| Path | Purpose |
|---|---|
| `reproduce.py`, root shell/MATLAB scripts | Public entry points |
| `ThreeBrains/src`, `ThreeBrains/lib` | Audited Java simulator source and pinned JARs |
| `FLaskAPIs/` | Frozen services, original predictor preparation/training, shared runners and focused regression tests |
| `experiments/delta_t/` | Registered interval-sensitivity runner and source audit |
| `matlab/` | Publication exporters |
| `results/` | Read-only archived per-run tables, summaries and PDF figures |
| `provenance/` | Input mapping, source audit and SHA-256 manifest |
| `scripts/` | Independent numerical verification and Table 4 export |
| `docs/` | Protocol, data, installation, provenance and validation details |

Generated environments, raw reruns, caches, IDE files and review ZIPs are ignored by Git. This is a separate publication repository. The original [SCOPE repository](https://github.com/nancyboughannam/SCOPE) retains its development history; that history is not imported here. Focused regression tests are retained because they check the reproduction workflow and policy behavior.

## Verification and development

```bash
.venv/bin/python reproduce.py verify
.venv/bin/python reproduce.py table4
.venv/bin/python reproduce.py calibration-table
.venv/bin/python -m pytest
```

The Table 4 command evaluates all six saved candidate-aware models on the held-out rows and checks the stored state-only predictions. To refit the original training procedure into a separate timestamped folder:

```bash
.venv/bin/python reproduce.py train
```

Freshly fitted models do not replace the archived models or the main simulation inputs. Exact archived data and models are included for reference; numerical equality of newly executed simulations should be assessed using the recorded platform and environment. See [validation evidence and limits](docs/VALIDATION.md).

## Citation, license and support

Use [CITATION.cff](CITATION.cff) and cite the exact Git commit or an immutable release. This repository does not claim that the manuscript has been accepted, and no DOI is assigned here. A permanent archival DOI should be added only after an actual archive has been deposited.

Original SCOPE Python code and documentation retain the root [MIT license](LICENSE). The modified EdgeCloudSim Java source retains its [GPLv3 license](ThreeBrains/LICENSE); bundled dependencies retain their respective upstream terms. See [NOTICE.md](NOTICE.md) and [THIRD_PARTY.md](THIRD_PARTY.md).

Report reproducibility problems through [GitHub Issues](https://github.com/nancyboughannam/SCOPE-reproducibility/issues), including the commit, OS/CPU, Python and Java versions, command, and failing log. Do not attach credentials or unrelated personal files.
