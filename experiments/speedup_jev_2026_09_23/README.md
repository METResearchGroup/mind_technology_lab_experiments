# Batched Jev speedup

This experiment measures how much batching posts into one Jev request speeds up moral outrage scoring on the same 1,000 Brady 2021 tweets used in PR 20. It reports quality, latency, token use, and estimated cost at batch sizes 1, 5, 10, 20, 30, and 40.

The tracking issue is [issue 17](https://github.com/METResearchGroup/mind_technology_lab_experiments/issues/17). The baseline run is [PR 20](https://github.com/METResearchGroup/mind_technology_lab_experiments/pull/20). See [SETUP.md](SETUP.md) for install and run commands, and [RESULTS.md](RESULTS.md) for the current run.
