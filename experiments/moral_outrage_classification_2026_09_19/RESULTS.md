# Results

Sample comparison tables are empty until Step 7.

## Smoke

| model name | total tokens | estimated cost | estimated runtime |
| --- | ---: | ---: | ---: |
| Jev | 1050 | unknown | 147.8 |
| Perspective API | 0 | 0.000000 | 0.0 |
| Bedrock:us.openai.gpt-5.6-luna | 454 | 0.000296 | 813.3 |
| Bedrock:us.openai.gpt-5.6-terra | 318 | 0.001162 | 816.5 |
| Bedrock:us.anthropic.claude-sonnet-5 | 432 | 0.001944 | 2013.5 |
| Bedrock:qwen.qwen3-32b-v1:0 | 351 | 0.000077 | 408.8 |
| Bedrock:deepseek.v3-v1:0 | 277 | 0.000187 | 354.4 |

Jev estimated cost is `unknown` because TypeSafe has no public token price. Runtime is median request latency in milliseconds.
