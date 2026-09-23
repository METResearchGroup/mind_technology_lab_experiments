# Step 3: Build the batched Jev engine

Build the engine that sends one request per batch of posts, the shared rate limiter, and the threaded batch loop with retries, skip-already-scored, and deadletter handling.

## Files to inspect

- `/workspace/experiments/moral_outrage_classification_2026_09_19/shared/engine_loop.py` (retry, skip-seen, deadletter pattern)
- `/workspace/experiments/moral_outrage_classification_2026_09_19/models/jev.py`
- `/workspace/experiments/speedup_jev_2026_09_23/.venv/lib/python*/site-packages/typesafe_sdk/` (client signature, `RetryPolicy`, exception classes)

## Files allowed to change

- `/workspace/experiments/speedup_jev_2026_09_23/shared/records.py`
- `/workspace/experiments/speedup_jev_2026_09_23/shared/rate_limiter.py`
- `/workspace/experiments/speedup_jev_2026_09_23/shared/batch_runner.py`
- `/workspace/experiments/speedup_jev_2026_09_23/models/batched_jev.py`

## Files forbidden to change

- Anything under `/workspace/experiments/moral_outrage_classification_2026_09_19/`
- The plan files under `/workspace/docs/plans/2026-09-23_speedup-jev-batching_d84619/`

## Contracts

`shared/records.py` holds three pydantic models.

- `PostTask`: `source_row_id: str`, `text: str`, `gold_label: int`.
- `PostPrediction`: `source_row_id`, `text`, `gold_label`, `batch_size: int`, `request_index: int`, `position_in_request: int`, `n_posts_in_request: int`, `probability: float`, `binary_label: int`, `request_latency_ms: float`, `per_post_latency_ms: float`, `request_input_tokens: int`, `request_output_tokens: int`, `model_version: str`, `attempts: int`.
- `RequestLog`: `batch_size`, `request_index`, `n_posts_in_request`, `request_latency_ms`, `input_tokens`, `output_tokens`, `estimated_cost_usd`, `model_version`, `attempts`.

`models/batched_jev.py`:

- `JEV_MODEL_ID = "jev-1.13.0"`, `REQUEST_TIMEOUT_SECONDS = 30.0`.
- `build_state(texts: list[str]) -> dict[str, list[str]]` returns `{"posts": texts}`.
- `build_questions(n_posts: int) -> dict[str, Noul]` returns one Noul per post with id `post_{i}` and instructions ``"Does `posts[i]` express moral outrage? " + BRADY_MORAL_OUTRAGE_DEFINITION``, where `i` is the zero-based list index written as a digit.
- `BatchResult` holds `probabilities: list[float]`, `latency_ms: float`, `input_tokens: int`, `output_tokens: int`, `model_version: str`.
- `score_batch(client, texts: list[str]) -> BatchResult` sends one `system_one` call timed with `shared/timer.py` and raises `MissingAnswerError` when any `post_{i}` is absent from the answers.
- `build_client(api_key: str) -> TypeSafeClient` sets `retry=RetryPolicy(max_retries=0)` and the timeout.

`shared/rate_limiter.py`:

- `RequestStartLimiter(max_starts_per_minute: int)` with `wait() -> None`. It is thread safe and blocks until starting one more request keeps the count in any 60 second window at or below the cap. `MAX_REQUEST_STARTS_PER_MINUTE = 1000`.

`shared/batch_runner.py`:

- `WORKER_THREADS = 8`, `MAX_EXTRA_ATTEMPTS = 3`, `BACKOFF_SECONDS = (1.0, 2.0, 4.0)`.
- `make_batches(tasks: list[PostTask], batch_size: int) -> list[list[PostTask]]` cuts tasks in `int(source_row_id)` order into consecutive groups.
- `run_pass(tasks, batch_size, output_dir, scorer) -> PassSummary`, where `scorer` is a callable that takes a list of texts and returns a `BatchResult`. It does the following.
  - Skips posts already listed in `output_dir/predictions.jsonl`.
  - Submits one job per batch to a `ThreadPoolExecutor(WORKER_THREADS)`. Each job calls `limiter.wait()` before each attempt, then the scorer.
  - Retries up to `MAX_EXTRA_ATTEMPTS` times with the backoff above. `TypeSafeAuthenticationError` and `TypeSafePermissionDeniedError` stop the pass.
  - Appends predictions to `predictions.jsonl` and one line per request to `requests.jsonl` from the main thread as jobs finish.
  - Appends failed posts to `deadletter.jsonl` with `source_row_id`, `request_index`, `error`, and `attempts`.
  - Appends one line to `runs.jsonl` with `batch_size`, `started_at`, `wall_time_seconds`, `n_requests`, `n_scored`, and `n_deadletter`.
- The live scorer holds one `TypeSafeClient` per thread, stored in `threading.local()`.

## Must pass

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && uv run python -c "from models.batched_jev import build_questions; q = build_questions(3); print(sorted(q)); print(q['post_2'].instructions[:40])"
```

Expected output:

```text
['post_0', 'post_1', 'post_2']
Does `posts[2]` express moral outrage? M
```

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && uv run python -c "from shared.batch_runner import make_batches; from shared.records import PostTask; t=[PostTask(source_row_id=str(i), text='x', gold_label=0) for i in range(1000)]; print([len(make_batches(t, n)) for n in (1, 5, 10, 20, 30, 40)], len(make_batches(t, 30)[-1]))"
```

Expected output: `[1000, 200, 100, 50, 34, 25] 10`

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && uv run python -c "import time; from shared.rate_limiter import RequestStartLimiter; l=RequestStartLimiter(3); s=time.monotonic(); [l.wait() for _ in range(3)]; print(round(time.monotonic()-s) == 0)"
```

Expected output: `True`

## Must fail

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && uv run python -c "from models.batched_jev import score_batch; from types import SimpleNamespace as N; c=N(system_one=lambda **k: N(model='jev-1.13.0', answers={'post_0': N(noul=0.9)}, usage=N(input_tokens=1, output_tokens=0))); score_batch(c, ['a', 'b'])"
```

Expected: exits non-zero with `MissingAnswerError` naming `post_1`.
