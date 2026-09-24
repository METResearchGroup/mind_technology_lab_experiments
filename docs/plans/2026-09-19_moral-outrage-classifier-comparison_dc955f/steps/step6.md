# Step 6: Run the 1,000-row sample in three parallel jobs after approval

Score the sample file with Jev, Perspective, and Bedrock after the user approves the smoke table. Write per-model labels, metrics, plots, and RESULTS files.

## Scope

- **Caller:** Three parallel processes (three subagents or three shells), one engine each. Bedrock's process loops the five model ids.
- **Task:** `label_records` on `data/sample_1000.parquet` → parquet, `results.json`, `static/` histograms, `RESULTS.md`, deadletter.
- **Out of scope:** Root RESULTS comparison (Step 7), S3 upload (Step 7), changing the sample, re-running smoke.

## Gate

Do not start this step unless the user has approved the Step 5 table in the same conversation or in an explicit follow-up. If approval is missing, stop and say so.

## Files

### Inspect

- `experiments/moral_outrage_classification_2026_09_19/data/sample_1000.parquet`
- `experiments/moral_outrage_classification_2026_09_19/data/sample_1000.manifest.json`
- Engine modules and `shared/engine_loop.py`
- `shared/metrics.py`
- Issue 17 output tree

### Allowed to change

