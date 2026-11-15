# Experiment definitions

## Main study and controls

The five loads are 600, 900, 1200, 1500 and 1800 vehicles. Ten paired iterations (3401–3410) use workload seed `20260828 + iteration`. Each scenario is 60 simulated minutes with a three-minute warm-up. The initial controller configuration is `(0.6, 0.5, 0.7, 0.4, 85, 80, 90)` in the order alpha, three load weights, and three thresholds.

SCOPE uses λ=0.01, Rmax=0.15 and 60-second planning. The seven-parameter movement is the mean absolute change normalized by ranges `(0.9, 0.8, 0.8, 0.8, 75, 75, 75)`. The hard limit is enforced per update. Zero limit violations are a consequence of this mechanism, not independent evidence of superior task performance.

Main policies are SCOPE, AI_BASED, EXP3_MC, RAIDER_TRAX, RANDOM and SCOPE_STATIC. RANDOM is retained in every main comparison and in the inferential comparison family. The static control is selected per load from four training-ranked candidates, including the initial configuration, using separate calibration iterations 3201–3202. It is a calibrated matched control, not an external baseline or an exhaustive oracle.

The archived confirmatory run used `deadline_guard_v1` for EXP3. The subsequent routing ablation reran only the 50 main EXP3 scenarios with `edge_first_v1`. The final main figures use those 50 runs and reuse the same 350 unaffected runs. The guard-on results and paired differences remain available. This is a post-confirmation routing analysis, not an independent new confirmatory experiment. EXP3 uses the full catalogue (1408 training configurations plus the initial configuration), with its existing observation-based reward, normalization and QoS trigger.

## Ablations and adaptation

At 1800 vehicles, HARD_ONLY removes the soft movement cost (λ=0), SOFTCOST_OPT removes the hard bound, and PERFORMANCE_ONLY removes both. The same main SCOPE and static runs supply the comparison controls; they are not counted twice as independent replicates.

The adaptation scenario uses 1200 vehicles. The arrival-rate multiplier is 1.5 from 1200 to 2400 seconds. Policies include SCOPE, its matched SCOPE_FROZEN control, SCOPE_STATIC, the three ablations and AI_BASED. SCOPE_FROZEN follows the adaptive controller until the shift, then holds its configuration. Phase means summarize outcomes within phase-aligned reporting windows; they are not direct measurements of recovery or response time.

## λ calibration

The three development iterations 3301–3303 compare λ=0, 0.01 and 0.05 with Rmax=0.15. Each setting is evaluated at steady 1800 vehicles and in the 1200-vehicle shift scenario, with both adaptive and matched frozen controllers for the latter: 27 simulations in total. The manuscript table reports the adaptive cases as mean ± **sample standard deviation**, not confidence intervals. Movement and accepted-update counts include warm-up decisions. All runs, including unfavorable ones, are retained. This is descriptive development calibration; it does not establish a unique optimum. Reproduction does not reselect λ based on the final evaluation.

The older Rmax and reduced-catalogue sweeps struck out in the manuscript revision belong to a different implementation and are excluded from this corrected publication snapshot. The present protocol holds Rmax at 0.15 and uses the complete training-derived catalogue; it does not claim a reproduced budget sweep or a smallest successful budget.

## Planning interval sensitivity

The ΔT study uses fresh iterations 3601–3610 and intervals 15, 30, 60 and 90 seconds. Cases are steady 900, steady 1800, and the 1200-vehicle workload shift above. The original trained models and λ/Rmax are frozen.

The isolated runner changes one copied Java constant into a validated system property. Its default remains 60 seconds. The original implementation resets telemetry counters when planning occurs; changing ΔT therefore changes both decision frequency and the measurement horizon seen by models trained on 60-second windows. Rmax is per update, so a shorter interval also permits more cumulative movement per simulated hour. The experiment does not isolate adaptation speed, establish a universally optimal interval or justify selecting a new interval from completed test results.

## Metric and inference rules

- Failure percentage is `100 * failed / (completed + failed)` for finalized tasks; pending tasks are reported separately.
- Service, processing and network delay means are conditional on completion. A lower service mean can accompany a high failure percentage.
- QoE for all finalized tasks and QoE for completed tasks are distinct quantities.
- VM utilization uses the corrected all-VM percentage telemetry schema.
- Ten simulation iterations are the replicates. Individual tasks, applications and windows do not enlarge the independent sample size.
- Mean intervals are pointwise two-sided 95% Student-t intervals. They are not multiplicity-adjusted confidence bands.
- Main inference has 50 paired tests (five comparators × five loads × two primary metrics); ablations have six; the adaptive/frozen pair has two. Holm adjustment is separate for those families.
- The EXP3 routing comparison has ten paired tests. The ΔT study has one family of 18 paired tests (three alternatives to 60 s × three cases × two metrics).

All registered outcomes are retained. The results do not support a blanket claim that SCOPE is best on every metric/load: RANDOM can show a lower completed-task service mean, and the calibrated static control can perform strongly. Interpret the measured trade-offs and the supplied paired comparisons.
