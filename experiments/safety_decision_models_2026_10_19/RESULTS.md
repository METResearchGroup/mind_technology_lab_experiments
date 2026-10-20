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

## Core pack

Run `run_id=20261020T040920Z_90c5fd13` (step 7 metrics). Threshold 0.5 and development-tuned values.

| Dataset | Arm | Metric | Tuned | At 0.5 |
| --- | --- | --- | ---: | ---: |
| toxigen | jev | accuracy | 0.5394 | 0.5394 |
| toxigen | clef | accuracy | 0.5000 | 0.5000 |
| toxigen | clef-flash | accuracy | 0.5309 | 0.5309 |
| toxigen | guardrails | miss_rate | 0.9026 | — |
| openai_moderation | jev | mean_auprc | 0.0589 | 0.0573 |
| openai_moderation | clef | mean_auprc | 0.0563 | 0.0560 |
| openai_moderation | clef-flash | mean_auprc | 0.0602 | 0.0574 |
| openai_moderation | guardrails | miss_rate | 0.8602 | — |
| toxicchat | jev | toxic_f1 | 0.0872 | 0.0872 |
| toxicchat | jev | jailbreak_f1 | 0.0000 | 0.0000 |
| toxicchat | clef | toxic_f1 | 0.1230 | 0.1230 |
| toxicchat | clef | jailbreak_f1 | 0.0143 | 0.0143 |
| toxicchat | clef-flash | toxic_f1 | 0.1398 | 0.1398 |
| toxicchat | clef-flash | jailbreak_f1 | 0.0362 | 0.0362 |
| toxicchat | guardrails | miss_rate | 0.8785 | — |
| prompt_injections | jev | accuracy | 0.5172 | 0.5172 |
| prompt_injections | clef | accuracy | 0.5259 | 0.5259 |
| prompt_injections | clef-flash | accuracy | 0.4741 | 0.4741 |
| prompt_injections | guardrails | miss_rate | 1.0000 | — |
| wildguardmix | jev | prompt_harm_f1 | 0.5855 | 0.5855 |
| wildguardmix | jev | prompt_harm_auprc | 0.9855 | 0.9855 |
| wildguardmix | clef | prompt_harm_f1 | 0.6359 | 0.6359 |
| wildguardmix | clef | prompt_harm_auprc | 0.9864 | 0.9864 |
| wildguardmix | clef-flash | prompt_harm_f1 | 0.5188 | 0.5188 |
| wildguardmix | clef-flash | prompt_harm_auprc | 0.9848 | 0.9848 |
| wildguardmix | guardrails | miss_rate | 0.9982 | — |
| do_not_answer | jev | detection_rate | 0.7433 | 0.7433 |
| do_not_answer | clef | detection_rate | 0.6017 | 0.6017 |
| do_not_answer | clef-flash | detection_rate | 0.4462 | 0.4462 |
| do_not_answer | guardrails | detection_rate | 0.0000 | — |
| xstest | jev | false_positive_rate_safe | 0.0000 | 0.3920 |
| xstest | jev | detection_rate_harmful | 0.0000 | 0.5400 |
| xstest | clef | false_positive_rate_safe | 0.0000 | 0.4920 |
| xstest | clef | detection_rate_harmful | 0.0000 | 0.6150 |
| xstest | clef-flash | false_positive_rate_safe | 0.0000 | 0.3840 |
| xstest | clef-flash | detection_rate_harmful | 0.0000 | 0.5400 |
| xstest | guardrails | miss_rate | 0.9400 | — |
| harmbench | jev | miss_rate | 0.2870 | 0.2870 |
| harmbench | clef | miss_rate | 0.3937 | 0.3937 |
| harmbench | clef-flash | miss_rate | 0.4688 | 0.4688 |
| harmbench | guardrails | miss_rate | 1.0000 | — |
| jailbreakbench | jev | miss_rate | 0.6600 | 0.6600 |
| jailbreakbench | jev | false_positive_rate | 0.9700 | 0.9700 |
| jailbreakbench | clef | miss_rate | 0.4600 | 0.4600 |
| jailbreakbench | clef | false_positive_rate | 0.9900 | 0.9900 |
| jailbreakbench | clef-flash | miss_rate | 0.7600 | 0.7600 |
| jailbreakbench | clef-flash | false_positive_rate | 0.9300 | 0.9300 |
| jailbreakbench | guardrails | miss_rate | 0.8100 | — |
| go_emotions | jev | macro_f1 | 0.0557 | 0.0557 |
| go_emotions | clef | macro_f1 | 0.0519 | 0.0519 |
| go_emotions | clef-flash | macro_f1 | 0.0486 | 0.0486 |
| go_emotions | guardrails | miss_rate | 0.9178 | — |
| emotion | jev | accuracy | 0.2450 | 0.2450 |
| emotion | clef | accuracy | 0.2490 | 0.2490 |
| emotion | clef-flash | accuracy | 0.2445 | 0.2445 |
| emotion | guardrails | miss_rate | 0.9700 | — |