- `experiments/moral_outrage_classification_2026_09_19/scripts/run_jev.py` (create)
- `experiments/moral_outrage_classification_2026_09_19/scripts/run_perspective_api.py` (create)
- `experiments/moral_outrage_classification_2026_09_19/scripts/run_bedrock.py` (create)
- `experiments/moral_outrage_classification_2026_09_19/outputs/jev/`
- `experiments/moral_outrage_classification_2026_09_19/outputs/perspective_api/`
- `experiments/moral_outrage_classification_2026_09_19/outputs/bedrock/us.openai.gpt-5.6-luna/`
- `experiments/moral_outrage_classification_2026_09_19/outputs/bedrock/us.openai.gpt-5.6-terra/`
- `experiments/moral_outrage_classification_2026_09_19/outputs/bedrock/us.anthropic.claude-sonnet-5/`
- `experiments/moral_outrage_classification_2026_09_19/outputs/bedrock/qwen.qwen3-32b-v1:0/` (if `:` is painful on disk, use `qwen.qwen3-32b-v1_0` and record the mapping in that folder's `RESULTS.md`; prefer the literal id when the OS allows it)
- `experiments/moral_outrage_classification_2026_09_19/outputs/bedrock/deepseek.v3-v1:0/` (same rule)
- `experiments/moral_outrage_classification_2026_09_19/tests/test_run_outputs.py` (shape tests on fixtures, not live)

### Forbidden to change

- `data/sample_1000.parquet` rows
- Smoke text constants
- Root `RESULTS.md` comparison section (Step 7)
- Root workspace / CI

## Output contract per model directory

Each model directory must contain:

| File | Contents |
| --- | --- |
| `labels.parquet` | One row per successfully scored sample row; columns match `PredictionRecord` |
| `results.json` | Keys `model_name`, `n_scored`, `n_deadletter`, `f1`, `accuracy`, `precision`, `recall`, `p50`, `p90`, `p99`, `total_input_tokens`, `total_output_tokens`, `estimated_cost_usd` |
| `static/score_hist.png` | Bar histogram of `probability` for rows that have one. Skip the file and say so in RESULTS if every `probability` is null |
| `RESULTS.md` | Short writeup: the `results.json` numbers in a table, path to the histogram, deadletter count |
| `deadletter.jsonl` | Present even if empty is optional; if missing, `n_deadletter` must be `0` and RESULTS must say no failures |

`n_scored + n_deadletter` must equal 1,000 for that model. If you stop a job early, do not write a final `results.json` that pretends the run finished.

## Runners

Each script:

1. Load `data/sample_1000.parquet`.
2. Refuse to run if the manifest counts are not 1000/560/440.
3. Call `label_records` with skip-seen so a restart continues.
4. Write `results.json` and `RESULTS.md` only after the loop ends.
5. Print `DONE {model_name} scored={n} deadletter={n}` on stdout.

Bedrock script takes no extra models. It runs the five model ids in sequence inside the one process (issue 17: one engine job, five models).

## Parallelism

Start the three scripts in three processes. Do not serialize Jev behind Perspective behind Bedrock. Perspective stays at ~1 QPS. Jev and Bedrock use their own retries and must not share a global lock.

## Implement-from-spec phases

### Phase 1. Scope

Caller = `uv run python scripts/run_jev.py` (and the two siblings).

### Phase 2. Scaffold

Scripts parse args (`--output-root` default `outputs/`) and call stub `run()`.

### Phase 3. Contracts

Directory layout and `results.json` keys above.

### Phase 4. Test design

1. **Given** a 4-row fake sample and a fake engine **when** runner finishes **then** `results.json` has the required keys and `n_scored + n_deadletter == 4`.
2. **Given** an existing labels parquet with 2 of 4 ids **when** runner runs **then** `label_one` is called twice.
3. **Given** manifest `n_rows != 1000` **when** runner starts **then** exit non-zero before any provider call.

### Phase 5. Implement units of work (order)

1. Shared `write_model_outputs(records, deadletters, output_dir)` helper.
2. Jev runner.
3. Perspective runner.
4. Bedrock runner (five ids).
5. Histogram writer.

### Phase 6

Fixture tests green. Live run only after approval.

## Commands

Start only after approval. From `experiments/moral_outrage_classification_2026_09_19/`:

```bash
uv run pytest tests/test_run_outputs.py -q
```

Expected: fixture tests pass.

```bash
uv run python scripts/run_jev.py &
uv run python scripts/run_perspective_api.py &
uv run python scripts/run_bedrock.py &
wait
```

Expected: three processes exit 0 (or a named provider error). Each model directory has `labels.parquet`, `results.json`, `RESULTS.md`.

```bash
uv run python -c "import pandas as pd; df=pd.read_parquet('outputs/jev/labels.parquet'); print(len(df))"
```

Expected: a number `<= 1000`. After a clean finish with no deadletter, `1000`.

## Pass / fail

### Must pass

- [ ] User approval recorded before live sample traffic.
- [ ] Three processes, not one process running all engines in series.
- [ ] Each finished model: `n_scored + n_deadletter == 1000`.
- [ ] Metrics use `shared/metrics.py`.
- [ ] Failed rows have `error` and `attempts` in deadletter.

### Must fail / must not happen

- [ ] Scoring rows outside the sample file.
- [ ] Drawing a new sample.
- [ ] Writing the root comparison (Step 7).
- [ ] Swapping a Bedrock id on failure.

## Done when

Every model directory for Jev, Perspective, and the five Bedrock ids has labels (or deadletter), metrics JSON, and a RESULTS file. Ready for Step 7 to build the root comparison and upload.

## Addendum 2026-09-19

Do not write pytest files. Do not redraw the sample.

The Perspective runner still reads `data/sample_1000.parquet` and still calls `PerspectiveApiEngine.label_records`. Before the loop, drop sample rows whose stored `pred_label` is empty. Join the labels file by `source_row_id`. Do not join by tweet `id` or by `text`.

For the current sample those dropped ids are `1990`, `6429`, `19057`, `19803`, `19853`, `19977`, and `22320`. That leaves 993 Perspective rows (554 gold 0 and 439 gold 1). They are missing labels, not deadletters.

`assert_run_complete` for Perspective must use `n_scored + n_deadletter == 1000 - n_missing_label`. After a clean file-backed run, `n_scored` is `993`, `n_missing_label` is `7`, and `n_deadletter` is `0`. Write `n_missing_label` in `outputs/perspective_api/results.json` and in that folder's `RESULTS.md`. Compute F1 and the other classification metrics on the 993 scored rows.

Jev and Bedrock still require smoke-table approval before any 1,000-row provider traffic. The Perspective job is a file lookup, and it still waits for that same approval so the three jobs stay together.

```bash
cd experiments/moral_outrage_classification_2026_09_19
uv run python -c "import pandas as pd; s=pd.read_parquet('data/sample_1000.parquet'); p=pd.read_csv('data/perspective_api_labeled_26k_twitter_dataset.csv'); p['source_row_id']=p.index.astype(str); s['source_row_id']=s['source_row_id'].astype(str); m=s.merge(p[['source_row_id','pred_label']], on='source_row_id', how='left'); print(int(m.pred_label.isna().sum()), sorted(m.loc[m.pred_label.isna(),'source_row_id'].astype(int).tolist()))"
```

Expected: `7 [1990, 6429, 19057, 19803, 19853, 19977, 22320]`

After the Perspective job:

```bash
uv run python -c "import json; from pathlib import Path; d=json.loads(Path('outputs/perspective_api/results.json').read_text()); print(d['n_scored'], d['n_missing_label'], d['n_deadletter'])"
```

Expected: `993 7 0`
