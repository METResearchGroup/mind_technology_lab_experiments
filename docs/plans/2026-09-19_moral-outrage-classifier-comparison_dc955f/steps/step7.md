# Step 7: Write the root comparison and upload to S3

Fill the root RESULTS file from the per-model `results.json` files. Add the Jev versus Perspective histograms and difference summary. Upload the experiment tree to S3. Notify the user.

## Scope

- **Caller:** `experiments/moral_outrage_classification_2026_09_19/scripts/write_root_results.py` then `scripts/upload_s3.py`.
- **Task:** Root tables, calibration plots, S3 mirror, user notice.
- **Out of scope:** Re-scoring, changing engines, changing the sample, new metrics beyond plan decision 11.

## Files

### Inspect

- `outputs/jev/results.json` and `outputs/jev/labels.parquet`
- `outputs/perspective_api/results.json` and `outputs/perspective_api/labels.parquet`
- `outputs/bedrock/*/results.json`
- `shared/metrics.py` (`paired_difference_summary`)
- `/workspace/AGENTS.md` (bucket `mind-technology-lab-experiments`, prefix = local folder path)

### Allowed to change

- `experiments/moral_outrage_classification_2026_09_19/RESULTS.md`
- `experiments/moral_outrage_classification_2026_09_19/scripts/write_root_results.py` (create)
- `experiments/moral_outrage_classification_2026_09_19/scripts/upload_s3.py` (create)
- `experiments/moral_outrage_classification_2026_09_19/outputs/comparison/jev_hist.png`
- `experiments/moral_outrage_classification_2026_09_19/outputs/comparison/perspective_hist.png`
- `experiments/moral_outrage_classification_2026_09_19/outputs/comparison/difference_hist.png`
- `experiments/moral_outrage_classification_2026_09_19/outputs/comparison/difference_summary.json`
- `experiments/moral_outrage_classification_2026_09_19/tests/test_write_root_results.py`

### Forbidden to change

- Per-model `labels.parquet` contents
- Sample file
- Engine code unless a one-line path bug blocks reading outputs
- Extra calibration methods (ECE, Brier, reliability diagrams)

## Root RESULTS contract

`RESULTS.md` must contain, in this order:

1. One sentence: scores are on the 1,000-row stratified sample (560 gold 0, 440 gold 1), seed `20260919`.
2. **Quality table:** rows = seven model names from Step 5; columns = F1, accuracy, precision, recall.
3. **Latency table:** same rows; columns = p50, p90, p99 (milliseconds).
4. **Cost table:** same rows; columns = total tokens, estimated cost USD (Perspective `0`; Jev `unknown` if still no public price).
5. **Calibration:** two bar histograms (Jev probabilities, Perspective probabilities) and one histogram of Jev minus Perspective on paired `source_row_id`s. Report mean, median, standard deviation, and interquartile range of that difference. Pair only rows that have a probability from both scorers. State how many rows were dropped for a missing probability.
6. Deadletter counts per model.
7. A one-line pointer to `SETUP.md` for region, secrets, and model ids.

If a Bedrock model has `probability` null on every row, keep it in tables 2 to 4 and omit it from calibration (calibration is Jev vs Perspective only).

## S3 upload contract

- Bucket: `mind-technology-lab-experiments`
- Prefix: `experiments/moral_outrage_classification_2026_09_19/`
- Region: `us-east-2`
- Upload the experiment tree except `.venv/`, `__pycache__/`, and `data/26k_training_data.csv`.
- Do upload `data/sample_1000.parquet`, `data/sample_1000.manifest.json`, `outputs/`, `RESULTS.md`, `README.md`, `SETUP.md`, and source.
- Use the same AWS key resolution as Step 2.

After upload, print:

```text
UPLOAD COMPLETE s3://mind-technology-lab-experiments/experiments/moral_outrage_classification_2026_09_19/
```

Then notify the user in the agent reply that the run is finished and point at local `RESULTS.md` and that S3 URI.

## Implement-from-spec phases

### Phase 1. Scope

Caller = `write_root_results` then `upload_tree`.

### Phase 2. Scaffold

Scripts with stubs.

### Phase 3. Contracts

Table order and S3 prefix above.

### Phase 4. Test design

1. **Given** fixture `results.json` files for all seven models **when** `write_root_results` **then** `RESULTS.md` contains the three tables and the four difference numbers.
2. **Given** Jev and Perspective labels that share three `source_row_id`s **when** pairing **then** the difference list has length 3.
3. **Given** one id present only in Jev **when** pairing **then** that id is counted in `n_dropped`.
4. Upload helper: unit-test the key-prefix mapping (`local outputs/jev/results.json` → `experiments/moral_outrage_classification_2026_09_19/outputs/jev/results.json`) with a fake S3 client. Do not require live S3 for pytest.

### Phase 5. Implement units of work (order)

1. Pair Jev/Perspective probabilities + difference summary.
2. Markdown tables from `results.json`.
3. Three PNG histograms.
4. Write `RESULTS.md`.
5. S3 upload with fake-client tests, then live upload.

### Phase 6

Fixture tests green. Live upload listed. User notified.

## Commands

From `experiments/moral_outrage_classification_2026_09_19/`:

```bash
uv run pytest tests/test_write_root_results.py -q
```

Expected: all pass.

```bash
uv run python scripts/write_root_results.py
```

Expected: `RESULTS.md` updated; three PNGs under `outputs/comparison/`; `difference_summary.json` has `mean`, `median`, `std`, `iqr`, `n_paired`, `n_dropped`.

```bash
uv run python scripts/upload_s3.py
```

Expected: `UPLOAD COMPLETE s3://mind-technology-lab-experiments/experiments/moral_outrage_classification_2026_09_19/`

```bash
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-$AWS_ACCESS_KEY_SECRET}"
python3 -c "import boto3; c=boto3.client('s3', region_name='us-east-2'); print(c.head_object(Bucket='mind-technology-lab-experiments', Key='experiments/moral_outrage_classification_2026_09_19/RESULTS.md')['ContentLength']>0)"
```

Expected: `True`

## Pass / fail

### Must pass

- [ ] Root RESULTS has quality, latency, cost, and the four difference stats.
- [ ] Calibration uses Jev and Perspective only.
- [ ] S3 prefix matches the local folder path.
- [ ] Full 26k CSV is not uploaded.
- [ ] User is told the run is finished.

### Must fail / must not happen

- [ ] Re-running engines to "refresh" numbers without a new approval.
- [ ] Adding TOXICITY or extra calibration methods.
- [ ] Uploading `.venv` or secret files.

## Done when

Root RESULTS is filled, the tree is on S3 at the named prefix, and the user has been notified. The plan package's implementation work ends here.
