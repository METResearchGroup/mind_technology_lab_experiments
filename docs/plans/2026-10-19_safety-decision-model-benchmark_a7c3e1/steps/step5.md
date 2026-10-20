# Step 5: Create guardrail and publish crosswalk

The implementer creates one numbered Amazon Bedrock guardrail in `us-east-2`, publishes the dataset-label-to-filter crosswalk in committed config, records the guardrail version id in the run manifest, and confirms the guardrails arm on the 20-item smoke set. This step does not score the core pack.

## Scope

- **Depends on:** Step 1 (`experiments/safety_decision_models_2026_10_19/scorers/guardrails.py` and shared record types). Step 4 (Jev harness check) must finish successfully before any live guardrail create call.
- **Task:** Fix the crosswalk in `configs/study.json` before step 6 test scores exist. Create the guardrail resource. Wire the version id into the manifest (and into the scorer only if needed). Re-run guardrails smoke on 20 development items so every row has a non-empty band.
- **Out of scope:** Core-pack scoring (`scripts/run_score.py`), metrics, figures, S3 upload, editing templates or dataset loaders, harness-check numbers from step 4 (do not use them to choose crosswalk cells), Do-Not-Answer question text (not involved in this step), pytest or any `tests/` directory.

**Integrity rule (proposal RQ4 and Decisions made item 1):** The crosswalk is written from dataset label semantics only. It is committed before the first full-pack test number. It does not use step 4 harness-check metrics. After commit, crosswalk cells do not change for that study.

## Files to inspect

- `/workspace/docs/plans/2026-10-19_safety-decision-model-benchmark_a7c3e1/proposal.md` (section 4 scorers, section 6 RQ4, Decisions made item 1, section 10 step 5)
- `/workspace/docs/plans/2026-10-19_safety-decision-model-benchmark_a7c3e1/plan.md` (Step 5 and dependency table)
- `/workspace/experiments/safety_decision_models_2026_10_19/scorers/guardrails.py` (from step 1)
- `/workspace/experiments/safety_decision_models_2026_10_19/shared/records.py` (`PredictionRecord`, `ExampleRecord`)
- `/workspace/experiments/safety_decision_models_2026_10_19/configs/study.json` (pins, prices, region; add `crosswalk` here)
- `/workspace/experiments/safety_decision_models_2026_10_19/scripts/smoke.py` (`--arm guardrails`)
- `/workspace/experiments/safety_decision_models_2026_10_19/SETUP.md` (AWS and region)
- `/workspace/experiments/speedup_jev_2026_09_23/shared/secrets.py` (lab AWS key resolution pattern)
- AWS Bedrock Guardrails API docs for `CreateGuardrail`, `CreateGuardrailVersion`, and `ApplyGuardrail` in `us-east-2`

## Files allowed to change

- `experiments/safety_decision_models_2026_10_19/configs/study.json` (add committed `crosswalk` object; may add guardrail metadata fields that are not secrets)
- `experiments/safety_decision_models_2026_10_19/scorers/guardrails.py` only if required to read the guardrail version id from config or manifest at score time
- `experiments/safety_decision_models_2026_10_19/outputs/manifests/{run_id}.json` (gitignored; write `guardrail_version_id` or equivalent key for the numbered version)

## Files forbidden to change

- Anything under `experiments/safety_decision_models_2026_10_19/datasets/`
- Anything under `experiments/safety_decision_models_2026_10_19/data/templates/`
- `experiments/safety_decision_models_2026_10_19/scorers/jev.py`
- `experiments/safety_decision_models_2026_10_19/scorers/clef.py`
- `tests/` anywhere in the repo for this study (no pytest files)
- Step 4 harness-check content in `RESULTS.md` (read-only for this step)

## Work

1. **Publish the crosswalk first (commit before create).** Under `experiments/safety_decision_models_2026_10_19/configs/study.json`, add a top-level `crosswalk` key. Do not invent a new config directory; the approved tree is `configs/study.json` only.

   The crosswalk maps each **dataset label** (harm taxonomy label on the row, not the arm name) to zero or more of the six Bedrock content filters:

   - `Hate`
   - `Insults`
   - `Sexual`
   - `Violence`
   - `Misconduct`
   - `Prompt Attack`

   Authoring rules from RQ4:

   - Sexual and hate labels map to obvious filters (`Sexual`, `Hate`).
   - Harassment maps only partly to `Insults` (document the choice in a short comment inside the JSON or in `SETUP.md` if needed; do not tune cells using step 4 numbers).
   - **Self-harm** has no Bedrock filter. Its crosswalk entry is an empty list and stays unmapped on purpose.
   - Prompt-injection and jailbreak-style labels may map to `Prompt Attack` where the dataset semantics match; violence and misconduct labels map when semantics match.
   - GoEmotions and Emotion labels are emotions, not harm taxonomy. Map only if the study defines explicit harm-related subsets; otherwise use empty lists or a documented `emotion` section that does not pretend filters match emotion names.

   Suggested JSON shape (values are illustrative; implementer fills rows from dataset cards, not from test metrics):

   ```json
   {
     "crosswalk": {
       "openai_moderation": {
         "sexual": ["Sexual"],
         "hate": ["Hate"],
         "harassment": ["Insults"],
         "self-harm": [],
         "violence": ["Violence"],
         "illicit": ["Misconduct"]
       },
       "toxigen": { },
       "default": []
     }
   }
   ```

   Commit `study.json` with `crosswalk` before calling Bedrock to create the guardrail.

