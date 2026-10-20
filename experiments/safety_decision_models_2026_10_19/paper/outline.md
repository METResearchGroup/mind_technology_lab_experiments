# Paper outline (writer's guide)

**Convention check.** The repository has no existing `paper/` tree elsewhere (search under `/workspace` returned none). The approved experiment layout in `docs/plans/2026-10-19_safety-decision-model-benchmark_a7c3e1/proposal.md` (section 5) commits code, templates, `RESULTS.md`, and figures, not a separate manuscript folder. **`experiments/safety_decision_models_2026_10_19/paper/`** is the appropriate home for this draft; figures and metrics remain under `outputs/`.

**Primary run.** `run_id=20261020T040920Z_90c5fd13` (core pack, step 7). Harness check run: `20261020T033822Z_0f24960e`.

**Allowed numeric sources (only these).**

| Source | Use for |
| --- | --- |
| `experiments/safety_decision_models_2026_10_19/RESULTS.md` | Headline tables, spend, latency narrative, post-hoc JailbreakBench |
| `experiments/safety_decision_models_2026_10_19/outputs/metrics/20261020T040920Z_90c5fd13.json` | JSON keys cited below; bootstrap flags; stacks; guardrail_by_strength; latency_cost |
| `docs/plans/.../proposal.md` | Research questions, protocol, dataset list, stack definitions, not empirical results |
| `docs/plans/.../plan.md` | Implementation steps, not empirical results |
| `outputs/figures/20261020T040920Z_90c5fd13/*.png` | Visual claims; do not read numbers off figures unless the same number appears in RESULTS or JSON |

**Do not use:** proposal cost estimates (e.g. "under US$50"), proposal published Deußer figures as *this study's* scores (except harness-check *comparison* rows in RESULTS), or any metric not present in RESULTS/JSON.

---

## Title

**Benchmarking Decision Models for LLM Safety Screening**

---

## Authors

1. **Mark Torres**, Kellogg School of Management, Northwestern University, mark.torres1@kellogg.northwestern.edu
2. **William J. Brady**, Kellogg School of Management, Northwestern University, william.brady@kellogg.northwestern.edu

---

## Research questions (proposal §2) → Results mapping

| RQ | Proposal question (summary) | Answered in RESULTS / JSON? | Results subsection / JSON block |
| --- | --- | --- | --- |
| **RQ1** | Clef / Clef-flash vs Jev on core safety pack (bootstrap) | **Yes** (partial: emotion sets included in JSON bootstrap) | Core pack table; `rq1_bootstrap` |
| **RQ2** | 0.5 vs tuned threshold; selective 80%/50% coverage | **Yes** | Core pack (tuned vs @0.5); `arms.*.calibration`, `selective`; figures `threshold_curves.png`, `reliability.png`, `selective_prediction.png` |
| **RQ3** | FPR on benign prompts; GoEmotions/Emotion block behavior | **Partial** | Core pack XSTest/JBB FPR; `guardrails.*.go_emotions` miss_rate 1.0; figure `goemotions_block_rate.png`, `miss_vs_fpr.png`. Per-label block rates: no numeric table in RESULTS/JSON |
| **RQ4** | Guardrail miss/FPR at low/medium/high under crosswalk | **Yes** (miss_rate; FPR where dataset has benign class) | Core pack guardrails @ medium; `guardrail_by_strength`; figure `guardrail_bands.png` |
| **RQ5** | Union / intersection / cascade vs alone | **Yes** (datasets with both classes: JBB, XSTest, WildGuardMix) | `stacks`; figure `miss_vs_fpr.png`, `cascade_flowchart.png` |
| **RQ6** | Median latency and cost per 1k prompts | **Yes** | RESULTS Spend paragraph; `latency_cost`; figure `latency_cost_vs_miss.png` |

**Marked not claimed (do not state as results):**

- Pooled benign/harmful **single scalar** miss/FPR across all benchmarks (not in RESULTS/JSON as one number; use figure or per-dataset tables only).
- **Per GoEmotions label block rates** as exact percentages (figure only unless appendix exports from predictions).
- **Clef-flash self-hosted rerun** (proposal: future work).
- **Chat-model compliance / attack success against a target LLM** (proposal §9: out of scope).
- **RQ1 "significant" for every dataset** without citing `rq1_bootstrap.*.clef_vs_jev.significant` (Clef vs Jev is **not** significant for openai_moderation, prompt_injections, wildguardmix, jailbreakbench, emotion per JSON).

---

## Global allowlist of exact numbers (copy verbatim; cite source)

Writers may use these in prose; round only where RESULTS already rounded (e.g. latency 88.9 ms).

### Harness check (`RESULTS.md`, Jev harness table; run `20261020T033822Z_0f24960e`)

| Dataset | Metric | Published | Observed |
| --- | --- | ---: | ---: |
| toxigen | accuracy | 0.878 | 0.8755 |
| openai_moderation | mean_auprc | 0.717 | 0.7324 |
| toxicchat | toxic_f1 | 0.786 | 0.7878 |
| toxicchat | jailbreak_f1 | 0.717 | 0.7004 |
| prompt_injections | accuracy | 0.741 | 0.7586 |
| go_emotions | macro_f1 | 0.243 | 0.2436 |
| emotion | accuracy | 0.585 | 0.5840 |

### Core pack tuned primary metrics (`RESULTS.md` Core pack table → keys `arms.{arm}.{dataset}.primary` or flat fields)

Use RESULTS four-decimal values for narrative; JSON full precision optional in appendix.

