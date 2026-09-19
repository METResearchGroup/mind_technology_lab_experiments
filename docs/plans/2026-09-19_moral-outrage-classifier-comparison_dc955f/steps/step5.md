# Step 5: Run smoke tests and publish the cost table

Classify three fixed texts on Jev, Perspective, and each of the five Bedrock models. Write the cost and latency table. Stop. Do not start the 1,000-row jobs.

## Scope

- **Caller:** You run the three smoke modules from a shell. The human reads `RESULTS.md` and approves or stops.
- **Task:** Live calls on three texts only; write the smoke table; halt.
- **Out of scope:** Reading `data/sample_1000.parquet` for scoring, S3 upload of the full tree, root comparison plots.

## Files

### Inspect

- `experiments/moral_outrage_classification_2026_09_19/models/jev.py`
- `experiments/moral_outrage_classification_2026_09_19/models/perspective_api.py`
- `experiments/moral_outrage_classification_2026_09_19/models/bedrock.py`
- `experiments/moral_outrage_classification_2026_09_19/RESULTS.md`
- `experiments/moral_outrage_classification_2026_09_19/SETUP.md`
- AWS Bedrock on-demand token prices for `us-east-2` (document URL and date in SETUP)

### Allowed to change

- `experiments/moral_outrage_classification_2026_09_19/models/smoke_tests/texts.py` (create; the three strings)
- `experiments/moral_outrage_classification_2026_09_19/models/smoke_tests/jev.py`
- `experiments/moral_outrage_classification_2026_09_19/models/smoke_tests/perspective_api.py`
- `experiments/moral_outrage_classification_2026_09_19/models/smoke_tests/bedrock.py`
- `experiments/moral_outrage_classification_2026_09_19/shared/pricing.py` (hardcode published prices)
- `experiments/moral_outrage_classification_2026_09_19/RESULTS.md` (smoke table only)
- `experiments/moral_outrage_classification_2026_09_19/SETUP.md` (price URL and date)
- `experiments/moral_outrage_classification_2026_09_19/outputs/smoke/` (runtime table JSON, gitignored)

### Forbidden to change

- Sample parquet contents
- Starting Step 6 runners
- Perspective attribute (must stay `MORAL_OUTRAGE`)
- Brady instruction string
- Root CI / workspace members

## Contracts

### Smoke texts (exact)

```python
SMOKE_TEXTS = [
    "They cheated those families on purpose and they should be punished.",
    "The cafe opens at nine and the coffee is fine.",
    "I cannot believe a public official would lie to voters like that and walk away.",
]
```

Gold labels are not required for smoke. Do not replace these strings.

### Table columns (exact, issue 17)

| Column | Rule |
| --- | --- |
| model name | `Jev`, `Perspective API`, or `Bedrock:{model id}` |
| total tokens | `sum(input_tokens) + sum(output_tokens)` across the three texts; `0` or blank for Perspective |
| estimated cost | USD, 6 decimal places. Perspective is `0`. TypeSafe: if no public price exists, write `unknown` and a footnote, do not invent a number |
| estimated runtime | median `latency_ms` of the three calls, shown in milliseconds |

Seven rows, in this order:

1. `Jev`
2. `Perspective API`
3. `Bedrock:us.openai.gpt-5.6-luna`
4. `Bedrock:us.openai.gpt-5.6-terra`
5. `Bedrock:us.anthropic.claude-sonnet-5`
6. `Bedrock:qwen.qwen3-32b-v1:0`
7. `Bedrock:deepseek.v3-v1:0`

### Pricing

Hardcode Bedrock USD per million input/output tokens from the public AWS price page for `us-east-2`. Write the page URL and the calendar date you copied the numbers into `SETUP.md`. Do not scrape prices at runtime.

### Stop rule

After the table is in `RESULTS.md`, print:

```text
SMOKE COMPLETE. Waiting for approval before the 1000-row jobs.
```

Exit 0. Do not call `label_records` on the sample.

## Implement-from-spec phases

### Phase 1. Scope

Caller = `uv run python -m models.smoke_tests.jev` (and the other two modules), or one `uv run python -m models.smoke_tests` that runs all seven rows.

### Phase 2. Scaffold

Smoke modules import engines and `SMOKE_TEXTS`. Stub `main()` if needed.

### Phase 3. Contracts

Table schema and stop message above.

### Phase 4. Test design

1. **Given** three fake records **when** `build_smoke_table` **then** columns and row order match the contract.
2. **Given** Perspective records **then** estimated cost is `0`.
3. **Given** a smoke `main` **then** it does not import `write_sample_if_missing` or read `sample_1000.parquet`.

Live smoke is manual, not CI.

### Phase 5. Implement units of work (order)

1. `SMOKE_TEXTS` + table builder from records.
2. Jev smoke `main`.
3. Perspective smoke `main`.
4. Bedrock smoke `main` looping the five ids.
5. Write markdown table into `RESULTS.md` under heading `Smoke`.
6. Print the stop line.

### Phase 6

Table present. Stop line printed. Sample file unread by smoke.

## Commands

From `experiments/moral_outrage_classification_2026_09_19/`:

```bash
uv run pytest tests/test_smoke_table.py -q
```

Expected: table-builder tests pass (create `tests/test_smoke_table.py`).

```bash
uv run python -m models.smoke_tests
```

Expected: seven live rows; `RESULTS.md` contains a markdown table with those rows; last stdout line is `SMOKE COMPLETE. Waiting for approval before the 1000-row jobs.`; process exit code 0.

If Perspective rejects `MORAL_OUTRAGE`, the process must exit non-zero with `MoralOutrageAttributeRejected` and no TOXICITY retry.

If a Bedrock id is not enabled on the account, the process must exit non-zero and name that id. Do not substitute another model.

## Pass / fail

### Must pass

- [ ] Three texts only, the exact strings above.
- [ ] Seven table rows in the stated order.
- [ ] Perspective cost `0`.
- [ ] Stop message printed.
- [ ] `sample_1000.parquet` is not opened by the smoke process (no `read_parquet` on that path).

### Must fail / must not happen

- [ ] Starting Jev/Perspective/Bedrock over the 1,000-row sample.
- [ ] Uploading to the experiment S3 prefix in this step (optional upload of the smoke table is allowed only if you already have a helper; default is local `RESULTS.md` only).
- [ ] Quietly skipping a Bedrock model.

## Done when

`RESULTS.md` has the smoke table and the process has stopped for approval. Step 6 does not begin until the user approves that table.
