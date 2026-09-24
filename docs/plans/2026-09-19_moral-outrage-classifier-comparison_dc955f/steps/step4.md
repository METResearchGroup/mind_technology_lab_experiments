# Step 4: Implement the three engines

Build Jev, Perspective, and Bedrock engines that each return `PredictionRecord`s. Reuse the batch / retry / skip-seen / deadletter loop from mirrorView-task. Do not run smoke or the 1,000-row jobs yet.

## Scope

- **Caller:** `label_records` on each engine, later run from `models/smoke_tests/*.py` (Step 5) and the sample runners (Step 6).
- **Task:** Three engine modules plus a local copy of the loop behavior (not a git submodule of mirrorView-task). Provider calls may be implemented; live traffic waits for Step 5.
- **Out of scope:** Writing RESULTS tables, S3 upload, starting the 1,000-row jobs.

## Files

### Inspect

- https://raw.githubusercontent.com/METResearchGroup/mirrorView-task/main/data_platform/generate_features/engines/base.py (`BaseBatchExecutionEngine.label_records`, `filter_seen_tasks`, `label_chunk`, deadletter)
- https://docs.typesafe.ai/introduction/quickstart#code-it-the-python-sdk
- https://docs.typesafe.ai/primitives (Noul, `noul` in `[0, 1]`)
- Perspective AnalyzeComment (`comments:analyze`, `requestedAttributes`)
- AWS Bedrock Converse in `us-east-2` for the five model IDs
- `experiments/moral_outrage_classification_2026_09_19/shared/records.py`
- `experiments/moral_outrage_classification_2026_09_19/shared/timer.py`
- `experiments/moral_outrage_classification_2026_09_19/shared/brady_definition.py`
- `experiments/moral_outrage_classification_2026_09_19/shared/secrets.py`

### Allowed to change

- `experiments/moral_outrage_classification_2026_09_19/models/jev.py`
- `experiments/moral_outrage_classification_2026_09_19/models/perspective_api.py`
- `experiments/moral_outrage_classification_2026_09_19/models/bedrock.py`
- `experiments/moral_outrage_classification_2026_09_19/shared/engine_loop.py` (local loop: batch, retry, skip seen ids, deadletter)
- `experiments/moral_outrage_classification_2026_09_19/shared/pricing.py` (token cost lookup used by records; numbers may stay `0.0` until Step 5)
- `experiments/moral_outrage_classification_2026_09_19/tests/test_jev.py`
- `experiments/moral_outrage_classification_2026_09_19/tests/test_perspective_api.py`
- `experiments/moral_outrage_classification_2026_09_19/tests/test_bedrock.py`
- `experiments/moral_outrage_classification_2026_09_19/tests/test_engine_loop.py`

### Forbidden to change

- Copying Bluesky campaign files from mirrorView-task (`campaigns/`, feed joins, Momento)
- Vendoring the whole `mirrorView-task` repo
- Switching Perspective to `TOXICITY` or any attribute other than `MORAL_OUTRAGE`
- Calling TypeSafe without `typesafe-sdk`
- Changing Brady instruction text
- Starting Step 5 smoke as part of this step
- Root workspace members

## Contracts

### Shared engine loop (`engine_loop.py`)

Reimplement the behavior in `BaseBatchExecutionEngine.label_records`, not the Bluesky types:

1. Split tasks into chunks of `batch_size` (default `8` for Jev and Bedrock, `1` for Perspective unless you have a documented batch API; Perspective AnalyzeComment is one comment per request, so `batch_size=1`).
2. Drop tasks whose `source_row_id` is already in the output parquet (`skip seen`).
3. Retry a failed chunk up to `max_label_retries=3` (4 attempts total) on timeout or HTTP 429/5xx.
4. On exhaustion, append one JSON line per failed row to `{output_dir}/deadletter.jsonl` with keys `source_row_id`, `error`, `attempts`, `batch_index`.
5. Append successful rows to `{output_dir}/labels.parquet` as they complete.

Do not import `data_platform` from mirrorView-task.

