# Additional manuscript experiments

## Recompute the reported results

From the repository root after setup:

```bash
.venv/bin/python reproduce.py revision-results
```

The command reads the archived measurements, prints the summaries, and checks the reconstructed values against the exported CSVs. It requires the pinned Python environment. Java and MATLAB are needed only for other stages.

| Experiment | Independent observations and settings | Archive |
|---|---|---|
| Prediction noise, Table 9 | Ten paired iterations (3401–3410), 1,800 vehicles. At each planning decision, noise with standard deviation 0, 1 or 2 times each predictor's validation RMSE is added before clipping and candidate scoring. Four paired contrasts use a single Holm adjustment. | [Per-run data, paired comparisons, calibration and protocol](../../results/prediction_noise/) |
| Local control-loop timing, Section 5.1.3 | Three iterations (3401–3403), 1,800 vehicles. Java measures telemetry capture through validated local policy application. The primary median and linearly interpolated 95th percentile pool 171 updates after the 180 s warm-up. | [Update timings, host protocol and instrumentation patch](../../results/control_loop_latency/) |
| Hard reconfiguration budget, Appendix Table A.9 | Four budgets (0.10, 0.15, 0.20, 0.30) and three paired development iterations (3301–3303) at 1,800 vehicles, with λ = 0.01 and ΔT = 60 s. This sensitivity study followed the main evaluation. | [Per-run outcomes, decision audit and protocol](../../results/reconfiguration_budget/) |

Each archive includes compressed per-run logs. The published protocols omit workstation-specific directory names, and the run bundles omit service health messages containing local paths. The original numerical data, timing records and study settings are preserved. Recorded wall-clock latency is specific to the measured host (Apple M2 MacBook Air, 8 GB); fresh timing measurements describe the machine executing them.

## Run the simulations again

Use a full JDK 21 or later and complete `bash SETUP.sh` first. Run these commands from the repository root on macOS or Linux. They unpack the archived drivers into separate writable folders and point the drivers at the frozen inputs in this clone. Run one driver at a time because the local optimizer uses port 5002.

```bash
export SCOPE_PROJECT="$PWD"
mkdir -p reruns/revision
for study in prediction_noise control_loop_latency reconfiguration_budget; do
  .venv/bin/python -m zipfile -e "experiments/revision_studies/$study.zip" "reruns/revision/$study"
done
```

| Experiment | Command | Output under `reruns/revision/` |
|---|---|---|
| Prediction noise, 30 runs | `.venv/bin/python reruns/revision/prediction_noise/driver/run_noise.py` | `prediction_noise/SCOPE_R1_10_Results.zip` |
| Local control-loop timing, 3 runs | `.venv/bin/python reruns/revision/control_loop_latency/driver/run_timing.py` | `control_loop_latency/SCOPE_R1_15_Results.zip` |
| Hard reconfiguration budget, 12 runs | `.venv/bin/python reruns/revision/reconfiguration_budget/run_sweep.py --output reruns/revision/budget-output` | `budget-output/results/` |

The noise driver also accepts `--smoke` for a shorter execution check on separate seeds. Full-scale timing should be run on an otherwise idle machine. If running commands in a new shell, set `SCOPE_PROJECT` again from the repository root.
