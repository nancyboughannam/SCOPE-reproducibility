# Reproduction instructions

## Platform and installation

The orchestration scripts target macOS and Linux. They use POSIX file locks and process groups. Native Windows is not supported; WSL is a possible adaptation, not a validated platform for this snapshot.

Use Python 3.11 or 3.12, JDK 21+, and MATLAB R2020a+ for the original figure style. MATLAB needs Times New Roman and no additional statistics toolbox: plotting reads precomputed intervals and checks them numerically. MATLAB is not needed to simulate, verify tables, or inspect the archived PDFs.

Check your installed programs in Terminal:

```bash
python3 --version
java -version
java -m jdk.compiler/com.sun.tools.javac.Main -version
```

The last command must report a compiler of at least version 21. The runner compiles through the Java compiler module, so a separate `javac` command on PATH is not required. Obtain Python from [python.org](https://www.python.org/downloads/) and a JDK from [Eclipse Temurin](https://adoptium.net/temurin/releases/), or use your institution's managed installation.

If the default Python is incompatible, select the installed interpreter explicitly:

```bash
SCOPE_PYTHON=/full/path/to/python3.12 bash SETUP.sh
```

For Java on macOS, an installed JDK can be selected with:

```bash
export JAVA_HOME=$(/usr/libexec/java_home -v 21)
bash RUN_SIMULATION.sh --profile smoke
```

Alternatively pass `--java /full/path/to/bin/java` to `RUN_SIMULATION.sh`. If XGBoost reports a missing `libomp.dylib` on macOS, install the OpenMP runtime through your package manager (for an existing Homebrew installation: `brew install libomp`), then repeat setup. Do not mix Intel and Apple Silicon Python/JDK installations accidentally.

Pinned direct dependencies are in `requirements-reproducibility.txt`; their versions match the archived study. Transitive dependencies are resolved by pip for the host platform. Every prepared study records its scientific package versions, hashes of copied inputs, Java executable and protocol. The historical environment did not include a complete platform-independent transitive lock; none is claimed here.

## Execution choices

Always run commands from the repository root. The default workflow uses original saved models; it does not retrain or select settings based on the test runs.

| Goal | Terminal command |
|---|---|
| Integrity and numerical checks | `.venv/bin/python reproduce.py verify` |
| Prediction noise, local timing and budget sensitivity | `.venv/bin/python reproduce.py revision-results` ([fresh-run protocols](../experiments/revision_studies/README.md)) |
| Held-out predictor performance (Table 5) | `.venv/bin/python reproduce.py table5` |
| λ table, mean ± sample SD | `.venv/bin/python reproduce.py calibration-table` |
| Smoke execution of every component | `bash RUN_SIMULATION.sh --profile smoke` |
| Full main and ΔT studies | `bash RUN_SIMULATION.sh` |
| Only main study, in a distinct folder | `bash RUN_SIMULATION.sh --study main --output reruns/main_only` |
| Only ΔT study, in a distinct folder | `bash RUN_SIMULATION.sh --study delta --output reruns/delta_only` |
| Only λ calibration, in a distinct folder | `bash RUN_SIMULATION.sh --study lambda --output reruns/lambda_only` |
| Prepare full suite without starting simulations | `.venv/bin/python reproduce.py prepare` |
| Progress receipts | `.venv/bin/python reproduce.py status` |

`prepare` and `run` acquire a suite lock. The default full suite runs serially to preserve the services' ports and execution ordering. Do not run two suites concurrently on the same machine. Completed job receipts bind the result to hashes of its evidence; modifying a finished job causes resume to fail rather than silently accepting changed data.

Ctrl+C requests orderly shutdown. Wait for `STOPPED` before restarting. Reuse the same command and output location. If you change code, package versions, protocol or Java, start a new `--output`; do not edit the saved checksums to bypass validation.

The smoke suite runs 53 scenarios: 9 λ calibration + 8 static calibration + 22 study + 2 edge-first EXP3 + 12 ΔT. Shortened simulations and separate iteration IDs are used. Smoke outcomes are not estimates of the published effects.

The default full run also regenerates the λ-calibration evidence without reselecting the already frozen weight. Export its mean ± sample SD table with `.venv/bin/python reproduce.py calibration-table --source rerun`. Use `--output reruns/lambda_only` for a custom λ-only run.

## MATLAB and packaging

Archived figures:

```matlab
cd('/absolute/path/to/SCOPE-reproducibility')
RUN_MATLAB
```

Fresh full suite:

```matlab
RUN_MATLAB('rerun')
```

Custom full-suite folder:

```matlab
RUN_MATLAB('rerun','/absolute/path/to/new_run')
```

For a completed main-only or ΔT-only study, call the corresponding exporter directly:

```matlab
addpath(fullfile(pwd,'matlab'))
plot_scope_original_with_random(fullfile(pwd,'reruns','main_only','main'))
plot_delta_t_results(fullfile(pwd,'reruns','delta_only','delta_t'))
```

The individual exporters choose timestamped output folders beside their data. These folders are included when the containing rerun is packaged. For the combined `RUN_MATLAB`, packaging selects the latest completed figure folder whose recorded data root and source match the requested package.

Return to Terminal to package:

```bash
bash ZIP_RESULTS.sh archived
# or, for the default fresh full suite:
bash ZIP_RESULTS.sh rerun
# or a custom completed suite:
bash ZIP_RESULTS.sh rerun --output reruns/main_only
```

No external upload occurs. macOS Finder opens with the ZIP selected; Linux prints the path. A fresh-run package includes job evidence and summaries, while the repository supplies the source and frozen dependencies. Without a newly generated matching MATLAB folder, the command explicitly says so.

## Training provenance and optional refitting

The original raw collection CSV, cleaning script, split CSVs, training script, candidate models, predictions, validation-selected hyperparameters and model metrics are included. The 50 source collection scenarios used iterations 3001–3010 across five loads, with `SCOPE_DATA_COLLECTION` and the corrected routing/telemetry schema. The raw collection file permits rebuilding the dataset without rerunning collection.

Inspect cleaning options before rebuilding a separate dataset:

```bash
.venv/bin/python FLaskAPIs/prepare_candidate_dataset.py --help
.venv/bin/python reproduce.py train
```

`train` fits the original procedure from the supplied train/validation/test partition and writes to a new `reruns/predictor_training_...` folder. It does not promote a new model into the main simulation. The shared `run_deadline_pilot.py` also retains the historical collection/training utilities needed to explain the original pipeline; its development `all` command is not the publication launcher.

The validation refit on Linux completed successfully but did **not** reproduce identical fitted models or validation-selected stopping rounds. The cause has not been isolated. The saved six candidate models reproduce the original Table 5 values, and those frozen models are therefore the default for paper-result reproduction. Do not substitute a fresh refit while claiming it is the original published model. Stored state-only predictions support the original control column; the state-only fitted models were not saved by the historical trainer.

## Common failures

| Message | Action |
|---|---|
| Port 5002/5003 occupied | Stop the old Flask service you launched, then rerun; the runner will not kill it. |
| JDK 21+ required | Select a JDK, not a JRE; use the compiler-module command above. |
| Changed or missing file | Restore the exact input or use a new output for intentional modifications. Never overwrite an old completion receipt. |
| Profile/settings differ | Keep smoke, full and different experiment selections in separate output roots. |
| Partial preparation retained | Preserve that folder for diagnosis and choose a new output root. |
| MATLAB cannot find RUN_MATLAB | Change MATLAB's current folder to the repository root. |
| Times New Roman missing | Install the font before exporting; archived PDFs remain available. |
| File download failed during setup | Resolve the package-index/network problem and repeat setup before starting a study. |

Space usage grows with diagnostic logs. The runner uses `-Xmx2g` for Java plus Python/model memory; this is a Java heap setting, not a measured total-RAM requirement. Use several GB of free RAM and enough free storage for the full raw logs; inspect available storage during long runs. No fabricated hardware benchmark is supplied.
