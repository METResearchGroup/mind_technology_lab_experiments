# Proposal: Safety benchmarks for typed decision models and Bedrock Guardrails

Scope: a research proposal for a new standalone study. The study scores typed decision models and Amazon Bedrock Guardrails, alone and stacked, on public safety datasets and two emotion datasets. Routing, grounding, rubric scoring, commonsense, sentiment, and multilingual tasks are out of scope. No code, data, or labels from another lab project are inputs.

## 1. Motivation and background

A typed decision model answers a fixed question about a text and returns a probability, with no free-text reply. TypeSafe AI's Jev is the commercial model in this class. Cloudflare's Clef and Clef-flash use the same request shape and publish open weights. A product that talks with people about mental health or emotional wellbeing needs that decision on the way in, because the assistant has to block a request for real harm and still leave ordinary sadness, anger, or fear in the conversation. A miss leaves a harmful request in the session. A false positive refuses someone who was only describing how they feel.

The lab studies emotion and behavior on online platforms, which is why a block on angry or sad text is in this study, and the scores themselves are classifier results on public benchmarks.

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
| Clef | Workers AI `@cf/cloudflare/clef` | Body fields `model` (`clef`), `state`, and `questions`. `questions` is an object keyed by question id. Hosted context is 64,000 tokens. Workers AI shortens a longer state and still returns an answer, so the scorer marks that row truncated. Pin the Hugging Face revision `Cloudflare/clef`. |
| Clef-flash | Workers AI `@cf/cloudflare/clef-flash` | Same body, with `model` set to `clef-flash`. Hosted context is 24,576 tokens. The same silent shortening applies, and the scorer marks the row truncated. A self-hosted rerun of the weights is future work. |
| Guardrails | `ApplyGuardrail`, source `INPUT`, content filters only | Hate, Insults, Sexual, Violence, Misconduct, Prompt Attack. No denied topics, word lists, or grounding checks, so the bill and the decision stay on the six filters. |
| Stack | One decision model plus the guardrail | Three policies, defined below. Each decision model gets its own stack. |

Each decision-model request has a state (the text) and one or more questions. A Choice question picks one of a fixed set of labels. A Noul question returns the probability that the answer is yes. A Score question places the text on an ordered rubric of two to ten levels. The public harness documents 32,000 tokens for the state plus the longest question, and 64,000 tokens per request (`jev-benchmarking/docs/datasets.md`). Clef's hosted limit is 64,000 tokens. Clef-flash on Workers AI is 24,576 tokens. Workers AI shortens a longer `state` to fit and still returns an answer, so the scorer marks that row truncated. A self-hosted rerun of the Clef-flash weights is future work.

### Stack policies

Thresholds `t`, `t_high`, and `t_low` are fit on the development split only, then confirmed. The reported test rows are not used to pick them. The fit targets a false-positive budget of 5% on development items that have a benign label. Sets with no benign class do not set the budget.

- Union. Block if the guardrail blocks or if `P(harm) >= t`.
- Intersection. Block if the guardrail blocks and `P(harm) >= t`.
- Cascade. Block if `P(harm) >= t_high`. Allow if `P(harm) <= t_low`. Otherwise use the guardrail's block decision.

We also report every decision model at 0.5, with no guardrail, so the threshold effect is visible on its own. These three policies are functions of saved prediction records. They do not call a model, and the same functions are the block rule a later runtime would apply to new scorer output.

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

## 4. Data loading and shared interfaces

The run loads each public dataset through its own loader, scores every arm through one shared method, and computes the stack policies from the saved predictions. The policy function is the runtime block rule. The code is a later change. The paths below are files that already exist, and the study uses them when the code is written.

### Files we will reuse

The public harness at https://github.com/AppliedMachineLearning-Lab/jev-benchmarking loads Hugging Face datasets in `jev_benchmarking/tasks/base.py` (`load_split`). The same file builds Choice, Noul, and Score questions (`choice`, `noul`, `score`). Overlapping safety tasks are in `jev_benchmarking/tasks/safety.py`. ToxiGen uses config `annotated`, and ToxicChat uses config `toxicchat0124`. OpenAI Moderation and prompt injections use the default config. GoEmotions uses config `simplified`, and Emotion uses config `split`, both in `jev_benchmarking/tasks/classification.py`. `load_dataset` is called there without a revision argument. Our loaders pin each dataset to the commit from the first successful load, write that commit into the run manifest, and refuse a later load whose commit differs. Raw responses go to SQLite, and `request_key` in `jev_benchmarking/cache.py` hashes the model, the state, and the questions. `jev_benchmarking/runner.py` caps how fast requests start, retries transient failures, and records HTTP 400 `max_tokens_exceeded` in an errors table. Metric code is in `jev_benchmarking/metrics.py`. The threshold grid is in `jev_benchmarking/thresholds.py`.

WildGuardMix, Do-Not-Answer, XSTest, HarmBench, and JailbreakBench are absent from the harness. `jev_benchmarking/docs/datasets.md` says `walledai/XSTest` and `allenai/wildguardmix` were left out because they require a Hugging Face form and because they overlap the moderation sets. The study loads `allenai/xstest-response` and `allenai/wildguardmix`, because the false-positive rate on safe prompts and the adversarial flag are questions in section 2.

