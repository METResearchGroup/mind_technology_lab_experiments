# Jev batching speedup for moral outrage scoring

This experiment measures latency, cost, and quality when batching Jev moral outrage scoring on the same 1,000 Brady 2021 tweets used in PR 20. It reports quality, latency, token use, and estimated cost at batch sizes 1, 5, 10, 20, 30, and 40.

The tracking issue is [issue 17](https://github.com/METResearchGroup/mind_technology_lab_experiments/issues/17). PR 20 is the reference run, and batch size 1 on `jev-1.13.0` is the in-run baseline (see RESULTS.md). See [SETUP.md](SETUP.md) for install and run commands, and [RESULTS.md](RESULTS.md) for the current run.
