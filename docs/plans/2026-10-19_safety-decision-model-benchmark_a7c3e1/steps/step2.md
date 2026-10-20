# Step 2: Confirm one template per dataset

## Scope

- **Caller:** The implementer authoring committed JSON question specs that `experiments/safety_decision_models_2026_10_19/scripts/smoke.py` (step 3) and `scripts/run_score.py` (steps 4 and 6) load via `data/templates/{dataset}.json`. Downstream code reads `QuestionSpec` and `template_version` from those files only.
- **Task:** For each of the eleven core datasets, confirm one template on twenty development examples, write `experiments/safety_decision_models_2026_10_19/data/templates/{dataset}.json`, and archive any prior confirmed version before edits. Templates contain question wording only, never Hugging Face row text.
- **Out of scope:** New scripts (there is no `confirm_templates.py` in the approved tree). Live calls to Jev, Clef, Clef-flash, or Bedrock Guardrails. Smoke test execution (step 3). Harness check on full splits (step 4). Changes to dataset loaders, scorers, cache, `run_score.py`, configs, or docs. pytest, a `tests/` directory, or any file outside `data/templates/`. Reading AWS Secrets Manager or other credentials.

Proposal mapping: section 4 (Templates, the request cache, and limits; question spec in Scorers), section 5 (`data/templates/` tree), section 10 step 2.

## Files to inspect

- `/workspace/docs/plans/2026-10-19_safety-decision-model-benchmark_a7c3e1/proposal.md` (sections 4 and 5; core datasets table in section 3 for non-overlapping wording)
- `/workspace/docs/plans/2026-10-19_safety-decision-model-benchmark_a7c3e1/plan.md` (Step 2, dependencies, inputs table)
- `/workspace/docs/plans/2026-10-19_safety-decision-model-benchmark_a7c3e1/steps/step1.md` (`QuestionSpec`, `template_version`, loader list)
- `/workspace/docs/plans/2026-10-19_safety-decision-model-benchmark_a7c3e1/steps/step3.md` (how smoke loads templates)
- `experiments/safety_decision_models_2026_10_19/shared/records.py` (`QuestionSpec` type; read only)
- `experiments/safety_decision_models_2026_10_19/datasets/*.py` (development split rules; read only)
- Public harness (not vendored): https://github.com/AppliedMachineLearning-Lab/jev-benchmarking
  - `jev_benchmarking/tasks/base.py` (`choice`, `noul`, `score` JSON shape)
  - `jev_benchmarking/tasks/safety.py` (`ToxiGen`, `OpenAIModeration`, `ToxicChat`, `PromptInjections` `build` methods)
  - `jev_benchmarking/tasks/classification.py` (`GoEmotions`, `Emotion` `build` methods)

## Files allowed to change

Create or edit only these paths (eleven active templates plus archives):

- `experiments/safety_decision_models_2026_10_19/data/templates/toxigen.json`
- `experiments/safety_decision_models_2026_10_19/data/templates/openai_moderation.json`
- `experiments/safety_decision_models_2026_10_19/data/templates/toxicchat.json`
- `experiments/safety_decision_models_2026_10_19/data/templates/prompt_injections.json`
- `experiments/safety_decision_models_2026_10_19/data/templates/wildguardmix.json`
- `experiments/safety_decision_models_2026_10_19/data/templates/do_not_answer.json`
- `experiments/safety_decision_models_2026_10_19/data/templates/xstest.json`
- `experiments/safety_decision_models_2026_10_19/data/templates/harmbench.json`
- `experiments/safety_decision_models_2026_10_19/data/templates/jailbreakbench.json`
- `experiments/safety_decision_models_2026_10_19/data/templates/go_emotions.json`
- `experiments/safety_decision_models_2026_10_19/data/templates/emotion.json`
- `experiments/safety_decision_models_2026_10_19/data/templates/archive/{dataset}/{template_version}.json` (copy of the previous file before any edit to a confirmed template)

`{dataset}` in archive paths uses the same short names as the filenames above (without `.json`).

## Files forbidden to change

- Everything under `experiments/safety_decision_models_2026_10_19/` except the paths listed in Files allowed to change
- `experiments/safety_decision_models_2026_10_19/datasets/`, `scorers/`, `shared/`, `scripts/`, `configs/`, `policies/`, `cache/`, `outputs/`, `README.md`, `SETUP.md`, `RESULTS.md`, `pyproject.toml`, `.gitignore`
- `/workspace/pyproject.toml`, `/workspace/uv.lock`, CI workflows, plan and proposal files
- Any `tests/` directory or `test_*.py` under the experiment folder
- Committed files that contain Do-Not-Answer question text or copied evaluation row text

## Work

1. **Depends on step 1.** Dataset loaders and `QuestionSpec` types must exist before this step. Do not modify them here.

