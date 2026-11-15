# Contributing

Create a topic branch and keep archived scientific inputs unchanged. For algorithm changes, write to a new output folder and report the commit, complete protocol, environment, all seeds and all outcomes. Never replace an unfavorable result or silently update a completed-job receipt.

Run `python -m pytest` and `python reproduce.py verify` from the configured environment. Changes to simulation execution should also pass `bash RUN_SIMULATION.sh --profile smoke --output reruns/your_smoke_check`. Reproduction-affecting changes need an explicit before/after explanation and a new full run; smoke results alone cannot validate scientific conclusions.

Open pull requests with the concrete problem, resulting behavior, tests run and remaining limitations. Do not commit `.venv`, raw rerun folders, caches, credentials, IDE metadata or generated ZIPs. Preserve upstream source headers and licenses.