2. **Create the guardrail (after step 4 passes).** In `us-east-2`, create one guardrail with exactly six content filters (the names above), each enabled for input. Set filter action to **`NONE`** (detect-only; no automatic block from the filter config). Create a **numbered guardrail version** and capture its version identifier (ARN or id string Bedrock returns).

   **Detect-only call pattern (Decisions made item 1):** At scoring time, one `ApplyGuardrail` call per example with `source` `INPUT`, filter action `NONE`, and the published guardrail version id. Do not rely on three separate Apply calls for low, medium, and high unless the fallback in this step applies.

   **Strength is applied after the call** to the returned confidence band (`NONE`, `LOW`, `MEDIUM`, `HIGH`):

   | Strength | Bands treated as blocked |
   | --- | --- |
   | low | `HIGH` only |
   | medium | `HIGH`, `MEDIUM` |
   | high | `HIGH`, `MEDIUM`, `LOW` |

   `NONE` is never blocked at any strength. Rank order for analysis: `NONE` < `LOW` < `MEDIUM` < `HIGH`. The rank is a rank, not a probability.

   **Fallback (three numbered versions):** Create three numbered guardrail versions only if a probe `ApplyGuardrail` detect response **omits** the band field the scorer needs. If detect mode returns bands on one call, keep a single version and derive low, medium, and high block decisions in code from that one response.

3. **Record the version id.** Write the chosen guardrail **version** id into `experiments/safety_decision_models_2026_10_19/outputs/manifests/{run_id}.json` for the smoke or study run id in use (same manifest pattern as step 1). Include region `us-east-2`. If `scorers/guardrails.py` must read the version id at runtime, load it from `study.json` or the manifest without committing secrets.

4. **Do not start step 6.** No writes to `outputs/predictions/` for the full core pack in this step.

## Interfaces

`DecisionScorer` for arm `guardrails` (`scorers/guardrails.py`):

- Input: `list[ExampleRecord]`, `QuestionSpec` (guardrails scoring uses prompt text from the example; it does not use Noul wording for the Bedrock call itself).
- Output: `list[PredictionRecord]` with:
  - `arm`: `"guardrails"`
  - `probability`: **`null`** (bands are not probabilities)
  - `band`: one of **`NONE`**, **`LOW`**, **`MEDIUM`**, **`HIGH`** (non-empty string on success; use the band the scorer defines from `ApplyGuardrail` output, typically the maximum relevant band across filters listed in `crosswalk` for that row's label, or the global max across enabled filters if the study fixes that rule in code)
  - `model_version`: guardrail version id string
  - `raw_response`: parsed `ApplyGuardrail` payload (no secrets)
  - `billed_units`: text units when the API reports them (smoke may be zero or omitted until step 6 billing matters)

Blocking for RQ4 miss rate and false-positive rate is computed in metrics (step 7) by applying the strength table to `band`, not by storing three probabilities.

## Commands

From the experiment root:

```bash
cd /workspace/experiments/safety_decision_models_2026_10_19
```

After `crosswalk` is committed and the guardrail version exists:

```bash
uv run python scripts/smoke.py --arm guardrails
```

Optional probe before smoke (implementer script or one-off AWS CLI) to confirm detect mode returns a band on one development string. If bands are missing, follow the three-version fallback before smoke.

Do not run `scripts/run_score.py` on the core pack in this step.

Do not run pytest.

## Smoke check

Re-run guardrails smoke **after** the guardrail resource and numbered version exist:

```bash
cd /workspace/experiments/safety_decision_models_2026_10_19 && uv run python scripts/smoke.py --arm guardrails
```

**Pass criteria (same as proposal section 4 smoke):**

- Exactly **20** development items scored end to end for arm `guardrails`.
- Every returned `PredictionRecord` has **`band` non-empty** (`NONE`, `LOW`, `MEDIUM`, or `HIGH`).
- Every returned row has **`probability` null**.
- No empty band list and no missing band on any row.
- A second immediate run with the same items should hit `cache/responses.db` (cache behavior is validated in step 3 for all arms; guardrails must participate after this step).

**Fail:** Stop if any band is empty, if the scorer writes a probability for guardrails, or if `ApplyGuardrail` errors persist after retries.

## Cost and credentials

**Credentials (region `us-east-2` only for Bedrock in this step):**

- `LAB_AWS_ACCESS_KEY_ID` and `LAB_AWS_ACCESS_KEY_SECRET` (with standard AWS env fallbacks per existing lab scripts)
- IAM permissions: `bedrock:ApplyGuardrail` and permission to **create** a guardrail and version in `us-east-2`

**Not used in this step:** TypeSafe API key, `hf-token`, Cloudflare Workers AI secret, or any Jev or Clef credentials.

**Cost:**

- **Creating** the guardrail and a numbered version is not billed as Guardrails **text units**. Treat create as a one-time control-plane operation with negligible or zero per-text-unit metering in the study budget.
- **Per-call** Guardrails pricing is **US$0.15 per 1,000 text units** on `ApplyGuardrail`. That charge applies in this step's guardrails smoke re-run (up to 20 text units) and in **step 6** (full core pack), not to the guardrail create API itself.

## Done when

1. `experiments/safety_decision_models_2026_10_19/configs/study.json` contains a committed `crosswalk` keyed by dataset labels, with self-harm explicitly unmapped (empty filter list), and the crosswalk was not derived from step 4 harness-check numbers.
2. A numbered Bedrock guardrail exists in `us-east-2` with the six filters, filter action `NONE`, and detect-only `ApplyGuardrail` documented in the scorer.
3. Low, medium, and high block rules are implemented as post-call band logic, unless three numbered versions were required because detect mode omitted the band.
4. `outputs/manifests/{run_id}.json` records the guardrail **version** id (and region).
5. `uv run python scripts/smoke.py --arm guardrails` on 20 items completes with non-empty `band` on every row and `probability` null throughout.
6. Step 6 has not been started; no full-pack prediction files were written in this step.
