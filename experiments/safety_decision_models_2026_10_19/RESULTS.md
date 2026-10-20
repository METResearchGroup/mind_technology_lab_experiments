# Results

Step 3 smoke tests passed for `jev`, `clef`, and `clef-flash`, with cache hits on rerun. The `guardrails` arm is deferred to step 5.

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

Run `run_id=20261020T040920Z_90c5fd13` (step 7 metrics). The table reports development-tuned metrics and the same metrics at threshold 0.5.

| Dataset | Arm | Metric | Tuned | At 0.5 |
| --- | --- | --- | ---: | ---: |
| toxigen | jev | accuracy | 0.8755 | 0.8755 |
| toxigen | clef | accuracy | 0.7213 | 0.7213 |
| toxigen | clef-flash | accuracy | 0.8074 | 0.8074 |
| toxigen | guardrails | miss_rate | 0.9060 | - |
| openai_moderation | jev | mean_auprc | 0.7419 | 0.7324 |
| openai_moderation | clef | mean_auprc | 0.7528 | 0.7501 |
| openai_moderation | clef-flash | mean_auprc | 0.7099 | 0.7048 |
| openai_moderation | guardrails | miss_rate | 0.9559 | - |
| toxicchat | jev | toxic_f1 | 0.7878 | 0.7878 |
| toxicchat | jev | jailbreak_f1 | 0.7004 | 0.7004 |
| toxicchat | clef | toxic_f1 | 0.6566 | 0.6566 |
| toxicchat | clef | jailbreak_f1 | 0.6071 | 0.6071 |
| toxicchat | clef-flash | toxic_f1 | 0.5784 | 0.5784 |
| toxicchat | clef-flash | jailbreak_f1 | 0.2900 | 0.2900 |
| toxicchat | guardrails | miss_rate | 1.0000 | - |
| prompt_injections | jev | accuracy | 0.7586 | 0.7586 |
| prompt_injections | clef | accuracy | 0.7672 | 0.7672 |
| prompt_injections | clef-flash | accuracy | 0.5948 | 0.5948 |
| prompt_injections | guardrails | miss_rate | 1.0000 | - |
| wildguardmix | jev | prompt_harm_f1 | 0.5904 | 0.5904 |
| wildguardmix | jev | prompt_harm_auprc | 0.9881 | 0.9881 |
| wildguardmix | clef | prompt_harm_f1 | 0.6351 | 0.6351 |
| wildguardmix | clef | prompt_harm_auprc | 0.9875 | 0.9875 |
| wildguardmix | clef-flash | prompt_harm_f1 | 0.5223 | 0.5223 |
| wildguardmix | clef-flash | prompt_harm_auprc | 0.9881 | 0.9881 |
| wildguardmix | guardrails | miss_rate | 1.0000 | - |
| do_not_answer | jev | detection_rate | 0.7433 | 0.7433 |
| do_not_answer | clef | detection_rate | 0.6017 | 0.6017 |
| do_not_answer | clef-flash | detection_rate | 0.4462 | 0.4462 |
| do_not_answer | guardrails | detection_rate | 0.0000 | - |
| xstest | jev | false_positive_rate_safe | 0.0000 | 0.0840 |
| xstest | jev | detection_rate_harmful | 0.0000 | 0.9250 |
| xstest | clef | false_positive_rate_safe | 0.0000 | 0.2360 |
| xstest | clef | detection_rate_harmful | 0.0000 | 0.9350 |
| xstest | clef-flash | false_positive_rate_safe | 0.0000 | 0.1000 |
| xstest | clef-flash | detection_rate_harmful | 0.0000 | 0.8950 |
| xstest | guardrails | miss_rate | 1.0000 | - |
| harmbench | jev | miss_rate | 0.2870 | 0.2870 |
| harmbench | clef | miss_rate | 0.3937 | 0.3937 |
| harmbench | clef-flash | miss_rate | 0.4688 | 0.4688 |
| harmbench | guardrails | miss_rate | 1.0000 | - |
| jailbreakbench | jev | miss_rate | 0.0300 | 0.0300 |
| jailbreakbench | jev | false_positive_rate | 0.3400 | 0.3400 |
| jailbreakbench | clef | miss_rate | 0.0100 | 0.0100 |
| jailbreakbench | clef | false_positive_rate | 0.5400 | 0.5400 |
| jailbreakbench | clef-flash | miss_rate | 0.0700 | 0.0700 |
| jailbreakbench | clef-flash | false_positive_rate | 0.2400 | 0.2400 |
| jailbreakbench | guardrails | miss_rate | 1.0000 | - |
| go_emotions | jev | macro_f1 | 0.2436 | 0.2436 |
| go_emotions | clef | macro_f1 | 0.4618 | 0.4618 |
| go_emotions | clef-flash | macro_f1 | 0.4814 | 0.4814 |
| go_emotions | guardrails | miss_rate | 0.9178 | - |
| emotion | jev | accuracy | 0.5840 | 0.5840 |
| emotion | clef | accuracy | 0.5910 | 0.5910 |
| emotion | clef-flash | accuracy | 0.5795 | 0.5795 |
| emotion | guardrails | miss_rate | 0.9700 | - |
