# Provenance and preservation

## Source selection

The original [SCOPE development repository](https://github.com/nancyboughannam/SCOPE) was inspected at commit `6d07210a435906fb1ddc3d9a6b31ff476657fa39`. Its older README and exploratory outputs did not describe the corrected final protocol. This separate repository contains the curated snapshot and does not modify or import the original repository's history.

The source snapshot was recovered from `SCOPE_Table4_GitHub_Ready.zip` (SHA-256 `1addba87b3bee4a34380a20582f4bdfec1cb77c6a2430a50ce603318e9b56890`), with a prepared review commit `180975704f03215f67b36b846fe7cc21aae42f3f`. Only the original-model publication pathway is promoted here. Expanded-data retraining, diagnostic reruns, duplicate exports, IDE metadata, obsolete launchers and exploratory result folders are excluded from the publication working tree.

The original optimizer service is restored from that package's `v5_reference_code` snapshot. It matches the completed ΔT study's audited service hash. The other simulation services and shared core runners match the archived study; the confirmatory runner includes the already archived EXP3 routing-support change. Java source and all nine JARs are checked against the frozen runtime audit. No policy algorithm, model, seed or scientific metric was changed as part of repository cleanup.

`provenance/runtime_files.json` maps repository paths to the 94 frozen runtime paths expected by `experiments/delta_t/audited_source_hashes.json`. These checks include Java sources/libraries, services, models, training catalogue, workload configuration and Weka models. `source_verification.json` retains the earlier Java/source audit.

## Archived scientific evidence

The final original main-study metadata has SHA-256:

`7a243a2a25573b173412305fb0f98f8c8d4b864c50f37a0f116c26ebf993e323`

The main and guard-on CSV files are copied unchanged from the audited study archive. The RANDOM-inclusive plotting source and archived figures come from `SCOPE_Original_RANDOM_Final.zip`. The ΔT tables, plotting code, source audit and runner come from `v5_delta_t_3601_3610_review_20261113T170231893870Z.zip`.

The λ calibration is copied from `SCOPE_lambda_calibration_3301_3303.zip`. Its 27 completed scenarios use the same original predictors. The supplied original λ runner and its shared core/service files match the archive byte for byte. The publication entry point adapts preparation to the relocatable frozen files while leaving simulation and summary calculations unchanged.

Archived study metadata contains original paths and software provenance. New runs create fresh local metadata and runtime copies. No command attempts to use Nancy's historical `/Users/...` or development-machine paths.

`provenance/artifact_hashes.json` binds the distributed files to SHA-256 checksums. `reproduce.py verify` also independently recomputes the archived statistics. This verifies internal consistency and preservation, not independent authenticity of the original experiment.

## What is and is not bundled

The repository contains original predictor collection/split data, saved models, per-run scientific tables, decision/window tables, summary statistics, full source, workload inputs, Weka models and Java dependencies. The large original raw Java/service log trees are not duplicated in Git. Fresh reproduction creates those logs with immutable completion receipts. Archived summaries are not mislabeled as raw logs.

The clean source was recovered from `SCOPE_Publication_Recovery.zip` (SHA-256 `2e6c641ff0b94a06c588e979a8ccd9e142cb2df6ccc2d5be36f79557111ea897`), prepared at commit `89b6451baaf6b9bbf40f2f663dc442f2d27d7c4d`. That source revision is retained in `REVISION.txt` for archive-only checkouts; when Git is available, reproduction metadata records the actual checkout commit. Repository URLs and documentation have been updated for this separate publication destination. Historical generated outputs and development history remain in the original repository. New simulations and figures use separate ignored folders.

## Citation and release

The paper should reference `https://github.com/nancyboughannam/SCOPE-reproducibility` plus the exact publication commit/tag. After the author checks MATLAB exports on the reference Mac and resolves any manuscript-to-artifact mismatches, publish a versioned release and, if desired, deposit that release in an archival service. Add its actual DOI to `CITATION.cff` and the manuscript only after issuance. The validation record distinguishes archived evidence, newly executed checks, and checks that remain unavailable.
