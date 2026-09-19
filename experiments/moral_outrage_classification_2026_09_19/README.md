# Moral outrage classifier comparison

Compares TypeSafe Jev, Perspective `MORAL_OUTRAGE`, and five Amazon Bedrock chat models on Brady, McLoughlin, Doan, and Crockett 2021 labeled tweets.

Tracking issue: [issue 17](https://github.com/METResearchGroup/mind_technology_lab_experiments/issues/17).

Setup: [SETUP.md](SETUP.md). Results: [RESULTS.md](RESULTS.md).

Scoring uses one stratified random sample of 1,000 posts, not the full 26,000-row file. Smoke classifies three fixed texts on every scorer, then waits for approval before the 1,000-row jobs.