### Jev (`models/jev.py`)

- Client: `typesafe_sdk.TypeSafeClient` with `TYPESAFE_API_KEY` from `load_typesafe_api_key()`.
- Model: `jev-latest` (SDK default is fine if it is `jev-latest`; pass it explicitly).
- One question id `moral_outrage`, type Noul, `instructions=BRADY_MORAL_OUTRAGE_INSTRUCTIONS`.
- `state` is the post `text` (string).
- `probability` = `response.answers["moral_outrage"].noul`.
- `model_name` = `Jev`.
- Tokens from `response.usage` when present (`input_tokens`, `output_tokens`).
- Wrap the `system_one` call with the shared timer.

### Perspective (`models/perspective_api.py`)

- HTTP POST `https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze?key={GOOGLE_API_KEY}`
- Body:

```json
{
  "comment": {"text": "<post text>"},
  "languages": ["en"],
  "requestedAttributes": {"MORAL_OUTRAGE": {}},
  "doNotStore": true
}
```

- `probability` = `attributeScores.MORAL_OUTRAGE.summaryScore.value`.
- `model_name` = `Perspective API`.
- Tokens: `None`. Cost: `0.0`.
- If the API returns 400/404 because `MORAL_OUTRAGE` is unknown, raise a dedicated error (`MoralOutrageAttributeRejected`). Do not retry with `TOXICITY`.
- Default to at most 1 request per second (sleep after each call). Wrap the HTTP call with the shared timer.

### Bedrock (`models/bedrock.py`)

- Region `us-east-2`. Client: `boto3.client("bedrock-runtime", region_name=AWS_REGION)`.
- One engine class; the model id is an argument.
- Allowed model ids (exact):

| Display `model_name` | `modelId` passed to Converse |
| --- | --- |
| `Bedrock:us.openai.gpt-5.6-luna` | `us.openai.gpt-5.6-luna` |
| `Bedrock:us.openai.gpt-5.6-terra` | `us.openai.gpt-5.6-terra` |
| `Bedrock:us.anthropic.claude-sonnet-5` | `us.anthropic.claude-sonnet-5` |
| `Bedrock:qwen.qwen3-32b-v1:0` | `qwen.qwen3-32b-v1:0` |
| `Bedrock:deepseek.v3-v1:0` | `deepseek.v3-v1:0` |

Reject any other id.

- System or developer text: `BRADY_MORAL_OUTRAGE_INSTRUCTIONS` plus a request for structured output `{ "moral_outrage": bool, "probability": float }` with `probability` in `[0, 1]`.
- Prefer Converse structured-output / tool JSON when the model supports it. If a model returns only `moral_outrage` bool, set `probability=None` and `binary_label` from the bool.
- Tokens from Converse usage. Wrap Converse with the shared timer.
- If the account lacks model access, raise a clear error naming the model id. Do not swap in a different model.

## Implement-from-spec phases

### Phase 1. Scope

Caller = `engine.label_records(tasks, output_dir=...)`.

### Phase 2. Scaffold

Create the three engine modules and `engine_loop.py` with stubs. Imports resolve from tests.

### Phase 3. Contracts

Public methods:

- `JevEngine.label_one(text: str) -> PredictionRecord` (or equivalent)
- `PerspectiveApiEngine.label_one(text: str) -> PredictionRecord`
- `BedrockEngine(model_id: str).label_one(text: str) -> PredictionRecord`
- `label_records(...)` on each, delegating to `engine_loop`

Bodies may stay stubbed until tests exist.

### Phase 4. Test design (mocked providers)

