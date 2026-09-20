# Moral outrage classifier comparison

This experiment compares TypeSafe Jev, stored Perspective moral-outrage labels, and five Amazon Bedrock models on labeled tweets from Brady, McLoughlin, Doan, and Crockett 2021.

The tracking issue is [issue 17](https://github.com/METResearchGroup/mind_technology_lab_experiments/issues/17). See [SETUP.md](SETUP.md) for install and IDs, and [RESULTS.md](RESULTS.md) for the current run.

Scoring uses one stratified random sample of 1,000 tweets, not the full 26,000-row file. Jev and Bedrock smoke classify three fixed texts. Perspective smoke reads three stored labeled rows. The 1,000-row sample run is complete. See [RESULTS.md](RESULTS.md).
