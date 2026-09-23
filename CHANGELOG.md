# CHANGELOG

## 2026-09-23

1. Ran a batched Jev moral-outrage scoring experiment on the PR 20 sample at batch sizes 1 through 40, reporting F1, latency, cost, and label drift against the single-post baseline and the PR 20 reference row. [PR #23](https://github.com/METResearchGroup/mind_technology_lab_experiments/pull/23)

## 2026-09-19

1. Added a standalone Brady 2021 moral-outrage classifier comparison of TypeSafe Jev, stored Perspective labels, and five Bedrock models. The experiment uses a locked 1,000-row stratified sample, a smoke cost gate before any 1,000-row Jev or Bedrock job, and the lab S3 prefix in SETUP. [PR #20](https://github.com/METResearchGroup/mind_technology_lab_experiments/pull/20)
