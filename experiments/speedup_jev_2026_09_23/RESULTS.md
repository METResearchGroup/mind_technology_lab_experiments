# Results

Model versions: jev-1.13.0 (this run), jev-latest (PR 20).
Price source: https://docs.typesafe.ai/models (2026-09-23).

Plot: `outputs/comparison/f1_and_latency_by_batch_size.png`

Per-batch RESULTS:
- batch size 1: `outputs/batch_1/RESULTS.md`
- batch size 5: `outputs/batch_5/RESULTS.md`
- batch size 10: `outputs/batch_10/RESULTS.md`
- batch size 20: `outputs/batch_20/RESULTS.md`
- batch size 30: `outputs/batch_30/RESULTS.md`
- batch size 40: `outputs/batch_40/RESULTS.md`

## Quality

| batch size | f1 | accuracy | precision | recall | scored | deadletter |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.752 | 0.747 | 0.661 | 0.873 | 1000 | 0 |
| 5 | 0.739 | 0.740 | 0.661 | 0.839 | 1000 | 0 |
| 10 | 0.712 | 0.713 | 0.637 | 0.807 | 1000 | 0 |
| 20 | 0.674 | 0.638 | 0.558 | 0.850 | 1000 | 0 |
| 30 | 0.647 | 0.564 | 0.503 | 0.909 | 1000 | 0 |
| 40 | 0.635 | 0.534 | 0.484 | 0.923 | 1000 | 0 |
| PR 20 | 0.732 | 0.717 | 0.627 | 0.880 | 1000 | 0 |

## Latency

| batch size | request p50 (ms) | request p90 (ms) | request p99 (ms) | per-post p50 (ms) | wall time (s) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 127.8 | 185.9 | 260.9 | 127.8 | 17.0 |
| 5 | 128.1 | 181.7 | 334.0 | 25.6 | 3.6 |
| 10 | 127.5 | 228.4 | 319.9 | 12.8 | 1.9 |
| 20 | 136.0 | 261.8 | 324.9 | 6.8 | 1.1 |
| 30 | 171.5 | 340.5 | 390.9 | 5.7 | 1.0 |
| 40 | 154.3 | 303.7 | 325.6 | 3.9 | 0.7 |
| PR 20 | 130.9 | 186.6 | 274.4 | 130.9 | not recorded |

## Cost

| batch size | requests | input tokens | output tokens | estimated USD | USD per 1,000 posts |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 1000 | 361632 | 22000 | 0.015189 | 0.015189 |
| 5 | 200 | 150432 | 18800 | 0.006318 | 0.006318 |
| 10 | 100 | 124032 | 18400 | 0.005209 | 0.005209 |
| 20 | 50 | 111332 | 18700 | 0.004676 | 0.004676 |
| 30 | 34 | 107268 | 18796 | 0.004505 | 0.004505 |
| 40 | 25 | 104982 | 18850 | 0.004409 | 0.004409 |
| PR 20 | 1000 | 349632 | 25000 | 0.014685 | 0.014685 |

## Drift from batch size 1

| batch size | label agreement | mean abs prob diff |
| --- | ---: | ---: |
| 1 | 1.000 | 0.000 |
| 5 | 0.891 | 0.078 |
| 10 | 0.854 | 0.107 |
| 20 | 0.767 | 0.170 |
| 30 | 0.697 | 0.211 |
| 40 | 0.667 | 0.230 |
| PR 20 | 0.942 | 0.040 |

## Notes

- Batch size 1 is today's baseline on jev-1.13.0. PR 20 used jev-latest with an unrecorded version.
- The request start cap of 1,000 per minute counts starts in a rolling 60 s window, so it did not throttle any pass (the batch size 1 pass started 1,000 requests in about 17 s).
- Wall time for PR 20 was not recorded.
- Drift is measured against today's batch size 1 on posts scored in both runs.
