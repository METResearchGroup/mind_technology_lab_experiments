# Proposal: Safety benchmarks for typed decision models and Bedrock Guardrails

Scope: a research proposal for a new standalone study. The study scores typed decision models and Amazon Bedrock Guardrails, alone and stacked, on public safety datasets and two emotion datasets. Routing, grounding, rubric scoring, commonsense, sentiment, and multilingual tasks are out of scope. No code, data, or labels from another lab project are inputs.

## 1. Motivation and background

A typed decision model answers a fixed question about a text and returns a probability, with no free-text reply. TypeSafe AI's Jev is the commercial model in this class. Cloudflare's Clef and Clef-flash use the same request shape and publish open weights. A product that talks with people about mental health or emotional wellbeing needs that decision on the way in, because the assistant has to block a request for real harm and still leave ordinary sadness, anger, or fear in the conversation. A miss leaves a harmful request in the session. A false positive refuses someone who was only describing how they feel.

Mark Torres, a research engineer at Northwestern's Kellogg School, builds evaluations for language models and studies how people use them, including how platform ranking changes conversation. His advisor, William Brady, studies moral and emotional contagion online, outrage, and the way algorithms shape what people learn from each other. When a filter blocks an angry or sad message, that block decides whether the message stays, drops, or goes to a person. The measurements in this study are classifier scores on public benchmarks. Contagion, ranking experiments, and private conversation labels sit outside it.