1. **Jev:** Fake client returns `noul=0.91` and usage tokens. `label_one` yields `model_name=="Jev"`, `probability==0.91`, `binary_label==1`, `latency_ms>=0`.
2. **Jev:** Instructions passed to Noul equal `BRADY_MORAL_OUTRAGE_INSTRUCTIONS`.
3. **Perspective:** Fake HTTP 200 with `summaryScore.value=0.12` yields `model_name=="Perspective API"`, `binary_label==0`, `estimated_cost_usd==0.0`.
4. **Perspective:** Fake HTTP 400 body saying unknown attribute raises `MoralOutrageAttributeRejected`.
5. **Bedrock:** Fake Converse for `us.openai.gpt-5.6-luna` yields `model_name=="Bedrock:us.openai.gpt-5.6-luna"`.
6. **Bedrock:** Constructing `BedrockEngine("anthropic.claude-sonnet-5")` (foundation id without `us.`) raises.
7. **Loop:** Given two tasks and an existing parquet that already contains the first `source_row_id`, only the second is sent to `label_one`.
8. **Loop:** Given `label_one` always raises, after retries `deadletter.jsonl` has the row, `attempts==4`, and parquet has no new row.

Do not hit the network in these tests.

### Phase 5. Implement units of work (order)

1. `engine_loop` skip-seen + deadletter (with a fake `label_one`).
2. Jev `label_one` against a fake client.
3. Perspective `label_one` against a fake HTTP transport.
4. Bedrock `label_one` against a fake `converse`.
5. Wire `label_records` on each engine to the loop.

### Phase 6

Mocked tests green. Live smoke is Step 5.

## Commands

```bash
cd experiments/moral_outrage_classification_2026_09_19
uv run pytest tests/test_engine_loop.py tests/test_jev.py tests/test_perspective_api.py tests/test_bedrock.py -q
```

Expected: all pass, no network.

## Pass / fail

### Must pass

- [ ] Three engine modules exist with the class names from issue 17: `JevEngine`, `PerspectiveApiEngine`, Bedrock runner in `bedrock.py`.
- [ ] Mocked tests cover happy path and the Perspective attribute-rejected path.
- [ ] Loop skips seen ids and writes deadletter with `error` and `attempts`.
- [ ] Brady string is imported, not rewritten.

### Must fail / must not happen

- [ ] Fallback to `TOXICITY`.
- [ ] Raw HTTP to TypeSafe instead of `typesafe-sdk`.
- [ ] Copying campaign code from mirrorView-task.
- [ ] Running the 1,000-row sample.

## Done when

Engines and the loop are unit-tested with fakes. Ready for Step 5 live smoke on three texts.

## Addendum 2026-09-19

Do not write pytest files. Do not call AnalyzeComment.

Keep the public shape of `PerspectiveApiEngine` in `experiments/moral_outrage_classification_2026_09_19/models/perspective_api.py`:

- `__init__(self, http_post=None, api_key=None, sleeper=None)`
- `label_one(self, text: str) -> PredictionRecord`
- `label_records(self, tasks, output_dir)`

Those constructor arguments may stay unused. Do not load `GOOGLE_API_KEY`. Do not sleep for a quota. Do not request `TOXICITY`.

On first use, load `experiments/moral_outrage_classification_2026_09_19/data/perspective_api_labeled_26k_twitter_dataset.csv`. Build two lookups:

- `source_row_id` (the CSV row index as a string, `"0"` to `"25999"`) for `label_records`
- exact `text` for `label_one`

`probability` is `0.0` or `1.0` from `pred_label`. `binary_label` comes from that same value. `model_name` stays `Perspective API`. Tokens stay `None`. Cost stays `0.0`. Wrap the file lookup with the shared timer so `latency_ms` is still set.

If `label_one` cannot find a non-empty `pred_label` for that exact text, raise `MissingPerspectiveLabel`. Do not turn that into a live HTTP error.

If `_label_task` cannot find a non-empty `pred_label` for `task.source_row_id`, raise `MissingPerspectiveLabel`. The Step 6 runner must drop those tasks before the loop, so they are not deadletters.

```bash
cd experiments/moral_outrage_classification_2026_09_19
uv run python -c "from models.perspective_api import PerspectiveApiEngine; import pandas as pd; df=pd.read_csv('data/perspective_api_labeled_26k_twitter_dataset.csv'); engine=PerspectiveApiEngine(); rec=engine.label_one(df.loc[0].text); print(rec.model_name, rec.binary_label, rec.probability, rec.estimated_cost_usd, rec.latency_ms>=0)"
```

