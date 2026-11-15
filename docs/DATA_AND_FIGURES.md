# Data dictionary and figure map

## Archived results

`results/v5_guard_on/` and `results/v5_guard_off/` each contain 400 scenario summaries, with four application rows per scenario. They share 350 identical non-EXP3 scenarios; they must not be pooled as 800 independent experiments.

| File | Contents |
|---|---|
| `study.json`, `study_checksum.txt` | Original registered metadata and its checksum; historical absolute paths are provenance, not installation requirements |
| `completion.json` | Completed/expected scenario counts and profile |
| `study_metrics.csv` | Per-scenario, per-application metrics; join by group, label, load and iteration |
| `mean_metrics.csv` | Per-policy means and pointwise t intervals; `n`, `mean`, `lower`, `upper` |
| `paired_comparisons.csv` | Paired differences, confidence intervals, raw and Holm-adjusted p-values; direction is recorded |
| `decision_metrics.csv` | Per-epoch controller configuration and normalized movement |
| `window_metrics.csv` | Per-application reporting-window telemetry |
| `phase_metrics.csv`, `phase_means.csv` | Per-seed and summarized workload-shift phase outcomes |
| `adaptation_responses.csv` | First observed configuration-change timing and change counts |
| `pair_checks.json` | Matched adaptive/frozen evidence checks |
| `exp3_guard_pairs.csv`, `exp3_guard_contrasts.csv` | Guard-on/off paired effects, in `v5_guard_off` |

`load` is vehicle count; `iteration` is the paired run identifier; `application` is ALL_APPS, TRAFFIC_MANAGEMENT, DANGER_ASSESSMENT or INFOTAINMENT. Failure and utilization fields ending `_pct` are percentages. Delay fields ending `_seconds` are seconds. Blank movement entries for task-level baselines mean the seven-parameter controller measure is not applicable, not zero.

ΔT tables use `scenario` and `interval_seconds`. `application=CONTROLLER` summary rows describe decision count and movement. Its `study_metrics.csv` contains 480 rows (120 scenarios × four applications); its 168 summary rows include 96 task-metric cells and 72 controller-metric cells.

Original predictor metrics use failure **fractions** and dimensionless deadline-normalized service time, not the percentage/seconds units of simulation figures. There are 550 held-out rows per application; these rows share only two held-out simulation iterations and should not be presented as 550 independent simulation replications.

`results/lambda_calibration/` contains all 27 calibration scenarios (108 application rows) and their decision/window/phase data. `calibration_means.csv` retains the archive's three-seed t intervals. For the manuscript table, `reproduce.py calibration-table` instead calculates mean ± sample SD directly from `lambda_metrics.csv`, including each run's maximum step before aggregation. These two kinds of uncertainty must not be interchanged.

## Figure outputs

`RUN_MATLAB` creates 38 SCOPE panels and two ΔT panels. Every panel is saved as PDF, PNG and editable FIG. The main comparative list is SCOPE, AI-based, EXP3-MC, RAIDER-TRAX and RANDOM. The calibrated static control is plotted separately and retained in the supplementary comparisons.

| Folder | Files/use |
|---|---|
| `scope/main/` | `{ALL_APPS,TRAFFIC_MANAGEMENT,DANGER_ASSESSMENT,INFOTAINMENT}_{failure_pct,service_seconds}`: eight main panels; plus `ALL_APPS_qoe_all_pct` |
| `scope/static_control/` | Two SCOPE-versus-static panels across all five loads |
| `scope/ablations/` | Failure, service, QoE, total movement and changes: five panels |
| `scope/adaptation/` | Two adaptive-versus-frozen phase panels |
| `scope/supplementary/` | Eighteen panels retaining all controls and descriptive metrics |
| `scope/exp3_routing_ablation/` | Two guard-on/off EXP3 panels |
| `delta_t/` | `DeltaT_FailedTasks` and `DeltaT_ServiceTime` |

The archived PDFs in `results/figures/` are the verified MATLAB exports received from the original studies. Their bytes are protected by the artifact manifest. The exporter retains the established font, line/marker styles, colors and confidence intervals. Most panels use an 11 × 11 cm canvas. Two dense main legends use an 11 × 14.5 cm canvas and two legend columns below the axes.

Before manuscript insertion, check the source (archived versus fresh run) and export path. Keep the ΔT panels together as the interval-sensitivity figure. Do not mix retrained predictor evaluations with figures generated from the original models.

### Legacy interval figures

The historical filenames `Fig1_DeltaT_Comparison.png` and `Fig2_Stability_Analysis.png` are not outputs of this reproducibility snapshot. In particular, the illustrative cloud-routing-probability trajectory is not the same figure as the completed 120-scenario interval study. A manuscript that still uses those filenames must be reconciled with the archived `DeltaT_FailedTasks.pdf` and `DeltaT_ServiceTime.pdf` panels and their matching caption. This repository does not claim to reproduce an unidentified legacy image from the new interval-study data.
