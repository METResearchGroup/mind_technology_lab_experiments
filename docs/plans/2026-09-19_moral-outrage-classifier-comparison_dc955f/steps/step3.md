# Step 3: Confirm the shared record, timer, and metrics

Confirm the prediction record, the request timer, thresholding, classification metrics, and latency percentiles. Tests first. No live provider calls.

## Scope

- **Caller:** Every engine in Step 4 writes one prediction record per scored row. Smoke (Step 5) and the sample jobs (Step 6) compute metrics from those records.
- **Task:** Pydantic (or equivalent) record, timer decorator, metric functions, failing-then-green unit tests.
- **Out of scope:** Jev / Perspective / Bedrock HTTP, sample download (already Step 2), plots (Step 6 and 7).

## Files

### Inspect

- [../plan.md](../plan.md) decisions 10 and 11
- Issue 17 metric list (F1, accuracy, precision, recall, p50/p90/p99)
- `experiments/moral_outrage_classification_2026_09_19/shared/data.py` (`source_row_id`, `gold_label`)

### Allowed to change

- `experiments/moral_outrage_classification_2026_09_19/shared/records.py` (create)
- `experiments/moral_outrage_classification_2026_09_19/shared/timer.py` (create)
- `experiments/moral_outrage_classification_2026_09_19/shared/metrics.py` (create)
- `experiments/moral_outrage_classification_2026_09_19/shared/brady_definition.py` (create; prompt text only)
- `experiments/moral_outrage_classification_2026_09_19/tests/test_records.py` (create)
- `experiments/moral_outrage_classification_2026_09_19/tests/test_timer.py` (create)
- `experiments/moral_outrage_classification_2026_09_19/tests/test_metrics.py` (create)

### Forbidden to change

- `shared/data.py` and `shared/secrets.py` behavior
- Engine modules (still Step 4)
- Root workspace members
- Live network in these tests

## Contracts

### Brady instruction string (shared)

Put this exact text in `brady_definition.py` as `BRADY_MORAL_OUTRAGE_INSTRUCTIONS`. Jev Noul `instructions` and every Bedrock system prompt must use this string unchanged:

```text
Does this post express moral outrage? Moral outrage means all three of the following: (1) feelings about a perceived moral violation, (2) anger or disgust or contempt, and (3) blame or a wish to punish.
```

### Prediction record fields (exact names)

| Field | Type | Rule |
| --- | --- | --- |
| `source_row_id` | `str` | From the sample table |
| `text` | `str` | Input text |
| `gold_label` | `int` | `0` or `1` |
| `model_name` | `str` | `Jev`, `Perspective API`, or `Bedrock:{model id}` |
| `probability` | `float \| None` | In `[0, 1]` when present. Missing only when the model emitted a hard label and no probability |
| `binary_label` | `int` | `1` if `probability >= 0.5`, else `0`. If `probability` is `None`, use the model's hard label `0` or `1` |
| `latency_ms` | `float` | Wall time of the remote call, milliseconds, `>= 0` |
| `input_tokens` | `int \| None` | Provider usage if known |
| `output_tokens` | `int \| None` | Provider usage if known |
| `estimated_cost_usd` | `float` | `0.0` for Perspective. Jev/Bedrock from the Step 5 price table |

`model_name` values for Bedrock must be exactly:

- `Bedrock:us.openai.gpt-5.6-luna`
- `Bedrock:us.openai.gpt-5.6-terra`
- `Bedrock:us.anthropic.claude-sonnet-5`
- `Bedrock:qwen.qwen3-32b-v1:0`
- `Bedrock:deepseek.v3-v1:0`

### Timer

`timer.py` exposes a decorator (issue 17) that wraps a function making one remote call.

- Start `time.perf_counter()` before the call, stop after success or after the exception leaves the wrapper.
- Store `latency_ms = (end - start) * 1000.0` on a return object or as the last item in a `(result, latency_ms)` tuple. Pick one shape and use it in every engine.
- The decorator must not catch exceptions. Failed calls still record latency if you attach it to the exception (`e.latency_ms = ...`) or return a deadletter path in Step 4. For this step, tests only need success-path latency and a re-raised exception.

### Metrics

Functions in `metrics.py`:

- `binary_label_from_probability(p: float) -> int` at threshold `0.5` (`>=` is positive).
- `classification_report(gold: list[int], pred: list[int]) -> dict` with keys `f1`, `accuracy`, `precision`, `recall` as floats. Use standard binary definitions with positive class `1`. Zero-division: precision or recall is `0.0` when the denominator is 0.
- `latency_percentiles(latency_ms: list[float]) -> dict` with keys `p50`, `p90`, `p99`. Use nearest-rank or NumPy `percentile` with `method="linear"`; document the choice in a one-line docstring and keep it for every model.
- `paired_difference_summary(jev: list[float], perspective: list[float]) -> dict` with keys `mean`, `median`, `std`, `iqr` of `jev[i] - perspective[i]` (same order, same `source_row_id` pairing done by the caller). `std` is sample std (`ddof=1`). `iqr` is the 75th percentile minus the 25th.

