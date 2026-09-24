# Step 2: Load the labeled CSV, draw the sample, and load credentials

Download the Brady CSV, confirm column names, write a 1,000-row stratified sample, and load the two API keys from Secrets Manager. Do not score any posts.

## Scope

- **Caller:** `experiments/moral_outrage_classification_2026_09_19/shared/data.py` functions used later by smoke (Step 5) and the sample jobs (Step 6). Credential helper used by every engine.
- **Task:** Download the CSV, validate the header and label counts, draw the sample once, write the sample to disk, and load secrets in `us-east-2`.
- **Out of scope:** Engines, metrics, smoke HTTP calls, Bedrock Converse, S3 upload of results.

## Files

### Inspect

- `experiments/moral_outrage_classification_2026_09_19/SETUP.md`
- `cookbooks/how_to_use_aws_secrets_manager/main.py` on `main` (`SECRET_NAME`, `SECRET_REGION = "us-east-2"`, JSON `SecretString`, field lookup). If the file is missing on this branch, `git show origin/main:cookbooks/how_to_use_aws_secrets_manager/main.py`.
- S3 object `s3://met-research-group-datasets/moral_outrage_classifier/26k_training_data.csv` (header already inspected: `text`, `outrage`, `tweet_id`, ...)
- `/workspace/AGENTS.md` lab AWS key names

### Allowed to change

- `experiments/moral_outrage_classification_2026_09_19/shared/aws_region.py` (create; constant only)
- `experiments/moral_outrage_classification_2026_09_19/shared/secrets.py` (create)
- `experiments/moral_outrage_classification_2026_09_19/shared/data.py` (create)
- `experiments/moral_outrage_classification_2026_09_19/tests/test_data.py` (create)
- `experiments/moral_outrage_classification_2026_09_19/tests/test_secrets.py` (create; no live secret values in asserts)
- `experiments/moral_outrage_classification_2026_09_19/SETUP.md` (add the locked column names and sample path after discovery)
- `experiments/moral_outrage_classification_2026_09_19/data/` (runtime files, gitignored)

### Forbidden to change

- Root `pyproject.toml` workspace members
- Engine modules (still absent)
- `shared/timer.py` (Step 3)
- Anything under `outputs/`
- Secret values in git, README, SETUP, tests, or logs

## Contracts

### Region

```python
AWS_REGION = "us-east-2"
```

Every boto3 client in this experiment passes `region_name=AWS_REGION`. Do not read `AWS_REGION` / `AWS_DEFAULT_REGION` from the environment to choose the region.

### Dataset columns (locked from the live object)

| Role | CSV column | Notes |
| --- | --- | --- |
| Text | `text` | 26,000 non-empty strings |
| Gold label | `outrage` | string `"0"` or `"1"` in the file; store as int `0` or `1` |
| Tweet id | `tweet_id` | metadata only; 1,160 empty, 27 duplicate ids |
| Row id | original data-row index | integer `0` .. `25999` in the downloaded file, stored as string |

Fail the loader if the file does not have exactly 26,000 data rows, 14,563 `outrage==0`, and 11,437 `outrage==1`.

### Sample

| Rule | Value |
| --- | --- |
| Size | 1,000 |
| Stratify on | `outrage` |
| Counts | 560 rows with `outrage==0`, 440 with `outrage==1` |
| RNG | `numpy.random.Generator` with seed `20260919` |
| Draw | once; if the sample file already exists with a matching manifest, reuse it |
| Path | `experiments/moral_outrage_classification_2026_09_19/data/sample_1000.parquet` |
| Manifest | `experiments/moral_outrage_classification_2026_09_19/data/sample_1000.manifest.json` |

Manifest JSON keys (exact):

- `source_uri`: `s3://met-research-group-datasets/moral_outrage_classifier/26k_training_data.csv`
- `seed`: `20260919`
- `n_rows`: `1000`
- `n_gold_0`: `560`
- `n_gold_1`: `440`
- `row_id_field`: `source_row_id`

Sample table columns (exact): `source_row_id`, `text`, `gold_label`, `tweet_id` (nullable string).

Sampling method: for each gold class, shuffle that class's rows with the same Generator and take the prefix of the required count. Concatenate 560 + 440. Sort the result by `source_row_id` so later diffs are stable. Do not use a library split helper that could change counts.

### Secrets

| Purpose | SecretId | JSON field | Env export |
| --- | --- | --- | --- |
| TypeSafe / Jev | `jev-typesafe-api-key` | `TYPESAFE_API_KEY` | `TYPESAFE_API_KEY` |
| Perspective | `google-api-key` | `GOOGLE_API_KEY` | `GOOGLE_API_KEY` |

Loader behavior (copy the cookbook shape):

1. Build a boto3 session with region `us-east-2`.
2. Resolve AWS keys: if `LAB_AWS_ACCESS_KEY_ID` and `LAB_AWS_ACCESS_KEY_SECRET` are non-empty, use them (`aws_access_key_id`, `aws_secret_access_key`). Else use `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`, and if `AWS_SECRET_ACCESS_KEY` is empty, use `AWS_ACCESS_KEY_SECRET`.
3. `get_secret_value(SecretId=...)`.
4. Parse `SecretString` as JSON. Read the named field. Raise `SystemExit` with the secret name (not the value) if missing.
5. Return the string. Never print it.

A tiny CLI `python -m shared.secrets` (or `scripts/check_secrets.py`) must print only `ok jev-typesafe-api-key` and `ok google-api-key` on success.

## Implement-from-spec phases

