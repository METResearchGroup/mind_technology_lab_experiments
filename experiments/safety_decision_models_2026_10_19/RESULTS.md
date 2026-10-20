# Results

Step 3 smoke tests passed for `jev`, `clef`, and `clef-flash`. The second pass hit the cache. Guardrails scores appear in the core-pack table.

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
| toxigen | jev | accuracy | 0.8755 | 0.8755 |
| toxigen | clef | accuracy | 0.7213 | 0.7213 |
| toxigen | clef-flash | accuracy | 0.8074 | 0.8074 |
| toxigen | guardrails | miss_rate | 0.6103 | — |
| openai_moderation | jev | mean_auprc | 0.7419 | 0.7324 |
| openai_moderation | clef | mean_auprc | 0.7528 | 0.7501 |
| openai_moderation | clef-flash | mean_auprc | 0.7099 | 0.7048 |
| openai_moderation | guardrails | miss_rate | 0.2126 | — |
| toxicchat | jev | toxic_f1 | 0.7878 | 0.7878 |
| toxicchat | jev | jailbreak_f1 | 0.7004 | 0.7004 |
| toxicchat | clef | toxic_f1 | 0.6566 | 0.6566 |
| toxicchat | clef | jailbreak_f1 | 0.6071 | 0.6071 |
| toxicchat | clef-flash | toxic_f1 | 0.5784 | 0.5784 |
| toxicchat | clef-flash | jailbreak_f1 | 0.2900 | 0.2900 |
| toxicchat | guardrails | miss_rate | 0.2624 | — |
| prompt_injections | jev | accuracy | 0.7586 | 0.7586 |
| prompt_injections | clef | accuracy | 0.7672 | 0.7672 |
| prompt_injections | clef-flash | accuracy | 0.5948 | 0.5948 |
| prompt_injections | guardrails | miss_rate | 0.6000 | — |
| wildguardmix | jev | prompt_harm_f1 | 0.4940 | 0.5904 |
| wildguardmix | jev | prompt_harm_auprc | 0.9881 | 0.9881 |
| wildguardmix | clef | prompt_harm_f1 | 0.5933 | 0.6351 |
| wildguardmix | clef | prompt_harm_auprc | 0.9875 | 0.9875 |
| wildguardmix | clef-flash | prompt_harm_f1 | 0.4210 | 0.5223 |
| wildguardmix | clef-flash | prompt_harm_auprc | 0.9881 | 0.9881 |
| wildguardmix | guardrails | miss_rate | 0.4208 | — |
| do_not_answer | jev | detection_rate | 0.7433 | 0.7433 |
| do_not_answer | clef | detection_rate | 0.6017 | 0.6017 |
| do_not_answer | clef-flash | detection_rate | 0.4462 | 0.4462 |
| do_not_answer | guardrails | detection_rate | 0.1523 | — |
| xstest | jev | false_positive_rate_safe | 0.0120 | 0.0840 |
| xstest | jev | detection_rate_harmful | 0.8400 | 0.9250 |
| xstest | clef | false_positive_rate_safe | 0.1080 | 0.2360 |
| xstest | clef | detection_rate_harmful | 0.8950 | 0.9350 |
| xstest | clef-flash | false_positive_rate_safe | 0.0280 | 0.1000 |
| xstest | clef-flash | detection_rate_harmful | 0.7600 | 0.8950 |
| xstest | guardrails | miss_rate | 0.1700 | — |
| harmbench | jev | miss_rate | 0.2870 | 0.2870 |
| harmbench | clef | miss_rate | 0.3937 | 0.3937 |
| harmbench | clef-flash | miss_rate | 0.4688 | 0.4688 |
| harmbench | guardrails | miss_rate | 0.2026 | — |
| jailbreakbench | jev | miss_rate | 0.0300 | 0.0300 |
| jailbreakbench | jev | false_positive_rate | 0.3400 | 0.3400 |
| jailbreakbench | clef | miss_rate | 0.0100 | 0.0100 |
| jailbreakbench | clef | false_positive_rate | 0.5400 | 0.5400 |
| jailbreakbench | clef-flash | miss_rate | 0.0700 | 0.0700 |
| jailbreakbench | clef-flash | false_positive_rate | 0.2400 | 0.2400 |
| jailbreakbench | guardrails | miss_rate | 0.9800 | — |
| go_emotions | jev | macro_f1 | 0.3229 | 0.2436 |
| go_emotions | clef | macro_f1 | 0.4624 | 0.4618 |
| go_emotions | clef-flash | macro_f1 | 0.4814 | 0.4814 |
| go_emotions | guardrails | miss_rate | 1.0000 | — |
| emotion | jev | accuracy | 0.5840 | 0.5840 |
| emotion | clef | accuracy | 0.5910 | 0.5910 |
| emotion | clef-flash | accuracy | 0.5795 | 0.5795 |
| emotion | guardrails | miss_rate | 1.0000 | — |
## Post-hoc sensitivity analysis

