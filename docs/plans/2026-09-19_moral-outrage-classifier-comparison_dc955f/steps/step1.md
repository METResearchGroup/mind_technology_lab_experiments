# Step 1: Scaffold the experiment folder and documents

Create the standalone experiment tree, the user docs, a local dependency file, and the root lint excludes. Do not make live AWS calls, and do not add engines.

## Scope

- **Caller:** A later `python -m` / script entry under `experiments/moral_outrage_classification_2026_09_19/` (wired in Steps 4 to 6). Step 1 only makes the tree and docs so those callers have a home.
- **Task:** Folder, README, SETUP, RESULTS stub, `pyproject.toml`, empty package dirs, gitignore for tweet text, root ruff/pyright exclude.
- **Out of scope:** Downloading the CSV, Secrets Manager, engines, tests beyond "the folder exists", smoke, S3 upload.

## Files

### Inspect

- `/workspace/docs/plans/2026-09-19_moral-outrage-classifier-comparison_dc955f/plan.md`
- `/workspace/AGENTS.md` (S3 bucket, lab AWS key names, standalone vs `autoresearch/`)
- `/workspace/SETUP.md` (standalone experiments are not root-uv members)
- `/workspace/pyproject.toml` (`[tool.uv.workspace]`, `[tool.ruff] extend-exclude`, `[tool.pyright] exclude`)
- `/workspace/mech_interp_reddit/pyproject.toml` and `/workspace/mech_interp_reddit/README.md` (standalone install)
- `/workspace/.github/workflows/ci.yml` (root ruff/pyright/pytest; do not add the new folder to CI)
- [Issue 17](https://github.com/METResearchGroup/mind_technology_lab_experiments/issues/17) folder tree

### Allowed to change

- `experiments/moral_outrage_classification_2026_09_19/README.md` (create)
- `experiments/moral_outrage_classification_2026_09_19/SETUP.md` (create)
- `experiments/moral_outrage_classification_2026_09_19/RESULTS.md` (create stub)
- `experiments/moral_outrage_classification_2026_09_19/pyproject.toml` (create)
- `experiments/moral_outrage_classification_2026_09_19/.gitignore` (create)
- `experiments/moral_outrage_classification_2026_09_19/models/__init__.py` (create empty)
- `experiments/moral_outrage_classification_2026_09_19/models/smoke_tests/__init__.py` (create empty)
- `experiments/moral_outrage_classification_2026_09_19/shared/__init__.py` (create empty)
- `experiments/moral_outrage_classification_2026_09_19/data/.gitkeep` (create)
- `experiments/moral_outrage_classification_2026_09_19/outputs/.gitkeep` (create)
- `/workspace/pyproject.toml` (add the experiment path to ruff `extend-exclude` and pyright `exclude` only)

### Forbidden to change

- `/workspace/pyproject.toml` `[tool.uv.workspace] members` (must stay `["autoresearch/*"]`)
- `/workspace/uv.lock`
- `/workspace/.github/workflows/ci.yml`
- `/workspace/AGENTS.md`, `/workspace/SETUP.md`, `/workspace/README.md`
- Any file under `autoresearch/`, `mech_interp_reddit/`, `openai_rate_limit_scaling/`, `ai_agent_simulation_networks/`
- Engine modules (`jev.py`, `perspective_api.py`, `bedrock.py`, `timer.py`). Create parent dirs only.

## Work

1. Create this tree (empty `__init__.py` files where listed; no engine modules yet):

```text
experiments/moral_outrage_classification_2026_09_19/
  README.md
  SETUP.md
  RESULTS.md
  pyproject.toml
  .gitignore
  data/.gitkeep
  models/__init__.py
  models/smoke_tests/__init__.py
  outputs/.gitkeep
  shared/__init__.py
```

2. `README.md` must link [issue 17](https://github.com/METResearchGroup/mind_technology_lab_experiments/issues/17), `SETUP.md`, and `RESULTS.md`. State that scoring uses a 1,000-row stratified sample, not the full 26,000 rows. State that smoke runs on three texts and then waits for approval.

3. `SETUP.md` must list, in short sentences:
   - Dataset URI `s3://met-research-group-datasets/moral_outrage_classifier/26k_training_data.csv`
   - Sample rule: 1,000 rows, 560 gold 0 / 440 gold 1, seed locked in Step 2
   - Region constant `us-east-2`
   - Secret `jev-typesafe-api-key` JSON field `TYPESAFE_API_KEY`
   - Secret `google-api-key` JSON field `GOOGLE_API_KEY`
   - Lab keys `LAB_AWS_ACCESS_KEY_ID` and `LAB_AWS_ACCESS_KEY_SECRET`, with fallback `AWS_ACCESS_KEY_ID` plus `AWS_ACCESS_KEY_SECRET` mapped to `AWS_SECRET_ACCESS_KEY`
   - Bedrock model IDs `us.openai.gpt-5.6-luna`, `us.openai.gpt-5.6-terra`, `us.anthropic.claude-sonnet-5`, `qwen.qwen3-32b-v1:0`, `deepseek.v3-v1:0`
   - Output prefix `s3://mind-technology-lab-experiments/experiments/moral_outrage_classification_2026_09_19/`
   - Install: `cd experiments/moral_outrage_classification_2026_09_19 && uv sync` (local `.venv`, not the root workspace)

4. `RESULTS.md` stub: heading plus one sentence that smoke and sample tables are empty until Step 5 and Step 7.

5. `pyproject.toml`: package name `moral-outrage-classification`, `requires-python = ">=3.10"`, `package = false` or a src layout that does not install into the root workspace. Runtime deps may be declared now (boto3, pandas, pyarrow, pydantic, typesafe-sdk, requests, numpy, matplotlib, tqdm, pytest) or added when first imported. Prefer declaring them here so `uv sync` in this folder is enough.

6. `.gitignore` must ignore tweet text and run artifacts:

```text
.venv/
data/*.csv
data/*.parquet
data/*.json
!data/.gitkeep
outputs/**/*.parquet
outputs/**/*.json
outputs/**/deadletter.jsonl
__pycache__/
```

Keep `outputs/**/RESULTS.md` and `outputs/**/static/` un-ignored if you write them later; ignoring parquet/json is required.

7. In `/workspace/pyproject.toml`, append `"experiments/moral_outrage_classification_2026_09_19"` (or `moral_outrage_classification_2026_09_19` if the existing entries are repo-root folder names; match the `mech_interp_reddit` style) to both `tool.ruff.extend-exclude` and `tool.pyright.exclude`.

## Implement-from-spec phases

### Phase 1. Scope

Caller is later CLI/scripts in this folder. Task is tree + docs + exclude.

### Phase 2. Scaffold

Create the files listed. No loader or engine bodies.

### Phase 3. Contracts

SETUP is the contract for region, secret names, model IDs, sample size. Do not invent a second copy of those facts in code yet.

### Phase 4. Test design

No new pytest module required. Root `tests/test_scaffold.py` must still pass.

### Phase 5. Implement

Write the files. One commit for this step.

### Phase 6

Commands below pass.

## Pass / fail

### Must pass

- [ ] Every path in the tree exists.
- [ ] README links issue 17, SETUP, RESULTS.
- [ ] SETUP names both secret names, both JSON fields, `us-east-2`, the five Bedrock IDs, the sample rule, and both S3 URIs.
- [ ] `[tool.uv.workspace] members` is still `["autoresearch/*"]`.
- [ ] Root ruff/pyright exclude lists include the new folder.

```bash
test -f experiments/moral_outrage_classification_2026_09_19/README.md
test -f experiments/moral_outrage_classification_2026_09_19/SETUP.md
test -f experiments/moral_outrage_classification_2026_09_19/RESULTS.md
test -f experiments/moral_outrage_classification_2026_09_19/pyproject.toml
test -f experiments/moral_outrage_classification_2026_09_19/models/__init__.py
test -f experiments/moral_outrage_classification_2026_09_19/shared/__init__.py
grep -n 'moral_outrage_classification_2026_09_19' pyproject.toml
```

Expected: all `test` commands exit 0. `grep` prints at least one ruff `extend-exclude` line and one pyright `exclude` line.

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest -q
```

Expected: all green. The new folder is not type-checked by root pyright.

```bash
cd experiments/moral_outrage_classification_2026_09_19 && uv sync
```

Expected: exit 0, a `.venv` under the experiment folder (or uv's project environment for that `pyproject.toml`), not a change to `/workspace/uv.lock`.

### Must fail / must not happen

- [ ] Adding the folder to `[tool.uv.workspace] members`.
- [ ] Creating `models/jev.py` / `perspective_api.py` / `bedrock.py` in this step.
- [ ] Downloading the CSV or calling AWS.
- [ ] Committing tweet text.

## Done when

The experiment folder, docs, local dependency file, gitignore, and root excludes exist. Ready for Step 2 to download data and secrets into that tree.