2. **Development pool (twenty items per dataset).** Use the same development rows step 3 will smoke test. Load via step 1 loaders, then take twenty stable rows:
   - **ToxiGen, ToxicChat, prompt injections:** Hugging Face split `train` (harness `dev`).
   - **GoEmotions, Emotion:** split `validation` (harness `dev`).
   - **OpenAI Moderation:** no harness `dev` split. Hold out twenty percent of rows with a stable hash of `example_id` (same rule as proposal section 4). Use that holdout only to read wording context; step 4 scores all 1,680 rows at threshold 0.5.
   - **Do-Not-Answer, XSTest (deduped prompts), JailbreakBench, WildGuardMix, HarmBench:** no named dev split. Hold out twenty percent with the same hash of `example_id` rule.
   - **Selection within the dev pool:** sort by `example_id` ascending and take the first twenty rows so reruns pick the same items.

3. **Confirm wording.** For each dataset, read twenty development `text` values alongside the template instructions. Placeholders in instructions must match the state field names the scorer passes (for example `` `text` ``, `` `prompt` ``, `` `comment` ``) as in the harness `build` methods. Adjust instructions until they are final for the study. This step does not call providers; confirmation is manual review against development rows.

4. **Six overlapping harness datasets.** Start from the harness `build` question dicts (copy instruction strings and criteria structure, not row values):
   - `toxigen`: heads `toxic` (Noul) and `toxicity` (Score with five levels from `ToxiGen.levels` in `safety.py`).
   - `openai_moderation`: eight Nouls keyed `S`, `H`, `V`, `HR`, `SH`, `S3`, `H2`, `V2` with the same `instructions` objects as `OpenAIModeration.build`.
   - `toxicchat`: heads `toxic` and `jailbreak`.
   - `prompt_injections`: head `answer` (single Noul).
   - `go_emotions`: twenty-eight Nouls keyed by label id (see `GoEmotions.build` in `classification.py`).
   - `emotion`: head `answer` (Choice over six labels).

5. **Five study-only datasets.** Wording follows proposal section 3 (no harness `build` to copy):
   - `wildguardmix`: two Nouls aligned with `prompt_harm_label` and the adversarial flag.
   - `do_not_answer`: one Noul for whether a safeguard should refuse the question (scoring instructions only). Never paste the 939 dataset questions into git.
   - `xstest`: one Noul on whether `prompt_type` is `prompt_harmful` (after prompt dedupe in the loader).
   - `harmbench`: one Noul for whether the text is a request for harm (both `DirectRequest` and `HumanJailbreaks` configs share this template).
   - `jailbreakbench`: one Noul on the goal text (harmful and benign splits share this template).

6. **On-disk JSON shape.** Each `{dataset}.json` file is one JSON object: keys are question head ids; values are harness-shaped dicts with `type` (`noul`, `choice`, or `score`), `instructions` (string or structured object as in the harness), and `criteria` (option map, score levels list, or null). This object is the `QuestionSpec` passed to `DecisionScorer.score`. Do not wrap dataset rows, gold labels, or example ids in the file.

7. **Template version.** `template_version` is the lowercase hex SHA-256 digest of the template file bytes on disk (UTF-8 JSON as saved). The cache key in step 1 uses this value with arm, model version, and `example_id`; this step does not write `cache/responses.db`.

8. **Archive before edit.** When changing a template that was already confirmed, copy the current file to `data/templates/archive/{dataset}/{template_version}.json` using the hash of the file being replaced, then edit `{dataset}.json`. Keep archives in git.

9. **Do-Not-Answer rule.** The loader may read question text into gitignored `data/records/` or `data/snapshots/`. The committed `do_not_answer.json` holds only the refusal Noul spec. Risk area and type of harm stay on `ExampleRecord.metadata`, not in the template file.

10. **No new automation.** Do not add `scripts/confirm_templates.py` or any other script in this step. Verification uses the Commands below only.

## Interfaces

**QuestionSpec** (committed in each `data/templates/{dataset}.json`)

| Piece | Contract |
| --- | --- |
| Top level | JSON object: question head id to question dict |
| Per-question fields | `type`, `instructions`, `criteria` (optional) matching `jev_benchmarking/tasks/base.py` helpers |
| Kinds | Choice (`type: choice`), Noul (`type: noul`), Score (`type: score`) |
| Excluded | Row `text`, gold labels, `example_id`, Hugging Face fields, Do-Not-Answer question bodies |

**template_version**

| Piece | Contract |
| --- | --- |
| Definition | `hashlib.sha256(path.read_bytes()).hexdigest()` for the template file path |
| Use | Recorded on each `PredictionRecord` and in the run manifest; part of cache key `hash(arm, model_version, template_version, example_id)` |
| This step | Compute and print versions; do not write the cache |

