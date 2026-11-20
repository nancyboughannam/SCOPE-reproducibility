# Validation evidence and limits

Validation was performed on 15 November 2026 in Linux x86-64 with Python 3.12 and OpenJDK 21.0.13, using the scientific package versions pinned in `requirements-reproducibility.txt`.

## Checks completed

- All 94 frozen runtime inputs match the completed study's audited hashes, including the original optimizer service, Java source/libraries, workload files and saved models.
- Both archived main datasets pass independent recomputation of 1,552 means/intervals each, 42 phase means each, 58 paired tests each, and their Holm families.
- The ΔT archive passes all 168 task/controller mean/interval checks and all 18 paired/Holm comparisons.
- The EXP3 routing archive passes paired-value checks and all ten Holm comparisons.
- The λ-calibration archive contains all 27 scenarios and passes all 45 archived mean/interval checks. Its manuscript table is separately exported as mean ± sample SD.
- All six frozen candidate-aware predictors reproduce the corrected original held-out Table 5 values. Archived state-only predictions and disjoint iteration partitions are checked.
- Forty-two regression tests pass, covering objective/routing behavior, EXP3 feedback, immutable receipts, stopping, protected output paths and the frozen runtime mapping.
- The complete smoke execution covers 53 scenarios: nine λ calibration, eight static calibration, 22 main/ablation/adaptation, two edge-first EXP3, and 12 ΔT. Completed jobs are skipped on resume.
- Two additional full-duration reference scenarios (SCOPE and RANDOM, iteration 3401, 1800 vehicles) match the original archived outcomes across 112 application metrics. Maximum absolute difference: `7.105427357601002e-15`.
- An actual Ctrl+C interruption of an active ΔT simulation exits with code 130, prints STOPPED, frees the service port and preserves the partial attempt. Resume completes all 12 scenarios in that test while keeping the interrupted attempt.
- Archived and fresh-result ZIP creation complete successfully.

## Limits that remain explicit

The recovery into the separate reproducibility repository was checked again on 15 November 2026. Setup, all 235 artifact hashes, the 94 frozen runtime inputs, the archived statistical summaries, the predictor export (then labeled Table 4), the calibration-table export, all 42 regression tests, all 53 smoke simulations, and archived ZIP packaging passed. Only documentation and the added validation record differ from the recovered snapshot. The structured record is in [restoration_validation.json](../provenance/restoration_validation.json).

The full 637-simulation suite was not rerun during repository preparation. Its archived full-study evidence is included and checked; the smoke suite and two full-duration reference cases validate the new execution path without claiming a new complete scientific experiment.

MATLAB and macOS were unavailable in this validation environment. The original archived MATLAB PDF exports are included and checksummed. The root MATLAB entry point and two legend-placement adjustments were inspected but not executed here. Check those exports on the reference Mac before replacing manuscript figures. Finder opening and macOS `caffeinate` behavior are implemented but not locally exercised.

A separate refit of the original training procedure completed, but fitted models and validation-selected stopping rounds were not identical to the archive on this Linux runtime. The cause was not isolated. Original models remain the default; no refitted result is presented as the original Table 5 or silently promoted into simulation. The historical trainer did not save the fitted state-only controls, so their original table column is verified from archived predictions; refitting those controls may differ.

The GitHub Actions workflow is provided; the checks above were run locally during preparation. Remote Actions results should be read from this repository's Actions tab. The curated snapshot is maintained in the separate `nancyboughannam/SCOPE-reproducibility` repository; the original development repository is unchanged.