In this repository, `shared/aws/constants.py` sets `DEFAULT_REGION_NAME` to `us-east-2`, and `shared/aws/s3.py` can upload bytes to one bucket. Experiment scripts upload with boto3 instead, from `experiments/moral_outrage_classification_2026_09_19/scripts/upload_s3.py` and `experiments/speedup_jev_2026_09_23/scripts/upload_s3.py`, to bucket `mind-technology-lab-experiments`, with a prefix equal to the experiment folder. `experiments/speedup_jev_2026_09_23/shared/rate_limiter.py` defines `RequestStartLimiter`. `experiments/speedup_jev_2026_09_23/shared/secrets.py` loads the TypeSafe key (`load_typesafe_api_key`). `experiments/moral_outrage_classification_2026_09_19/shared/records.py` is a pydantic prediction row for a different labeling task, so the field list is the pattern and the model for this study is new. `AGENTS.md` names `HF_TOKEN` for Hugging Face access. `lib/load_env_vars.py` loads the GitHub token only, so the loaders read secret `hf-token` themselves, as in the credentials subsection.

### Example records

Each loader records a Hugging Face id, a revision, a config, and a split, and it writes one row per example. The shared fields are `example_id`, `dataset`, `split`, `text`, `gold_labels`, `harm_category`, `is_benign_known`, and `metadata`. `gold_labels` is a binary harm bit, a multi-label map, or a class name. `is_benign_known` is true only when the dataset marks that row benign. A row with no benign label stays false, and it stays out of the false-positive rate. `metadata` holds the adversarial flag, `prompt_type`, risk area, or type of harm when the source row has that field.

```python
class ExampleRecord(BaseModel):
    example_id: str
    dataset: str
    split: str
    text: str
    gold_labels: dict[str, bool] | str
    harm_category: str | None
    is_benign_known: bool
    metadata: dict[str, str | bool]
```

A few loaders need extra rules.

XSTest uses `allenai/xstest-response`, which asks for a form before download. The loader keeps one row per prompt text, drops duplicate prompts, and ignores reply labels. `prompt_type` stays in `metadata`.

HarmBench uses `swiss-ai/harmbench`, once for config `DirectRequest` and once for config `HumanJailbreaks`. Test rows are scored. Validation rows are the development pool for thresholds, and they are not a benign class.

JailbreakBench uses `JailbreakBench/JBB-Behaviors`, config `behaviors`. The `harmful` split and the `benign` split are both loaded. `is_benign_known` is true on the benign split.

Access-controlled datasets use the token from secret `hf-token`. A missing token fails that dataset and leaves the others loadable.

Where the harness already names a development split, we use it. ToxiGen, ToxicChat, and prompt injections use `train`. GoEmotions and Emotion use `validation`. OpenAI Moderation sets `dev` to `None` in `safety.py`. Do-Not-Answer, the XSTest prompts after duplicate removal, and JailbreakBench have no development split. For those, a hash of `example_id` holds out 20% as development. The Jev harness check on OpenAI Moderation scores all 1,680 rows at threshold 0.5. The tuned threshold is fit on the 20% holdout, and that holdout is left out of the tuned test number.

Do-Not-Answer keeps `risk_area` and the type of harm on the row, and that dataset is written to its own file so a later paper can include the aggregates or leave them out.

### Scorers

`DecisionScorer` is a Python `Protocol` with one method. The method takes example records and a question spec, and it returns prediction records. Jev, Clef, Clef-flash, and Guardrails each implement it.

```python
class DecisionScorer(Protocol):
    def score(
        self, records: list[ExampleRecord], question: QuestionSpec
    ) -> list[PredictionRecord]: ...
```

The question spec is Choice, Noul, or Score, in the same JSON shape as `choice`, `noul`, and `score` in `jev_benchmarking/tasks/base.py`. On the six datasets the harness already runs, the first template is the `build` method in `safety.py` or `classification.py`, so the harness check uses that wording.

