# Step 4: Run five rounds and rank them

## Scope

- **Depends on:** Steps 1 to 3 complete. Step 3 must have passed its smoke command and produced a smoke `cost.json` with a cost note a human can accept. Do not start the 72-call study until that acceptance is recorded outside this repo (for example in the issue or PR thread).
- **Caller:** `PYTHONPATH=/workspace:/workspace/experiments/social_science_idea_generation_2026_10_21 uv run --project experiments/social_science_idea_generation_2026_10_21 python -m src.run_study` (blocked in this step; see [Commands](#commands)).
- **Task:** Implement `run_study` in `experiments/social_science_idea_generation_2026_10_21/src/run_study.py`. The function reads `inputs/brief.md`, runs five independent rounds, runs the seven-ballot vote on a sixth LangSmith thread, writes `study.json` and `RESULTS.md` locally, and uploads only those two files under the `runs/` S3 prefix. Do not launch the full study in this step.
- **Proposal mapping:** [proposal.md](../proposal.md) section **Steps**, subsection **Step 4: Run five rounds and rank them**; **Who speaks, and what each agent reads** (round isolation and ballot transcript rule); **Tracing** (`run_vote` sixth thread); **Storage** (single `study.json`, no duplicate round objects on S3); **Schema and key interfaces** (`VoteRecord`, `StudyResult`, ranking tie-break); **Expected results** (72 calls, six threads, `RESULTS.md` contents); **Decisions** item 5 (seven voters, synthesizer does not vote) and item 7 (stop until smoke cost is accepted).
- **Plan mapping:** [plan.md](../plan.md) Step 4 and **What "done" looks like** items 4 and 5.
- **Out of scope:** Running the 72-call study before smoke cost acceptance; pytest, `tests/`, or any `test_*.py`; re-implementing `run_round` or `estimate_full_run_cost`; editing `lib/load_env_vars.py`, repository `shared/`, root `pyproject.toml`; uploading per-round JSON or `vote.json`; committing `outputs/**/study.json` from a live run. Define `run_vote` in `src/run_study.py`.

## Implement-from-spec phases (skip test design)

Follow the phase order in the table. Skip phase 4, test design. The plan adds no pytest file. The check for this step is the import command, and the full study command stays blocked.

| Phase | Goal for this step | Gate |
| --- | --- | --- |
| 1 Scope | Caller is `run_study(brief_path, run_id)` and `python -m src.run_study`; file tree is only `src/run_study.py` plus optional `RESULTS.md` update after a later allowed run | Caller and out-of-scope listed |
| 2 Scaffold | Create `run_study.py` with imports, `run_study` stub, and `if __name__ == "__main__"` that would call `run_study` when run as a module | Imports resolve with the Step 4 verification command |
| 3 Contracts | Signature `run_study(brief_path: Path, run_id: str) -> StudyResult` matches [proposal.md](../proposal.md) **Schema and key interfaces** | Return type and fields match `StudyResult` in `workflow/schemas.py` |
| 4 Test design | **Skipped** | N/A |
| 5 Implement | Wire keys, tracing, five `run_round` calls, `run_vote`, token totals, local writes, S3 upload | **One commit** touching only `src/run_study.py` |
| 6 Done | Verification command prints `run_study`; full CLI documented and marked blocked | Pass criteria at end of this file |

## Files to inspect

- `/workspace/docs/plans/2026-10-21_social-science-idea-generation_d9ac12/proposal.md` (sections cited above)
- `/workspace/docs/plans/2026-10-21_social-science-idea-generation_d9ac12/plan.md`
- `experiments/social_science_idea_generation_2026_10_21/workflow/schemas.py` (`StudyResult`, `VoteRecord`, `RoundRecord`, `Ballot`, `CriterionScore`, `RevisedProposal`)
- `experiments/social_science_idea_generation_2026_10_21/workflow/constants.py` (`MODEL_ID`, `REASONING_EFFORT`, `S3_BUCKET`, `EXPERIMENT_NAME`)
- `experiments/social_science_idea_generation_2026_10_21/workflow/roles.py` (`ROLE_ORDER`)
- `experiments/social_science_idea_generation_2026_10_21/workflow/tracing.py` (`configure_tracing`)
- `experiments/social_science_idea_generation_2026_10_21/src/run_round.py` (`run_round`, `revised_proposal`)
- `experiments/social_science_idea_generation_2026_10_21/src/run_smoke.py` (S3 key shape and `run_id` pattern from Step 3)
- `experiments/social_science_idea_generation_2026_10_21/inputs/brief.md`
- `experiments/social_science_idea_generation_2026_10_21/RESULTS.md` (stub from Step 1; leave unchanged until an allowed full run)
- `/workspace/lib/load_env_vars.py` (`EnvVarsContainer.get_env_var`, allowlist rows from Step 2)
- `/workspace/shared/aws/s3.py` (`S3.upload_file`)
- `/workspace/shared/aws/constants.py` (`DEFAULT_REGION_NAME`, `us-east-2`)

## Files allowed to change

- `experiments/social_science_idea_generation_2026_10_21/src/run_study.py` (required deliverable)
- `experiments/social_science_idea_generation_2026_10_21/RESULTS.md` **only** when a human has accepted the smoke cost and someone runs the blocked CLI later; not as part of the Step 4 verification commit

## Files forbidden to change

- `experiments/social_science_idea_generation_2026_10_21/src/run_round.py` except if Step 3 left a bug that blocks import (fix in a separate step; do not re-implement round logic here)
- `lib/load_env_vars.py`, anything under `/workspace/shared/` except reading APIs, root `pyproject.toml`
- Any pytest file, `tests/`, or `test_*.py`
- Plan or proposal markdown under `docs/plans/`
- Git-tracking `outputs/**/*.json` from a live run

## Work

### 1. `run_study(brief_path, run_id) -> StudyResult`

1. **Keys (before any model call):**
   `openai_key = EnvVarsContainer.get_env_var("OPENAI_API_KEY", required=True)`
   `langsmith_key = EnvVarsContainer.get_env_var("LANGSMITH_API_KEY", required=True)`
   Do not print either value. Do not log secret material.

2. **Tracing:** Call `configure_tracing(langsmith_key)` before the first `run_round` or `run_vote` model call ([proposal.md](../proposal.md) **Tracing**).

3. **Brief:** Read `brief_path` as UTF-8 text. Compute `brief_sha256` the same way `run_round` does (reuse the helper from Step 3 if one exists; otherwise match the hash already stored on `RoundRecord.brief_sha256` from smoke).

4. **Model handle:** Build one shared `ChatOpenAI` via `build_chat_model(openai_key)` and pass it into each `run_round` if Step 3's signature requires it; if `run_round` loads the model internally, follow the existing signature from `src/run_round.py` without duplicating round logic.

5. **Five rounds:** For `round_index` in `1..5`, call `run_round(round_index, brief, run_id)` (adjust argument order to match Step 3).
   - Round `i` is seeded by `ROLE_ORDER[i - 1]` inside `run_round` ([proposal.md](../proposal.md) **Who speaks**).
   - Each round is 13 model calls on its own LangSmith thread ([proposal.md](../proposal.md) **Expected results**).
   - Later rounds do not receive earlier rounds' ideas; they only share the brief ([proposal.md](../proposal.md) **Who speaks**).
   - Collect `list[RoundRecord]` in order. If a round stops after a parse retry failure inside `run_turn`, do not synthesize a missing proposal in `run_study` ([proposal.md](../proposal.md) **Schema and key interfaces**, parse failure paragraph).

6. **Vote:** Define `run_vote(rounds, run_id) -> VoteRecord` in `src/run_study.py` and call it from `run_study`. The vote uses a sixth `langsmith.uuid7` thread ([proposal.md](../proposal.md) **Tracing**, **Step 4**).
   **Voters (seven ballots):** the five disciplinary roles, the methodologist, and the critic. The synthesizer does not vote ([proposal.md](../proposal.md) **Decisions** item 5).
   **Ballot input:** the brief and the five **revised** proposals only; no round transcripts ([proposal.md](../proposal.md) table row **Ballot**).
   **Scores:** each ballot returns five `CriterionScore` rows with `non_obvious`, `feasible`, and `method_fits_question` as integers 1 to 5. Kind for the model call is `ballot`. Store `input_tokens`, `output_tokens`, and `reasoning_tokens` on the `Ballot` (0 when usage omits reasoning).
   **Per-proposal total on one ballot:** sum of the three scores, computed in Python inside `run_vote`, not requested from the model ([proposal.md](../proposal.md) **Schema and key interfaces** `Ballot` row).
   **Ranking:** sort round indexes by mean score total across ballots, higher first. Tie-break: higher mean `feasible`, then lower `round_index` ([proposal.md](../proposal.md) **Schema and key interfaces**).
   **`top_three`:** first three entries of `ranking`.
   `run_study` calls `run_vote`. Ballot prompts and ranking live only in `run_vote`.

7. **Token totals:** Set `total_input_tokens` and `total_output_tokens` on `StudyResult` to the sum of `input_tokens` and `output_tokens` across every `TurnRecord` in all five rounds plus every `Ballot` in `vote`. Do not add `reasoning_tokens` into `output_tokens`. Billed output already includes reasoning.

8. **Assemble `StudyResult`:**
   `run_id`, `model_id` (`MODEL_ID`), `reasoning_effort` (`REASONING_EFFORT`), `brief_sha256`, `rounds`, `vote`, `total_input_tokens`, `total_output_tokens`.

9. **Local write (when the blocked CLI runs):** Under gitignored `outputs/` (same convention as Step 3), write `outputs/runs/<run_id>/study.json` as JSON serialization of `StudyResult` (Pydantic `model_dump_json` or equivalent). `study.json` must embed full `rounds` and `vote`. Do **not** write `outputs/runs/<run_id>/round_*.json` or `vote.json`.

10. **`RESULTS.md` (when the blocked CLI runs):** Replace the Step 1 stub with a short report that:
    - Lists the **top three** revised proposals in `vote.top_three` order, including enough fields from each `RevisedProposal` (title, question, and method summary) that a reader can compare ideas without opening JSON.
    - States each round's mean ballot total or rank if helpful, but the authoritative order is `vote.ranking`.
    - Lists **every** round's `thread_id` from `RoundRecord` (rounds 1 to 5) so LangSmith links are recoverable.
    - Does not paste API keys or full turn transcripts.

11. **S3 upload (when the blocked CLI runs):** Use `S3(S3_BUCKET, region_name=DEFAULT_REGION_NAME)` from `shared.aws.s3` and `upload_file` for exactly two objects ([proposal.md](../proposal.md) **Storage**, **S3** tree):
    - `experiments/social_science_idea_generation_2026_10_21/runs/<run_id>/study.json`
    - `experiments/social_science_idea_generation_2026_10_21/runs/<run_id>/RESULTS.md`
    Do not upload duplicate per-round keys under `runs/` (smoke already uses `smoke/<run_id>/round.json`).

### 2. Module entrypoint

`if __name__ == "__main__":` should allocate or accept a `run_id` (match Step 3 style), default `brief_path` to `inputs/brief.md` relative to the experiment root, call `run_study`, and exit 0 on success. This block runs only when a human executes the blocked command after smoke cost acceptance.

### 3. Import style

`src` is a package because Step 3 adds an empty `src/__init__.py`. Import the round driver with `from src.run_round import run_round, revised_proposal`. Define `run_vote` in `src/run_study.py`. Do not import `run_vote` from `run_round`.

## Interfaces (must match proposal)

| Piece | Contract |
| --- | --- |
| `run_study` | `(brief_path: Path, run_id: str) -> StudyResult` |
| Round calls | 5 times `run_round`; 13 turns each; 65 round model calls total |
| Vote | `run_vote(rounds, run_id) -> VoteRecord`; 7 ballots; 1 sixth thread |
| `VoteRecord.ranking` | Round indexes, best mean total first; tie: mean `feasible`, then lower `round_index` |
| `VoteRecord.top_three` | First three indexes in `ranking` |
| `StudyResult` | Fields per proposal table; persisted as single `study.json` |
| S3 | Bucket `mind-technology-lab-experiments`; prefix `experiments/social_science_idea_generation_2026_10_21/runs/<run_id>/` |

## Commands

### Verification for Step 4 (run now; no model; no S3)

```bash
PYTHONPATH=/workspace:/workspace/experiments/social_science_idea_generation_2026_10_21 uv run --project experiments/social_science_idea_generation_2026_10_21 python -c "from src.run_study import run_study; print(run_study.__name__)"
```

**Expected stdout (exactly one line):**

```text
run_study
```

**Expected:** exit code 0. No OpenAI call. No LangSmith trace. No S3 upload. `RESULTS.md` remains the Step 1 stub.

### Blocked: full study (out of scope until smoke cost is accepted)

Do **not** run this command in Step 4. Run it only after a person accepts the smoke cost note from Step 3 ([proposal.md](../proposal.md) **Decisions** item 7).

```bash
PYTHONPATH=/workspace:/workspace/experiments/social_science_idea_generation_2026_10_21 uv run --project experiments/social_science_idea_generation_2026_10_21 python -m src.run_study
```

**Expected when later allowed:**

- Exit code 0
- 72 model calls (65 round + 7 ballot)
- 6 LangSmith threads (5 rounds + 1 vote)
- `study.json` and `RESULTS.md` under local `outputs/runs/<run_id>/` and the same two keys on S3 under `runs/<run_id>/`
- No secret values printed to stdout or stderr
- No per-round or standalone `vote.json` uploads under `runs/`

## Pass and fail

| Pass | Fail |
| --- | --- |
| Verification command prints `run_study` with exit 0 | Running the blocked 72-call command during Step 4 |
| `run_study.py` calls `run_round` and defines `run_vote` in this file | Adding pytest or `tests/` |
| Vote rules match proposal (seven voters, three criteria, totals in code, ranking tie-break) | Printing `OPENAI_API_KEY` or `LANGSMITH_API_KEY` |
| Blocked command documented and explicitly out of scope until cost acceptance | Uploading a second copy of each round JSON to `runs/` |
| Single git commit for `src/run_study.py` only | Committing `study.json` from a live run |

## Commit

- **One commit** on the feature branch containing only `experiments/social_science_idea_generation_2026_10_21/src/run_study.py`.
- Message suggestion: `feat(social-science-ideas): add run_study driver for five rounds and vote`
- Do not commit artifacts under `outputs/`.

## Done when

1. `src/run_study.py` implements `run_study` and the module entrypoint as specified.
2. The verification command passes with no model usage.
3. The blocked full-run command is written in this file and was not executed in Step 4.
4. A reviewer can trace vote and ranking rules to [proposal.md](../proposal.md) **Decisions** item 5 and **Schema and key interfaces**.
5. No new test files exist.