**Clef / Jev consumption (read only here)**

Scorers merge `ExampleRecord.text` into `state` and attach the template object as `questions` keyed by head id (see step 1 Clef body example). Guardrails in later steps ignore question text but still record `template_version` from the same file.

## Commands

Working directory:

```text
cd /workspace/experiments/safety_decision_models_2026_10_19
```

List template files (expect eleven):

```bash
ls -1 data/templates/*.json | wc -l
```

Expected: prints `11`.

Print `template_version` per dataset file (no new script; inline Python):

```bash
uv run python - <<'PY'
import hashlib
from pathlib import Path

root = Path("data/templates")
names = [
    "toxigen",
    "openai_moderation",
    "toxicchat",
    "prompt_injections",
    "wildguardmix",
    "do_not_answer",
    "xstest",
    "harmbench",
    "jailbreakbench",
    "go_emotions",
    "emotion",
]
for name in names:
    path = root / f"{name}.json"
    if not path.is_file():
        raise SystemExit(f"missing template: {path}")
    version = hashlib.sha256(path.read_bytes()).hexdigest()
    print(f"{name}\t{version}")
print("count", len(names))
PY
```

Expected: eleven lines `name` plus tab plus 64-character hex hash, then `count 11`.

Check that no template embeds development row text (loads twenty dev rows per dataset; fails if any row `text` appears as a substring in the matching template file):

```bash
uv run python - <<'PY'
from pathlib import Path

# Import loaders after step 1; adjust only if step 1 exposes a shared dev_rows(dataset, n=20) helper.
from datasets import toxigen, openai_moderation, toxicchat, prompt_injections, wildguardmix
from datasets import do_not_answer, xstest, harmbench, jailbreakbench, go_emotions, emotion

LOADERS = {
    "toxigen": toxigen,
    "openai_moderation": openai_moderation,
    "toxicchat": toxicchat,
    "prompt_injections": prompt_injections,
    "wildguardmix": wildguardmix,
    "do_not_answer": do_not_answer,
    "xstest": xstest,
    "harmbench": harmbench,
    "jailbreakbench": jailbreakbench,
    "go_emotions": go_emotions,
    "emotion": emotion,
}

def dev_rows(module, limit=20):
    if hasattr(module, "load_development_records"):
        rows = module.load_development_records(limit=limit)
    elif hasattr(module, "load_dev_records"):
        rows = module.load_dev_records(limit=limit)
    else:
        raise SystemExit(f"no dev loader on {module.__name__}")
    return rows[:limit]

root = Path("data/templates")
for name, mod in LOADERS.items():
    body = (root / f"{name}.json").read_text(encoding="utf-8")
    for row in dev_rows(mod):
        snippet = row.text.strip()
        if len(snippet) >= 40 and snippet in body:
            raise SystemExit(f"template {name}.json contains dev text from {row.example_id}")
print("no_row_text_in_templates")
PY
```

Expected: prints `no_row_text_in_templates`. If step 1 names the development helper differently, call that helper but keep the same twenty-row pool and substring rule.

Optional JSON validity:

```bash
uv run python -m json.tool data/templates/toxigen.json > /dev/null
```

Expected: exit code 0 for each template file.

## Smoke check

Not run in this step. Step 3 implements and runs `experiments/safety_decision_models_2026_10_19/scripts/smoke.py` on twenty development items per arm (`jev`, `clef`, `clef-flash`, and `guardrails` after step 5). This step passes when eleven template files exist, versions print as above, and templates contain no copied row text.

## Cost and credentials

No paid API usage. Do not read `jev-typesafe-api-key`, `cloudflare-workers-ai`, `hf-token`, or lab AWS keys for this step. Local `uv run` may import dataset modules; if a loader needs `hf-token` to draw development rows, that read is optional verification only and is not required to commit templates.

Model and Guardrails spend for this step: **US$0**.

## Done when

1. Exactly eleven files exist under `experiments/safety_decision_models_2026_10_19/data/templates/` with the short names listed in Work.
2. Each file is a confirmed `QuestionSpec` (question heads only). Six overlapping datasets match harness `build` wording from `safety.py` and `classification.py`. Five others match proposal section 3 task definitions.
3. Wording was checked against twenty development items per dataset using the development split rules in Work item 2.
4. `do_not_answer.json` contains scoring instructions only. No committed template or archive file contains Do-Not-Answer question text or other copied dataset row text.
5. Any superseded template was copied to `data/templates/archive/{dataset}/{template_version}.json` before edit.
6. The hash command prints eleven distinct `template_version` values (one per dataset file).
7. No files outside `data/templates/` were changed. No new scripts, tests, or scorer or loader edits.

Ready for step 3 to load these templates in `scripts/smoke.py`.