The Clef and Clef-flash body, checked against the Workers AI Clef docs (https://developers.cloudflare.com/workers-ai/models/clef/) and a live call, has three fields. `model` is `clef` or `clef-flash`. `state` is the text. `questions` is an object keyed by question id. Each value has `type` (`noul`, `choice`, or `score`), `instructions`, and `criteria`. The answer for that id is `result.answers.<id>`, for example `{"type": "noul", "noul": 0.0039}`. Billed input tokens are `result.usage.input_tokens`.

```python
clef_request = {
    "model": "clef",  # or "clef-flash"
    "state": text,
    "questions": {
        "harm": {"type": "noul", "instructions": question, "criteria": None},
    },
}
# result.answers["harm"] == {"type": "noul", "noul": 0.0039}
# result.usage["input_tokens"] is the billed count
```

Workers AI shortens a `state` that does not fit the context and still returns that answer. The scorer counts tokens before the call, or compares `result.usage.input_tokens` with the limit (64,000 for Clef, 24,576 for Clef-flash), and sets `error_status` to `truncated` when the prompt does not fit. The metric table keeps the row.

A prediction record stores `example_id`, `arm`, `model_version`, `template_version`, the probability or the Guardrails band, the raw response, latency, billed usage, and an error status. For a Noul, the probability is `result.answers.<id>.noul`. A context-limit overflow is stored as an error. On Jev that is the provider error. On Clef and Clef-flash it is the `truncated` status above.

```python
class PredictionRecord(BaseModel):
    example_id: str
    arm: str
    model_version: str
    template_version: str
    probability: float | None
    band: str | None
    raw_response: dict
    latency_ms: float
    billed_units: float
    error_status: str | None
```

The Guardrails implementation makes one detect-only `ApplyGuardrail` call, with the filter action set to `NONE`, in `us-east-2`. Low, medium, and high strength are applied to the returned bands after the call. Three numbered guardrail versions are created only if detect mode omits the band.

### Templates, the request cache, and limits

Each dataset has one JSON template file, and the template version is a hash of that JSON. We confirm the wording on 20 development items. After that confirmation, the file stays as it is.

The cache key is a hash of the arm, the model version, the template version, and `example_id`. A retry that finds the key reads the stored response and does not call the provider again. The store follows `ResponseCache` in `jev_benchmarking/cache.py`. Each provider uses its own `RequestStartLimiter`. HTTP 429 and 5xx wait and retry, as in `experiments/moral_outrage_classification_2026_09_19/shared/engine_loop.py`. The `us-east-2` ApplyGuardrail quota is read before the paid run and written into the manifest, because the harness cap is for the TypeSafe API.

### Policies and metrics read predictions only

Union, intersection, and cascade take prediction records as input. Threshold fitting and the metric code take the same records. A later runtime blocks or allows by calling that policy on new scorer output, without a second code path.

### Storage and checks

When the study is run, the local files and the S3 objects use the tree in section 5. Do-Not-Answer question text is not committed to git, and it is not uploaded. The paper reports detection rate by risk area and by type of harm.

The check before the full run is a smoke test. It sends 20 development items, end to end, once per arm (Jev, Clef, Clef-flash, and Guardrails). Each returned row has the example-record fields. Jev, Clef, and Clef-flash return a non-empty probability, and Guardrails returns a non-empty band. A second pass of the same 20 items hits the cache and makes no new provider call. The Jev smoke rows are scored with the same primary metric as the published harness check, so a broken template shows up before the full run.

### Credentials

Secrets stay in AWS Secrets Manager in `us-east-2`, or in environment variables, and they are never committed. Names follow the kebab-case already used in this region.

- TypeSafe. `load_typesafe_api_key` in `experiments/speedup_jev_2026_09_23/shared/secrets.py` reads secret `jev-typesafe-api-key`, JSON field `TYPESAFE_API_KEY`.
- Cloudflare Workers AI, for Clef and Clef-flash. Secret `cloudflare-workers-ai` already exists in `us-east-2` and holds JSON fields `account_id` and `api_token`. The token needs Workers AI read and edit permission.
- AWS, for `ApplyGuardrail` and for creating the numbered guardrail. `experiments/speedup_jev_2026_09_23/shared/secrets.py` resolves `LAB_AWS_ACCESS_KEY_ID` and `LAB_AWS_ACCESS_KEY_SECRET`, then the standard AWS environment names. The identity needs `bedrock:ApplyGuardrail` and permission to create a guardrail in `us-east-2`.
- Hugging Face, for datasets that require a form. Secret `hf-token` supplies the token. `lib/load_env_vars.py` loads the GitHub token only, so the loaders read `hf-token` themselves.

```mermaid
flowchart LR
  hub[Hugging Face] --> loaders[Dataset loaders]
  loaders --> examples[Example records]
  templates[Confirmed templates] --> scorers[Decision scorers]
  examples --> scorers
  scorers --> cache[Request cache]
  cache --> predictions[Prediction records]
  predictions --> policy[Stack policy]
  policy --> metrics[Metrics]
  predictions --> bucket[S3 prefix]
```

## 5. Proposed file structure

The study, when it is run, uses one local folder, and the S3 prefix is that same folder path. This proposal does not create the folder. The trees below are here so they can be approved or changed.

### Local tree

Git commits the code, the question templates, the configs, `README.md`, `SETUP.md`, `RESULTS.md`, and the figure PNG files. Git ignores the cache, the raw dataset files, and the prediction files. Do-Not-Answer question text is never in a committed file.

```text
experiments/safety_decision_models_2026_10_19/
  README.md                                          # committed
  SETUP.md                                           # committed
  RESULTS.md                                         # committed
  pyproject.toml                                     # committed
  uv.lock                                            # committed
  .gitignore                                         # committed
  datasets/                                          # committed adapters
    toxigen.py
    openai_moderation.py
    toxicchat.py
    prompt_injections.py
    wildguardmix.py
    do_not_answer.py                                 # adapter only; rows stay out of git
    xstest.py
    harmbench.py
    jailbreakbench.py
    go_emotions.py
    emotion.py
  scorers/                                           # committed
    jev.py
    clef.py                                          # arms clef and clef-flash
    guardrails.py
  policies/                                          # committed; read predictions only
    union.py
    intersection.py
    cascade.py
  shared/
    records.py                                       # ExampleRecord, PredictionRecord, QuestionSpec
    metrics.py                                       # committed
    thresholds.py                                    # committed
    cache.py                                         # committed
  data/
    templates/                                       # committed JSON
      {dataset}.json
      archive/{dataset}/{template_version}.json
    records/                                         # gitignored
      {dataset}.parquet
    snapshots/                                       # gitignored raw text, one file per HF commit
      {dataset}/rev_{commit}.parquet
  configs/
    study.json                                       # committed; pins, prices, region, crosswalk; no secrets
  cache/                                             # gitignored
    responses.db
  scripts/                                           # committed
    smoke.py                                         # 20 items per arm
    run_score.py
    run_metrics.py
    upload_s3.py
  outputs/
    predictions/{run_id}/{arm}/{dataset}.parquet     # gitignored
    predictions/{run_id}/{arm}/{dataset}.jsonl       # gitignored
    metrics/{run_id}.json                            # gitignored
    manifests/{run_id}.json                          # gitignored
    figures/{run_id}/*.png                           # committed
```

`.gitignore` starts from `experiments/speedup_jev_2026_09_23/.gitignore`. That file ignores parquet, json, and jsonl one directory under `data/`, and anywhere under `outputs/`. This study also ignores `cache/` and the nested `data/records/` and `data/snapshots/` paths, because those files sit one directory deeper than the speedup pattern. `data/templates/` and `outputs/figures/` stay in git, as do `RESULTS.md` files. The folder has no `tests/` directory. The smoke check is `scripts/smoke.py`, the same entry style as `experiments/speedup_jev_2026_09_23/scripts/smoke.py`.

Each template file holds the question spec, which is the type, the instructions, and the criteria. The file does not hold dataset rows. The template version is a hash of that JSON. When the wording changes, the previous file is copied to `data/templates/archive/{dataset}/{template_version}.json` before the edit, and that copy stays in git.

### S3 tree

The bucket is `mind-technology-lab-experiments`. The prefix is `experiments/safety_decision_models_2026_10_19/`. An upload joins that prefix to each file's path relative to the experiment root, the same join as `PREFIX + relative` in `experiments/moral_outrage_classification_2026_09_19/scripts/upload_s3.py` and `experiments/speedup_jev_2026_09_23/scripts/upload_s3.py`.

```text
s3://mind-technology-lab-experiments/experiments/safety_decision_models_2026_10_19/
  data/snapshots/{dataset}/rev_{commit}.parquet
  data/records/{dataset}.parquet
  cache/responses.db
  outputs/predictions/{run_id}/{arm}/{dataset}.parquet
  outputs/predictions/{run_id}/{arm}/{dataset}.jsonl
  outputs/metrics/{run_id}.json
  outputs/figures/{run_id}/
  outputs/manifests/{run_id}.json
```

The upload skips `.venv`, `__pycache__`, `.pytest_cache`, `.git`, and `.env`, as those two scripts do. It also skips every Do-Not-Answer snapshot, every Do-Not-Answer records file, and every cache entry that stores that question text. Aggregates by risk area and by type of harm still upload, inside the metrics file, with the question text left out.

`run_id` is the UTC start time and 8 hex characters, written as `{YYYYMMDD}T{HHMMSS}Z_{8 hex characters}`. The 8 hex characters hash the dataset revisions, the template versions, and the arm list. A later run gets a new id, so the earlier run stays in place. The moral outrage folder partitions by engine, under `outputs/jev/` and `outputs/bedrock/{model}/`. The speedup folder partitions by batch size, under `outputs/batch_{n}/`. Neither folder uses a run id. [PR 31](https://github.com/METResearchGroup/mind_technology_lab_experiments/pull/31) uses one directory per run under `outputs/`, and each directory holds `results.jsonl`, `grade.json`, `grade_items.jsonl`, and `manifest.json`. The `run_id` form here is proposed for this study.

A partition is one prediction file for one arm and one dataset under that `run_id`. The arm names are `jev`, `clef`, `clef-flash`, and `guardrails`. `{dataset}` is the short name from the local tree, for example `toxigen`. The Hugging Face id, the config, and the split are in the manifest. The snapshot key adds the commit, as `rev_{commit}`.

Union, intersection, and cascade read the four arm files. Their numbers go in `outputs/metrics/{run_id}.json`. They do not get prediction files of their own.

### How the tree maps to section 4

The dataset modules write `ExampleRecord` rows into `data/records/` and into the revision snapshot. `data/templates/{dataset}.json` is the `QuestionSpec`, and the template version is the hash of that file. `scorers/jev.py`, `scorers/clef.py`, and `scorers/guardrails.py` implement `DecisionScorer`. Clef and Clef-flash share `scorers/clef.py`, and the arm name on the prediction row separates them. Those scorers write `PredictionRecord` rows under `outputs/predictions/{run_id}/`. `cache/responses.db` stores the provider response under the cache key from section 4, a hash of the arm, the model version, the template version, and `example_id`. The three policy modules read those prediction rows only. `shared/metrics.py` and `shared/thresholds.py` read the same rows. `outputs/manifests/{run_id}.json` records the model pins, the dataset revisions, the template versions, the prices, and the region `us-east-2`.

### Where the conventions come from

[Issue 17](https://github.com/METResearchGroup/mind_technology_lab_experiments/issues/17) names `experiments/moral_outrage_classification_2026_09_19/`, with `README.md`, `SETUP.md`, `RESULTS.md`, model code, `outputs/`, and `shared/`, and it sets the S3 prefix to that same folder in `mind-technology-lab-experiments`. [PR 20](https://github.com/METResearchGroup/mind_technology_lab_experiments/pull/20) is the finished run of that issue, at `s3://mind-technology-lab-experiments/experiments/moral_outrage_classification_2026_09_19/`. [PR 23](https://github.com/METResearchGroup/mind_technology_lab_experiments/pull/23) uses the same prefix rule for `experiments/speedup_jev_2026_09_23/`, including `outputs/batch_{n}/` and `ablation_full_dataset/` under that prefix. `AGENTS.md` states the prefix rule for this repository. [PR 26](https://github.com/METResearchGroup/mind_technology_lab_experiments/pull/26) adds `shared/aws/s3.py`. The prefix rule stays the one in `AGENTS.md`. [PR 31](https://github.com/METResearchGroup/mind_technology_lab_experiments/pull/31) stores each run under `s3://mind-technology-lab-experiments/experiments/safety_prompting_2026_10_16/outputs/`.

Searches for the phrases "file structure", "directory structure", "folder structure", and "S3 layout" in pull requests in this repository returned no matches. Searches of `METResearchGroup/mirrorView-task` and `METResearchGroup/lab_wiki` failed, because the API said those repositories cannot be searched, so no issue or pull request from those repositories is cited. Issue 17 links a path in `mirrorView-task` for the moral outrage engines. The retry loop this study reuses is `experiments/moral_outrage_classification_2026_09_19/shared/engine_loop.py`.

## 6. Key analyses

**RQ1, model comparison.** For each core safety dataset, compute the primary metric for `jev-1.13.0`, Clef, and Clef-flash, with a 95% percentile bootstrap over items (500 resamples, the same choice as Deußer et al.). A difference counts only when the intervals do not overlap. On the six datasets in the harness-check table, compare our Jev number to the published interval before interpreting Clef. Break WildGuardTest into vanilla and adversarial prompts, using the adversarial flag, and break HarmBench into DirectRequest and HumanJailbreaks. The same comparison on GoEmotions uses macro-F1, and on Emotion it uses accuracy. Guardrails do not enter RQ1, because they do not emit the dataset label.

**RQ2, thresholds and confidence.** For each Noul, report F1, recall, and false-positive rate at 0.5 and at the development-tuned threshold. Plot the reliability curve and compute ECE and Brier on `P(yes)`. For selective prediction, rank by confidence and report the miss rate, and the accuracy where a gold label exists, at 80% coverage and at 50% coverage. On GoEmotions, repeat the per-label threshold grid that Deußer et al. used (step 0.01 on 1,000 training items) and report macro-F1 at 0.5 and at the tuned thresholds. On Emotion, report top-option ECE, which was 0.279 in the published run, the worst Choice calibration in that paper. Sets with fewer than 200 labeled development items (prompt injections, JailbreakBench) are reported at 0.5 only, with AUROC as the threshold-free number, because a tuned threshold on a tiny split will not hold.

**RQ3, over-refusal and emotion text.** False-positive rate on JailbreakBench `benign` and on XSTest prompts with `prompt_type` equal to `prompt_safe`, for every arm including the three stack policies. For GoEmotions and Emotion, the gold label is an emotion, not harm. The analysis is the block rate of each arm by gold label. The comparison is whether anger, disgust, and sadness are blocked more often than joy or neutral. We do not call an emotion block a false positive, because the dataset has no harm label. A comment can be both angry and abusive. Where GoEmotions has no abuse label, we say "block rate by emotion," not "over-refusal."

**RQ4, guardrail crosswalk.** Before scoring, write a table from each dataset label to zero or more of the six filters. The table is written before the first test number, and it stays unchanged after that. Sexual and hate have obvious candidates. Harassment is only partly Insults. Self-harm has no filter, and that cell stays empty on purpose. For each strength (low, medium, high), report the miss rate on harmful rows and the false-positive rate on benign rows, using the AWS rule above (high strength blocks more bands). The call is one detect-only `ApplyGuardrail` with the filter action set to `NONE`, and the three strengths are applied to the returned bands. Three numbered versions are created only if detect mode omits the band. Bands may be ranked (`NONE` < `LOW` < `MEDIUM` < `HIGH`) for a rank statistic. The rank stays a rank.

**RQ5, stack policies.** On the items that have both a harmful class and a benign class (JailbreakBench, XSTest `prompt_type`, WildGuardTest prompt harm), compute miss rate and false-positive rate for the decision model alone, the guardrail alone, union, intersection, and cascade. The development fit uses the 5% false-positive budget, and the test numbers are a single confirmed application of those thresholds. A policy is better only if it lowers the miss rate at the same or lower false-positive rate, or the reverse. If the three policies land on top of each other, the stack is not doing work beyond the stronger component.

**RQ6, latency and cost.** Record wall-clock latency per request (median and 95th percentile) from the client, and record the provider's billed usage (tokens for Jev and Clef, text units for Guardrails). Report cost per 1,000 prompts from the bill. Section 10 is only a budget check. Deußer et al. found that their rate limit set throughput, so we record the limit beside the latency.

## 7. Key visualizations

1. **Miss rate against false-positive rate.** Each point is an arm or a stack policy. The x-axis is the false-positive rate on the pooled benign prompts (JailbreakBench benign, XSTest `prompt_safe`, WildGuardTest benign prompts). The y-axis is the miss rate on the matched harmful prompts. Supports RQ3 and RQ5. A reader should see whether union, intersection, and cascade sit apart, and whether any point is below and to the left of Jev alone.
2. **Reliability diagrams.** X-axis is `P(yes)` in 15 equal-width bins. Y-axis is the observed frequency of harm. One panel for single-Noul safety sets, one panel for the 28 GoEmotions Nouls. Marker area is the number of answers. Series are Jev, Clef, and Clef-flash. Supports RQ2. Guardrail bands are not on this figure.
3. **Threshold curves.** For ToxicChat jailbreak, ToxiGen, and prompt injections, x-axis is the threshold on `P(yes)`, y-axis is F1, with a second panel for recall and false-positive rate. Vertical marks at 0.5 and at the development-tuned threshold. Supports RQ2. The prompt-injection panel will be wide, because n is 116.
4. **Guardrail band against dataset label.** Rows are dataset labels (including self-harm and an explicit "no filter" row). Columns are the six filters. Cells are the share of items whose returned band is at least medium. Supports RQ4. The empty self-harm row is part of the figure, so the missing category is visible.
5. **Selective prediction.** X-axis is coverage. Y-axis is miss rate for safety Nouls, and accuracy for Emotion. Horizontal guides at 50% and 80% coverage. Series are the three decision models. Supports RQ2.
6. **Block rate by GoEmotions label.** X-axis is the 28 labels, ordered by block rate under Jev. Y-axis is block rate. Grouped bars for Jev at the tuned threshold, Clef at its tuned threshold, and Guardrails at medium strength. Supports RQ3. The reader should be able to see whether anger and disgust rise above joy and neutral.
7. **Latency and cost against miss rate.** X-axis is median latency in milliseconds. Y-axis is miss rate on the pooled harmful prompts that have a paired benign set. Point size or a printed label is cost per 1,000 prompts from the bill. Supports RQ6.
8. **Cascade diagram.** A flowchart with three outcomes, block, allow, and "ask the guardrail," and the two thresholds on `P(harm)`. Supports RQ5. No data values, so it can be drawn before the run.

## 8. Key messaging

The claims below are hypotheses, and the paper may reject any of them. Bracketed numbers in the abstract are unfilled on purpose.

1. The harness reproduces published Jev figures on the six overlapping sets, inside the published 95% intervals. The hypothesis fails if our `jev-1.13.0` primary metric falls outside the interval for ToxiGen, OpenAI Moderation, ToxicChat, prompt injections, GoEmotions, or Emotion.
2. Clef does not win every safety set. The Decision Index lead is on other tasks, and Jev already trails Qwen on the small prompt-injection set. The hypothesis fails if Clef's interval lies entirely above Jev's on every core safety primary metric.
3. A threshold of 0.5 under-detects on at least one Noul safety set, and a development-tuned threshold raises F1 there. The published prompt-injection case (recall 50% at AUROC 0.982) is the pattern we expect to see again. The hypothesis fails if 0.5 maximizes F1 on every Noul set that has a development split.
4. Guardrails and the decision models miss different items. In particular, Guardrails miss more self-harm items than sexual items, because self-harm has no filter, and they miss more implicit ToxiGen items than explicit JailbreakBench harmful goals. The hypothesis fails if those detection rates match within bootstrap noise.
5. Union lowers the miss rate and raises the false-positive rate relative to either piece alone. Intersection does the opposite. Cascade, fit to the 5% false-positive budget, lands between them. The hypothesis fails if the three policies do not separate on figure 1.
6. Emotion text is blocked less often than harmful prompts, and anger and disgust are blocked more often than joy and neutral. The hypothesis fails if GoEmotions block rates do not differ by label, or if they match the miss rate on JailbreakBench harmful.
7. On this pack, billed cost per token keeps the published order (Clef at $0.240 per million input tokens, Jev at $0.042, Clef-flash at $0.038), and Clef-flash has the lowest median latency of the three. The hypothesis fails if the bill or the latency ranking reverses. Vendor latency numbers from the Decision Index are not evidence for this pack.

If those hypotheses hold, the block rule for a wellbeing assistant has to name the stack and the threshold. Lowering missed harm raises the rate at which ordinary emotion text is refused, so a single model name does not state the operating point.

## 9. Risks and limitations

**Contamination.** Deußer et al. (section 4.6) found that Jev scores calculation-heavy MMLU subjects at 94.3% and other MMLU subjects at 91.3%. Qwen and Gemma find the calculation-heavy subjects harder (Qwen 74.7% against 83.0%, Gemma 54.6% against 69.8%). Rotating the answer letters left calculation-heavy accuracy at 94.3%. Withholding the question dropped it to 31.5%, close to the 25% chance level. Those probes rule out a memorized letter and a memorized option list. They leave open memorized question-answer pairs. Jev's training data are private, and Clef's post-training mix is only partly described. ToxiGen, OpenAI Moderation, HarmBench, and JailbreakBench are public and widely copied. A high score can be memorization. We will repeat the option-rotation check on the six-way Emotion Choice. Noul questions have no option order. A paraphrase of a small development subset can show brittleness, and it is not a proof that the test text was unseen.

**Thresholds.** The same paper shows that 0.5 is a poor operating point when `P(yes)` is shifted. GoEmotions macro-F1 moves from 0.243 to 0.353 after tuning, and ToxicChat jailbreak F1 moves from 0.717 to 0.833. Tuned thresholds do not always transfer. Qwen's jailbreak F1 fell slightly after tuning (0.743 to 0.726). We fit thresholds on development data only, we always publish the 0.5 number beside the tuned number, and we do not tune on prompt injections or JailbreakBench.

**Category mismatch.** Guardrails categories are not the dataset labels. A crosswalk that is edited after seeing test scores would invent a result. The crosswalk is written first, and self-harm stays unmapped. Confidence bands are not probabilities, so a guardrail cannot be declared "better calibrated" than Jev.

**Harmful-only sets.** Do-Not-Answer, HarmBench, and the harmful half of several other sets have no benign class. Treating an unlabeled row as safe would understate the false-positive rate. Those sets contribute detection rate and miss rate only.

**Small sets.** Prompt injections have 116 test rows (published interval width about 0.16 on accuracy). JailbreakBench has 100 per class. HarmBench DirectRequest test has 320. Intervals will be wide, and a model ranking on those sets can flip. We will not headline a winner from the smallest set.

**Labels.** WildGuardTest prompt-harm labels have Fleiss' kappa 0.55 across three annotators (moderate agreement), as stated on the dataset card. Emotion labels are hashtag-derived and noisy, which is why published accuracy is 0.585 and ECE is 0.279. GoEmotions can mark several emotions on one comment, and a single Noul does not know that most of the other 27 are false, which is the over-prediction Deußer et al. measured (mean `P(yes)` 0.209 against an observed rate of 0.041 on multi-label Nouls).

**License.** Do-Not-Answer is in the core pack. The study is academic research, so non-commercial use fits CC BY-NC-SA 4.0. The card also names Apache 2.0 for source files, and the GitHub license field is Apache 2.0. The run follows the stricter card statement. Question text stays out of the paper, the git repository, and any public upload. The paper reports detection rate by risk area and by type of harm, from the dataset's own file, so a later draft can include those aggregates or leave them out. `allenai/xstest-response` requires the Allen Institute form and secret `hf-token`. If that form stalls, XSTest is omitted and the rest of the pack still runs. The public harness also marks `allenai/wildguardmix` as requiring a form, so WildGuard uses the same token.

**Versions.** `jev-1.13.0` is pinned. Clef and Clef-flash are pinned by hosted model id and by Hugging Face commit. Each dataset revision is the commit from the first successful load, stored in the run manifest, and a later load with a different commit is refused. The guardrail is a numbered version, in `us-east-2`, which is `DEFAULT_REGION_NAME` in `shared/aws/constants.py`. Filter strength is recorded from the detect-only bands. A later vendor update is a different study.

**What the miss rate is not.** We do not generate new jailbreak strings, and we do not measure whether a chat model would have complied. HarmBench's usual attack-success rate against a target model is a different quantity.

**Input length.** HumanJailbreaks prompts can be long. On Jev, a request over the context limit is an error, the same treatment the harness gives HTTP 400 `max_tokens_exceeded`. On Workers AI, Clef and Clef-flash shorten a long `state` to fit and still return an answer. The scorer counts tokens before the call, or compares `result.usage.input_tokens` with the limit, and stores those rows as `truncated`. Clef-flash's hosted limit is 24,576 tokens. Clef's is 64,000. A self-hosted rerun of the Clef-flash weights is future work. If the truncated or error rate exceeds 1% on any set, we report it beside the metric, and those rows stay in the table.

## 10. Plan and cost estimate

The estimate uses published prices as of 2026-10-19 and the row counts above. It is an estimate, not a quote. The bill from the run replaces it.

Row count for one pass of the core pack, counting one request per example and counting XSTest as about 500 unique prompts: about 20,500. Deußer et al. averaged 630 input tokens per request on their broader suite. At that average, one pass is about 12.9 million input tokens. If the jailbreak prompts run near 2,000 tokens instead, the token count is about three times larger.

| Arm | Published unit price | Estimate at 12.9M tokens or one text unit | Estimate if prompts are about 3 times longer |
| --- | --- | --- | --- |
| Jev `jev-1.13.0` | US$0.042 per million input tokens, output free (Deußer et al., price at their time of writing) | about US$0.54 | about US$1.60 |
| Clef | US$0.240 per million input tokens, output free (Cloudflare Workers AI pricing, page updated 2026-10-19) | about US$3.10 | about US$9.30 |
| Clef-flash | US$0.038 per million input tokens, output free (same page) | about US$0.49 | about US$1.50 |
| Guardrails content filters | US$0.15 per 1,000 text units. A text unit is up to 1,000 characters. Prompt Attack is included in this price on `ApplyGuardrail`. (https://aws.amazon.com/bedrock/pricing/) | about US$3.10 if each prompt is one text unit | about US$9 to US$20 |

A stack pays for the decision model and the guardrail. Three decision models plus one guardrail pass, short prompts, is on the order of US$8. The long-prompt case is on the order of US$15 to US$30. Three separate strength calls, used only if detect mode omits the band, push the upper end toward US$50. The 20-item smoke run and the development tune add a small fraction on top. Planning number for the required arms on the core pack: under US$50. The optional preference-data pool is not in this number, because a full pass of `hh-rlhf` would dominate the bill and needs its own estimate after a subsample is chosen.

At 1,100 requests per minute, the cap Deußer et al. actually hit, about 21,000 requests take on the order of 20 minutes of API time, before retries. The cache in section 4 keeps a retry from paying twice, so the estimate counts one call per example. The 20 minutes are API time only.

Steps, in order:

1. Write the loaders and the `DecisionScorer` interface from section 4, including the XSTest dedupe, the HarmBench configs, the JailbreakBench splits, and the `hf-token` load. Place those files in the tree in section 5 when the study is implemented. On the first successful load, pin each dataset revision to that commit and write it into the manifest.
2. Confirm one template per dataset on 20 development items. For the six overlapping sets, start from the `build` methods in the public harness so the harness check uses the same wording. Store the confirmed JSON under `data/templates/`.
3. Run the 20-item smoke test from section 4, once per arm. Stop if a probability or band is empty, if the rerun misses the cache, or if the Jev smoke metric cannot be compared with the published harness metric.
4. Run `jev-1.13.0` on the six overlapping sets and compare to the published intervals. For OpenAI Moderation, that check uses all 1,680 rows at threshold 0.5. Stop if we are outside an interval.
5. Create a numbered guardrail in `us-east-2` with the six content filters and the filter action set to `NONE`. Write the crosswalk into `configs/study.json`. Fall back to three numbered versions only if detect mode omits the band.
6. Score the core pack with Jev, Clef, Clef-flash, and `ApplyGuardrail`, through the cache in section 4. On hosted Clef and Clef-flash, mark a prompt over the context limit as `truncated`, because Workers AI shortens the state and still returns an answer. Clef-flash's limit is 24,576 tokens.
7. Fit thresholds on development splits. For OpenAI Moderation, fit the tuned threshold on the hash-stable 20% holdout and leave that holdout out of the tuned test number. Compute the metrics and the eight figures from the prediction records, using the union, intersection, and cascade functions. Write them under the paths in section 5, and upload with `scripts/upload_s3.py` using that prefix. Skip Do-Not-Answer question text.

Future artifacts, when the study is run, would live under `experiments/safety_decision_models_2026_10_19/` and the same prefix in `s3://mind-technology-lab-experiments/`. This proposal does not add that folder. The layout inside it is in section 5. The four review points at the end of this file were approved on 2026-10-20.

## 11. Draft abstract

Typed decision models return a probability for a fixed question, and they do not write the assistant's reply. We compare TypeSafe Jev (`jev-1.13.0`), Cloudflare Clef, Cloudflare Clef-flash, and Amazon Bedrock Guardrails, alone and in three stack policies (union, intersection, and cascade), on public safety datasets and on two emotion datasets. The safety sets are ToxiGen, OpenAI Moderation, ToxicChat, a prompt-injection set, WildGuardTest, Do-Not-Answer, XSTest prompts, HarmBench, and JailbreakBench. Do-Not-Answer is reported as detection rate by risk area and by type of harm, without the question text. The emotion sets are GoEmotions (28 labels) and the six-way Emotion set. We score prompts only. One detect-only `ApplyGuardrail` call supplies the low, medium, and high strengths. The stack policy over those scorer outputs is the block function a later runtime would call. A miss is a harmful prompt the filter allows, and a false positive is a benign prompt the filter blocks. On the sets that contain both classes, the cascade policy reaches a miss rate of [X%] and a false-positive rate of [Y%], compared with [A%] and [B%] for Jev alone and [C%] and [D%] for Guardrails alone. Expected calibration error on the yes/no harm probability is [ECE = __] for Jev and [ECE = __] for Clef. The gap between a 0.5 threshold and a development-tuned threshold is [Z] F1 points on [dataset]. Guardrails return a confidence band (`NONE`, `LOW`, `MEDIUM`, or `HIGH`), so expected calibration error does not apply to that band. Their six categories do not match the dataset labels, and self-harm has no filter of its own. Median latency is [__] ms for Jev, [__] ms for Clef, [__] ms for Clef-flash, and [__] ms for `ApplyGuardrail`. Block rates on GoEmotions differ by emotion label by [__] points between [label] and [label]. The bracketed figures will be filled from the run, and they are empty in this draft.

## Decisions made

1. **Guardrail strength.** One detect-only `ApplyGuardrail` call, with the filter action set to `NONE`. Low, medium, and high are applied after the call. Low blocks only a HIGH band, medium blocks HIGH and MEDIUM, and high blocks HIGH, MEDIUM, and LOW. Three numbered versions are the fallback only if detect mode omits the band.
2. **Do-Not-Answer.** Included in the core pack. Academic research fits non-commercial use under CC BY-NC-SA 4.0. Question text is not republished. Results are aggregates by risk area and by type of harm. The dataset is its own file, so a paper can include it or leave it out later.
3. **Emotion pair.** GoEmotions and `dair-ai/emotion`. Dreaddit is a possible later separate task, with its own label definition.
4. **Region.** `us-east-2`, the same value as `DEFAULT_REGION_NAME` in `shared/aws/constants.py`.
5. **Dataset revisions.** Each Hugging Face dataset is pinned to the commit from the first successful load. That commit is written into the run manifest, and a later load with a different commit is refused.
6. **OpenAI Moderation holdout.** The harness check scores all 1,680 rows at threshold 0.5. The tuned threshold is fit on a hash-stable 20% holdout, and that holdout is left out of the tuned test number.
7. **Clef-flash context.** Workers AI shortens a `state` over 24,576 tokens and still returns an answer. The scorer counts tokens before the call, or compares `result.usage.input_tokens` with that limit, and stores the row as `truncated`. A self-hosted rerun of the weights is future work.

Decisions 1 to 7 are closed.

## Review points

Approved on 2026-10-20. The four layout points below are the layout to implement.

1. **Local tree.** Approved. Use the tree in section 5. Git ignores `cache/`, `data/records/`, `data/snapshots/`, `outputs/predictions/`, `outputs/metrics/`, and `outputs/manifests/`. Git commits the code, the templates, the configs, `README.md`, `SETUP.md`, `RESULTS.md`, and the figure PNG files. The smoke entry is `scripts/smoke.py`, and the folder has no `tests/` directory.
2. **S3 tree and run id.** Approved. The prefix is `experiments/safety_decision_models_2026_10_19/`. The `run_id` form is `{YYYYMMDD}T{HHMMSS}Z_{8 hex characters}`. Stack policies are written into the metrics file, and they do not get prediction files.
3. **Do-Not-Answer text.** Approved. That question text stays out of git and out of S3. The loader reads it from Hugging Face into the gitignored local cache for the run. The upload skips that dataset's snapshot, its records file, and any cache entry that holds the text. Aggregates by risk area and by type of harm still upload.
4. **Figures path.** Approved. PNG files go under `outputs/figures/{run_id}/`. The moral outrage and speedup folders put images in `outputs/.../static/`.
