# Full 26k dataset ablation results

Model: jev-1.13.0. Price source: https://docs.typesafe.ai/models (2026-09-23).

Plot: `ablation_full_dataset/outputs/comparison/f1_and_latency_by_batch_size.png`

Per-batch RESULTS:
- batch size 10: `ablation_full_dataset/outputs/batch_10/RESULTS.md`
- batch size 20: `ablation_full_dataset/outputs/batch_20/RESULTS.md`
- batch size 40: `ablation_full_dataset/outputs/batch_40/RESULTS.md`
- batch size 60: `ablation_full_dataset/outputs/batch_60/RESULTS.md`
- batch size 80: `ablation_full_dataset/outputs/batch_80/RESULTS.md`

## Quality

| batch size | f1 | accuracy | precision | recall | scored | deadletter | share of main-run batch size 1 F1 (0.752 on 1,000-post sample) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 0.713 | 0.713 | 0.637 | 0.809 | 26000 | 0 | 0.948 |
| 20 | 0.662 | 0.629 | 0.553 | 0.825 | 26000 | 0 | 0.880 |
| 40 | 0.633 | 0.533 | 0.484 | 0.916 | 26000 | 0 | 0.842 |
| 60 | 0.624 | 0.500 | 0.466 | 0.944 | 26000 | 0 | 0.830 |
| 80 | 0.622 | 0.485 | 0.460 | 0.963 | 26000 | 0 | 0.827 |

## Latency

| batch size | request p50 (ms) | request p90 (ms) | request p99 (ms) | per-post p50 (ms) | wall time (s) | measured posts per minute (includes first-minute burst) | projected posts/min | cap bound |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 115.4 | 163.6 | 299.1 | 11.5 | 129.6 | 12037.9 | 10000.0 | yes |
| 20 | 131.8 | 196.6 | 331.3 | 6.6 | 65.3 | 23886.3 | 20000.0 | yes |
| 40 | 139.7 | 192.9 | 320.7 | 3.5 | 12.2 | 128309.5 | 40000.0 | no |
| 60 | 154.1 | 208.1 | 375.4 | 2.6 | 9.1 | 171473.2 | 60000.0 | no |
| 80 | 160.6 | 212.9 | 374.8 | 2.0 | 7.3 | 213606.0 | 80000.0 | no |

## Cost

| batch size | requests | input tokens | output tokens | estimated USD | USD per 1,000 posts | 20M hours (1,000 req/min cap) | 20M hours (1,200 req/min limit) | 20M USD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 2600 | 3220187 | 478400 | 0.135248 | 0.005202 | 33.3 | 27.8 | 104.04 |
| 20 | 1300 | 2889987 | 486200 | 0.121379 | 0.004668 | 16.7 | 13.9 | 93.37 |
| 40 | 650 | 2724887 | 490100 | 0.114445 | 0.004402 | 8.3 | 6.9 | 88.03 |
| 60 | 434 | 2670023 | 491396 | 0.112141 | 0.004313 | 5.6 | 4.6 | 86.26 |
| 80 | 325 | 2642337 | 492050 | 0.110978 | 0.004268 | 4.2 | 3.5 | 85.37 |

## Drift from batch size 10 on full data

| batch size | label agreement | mean abs prob diff |
| --- | ---: | ---: |
| 10 | 1.000 | 0.000 |
| 20 | 0.795 | 0.135 |
| 40 | 0.665 | 0.213 |
| 60 | 0.629 | 0.243 |
| 80 | 0.611 | 0.255 |

## Same-posts comparison (1,000 main-sample ids)

| batch size | ablation F1 on sample | main-run F1 on sample | label agreement | share of reference F1 (0.752) |
| --- | ---: | ---: | ---: | ---: |
| 10 | 0.720 | 0.712 | 0.818 | 0.958 |
| 20 | 0.663 | 0.674 | 0.683 | 0.882 |
| 40 | 0.620 | 0.635 | 0.748 | 0.825 |

## Notes

- This is a separate ablation from the main 1,000-post experiment.
- There is no batch size 1 pass on the full 26,000-post data.
- Posts were shuffled once with seed 20260923 before batching.
- The model is jev-1.13.0.
- Reference F1 0.752 is from the main run at batch size 1 on the 1,000-post sample, not the full data.
- The request start cap counts starts in a rolling 60 s window, so each pass starts with a burst of up to 1,000 requests.
- Passes with fewer than 1,000 requests never waited on the cap.
- Over 20M posts the burst is negligible, so the projection uses the cap rate.
- Batch size 10 wall time of 129.6 s is consistent with the cap floor of two full 60 s windows plus the remainder (about 120.0 s minimum for 2600 starts).