Do not add extra calibration stats.

## Implement-from-spec phases

### Phase 1. Scope

Caller = engine write of one record, then `classification_report` / `latency_percentiles`.

### Phase 2. Scaffold

Stub `PredictionRecord`, `timed`, and the four metric functions with `NotImplementedError`.

### Phase 3. Contracts

Signatures match the tables. User already approved the plan; do not wait again.

### Phase 4. Test design

1. **Given** `probability=0.5` **when** threshold **then** `binary_label==1`. **Given** `0.499` **then** `0`.
2. **Given** gold `[1,1,0,0]` and pred `[1,0,0,0]` **when** report **then** accuracy `0.75`, precision `1.0`, recall `0.5`, F1 `2/3`.
3. **Given** gold `[0,0]` and pred `[0,0]` **when** report **then** precision `0.0`, recall `0.0`, F1 `0.0`, accuracy `1.0`.
4. **Given** latencies `[10, 20, 30, 40, 50]` **when** percentiles **then** `p50` is the median of that list under the documented method; `p90` and `p99` are `>= p50`.
5. **Given** jev `[0.8, 0.2]` and perspective `[0.5, 0.4]` **when** difference summary **then** values are mean `0.05`, median `0.05`, and iqr/std computed from `[0.3, -0.2]`.
6. **Given** a function that sleeps ~20ms **when** decorated **then** `latency_ms >= 15` and the return value is unchanged.
7. **Given** a function that raises `ValueError` **when** decorated **then** `ValueError` propagates.
8. **Given** the Brady string constant **then** it contains `perceived moral violation`, `anger or disgust or contempt`, and `blame or a wish to punish`.

### Phase 5. Implement units of work (order)

1. Threshold helper + record validation.
2. Classification report.
3. Latency percentiles.
4. Paired difference summary.
5. Timer decorator.
6. Brady string module.

### Phase 6

All new tests green. No provider SDKs imported in these modules except types already in the experiment deps.

## Commands

```bash
cd experiments/moral_outrage_classification_2026_09_19
uv run pytest tests/test_records.py tests/test_timer.py tests/test_metrics.py -q
```

Expected: all pass.

## Pass / fail

### Must pass

- [ ] Record rejects `probability` outside `[0, 1]` when not `None`.
- [ ] Threshold, four metrics, percentiles, and Jev-minus-Perspective summary match the tests.
- [ ] Timer measures milliseconds and does not swallow exceptions.
- [ ] Brady string is a single shared constant.

### Must fail / must not happen

- [ ] Importing `typesafe_sdk` or Bedrock in these tests.
- [ ] A second copy of the Brady wording in an engine file in this step (engines do not exist yet).
- [ ] Extra calibration metrics (ECE, Brier, reliability diagrams).

## Done when

Shared record, timer, Brady text, and metrics are tested. Ready for Step 4 to implement engines against these types.

## Addendum 2026-09-19

Do not write pytest files. The old tests under `experiments/moral_outrage_classification_2026_09_19/tests/` are deleted. Check the shared record, timer, and metrics with live commands only.

```bash
cd experiments/moral_outrage_classification_2026_09_19
uv run python -c "from shared.metrics import binary_label_from_probability, classification_report, paired_difference_summary; print(binary_label_from_probability(0.5), binary_label_from_probability(0.499)); r=classification_report([1,1,0,0],[1,0,0,0]); print(r['accuracy'], r['precision'], r['recall'], r['f1']); d=paired_difference_summary([0.8,0.2],[0.5,0.4]); print(round(d['mean'],2), round(d['median'],2))"
```

Expected:

```text
1 0
0.75 1.0 0.5 0.6666666666666666
0.05 0.05
```

```bash
uv run python -c "from shared.records import PredictionRecord; from shared.brady_definition import BRADY_MORAL_OUTRAGE_INSTRUCTIONS; print(PredictionRecord.model_fields.keys()); print('perceived moral violation' in BRADY_MORAL_OUTRAGE_INSTRUCTIONS)"
```

Expected: the printed keys include `source_row_id`, `probability`, `binary_label`, and `latency_ms`. The second line is `True`.

```bash
uv run python -c "import time; from shared.timer import timed
@timed
def _sleep():
    time.sleep(0.02)
    return 7
value, latency_ms = _sleep()
print(value, latency_ms >= 15)"
```

Expected: `7 True`