Expected: `Perspective API 0 0.0 0.0 True`

```bash
uv run python -c "from models.perspective_api import PerspectiveApiEngine, MissingPerspectiveLabel; engine=PerspectiveApiEngine()
try:
    engine.label_one('this string is not in the stored Perspective file')
except MissingPerspectiveLabel:
    print('missing')
"
```

Expected: `missing`

```bash
uv run python -c "from models.perspective_api import PerspectiveApiEngine; print('commentanalyzer' in open('models/perspective_api.py').read())"
```

Expected: `False`

## Addendum 2026-09-19: Bedrock source file

Issue 17 now says to create `BedrockEngine` by repurposing [bedrock_engine.py](https://github.com/METResearchGroup/mirrorView-task/blob/main/data_platform/generate_features/engines/bedrock_engine.py).

Read that file before you change `experiments/moral_outrage_classification_2026_09_19/models/bedrock.py`. Copy these pieces into the experiment module (same names when they fit, same behavior when they do not):

- `json_instruction_for_schema`
- `parse_json_object` (markdown fence strip, then `json.loads`, then `{` `}` slice)
- `converse_label` and `_converse_once` (8 attempts, 1.0s sleep, retry on `json.JSONDecodeError`, `ValueError`, `ValidationError`, and `ClientError`)
- `inferenceConfig` with `maxTokens=32` and `temperature=0.0`
- `BedrockContentFilterError` when the text contains `blocked by our content filters` or `stopReason` is `content_filtered` or `guardrail_intervened`
- A Pydantic output schema validated with `model_validate`

The output schema is a local model, not `FeatureSpec.llm_output_schema`:

```python
class MoralOutrageLabel(BaseModel):
    moral_outrage: bool
    probability: float | None = Field(default=None, ge=0.0, le=1.0)
```

System text is `BRADY_MORAL_OUTRAGE_INSTRUCTIONS` plus `json_instruction_for_schema(MoralOutrageLabel)`. User text is the post text.

Keep the public experiment shape:

- `BedrockEngine(model_id, converse=None)`
- `label_one(text) -> PredictionRecord`
- `label_records(tasks, output_dir)` through `shared/engine_loop.py`

Map a validated `MoralOutrageLabel` onto `PredictionRecord` the same way as before. `probability` may be `None`. `binary_label` then comes from `moral_outrage`. Tokens still come from Converse `usage`. Region stays `us-east-2`. Allowed model IDs stay the five locked IDs.

Do not copy these pieces:

- `FeatureSpec`, `FeatureRunConfig`, `build_bedrock_engine`, or `DEFAULT_BEDROCK_NOVA_MICRO`
- The news / opinion / neither word fallback inside `_payload_from_loose_text`
- Thread-pool batch labeling as a replacement for `engine_loop`
- Reading region from `BEDROCK_REGION` or from the environment
- Converse `toolConfig` or native structured-output tools (the original Step 4 text asked for those, this addendum replaces that)

A content-filter error is a failed row. The shared loop retries or deadletters it. Do not swap the model id.

```bash
cd experiments/moral_outrage_classification_2026_09_19
uv run python -c "from models.bedrock import BedrockEngine, MoralOutrageLabel, json_instruction_for_schema; print(MoralOutrageLabel(moral_outrage=True, probability=0.9).moral_outrage); print('JSON object' in json_instruction_for_schema(MoralOutrageLabel)); print(BedrockEngine('us.openai.gpt-5.6-luna').model_name)"
```

Expected:

```text
True
True
Bedrock:us.openai.gpt-5.6-luna
```

```bash
uv run python -c "from models.bedrock import BedrockEngine
try:
    BedrockEngine('amazon.nova-micro-v1:0')
    print('accepted')
except ValueError:
    print('rejected')
"
```

Expected: `rejected`

```bash
uv run python -c "print('toolConfig' in open('models/bedrock.py').read(), 'nova-micro' in open('models/bedrock.py').read().lower())"
```

Expected: `False False`