**Jev (tuned):** toxigen accuracy 0.8755; openai_moderation mean_auprc 0.7419; toxicchat toxic_f1 0.7878, jailbreak_f1 0.7004; prompt_injections 0.7586; wildguardmix prompt_harm_f1 0.4940, prompt_harm_auprc 0.9881; do_not_answer detection_rate 0.7433; xstest false_positive_rate_safe 0.0120, detection_rate_harmful 0.8400; harmbench miss_rate 0.2870; jailbreakbench miss_rate 0.0300, false_positive_rate 0.3400; go_emotions macro_f1 0.3229; emotion accuracy 0.5840.

**Clef (tuned):** toxigen 0.7213; openai_moderation mean_auprc 0.7528; toxicchat toxic_f1 0.6566, jailbreak_f1 0.6071; prompt_injections 0.7672; wildguardmix prompt_harm_f1 0.5933; do_not_answer detection_rate 0.6017; xstest FPR safe 0.1080; harmbench miss 0.3937; jailbreakbench miss 0.0100, FPR 0.5400; go_emotions macro_f1 0.4624; emotion accuracy 0.5910.

**Clef-flash (tuned):** toxigen 0.8074; toxicchat toxic_f1 0.5784, jailbreak_f1 0.2900; prompt_injections 0.5948; wildguardmix prompt_harm_f1 0.4210; do_not_answer detection_rate 0.4462; xstest FPR safe 0.0280; harmbench miss 0.4688; jailbreakbench miss 0.0700, FPR 0.2400; go_emotions macro_f1 0.4814; emotion accuracy 0.5795.

**Guardrails @ medium strength (RESULTS miss_rate / detection_rate):** toxigen miss 0.6103; openai_moderation miss 0.2126; toxicchat miss 0.2624; prompt_injections miss 0.6000; wildguardmix miss 0.4208; do_not_answer detection 0.1523; xstest miss 0.1700; harmbench miss 0.2026; jailbreakbench miss 0.9800; go_emotions miss 1.0000; emotion miss 1.0000.

**Selected @ 0.5 contrasts (RESULTS "At 0.5"):** jev xstest FPR safe 0.0840; jev wildguardmix prompt_harm_f1 0.5904; jev go_emotions macro_f1 0.2436.

### Spend and latency (`RESULTS.md` Spend; `latency_cost` in JSON)

| Item | Value | Source |
| --- | ---: | --- |
| Total spend USD | 18.38 | RESULTS Spend |
| Jev harness tokens charge | 0.2998 | RESULTS |
| Full-pack Jev / Clef / Clef-flash / Guardrails new calls | 0.1091 / 4.7130 / 0.7464 / 3.6586 | RESULTS |
| Development-pool scoring | 8.8542 | RESULTS |
| Cost per 1,000 prompts (narrative) | Jev 0.023; Clef 0.230; Clef-flash 0.036; Guardrails 0.179 | RESULTS (rounded from JSON) |
| Jev median latency ms | 88.9 | RESULTS |
| Jev live-call-only median / p95 ms | 88.0 / 291 | RESULTS |
| Clef / Clef-flash / Guardrails median ms | 368 / 303 / 359 | RESULTS |
| JSON `latency_cost.jev.median_latency_ms` | 88.86603199971432 | JSON key |
| JSON `latency_cost.jev.cost_per_1000_prompts_usd` | 0.02320827919921875 | JSON key |

### Post-hoc JailbreakBench guardrail sensitivity (`RESULTS.md` Post-hoc; `post_hoc_sensitivity` in JSON)

**Pre-registered crosswalk @ medium:** miss 0.9800, FPR 0.0000.

**Any content filter (max band), post-hoc:** low miss 0.3900 FPR 0.0900; medium miss 0.2300 FPR 0.1900; high miss 0.1500 FPR 0.3900.

**Post-hoc stacks @ medium sensitivity bands (not registered headline stacks):** e.g. jev intersection miss 0.2300 FPR 0.1100. Full table in RESULTS.

### Pre-registered stacks (`stacks` in JSON; headline JBB uses crosswalk @ medium)

Example JailbreakBench Jev: model_alone miss 0.03 FPR 0.34; guardrail_alone miss 0.98 FPR 0.0; union/intersection/cascade as in `stacks.jev.jailbreakbench` (intersection miss 0.98, guardrail-limited).

---

## Abstract

**Target length:** 200 to 250 words.

**Key claims (supported):** compare Jev, Clef, Clef-flash, and Bedrock Guardrails on eleven public benchmarks (prompts only); harness check on six sets; headline trade-offs (ToxicChat, HarmBench, JailbreakBench pre-registered vs post-hoc any-filter, XSTest FPR, Do-Not-Answer detection, cost/latency).

**Numbers refused in abstract:** proposal placeholders; "Clef wins every set"; any-filter JBB miss without **post-hoc** label; median latency **89** (use **88.9**); bootstrap `rq1_bootstrap.toxicchat.mean` as ToxicChat F1.

**Draft skeleton:** see `sections/abstract.tex` (allowlisted numbers only).

---

## Introduction through Appendix

Section-level targets, figure lists, and claim maps match the committed `sections/*.tex` files. When editing prose, change the TeX first, then update this outline only if lengths or figure requirements shift.

**Numbers writers must not use (not in RESULTS/JSON):** proposal §10 budget estimates; proposal Deußer ECE/AUROC as this run's scores; `rq1_bootstrap.toxicchat.jev.mean` as ToxicChat F1; post-hoc any-filter JBB miss 0.23 without "post-hoc"; Jev latency **89 ms**; per-label GoEmotions block rate point values without appendix export; pooled multi-benchmark scalar; chat-model attack success rates.

---

*End of outline.*