**post-hoc sensitivity analysis** — JailbreakBench Bedrock guardrails only. The core-pack headline remains the pre-registered crosswalk (harmful → Prompt Attack only). Below, the any-filter variant takes the maximum confidence band across Hate, Insults, Sexual, Violence, Misconduct, and Prompt Attack, then applies the usual strength rule. Stacks reuse development-tuned model and cascade thresholds fit on the crosswalk guardrail bit at medium strength.

| Variant | Strength | Miss rate | FPR |
| --- | --- | ---: | ---: |
| Pre-registered crosswalk | medium | 0.9800 | 0.0000 |
| Any content filter (max band) | low | 0.3900 | 0.0900 |
| Any content filter (max band) | medium | 0.2300 | 0.1900 |
| Any content filter (max band) | high | 0.1500 | 0.3900 |

Model and cascade cutoffs were fit on the development pool using pre-registered crosswalk guardrail bands at medium strength; sensitivity bands are applied only in this post-hoc analysis.

| Model arm | Stack | Miss rate | FPR |
| --- | --- | ---: | ---: |
| jev | union | 0.0300 | 0.4200 |
| jev | intersection | 0.2300 | 0.1100 |
| jev | cascade | 0.0300 | 0.3400 |
| clef | union | 0.0100 | 0.5700 |
| clef | intersection | 0.2300 | 0.1600 |
| clef | cascade | 0.0100 | 0.5400 |
| clef-flash | union | 0.0500 | 0.3300 |
| clef-flash | intersection | 0.2500 | 0.1000 |
| clef-flash | cascade | 0.0700 | 0.2400 |

Figure: `outputs/figures/20261020T040920Z_90c5fd13/jailbreakbench_guardrail_sensitivity.png`.

## Spend

Prices are the 2026-10-19 rates in `configs/study.json`. The spend table rows are new provider charges from the run logs and from `development_scoring.additional_usd` in `outputs/metrics/20261020T040920Z_90c5fd13.json`.

| Charge | USD |
| --- | ---: |
| Jev harness `20261020T033822Z_0f24960e` (7,138,858 input tokens) | 0.2998 |
| Full-pack new calls, Jev | 0.1091 |
| Full-pack new calls, Clef | 4.7130 |
| Full-pack new calls, Clef-flash | 0.7464 |
| Full-pack new calls, Guardrails (24,391 text units) | 3.6586 |
| Development-pool scoring | 8.8542 |
| Step 3 smoke, logged token charges | 0.0027 |
| Metrics reband and rerun (cache only) | 0.00 |
| **Total** | **18.38** |

On the full-pack prediction rows, cost per 1,000 prompts is Jev $0.023, Clef $0.230, Clef-flash $0.036, and Guardrails $0.179. Median latency comes from each row's stored `latency_ms` on the original provider call. Cache replays count toward latency and are not zeroed. Jev median latency is 88.9 ms, with 88.0 ms for live calls only and 291 ms at p95. Clef-flash is 303 ms, Guardrails is 359 ms, and Clef is 368 ms.
