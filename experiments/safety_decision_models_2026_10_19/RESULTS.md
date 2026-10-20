# Results

Step 3: smoke passed for `jev`, `clef`, and `clef-flash` (cache hit on rerun). Arm `guardrails` deferred to step 5.

## Jev harness check (step 4)

Overall: **PASS** (`run_id=20261020T033822Z_0f24960e`).

| Dataset | Metric | Published | Interval | Observed | Status |
| --- | --- | ---: | --- | ---: | --- |
| toxigen | accuracy | 0.878 | 0.857-0.898 | 0.8755 | PASS |
| openai_moderation | mean_auprc | 0.717 | 0.675-0.759 | 0.7324 | PASS |
| toxicchat | toxic_f1 | 0.786 | ±0.02 | 0.7878 | PASS |
| toxicchat | jailbreak_f1 | 0.717 | ±0.02 | 0.7004 | PASS |
| prompt_injections | accuracy | 0.741 | 0.664-0.828 | 0.7586 | PASS |
| go_emotions | macro_f1 | 0.243 | ±0.02 | 0.2436 | PASS |
| emotion | accuracy | 0.585 | 0.563-0.605 | 0.5840 | PASS |

Predictions: `outputs/predictions/20261020T033822Z_0f24960e/jev/`.
Manifest: `outputs/manifests/20261020T033822Z_0f24960e.json`.