### Phase 1. Scope

Caller = `load_sample()` and `load_api_keys()` imported by later engines.

### Phase 2. Scaffold

Create `aws_region.py`, `data.py`, `secrets.py` with stub functions raising `NotImplementedError`.

### Phase 3. Contracts

Confirm the tables above. Stop if the live CSV header disagrees, and update SETUP with the confirmed names.

### Phase 4. Test design (failing)

In `tests/test_data.py` (no network):

1. **Given** a 10-row fixture with 6 zeros and 4 ones **when** stratified sample of 5 with seed `20260919` **then** counts are 3 zeros and 2 ones (same ratio rule: `round(5 * n_class / n)` then adjust so the total is 5; for the production 26k file the counts are hardcoded 560/440, so test the helper that takes explicit per-class counts).
2. **Given** two calls with the same seed and the same input **then** `source_row_id` lists are equal.
3. **Given** a fixture whose `outrage` counts are not 14563/11437 **when** `validate_full_frame` **then** raises.

In `tests/test_secrets.py`:

4. **Given** a fake Secrets Manager that returns `{"TYPESAFE_API_KEY":"abc"}` **when** load **then** returns `"abc"` and does not include `"abc"` in any log capture.
5. **Given** JSON missing the field **when** load **then** `SystemExit` and the message contains the secret name.

### Phase 5. Implement units of work (order)

1. `AWS_REGION` constant.
2. CSV download to `data/26k_training_data.csv` (gitignored) via boto3 `download_file`.
3. Parse + `source_row_id` + validate counts.
4. Stratified sample write + manifest.
5. Secrets loader + check CLI.

### Phase 6

Tests green. Live download and secret check succeed without printing key material.

## Commands

From `experiments/moral_outrage_classification_2026_09_19/` after `uv sync`:

```bash
uv run pytest tests/test_data.py tests/test_secrets.py -q
```

Expected: all pass.

```bash
uv run python -c "from shared.data import download_full_csv, load_full_frame, write_sample_if_missing; from shared.aws_region import AWS_REGION; print(AWS_REGION); p=download_full_csv(); df=load_full_frame(p); print(len(df), int((df.gold_label==0).sum()), int((df.gold_label==1).sum())); write_sample_if_missing(df)"
```

Expected stdout:

```text
us-east-2
26000 14563 11437
```

and file `data/sample_1000.parquet` with 1,000 rows.

```bash
uv run python -c "import pandas as pd; df=pd.read_parquet('data/sample_1000.parquet'); print(len(df), int((df.gold_label==0).sum()), int((df.gold_label==1).sum()))"
```

Expected: `1000 560 440`

```bash
uv run python -c "from shared.secrets import load_typesafe_api_key, load_google_api_key; a=load_typesafe_api_key(); b=load_google_api_key(); print('jev', len(a)>0); print('google', len(b)>0)"
```

Expected:

```text
jev True
google True
```

No key substring in the output.

## Pass / fail

### Must pass

- [ ] Full file validates 26000 / 14563 / 11437.
- [ ] Sample is 1000 / 560 / 440 and is identical on a second run with the same seed.
- [ ] `source_row_id` is unique in the sample.
- [ ] Both secrets load in `us-east-2`.
- [ ] SETUP names columns `text` and `outrage` and the sample path.

### Must fail / must not happen

- [ ] Scoring any row.
- [ ] Using `tweet_id` as the primary row id.
- [ ] Reading region from the environment.
- [ ] Printing or writing secret values.
- [ ] Drawing a new sample after the manifest exists (unless you delete it on purpose).

## Done when

The sample file and secret loader work. SETUP records the locked columns. Ready for Step 3 contracts on the prediction record and timer.

## Addendum 2026-09-19

Also download the stored Perspective labels. Do not write pytest files.

- URI: `s3://met-research-group-datasets/moral_outrage_classifier/perspective_api_labeled_26k_twitter_dataset.csv`
- Local path: `experiments/moral_outrage_classification_2026_09_19/data/perspective_api_labeled_26k_twitter_dataset.csv` (gitignored with the other data CSVs)
- Columns: `id`, `dataset`, `text`, `gold_label`, `pred_label`, `is_correct`, `model`
- 26,000 rows. `text` and `gold_label` match `26k_training_data.csv` in the same row order. `pred_label` is `0.0`, `1.0`, or empty (189 empty). `model` is `perspective_api`.
- Join later work to the Brady sample by `source_row_id` (original CSV row index `0` .. `25999`). Do not join on `id` (it is the tweet id, and 1,160 rows have none). Do not join on `text` for the sample job (511 texts repeat).

```bash
uv run python -c "from shared.data import DATA_DIR; from shared.aws_region import AWS_REGION; import boto3; from shared.secrets import resolve_aws_access_keys; aid, secret = resolve_aws_access_keys(); c=boto3.client('s3', region_name=AWS_REGION, aws_access_key_id=aid or None, aws_secret_access_key=secret or None); p=DATA_DIR/'perspective_api_labeled_26k_twitter_dataset.csv'; c.download_file('met-research-group-datasets','moral_outrage_classifier/perspective_api_labeled_26k_twitter_dataset.csv',str(p)); import pandas as pd; df=pd.read_csv(p); print(len(df), int(df.pred_label.isna().sum()), df.columns.tolist())"
```

Expected: `26000 189 ['id', 'dataset', 'text', 'gold_label', 'pred_label', 'is_correct', 'model']`

`GOOGLE_API_KEY` may still load for the secrets CLI. Perspective scoring must not use it.