Because the block is the decision we can score on public data, the prior Jev evaluations are the baseline. Deußer, Sparrenberg, and Sifa evaluated Jev `jev-1.13.0` zero-shot on 37 Hugging Face datasets, in "Evaluating and Benchmarking the System One Model Jev" (arXiv:2609.37647). Four of those datasets are safety sets, and two are emotion sets. The harness and the raw responses are public (https://github.com/AppliedMachineLearning-Lab/jev-benchmarking). Their safety numbers check our harness. They do not include a guardrail. Chung and colleagues, in "Jev-ToM" (arXiv:2610.18610), score five typed models on nine existing theory-of-mind benchmarks. The part worth copying is their extra analysis, in particular confidence cutoffs and the effect of attaching a reason to an answer. What we add is the guardrail stack, the split between missed harm and over-refusal, and the emotion texts, under one confirmed template per dataset.

Bedrock Guardrails scores text through a separate API. `ApplyGuardrail` can run without calling a foundation model. Its content filters are Hate, Insults, Sexual, Violence, Misconduct, and Prompt Attack. Each filter returns a confidence band (`NONE`, `LOW`, `MEDIUM`, or `HIGH`) and a block decision at a chosen strength. AWS documents the strength rule as follows. Low strength blocks only a HIGH band. Medium strength blocks HIGH and MEDIUM. High strength blocks HIGH, MEDIUM, and LOW. A NONE band does not block, so high strength is the more sensitive setting. A band is an ordered label, and expected calibration error does not apply to it, because the band is not a probability in `[0, 1]`. The six filter names also fail to match dataset labels one to one. Self-harm, which the OpenAI moderation set includes, has no filter of its own.

## 2. Key research questions

1. On the core safety pack, with one template per dataset confirmed before the evaluation split is scored, do Clef and Clef-flash move the primary metric relative to `jev-1.13.0` by more than the 95% bootstrap interval?
2. On the yes/no safety tasks and on GoEmotions, how large is the gap between a fixed threshold of 0.5 and a threshold fit only on a development split, and does withholding the least confident 20% and 50% of items reduce the miss rate?
3. On benign prompts (JailbreakBench benign, and XSTest prompts whose `prompt_type` is `prompt_safe`), what false-positive rate does each arm have, and do GoEmotions comments that carry an emotion label and no harm label get blocked?
4. Under a category crosswalk that we publish before any test score is computed, what miss rate and false-positive rate does `ApplyGuardrail` produce at low, medium, and high strength?
5. Relative to the decision model alone and to the guardrail alone, do the union, intersection, and cascade policies separate on miss rate versus false-positive rate?
6. At the pinned prices, what median latency and what billed cost per 1,000 prompts does each arm have on this pack?

## 3. Arms, benchmarks, and metrics

### Arms

| Arm | What is called | Role |
| --- | --- | --- |
| Jev | TypeSafe API, model `jev-1.13.0` | Zero-shot typed questions. Same primitive mapping as Deußer et al. where the dataset overlaps. |
| Clef | Workers AI `@cf/cloudflare/clef` | Same JSON request as Jev. Pin the hosted model and the Hugging Face revision `Cloudflare/clef`. |
| Clef-flash | Workers AI `@cf/cloudflare/clef-flash` | Same request as Clef. Hosted context is 24,576 tokens as of 2026-10-09. Weights on Hugging Face allow a longer context if self-hosted. |
| Guardrails | `ApplyGuardrail`, source `INPUT`, content filters only | Hate, Insults, Sexual, Violence, Misconduct, Prompt Attack. No denied topics, word lists, or grounding checks, so the bill and the decision stay on the six filters. |
| Stack | One decision model plus the guardrail | Three policies, defined below. Each decision model gets its own stack. |

Kev 9B (`jaredpalmer/kev-9b`) and Laya (`convaiinnovations/laya`) are optional. The Clef blog (Chen, Reneau, and Flansburg, 1 October 2026) lists both on the Jev Decision Index, a routing and tool suite. Laya's scores on that index are far below the others. Laya's own card documents a default English context of 512 tokens, which is a plausible reason those scores are low. We keep an optional arm only if a 20-example pilot returns a probability for every legal option, and the pilot includes one long jailbreak prompt so truncation is visible. If the pilot fails, that model is dropped and the failure is reported.

Each decision-model request has a state (the text) and one or more questions. A Choice question picks one of a fixed set of labels. A Noul question returns the probability that the answer is yes. A Score question places the text on an ordered rubric of two to ten levels. Jev's documented context limit in Deußer et al. is 32,000 tokens for the state plus the longest question. TypeSafe's current model page describes 64,000 tokens per request and 32,000 per question, so we check the limit that applies to `jev-1.13.0` before the run. Clef's hosted limit is 64,000 tokens. Prompts over the limit are counted as errors, not as safe.

### Stack policies

Thresholds `t`, `t_high`, and `t_low` are fit on the development split only, then confirmed. The reported test rows are not used to pick them. The fit targets a false-positive budget of 5% on development items that have a benign label. Sets with no benign class do not set the budget.

- Union. Block if the guardrail blocks or if `P(harm) >= t`.
- Intersection. Block if the guardrail blocks and `P(harm) >= t`.
- Cascade. Block if `P(harm) >= t_high`. Allow if `P(harm) <= t_low`. Otherwise use the guardrail's block decision.

We also report every decision model at 0.5, with no guardrail, so the threshold effect is visible on its own.

### Core datasets

All of these are public Hugging Face datasets. We score the prompt or the user text. We do not score a model reply, and we do not ask a chat model to comply. A missing benign label is not a benign example. On those sets we report a detection rate and a miss rate, and we do not report a false-positive rate.

| Dataset | Hugging Face id | Rows we score | Question | Guardrail use |
| --- | --- | --- | --- | --- |
| ToxiGen | `toxigen/toxigen-data` | test, 940 | Noul for toxic or not, plus a five-level Score, one request, as in Deußer et al. | Closest filter is Hate. Implicit hate may not match that filter. |
| OpenAI Moderation | `mmathys/openai-moderation-api-evaluation` | full set, 1,680 | One Noul per category (eight), one request | Partial crosswalk. Self-harm has no matching filter. |
| ToxicChat | `lmsys/toxic-chat` | test, 5,083 | Two Nouls, toxicity and jailbreak | Toxicity against the content filters. Jailbreak against Prompt Attack. |
| Prompt Injections | `deepset/prompt-injections` | test, 116 | One Noul | Prompt Attack is the native filter. The test set is small. |
| WildGuardMix | `allenai/wildguardmix` | WildGuardTest, 1,725 | Noul on `prompt_harm_label`. Second Noul on the adversarial flag. | Harm against the content filters. Adversarial against Prompt Attack. Train split (86,759) is not scored. |
| Do-Not-Answer | `LibrAI/do-not-answer` | 939 questions | Noul, "should a safeguard refuse this question?" Risk-area field is a breakdown, not a second task. | Detection rate only. No benign class. |
| XSTest responses | `allenai/xstest-response` | Unique prompts, using `prompt_type` | Noul on whether `prompt_type` is `prompt_harmful` | False-positive rate on `prompt_safe`. The card's splits are response tasks (446 and 449 rows). We dedupe prompts and ignore reply labels. |
| HarmBench | `swiss-ai/harmbench` | `DirectRequest` test, 320. `HumanJailbreaks` test, 1,600 | Noul, "is this a request for harm?" | Miss rate only. Val splits (80 and 400) are the development pool for thresholds, not a benign class. |
| JailbreakBench | `JailbreakBench/JBB-Behaviors`, config `behaviors` | `harmful` 100, `benign` 100 | Noul on the goal text | Miss rate on harmful. False-positive rate on benign. Benign goals are thematically similar to harmful ones, which is the over-refusal check. |
| GoEmotions | `google-research-datasets/go_emotions` | test, 5,427 | 28 Nouls, one per label, one request | Not an emotion score. We record whether the guardrail blocks the comment. |
| Emotion | `dair-ai/emotion` | test, 2,000 | Choice over the six labels | Same as GoEmotions. Block rate only. |

Deußer et al. already loaded GoEmotions and Emotion from those Hugging Face ids, so both exist as public datasets and both have a published Jev baseline. GoEmotions is the calibration stress test, because 28 rare labels are queried together. Emotion is a six-way Choice whose labels come from hashtags, and the same paper calls those labels noisy. We keep both for that reason. A distress corpus such as Dreaddit would be a later add, with its own label definition, and it is not in this run.

Optional later pool, not in the base cost: `Anthropic/hh-rlhf`, `PKU-Alignment/PKU-SafeRLHF`, and `ByteDance/SafePyramid`. The first two are large preference sets and would need a subsample and a written harm rule before any call. SafePyramid is not specified further here. We read its dataset card before anyone proposes adding it.

### Primary metrics, by dataset

| Dataset | Primary metric | Why |
| --- | --- | --- |
| ToxiGen | Accuracy on the toxic label, plus Spearman correlation for the Score | Matches Table 2 and Table 5 in Deußer et al. |
| OpenAI Moderation | Mean AUPRC across categories | Matches their Table 2. Also per-category AUPRC. |
| ToxicChat | Positive-class F1 for toxicity, and separately for jailbreak | Matches their Table 4. |
| Prompt Injections | Accuracy, plus recall at 0.5 | The set is small and was the clearest threshold failure in the paper. |
| WildGuardTest | F1 and AUPRC on prompt harm. Accuracy on the adversarial flag. | Prompt harm is imbalanced. The flag is a second label. |
| Do-Not-Answer | Detection rate (share refused) | Every row is a risky question. |
| XSTest prompts | False-positive rate on `prompt_safe`, detection rate on `prompt_harmful` | Over-refusal is the point of the safe prompts. |
| HarmBench | Miss rate, split by DirectRequest and HumanJailbreaks | No benign rows. |
| JailbreakBench | Miss rate on harmful, false-positive rate on benign | Both classes exist. |
| GoEmotions | Macro-F1 | Matches Deußer et al. Also micro-F1 and mean per-label AUROC. |
| Emotion | Accuracy | Matches their Table 2. |

For every probability we also report ECE with 15 equal-width bins, the Brier score, AUROC, and AUPRC. ECE uses the top-option probability for a Choice and `P(yes)` for a Noul. Selective prediction ranks items by the model's reported confidence and scores the most confident 80% and the most confident 50%, plus the area under the risk-coverage curve. Guardrail bands are not put into ECE or Brier.

A false positive is a benign prompt that the arm blocks. A miss is a harmful prompt that the arm allows. On a jailbreak set, the miss rate is the attack-success rate for this study. That name means "the filter let the harmful prompt through." It does not mean a target chat model complied.

### Published Jev numbers we will use as a harness check

The figures in the table are from Deußer et al., and they are prior results. If our `jev-1.13.0` run on the same split and the same template falls outside the published interval, we stop and correct the template before scoring Clef or the guardrail.

| Dataset | Published figure |
| --- | --- |
| ToxiGen | Accuracy 0.878, 95% interval 0.857 to 0.898, ECE 0.046, AUROC 0.949. Score Spearman 0.841 on offensiveness. |
| OpenAI Moderation | Mean AUPRC 0.717, interval 0.675 to 0.759, ECE 0.036. Per-category AUPRC from 0.93 (sexual) and 0.91 (self-harm) down to 0.53 (harassment). |
| ToxicChat | Toxicity F1 0.786 at 0.5 (0.793 with a tuned threshold). Jailbreak F1 0.717 at 0.5 and 0.833 with the tuned threshold (jailbreak threshold 0.85). AUROC 0.989 for toxicity and 0.994 for jailbreak. ECE 0.016. |
| Prompt Injections | Accuracy 0.741, interval 0.664 to 0.828, ECE 0.236, AUROC 0.982. At 0.5, precision is perfect and recall is 50%. |
| GoEmotions | Macro-F1 0.243 at 0.5 and 0.353 tuned. Micro-F1 0.239 at 0.5 and 0.387 tuned. ECE 0.176. Mean per-label AUROC 0.873. Median tuned threshold 0.86 across 28 labels. |
| Emotion | Accuracy 0.585, interval 0.563 to 0.605, ECE 0.279. At 50% coverage, accuracy 0.733. |

Their full run was 346,009 requests, 217.9 million input tokens, and US$9.15 at US$0.042 per million input tokens. Output tokens were free. Mean latency was 0.36 seconds, and the rate limit (1,100 requests per minute) bound the throughput. Qwen3.8-27B, scored on the same requests, led Jev on the 116 prompt-injection items (accuracy 0.767 against 0.741). That lead is inside a wide interval, and it is a reminder that Jev is not ahead on every safety set even before Clef is added.

## 4. Key analyses

**RQ1, model comparison.** For each core safety dataset, compute the primary metric for `jev-1.13.0`, Clef, and Clef-flash, with a 95% percentile bootstrap over items (500 resamples, the same choice as Deußer et al.). A difference counts only when the intervals do not overlap. On the six datasets in the harness-check table, compare our Jev number to the published interval before interpreting Clef. Break WildGuardTest into vanilla and adversarial prompts, using the adversarial flag, and break HarmBench into DirectRequest and HumanJailbreaks. The same comparison on GoEmotions uses macro-F1, and on Emotion it uses accuracy. Guardrails do not enter RQ1, because they do not emit the dataset label.

**RQ2, thresholds and confidence.** For each Noul, report F1, recall, and false-positive rate at 0.5 and at the development-tuned threshold. Plot the reliability curve and compute ECE and Brier on `P(yes)`. For selective prediction, rank by confidence and report the miss rate, and the accuracy where a gold label exists, at 80% coverage and at 50% coverage. On GoEmotions, repeat the per-label threshold grid that Deußer et al. used (step 0.01 on 1,000 training items) and report macro-F1 at 0.5 and at the tuned thresholds. On Emotion, report top-option ECE, which was 0.279 in the published run, the worst Choice calibration in that paper. Sets with fewer than 200 labeled development items (prompt injections, JailbreakBench) are reported at 0.5 only, with AUROC as the threshold-free number, because a tuned threshold on a tiny split will not hold.

**RQ3, over-refusal and emotion text.** False-positive rate on JailbreakBench `benign` and on XSTest prompts with `prompt_type` equal to `prompt_safe`, for every arm including the three stack policies. For GoEmotions and Emotion, the gold label is an emotion, not harm. The analysis is the block rate of each arm by gold label. The comparison is whether anger, disgust, and sadness are blocked more often than joy or neutral. We do not call an emotion block a false positive, because the dataset has no harm label. A comment can be both angry and abusive. Where GoEmotions has no abuse label, we say "block rate by emotion," not "over-refusal."

**RQ4, guardrail crosswalk.** Before scoring, write a table from each dataset label to zero or more of the six filters. The table is fixed, and it is not edited after the first test number is computed. Sexual and hate have obvious candidates. Harassment is only partly Insults. Self-harm has no filter, and that cell stays empty on purpose. For each strength (low, medium, high), report the miss rate on harmful rows and the false-positive rate on benign rows, using the AWS rule above (high strength blocks more bands). The preferred call sets the filter action to `NONE`, which is detect-only, so each category returns a band and we apply the three strengths offline from that one response. If detect mode omits the band, we create three numbered guardrail versions. Bands may be ranked (`NONE` < `LOW` < `MEDIUM` < `HIGH`) for a rank statistic. We will not call that rank a probability.

**RQ5, stack policies.** On the items that have both a harmful class and a benign class (JailbreakBench, XSTest `prompt_type`, WildGuardTest prompt harm), compute miss rate and false-positive rate for the decision model alone, the guardrail alone, union, intersection, and cascade. The development fit uses the 5% false-positive budget, and the test numbers are a single confirmed application of those thresholds. A policy is better only if it lowers the miss rate at the same or lower false-positive rate, or the reverse. If the three policies land on top of each other, the stack is not doing work beyond the stronger component.

**RQ6, latency and cost.** Record wall-clock latency per request (median and 95th percentile) from the client, and record the provider's billed usage (tokens for Jev and Clef, text units for Guardrails). Report cost per 1,000 prompts from the bill. Section 8 is only a budget check. Deußer et al. found that their rate limit set throughput, so we record the limit beside the latency.

## 5. Key visualizations

1. **Miss rate against false-positive rate.** Each point is an arm or a stack policy. The x-axis is the false-positive rate on the pooled benign prompts (JailbreakBench benign, XSTest `prompt_safe`, WildGuardTest benign prompts). The y-axis is the miss rate on the matched harmful prompts. Supports RQ3 and RQ5. A reader should see whether union, intersection, and cascade sit apart, and whether any point is below and to the left of Jev alone.
2. **Reliability diagrams.** X-axis is `P(yes)` in 15 equal-width bins. Y-axis is the observed frequency of harm. One panel for single-Noul safety sets, one panel for the 28 GoEmotions Nouls. Marker area is the number of answers. Series are Jev, Clef, and Clef-flash. Supports RQ2. Guardrail bands are not on this figure.
3. **Threshold curves.** For ToxicChat jailbreak, ToxiGen, and prompt injections, x-axis is the threshold on `P(yes)`, y-axis is F1, with a second panel for recall and false-positive rate. Vertical marks at 0.5 and at the development-tuned threshold. Supports RQ2. The prompt-injection panel will be wide, because n is 116.
4. **Guardrail band against dataset label.** Rows are dataset labels (including self-harm and an explicit "no filter" row). Columns are the six filters. Cells are the share of items whose returned band is at least medium. Supports RQ4. The empty self-harm row is part of the figure, so the missing category is visible.
5. **Selective prediction.** X-axis is coverage. Y-axis is miss rate for safety Nouls, and accuracy for Emotion. Horizontal guides at 50% and 80% coverage. Series are the three decision models. Supports RQ2.
6. **Block rate by GoEmotions label.** X-axis is the 28 labels, ordered by block rate under Jev. Y-axis is block rate. Grouped bars for Jev at the tuned threshold, Clef at its tuned threshold, and Guardrails at medium strength. Supports RQ3. The reader should be able to see whether anger and disgust rise above joy and neutral.
7. **Latency and cost against miss rate.** X-axis is median latency in milliseconds. Y-axis is miss rate on the pooled harmful prompts that have a paired benign set. Point size or a printed label is cost per 1,000 prompts from the bill. Supports RQ6.
8. **Cascade diagram.** A flowchart with three outcomes, block, allow, and "ask the guardrail," and the two thresholds on `P(harm)`. Supports RQ5. No data values, so it can be drawn before the run.

## 6. Key messaging

The claims below are hypotheses, and the paper may reject any of them. Bracketed numbers in the abstract are unfilled on purpose.

1. The harness reproduces published Jev figures on the six overlapping sets, inside the published 95% intervals. The hypothesis fails if our `jev-1.13.0` primary metric falls outside the interval for ToxiGen, OpenAI Moderation, ToxicChat, prompt injections, GoEmotions, or Emotion.
2. Clef does not win every safety set. The Decision Index lead is on other tasks, and Jev already trails Qwen on the small prompt-injection set. The hypothesis fails if Clef's interval lies entirely above Jev's on every core safety primary metric.
3. A threshold of 0.5 under-detects on at least one Noul safety set, and a development-tuned threshold raises F1 there. The published prompt-injection case (recall 50% at AUROC 0.982) is the pattern we expect to see again. The hypothesis fails if 0.5 maximizes F1 on every Noul set that has a development split.
4. Guardrails and the decision models miss different items. In particular, Guardrails miss more self-harm items than sexual items, because self-harm has no filter, and they miss more implicit ToxiGen items than explicit JailbreakBench harmful goals. The hypothesis fails if those detection rates match within bootstrap noise.
5. Union lowers the miss rate and raises the false-positive rate relative to either piece alone. Intersection does the opposite. Cascade, fit to the 5% false-positive budget, lands between them. The hypothesis fails if the three policies do not separate on figure 1.
6. Emotion text is blocked less often than harmful prompts, and anger and disgust are blocked more often than joy and neutral. The hypothesis fails if GoEmotions block rates do not differ by label, or if they match the miss rate on JailbreakBench harmful.
7. On this pack, billed cost per token keeps the published order (Clef at $0.240 per million input tokens, Jev at $0.042, Clef-flash at $0.038), and Clef-flash has the lowest median latency of the three. The hypothesis fails if the bill or the latency ranking reverses. Vendor latency numbers from the Decision Index are not evidence for this pack.

If those hypotheses hold, the block rule for a wellbeing assistant has to name the stack and the threshold. Lowering missed harm raises the rate at which ordinary emotion text is refused, so a single model name does not state the operating point.

## 7. Risks and limitations

**Contamination.** Deußer et al. (section 4.6) found that Jev scores calculation-heavy MMLU subjects at 94.3% and other MMLU subjects at 91.3%. Qwen and Gemma find the calculation-heavy subjects harder (Qwen 74.7% against 83.0%, Gemma 54.6% against 69.8%). Rotating the answer letters left calculation-heavy accuracy at 94.3%. Withholding the question dropped it to 31.5%, close to the 25% chance level. Those probes rule out a memorized letter and a memorized option list. They leave open memorized question-answer pairs. Jev's training data are private, and Clef's post-training mix is only partly described. ToxiGen, OpenAI Moderation, HarmBench, and JailbreakBench are public and widely copied. A high score can be memorization. We will repeat the option-rotation check on the six-way Emotion Choice. Noul questions have no option order. A paraphrase of a small development subset can show brittleness, and it is not a proof that the test text was unseen.

**Thresholds.** The same paper shows that 0.5 is a poor operating point when `P(yes)` is shifted. GoEmotions macro-F1 moves from 0.243 to 0.353 after tuning, and ToxicChat jailbreak F1 moves from 0.717 to 0.833. Tuned thresholds do not always transfer. Qwen's jailbreak F1 fell slightly after tuning (0.743 to 0.726). We fit thresholds on development data only, we always publish the 0.5 number beside the tuned number, and we do not tune on prompt injections or JailbreakBench.

**Category mismatch.** Guardrails categories are not the dataset labels. A crosswalk that is edited after seeing test scores would invent a result. The crosswalk is written first, and self-harm stays unmapped. Confidence bands are not probabilities, so a guardrail cannot be declared "better calibrated" than Jev.

**Harmful-only sets.** Do-Not-Answer, HarmBench, and the harmful half of several other sets have no benign class. Treating an unlabeled row as safe would understate the false-positive rate. Those sets contribute detection rate and miss rate only.

**Small sets.** Prompt injections have 116 test rows (published interval width about 0.16 on accuracy). JailbreakBench has 100 per class. HarmBench DirectRequest test has 320. Intervals will be wide, and a model ranking on those sets can flip. We will not headline a winner from the smallest set.

**Labels.** WildGuardTest prompt-harm labels have Fleiss' kappa 0.55 across three annotators (moderate agreement), as stated on the dataset card. Emotion labels are hashtag-derived and noisy, which is why published accuracy is 0.585 and ECE is 0.279. GoEmotions can mark several emotions on one comment, and a single Noul does not know that most of the other 27 are false, which is the over-prediction Deußer et al. measured (mean `P(yes)` 0.209 against an observed rate of 0.041 on multi-label Nouls).

**License.** The `LibrAI/do-not-answer` card says the datasets are under CC BY-NC-SA 4.0 and the source files are under Apache 2.0. The GitHub repository's license field is Apache 2.0. Until that conflict is resolved, we can score the questions in a private run, and we do not redistribute the question text. `allenai/xstest-response` is gated behind the Allen Institute responsible-use form. Access might stall the XSTest portion. The rest of the pack does not depend on it.

**Versions.** `jev-1.13.0` is pinned. Clef and Clef-flash are pinned by hosted model id and by Hugging Face commit. The guardrail is a numbered version, not `DRAFT`, in one region (`us-east-2`, matching other Bedrock work in this lab). Filter strength is recorded. A later vendor update is a different study.

**What the miss rate is not.** We do not generate new jailbreak strings, and we do not measure whether a chat model would have complied. HarmBench's usual attack-success rate against a target model is a different quantity.

**Input length.** HumanJailbreaks prompts can be long. Requests over the context limit are errors. If the error rate exceeds 1% on any set, we report it beside the metric and we do not drop those rows silently.

## 8. Plan and cost estimate

The estimate uses published prices as of 2026-10-19 and the row counts above. It is an estimate, not a quote. The bill from the run replaces it.

Row count for one pass of the core pack, counting one request per example and counting XSTest as about 500 unique prompts: about 20,500. Deußer et al. averaged 630 input tokens per request on their broader suite. At that average, one pass is about 12.9 million input tokens. If the jailbreak prompts run near 2,000 tokens instead, the token count is about three times larger.

| Arm | Published unit price | Estimate at 12.9M tokens or one text unit | Estimate if prompts are about 3 times longer |
| --- | --- | --- | --- |
| Jev `jev-1.13.0` | US$0.042 per million input tokens, output free (Deußer et al., price at their time of writing) | about US$0.54 | about US$1.60 |
| Clef | US$0.240 per million input tokens, output free (Cloudflare Workers AI pricing, page updated 2026-10-19) | about US$3.10 | about US$9.30 |
| Clef-flash | US$0.038 per million input tokens, output free (same page) | about US$0.49 | about US$1.50 |
| Guardrails content filters | US$0.15 per 1,000 text units. A text unit is up to 1,000 characters. Prompt Attack is included in this price on `ApplyGuardrail`. (https://aws.amazon.com/bedrock/pricing/) | about US$3.10 if each prompt is one text unit | about US$9 to US$20 |

A stack pays for the decision model and the guardrail. Three decision models plus one guardrail pass, short prompts, is on the order of US$8. The long-prompt case is on the order of US$15 to US$30. Three separate strength calls, used only if detect mode omits the band, push the upper end toward US$50. A 20-example pilot and a development tune add a small fraction on top. Planning number for the required arms on the core pack: under US$50. Optional Kev and Laya are self-hosted, and their GPU time is not in this number. The optional preference-data pool is not in this number, because a full pass of `hh-rlhf` would dominate the bill and needs its own estimate after a subsample is chosen.

At 1,100 requests per minute, the cap Deußer et al. actually hit, about 21,000 requests take on the order of 20 minutes of API time, before retries. That figure is throughput, not a schedule for analysis.

Steps, in order:

1. Confirm one template per dataset on 20 development items. For the six overlapping sets, start from the published templates in the Jev harness so the harness check is meaningful.
2. Run `jev-1.13.0` on those six sets and compare to the published intervals. Stop if we are outside an interval.
3. Create a numbered guardrail in `us-east-2` with the six content filters, and write the crosswalk.
4. Score the core pack with Jev, Clef, Clef-flash, and `ApplyGuardrail`. Cache requests so a retry does not pay twice.
5. Fit thresholds on development splits. Compute the metrics, the five stack comparisons, and the eight figures.
6. Run the Kev and Laya pilot only after step 2 succeeds. Include a model in the tables only if the pilot returns valid probabilities.

Future artifacts, when the study is run, would live under `experiments/safety_decision_models_2026_10_19/` and the same prefix in `s3://mind-technology-lab-experiments/`. This proposal does not add that folder.

## 9. Draft abstract

Typed decision models return a probability for a fixed question, and they do not write the assistant's reply. We compare TypeSafe Jev (`jev-1.13.0`), Cloudflare Clef, Cloudflare Clef-flash, and Amazon Bedrock Guardrails, alone and in three stack policies (union, intersection, and cascade), on public safety datasets and on two emotion datasets. The safety sets are ToxiGen, OpenAI Moderation, ToxicChat, a prompt-injection set, WildGuardTest, Do-Not-Answer, XSTest prompts, HarmBench, and JailbreakBench. The emotion sets are GoEmotions (28 labels) and the six-way Emotion set. We score prompts only. A miss is a harmful prompt the filter allows, and a false positive is a benign prompt the filter blocks. On the sets that contain both classes, the cascade policy reaches a miss rate of [X%] and a false-positive rate of [Y%], compared with [A%] and [B%] for Jev alone and [C%] and [D%] for Guardrails alone. Expected calibration error on the yes/no harm probability is [ECE = __] for Jev and [ECE = __] for Clef. The gap between a 0.5 threshold and a development-tuned threshold is [Z] F1 points on [dataset]. Guardrails return a confidence band (`NONE`, `LOW`, `MEDIUM`, or `HIGH`), so expected calibration error does not apply to that band. Their six categories do not match the dataset labels, and self-harm has no filter of its own. Median latency is [__] ms for Jev, [__] ms for Clef, [__] ms for Clef-flash, and [__] ms for `ApplyGuardrail`. Block rates on GoEmotions differ by emotion label by [__] points between [label] and [label]. The bracketed figures will be filled from the run, and they are empty in this draft.

## Decisions to confirm

1. **Guardrail strength.** Recommend one `ApplyGuardrail` call with the filter action set to `NONE` (detect only), then apply AWS's rule offline: low blocks only HIGH, medium blocks HIGH and MEDIUM, and high blocks HIGH, MEDIUM, and LOW. The alternative, if detect mode omits the band, is three numbered versions. Dropping the sweep and reporting medium only is the smaller alternative.
2. **Do-Not-Answer.** Recommend scoring it and not redistributing the question text, because the card conflicts (CC BY-NC-SA 4.0 for the dataset, Apache 2.0 for source files). The alternative is to drop it until the license is clear.
3. **Optional models.** Recommend a 20-example pilot for `jaredpalmer/kev-9b` and `convaiinnovations/laya`, including one long jailbreak prompt, and inclusion only if probabilities come back well-formed. The alternative is to leave them out of the study.
4. **Emotion pair.** Recommend keeping GoEmotions and `dair-ai/emotion`, because both have published Jev numbers. The alternative is to swap Emotion for Dreaddit later, as a separate distress task, not as a silent replacement.
5. **Region.** Recommend `us-east-2` for the guardrail. The alternative is another single region, recorded in the run notes, as long as it does not change mid-study.
