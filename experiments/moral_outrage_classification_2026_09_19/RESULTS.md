# Results

Scores are on the 1,000-row stratified sample (560 gold 0, 440 gold 1), seed `20260919`.

Perspective classification metrics used 993 rows. These sample `source_row_id` values have an empty stored `pred_label` and were dropped: `1990`, `6429`, `19057`, `19803`, `19853`, `19977`, `22320`.

## Quality

| model name | f1 | accuracy | precision | recall |
| --- | ---: | ---: | ---: | ---: |
| Jev | 0.7322611163670766 | 0.717 | 0.6272285251215559 | 0.8795454545454545 |
| Perspective API | 0.7252747252747253 | 0.7734138972809668 | 0.781578947368421 | 0.6765375854214123 |
| Bedrock:us.openai.gpt-5.6-luna | 0.7394594594594595 | 0.759 | 0.7051546391752578 | 0.7772727272727272 |
| Bedrock:us.openai.gpt-5.6-terra | 0.73542600896861 | 0.764 | 0.7256637168141593 | 0.7454545454545455 |
| Bedrock:us.anthropic.claude-sonnet-5 | 0.751219512195122 | 0.745 | 0.6581196581196581 | 0.875 |
| Bedrock:qwen.qwen3-32b-v1:0 | 0.7489795918367347 | 0.754 | 0.6796296296296296 | 0.8340909090909091 |
| Bedrock:deepseek.v3-v1:0 | 0.7529411764705882 | 0.727 | 0.6255639097744361 | 0.9454545454545454 |

## Latency

| model name | p50 | p90 | p99 |
| --- | ---: | ---: | ---: |
| Jev | 130.90724050016433 | 186.61326580004243 | 274.4072787899131 |
| Perspective API | 0.0019390008674236014 | 0.0022990003344602883 | 0.002888040835387077 |
| Bedrock:us.openai.gpt-5.6-luna | 1667.9069305000667 | 2169.9675109002783 | 3612.4557205600095 |
| Bedrock:us.openai.gpt-5.6-terra | 1601.9441704984274 | 2360.5878120999478 | 3385.76640126048 |
| Bedrock:us.anthropic.claude-sonnet-5 | 1898.9471474997117 | 2854.7221377990354 | 4415.324429698481 |
| Bedrock:qwen.qwen3-32b-v1:0 | 387.59046899940586 | 511.48561970003357 | 913.2531900694808 |
| Bedrock:deepseek.v3-v1:0 | 318.58724349876866 | 349.6913952003524 | 495.82751175192243 |

## Cost

| model name | total tokens | estimated cost USD |
| --- | ---: | ---: |
| Jev | 374632 | unknown |
| Perspective API | 0 | 0 |
| Bedrock:us.openai.gpt-5.6-luna | 196397 | 0.13329514 |
| Bedrock:us.openai.gpt-5.6-terra | 159156 | 0.8413702 |
| Bedrock:us.anthropic.claude-sonnet-5 | 179268 | 0.742248 |
| Bedrock:qwen.qwen3-32b-v1:0 | 139782 | 0.029061 |
| Bedrock:deepseek.v3-v1:0 | 115569 | 0.07584982 |

## Calibration

Bar histograms: `outputs/comparison/jev_hist.png` and `outputs/comparison/perspective_hist.png`. Difference histogram: `outputs/comparison/difference_hist.png`.

- paired rows: 993
- dropped for a missing probability: 7
- mean: 0.18886203423967776
- median: 0.12
- std: 0.37921025492224814
- iqr: 0.62

## Deadletter counts

- Jev: 0
- Perspective API: 0
- Bedrock:us.openai.gpt-5.6-luna: 0
- Bedrock:us.openai.gpt-5.6-terra: 0
- Bedrock:us.anthropic.claude-sonnet-5: 0
- Bedrock:qwen.qwen3-32b-v1:0: 0
- Bedrock:deepseek.v3-v1:0: 0

Region, secrets, and model ids: see SETUP.md.
