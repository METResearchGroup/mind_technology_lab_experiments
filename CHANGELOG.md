# CHANGELOG

## 2026-09-24

1. Repo-root callers can load `GITHUB_PAT_TOKEN` from AWS Secrets Manager secret `github-pat-token` (JSON field `GH_TOKEN`) through `EnvVarsContainer`, with the value cached in memory after the first read. [PR #26](https://github.com/METResearchGroup/mind_technology_lab_experiments/pull/26)
2. Added a shared S3 client for uploads, downloads, key listings, and CSV loads, with the default AWS region in `shared/aws/constants.py`. [PR #26](https://github.com/METResearchGroup/mind_technology_lab_experiments/pull/26)

## 2026-09-23

1. Ran a batched Jev moral-outrage scoring experiment on the PR 20 sample at batch sizes 1 through 40, reporting F1, latency, cost, and label drift against batch size 1 and the PR 20 reference row. [PR #23](https://github.com/METResearchGroup/mind_technology_lab_experiments/pull/23)

2. Ran a separate full-dataset ablation on 26,000 Brady moral-outrage posts at batch sizes 10 through 80, reporting F1, throughput under the 1,000 request starts per minute cap, cost, drift from batch size 10, and a 20M-post projection. [PR #23](https://github.com/METResearchGroup/mind_technology_lab_experiments/pull/23)

## 2026-09-19

1. Added a standalone Brady 2021 moral-outrage classifier comparison of TypeSafe Jev, stored Perspective labels, and five Bedrock models. The experiment uses a locked 1,000-row stratified sample, a smoke cost gate before any 1,000-row Jev or Bedrock job, and the lab S3 prefix in SETUP. [PR #20](https://github.com/METResearchGroup/mind_technology_lab_experiments/pull/20)
