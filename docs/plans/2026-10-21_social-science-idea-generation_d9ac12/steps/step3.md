# Step 3: Run one round and estimate the cost of five rounds

## Scope

- **Depends on:** [steps/step1.md](step1.md) (experiment package, `workflow/schemas.py`, `workflow/roles.py`, `workflow/constants.py`, `inputs/brief.md`, `.gitignore` for `outputs/**/*.json`) and [steps/step2.md](step2.md) (`lib/load_env_vars.py` allowlist rows, `workflow/agents.py`, `workflow/tracing.py`, experiment `pyproject.toml` with pinned deps).
- **Task:** Implement proposal Step 3: one full discussion round (round 1 only), LangSmith threading, local JSON records, S3 upload under `smoke/`, and `estimate_full_run_cost` from the smoke `RoundRecord`. Stop before rounds 2 through 5 and before any vote.
- **Out of scope:** `src/run_study.py` (Step 4), `lib/load_env_vars.py` (Step 2), root `pyproject.toml`, changes under repository `shared/`, pytest, any `tests/` path, any `test_*.py`, `run_vote`, five-round execution, `study.json`, `RESULTS.md` content beyond existing stub.

**Proposal mapping:**

| Topic | Proposal section |
| --- | --- |
| Step 3 goal | [Steps, Step 3](../proposal.md#step-3-run-one-round-and-estimate-the-cost-of-five-rounds) |
| Stage order and Deep Agents per turn | [Cross-cutting, Python driver](../proposal.md#the-python-driver-keeps-the-stage-order) |
| Context per turn | [Who speaks, table](../proposal.md#who-speaks-and-what-each-agent-reads) |
| Tracing | [Tracing](../proposal.md#tracing) |
| Storage and S3 | [Storage](../proposal.md#storage), [S3 tree](../proposal.md#s3) |
| Cost formula and assumptions | [Expected results](../proposal.md#expected-results) |
| Interfaces | [Schema and key interfaces](../proposal.md#schema-and-key-interfaces) |
| Retry and tool failure | Same section, paragraph after `workflow/constants.py` block |
| Decision 7 (stop after smoke) | [Decisions](../proposal.md#decisions) |

Follow the phase order in the table in this file. Skip phase 4, test design. The check for this step is the smoke command, and the step adds no pytest file.

## Phase 1: Scope the unit of work

**Main caller:** `run_smoke` in `experiments/social_science_idea_generation_2026_10_21/src/run_smoke.py`, run as a module from the repository root.

**Happy path:** Load brief, configure tracing and keys, run round 1 (`run_round`), estimate cost (`estimate_full_run_cost`), write `outputs/smoke/<run_id>/round.json` and `cost.json`, upload both to S3, print `run_id` and `estimated_cost_usd`, exit 0.

**File tree (this step only):**

```text
experiments/social_science_idea_generation_2026_10_21/
  workflow/cost.py          new
  src/__init__.py           empty package marker, required for `python -m src.run_smoke`
  src/run_round.py          new
  src/run_smoke.py          new
```

**Unit of work:** Round driver, cost estimator, smoke entrypoint. **Not in this step:** vote, study runner, allowlist edits, agent builder changes unless a compile error forces a one-line import fix in an allowed file (prefer zero edits outside the tree above).

## Files to inspect

- [proposal.md](../proposal.md) (sections cited above)
- [plan.md](../plan.md) (Step 3 summary, smoke-as-check)
- `experiments/social_science_idea_generation_2026_10_21/workflow/schemas.py` (`TurnRecord`, `RoundRecord`, `TurnKind`, payload models)
- `experiments/social_science_idea_generation_2026_10_21/workflow/roles.py` (`RoleSpec`, `ROLE_ORDER`)
- `experiments/social_science_idea_generation_2026_10_21/workflow/constants.py` (`DISCUSSION_ITERATIONS`, price constants, `S3_BUCKET`, `EXPERIMENT_NAME`, `PRICE_PAGE_URL`)
- `experiments/social_science_idea_generation_2026_10_21/workflow/agents.py` (`build_chat_model`, `build_role_agent`)
- `experiments/social_science_idea_generation_2026_10_21/workflow/tracing.py` (`configure_tracing`)
- `lib/load_env_vars.py` (`EnvVarsContainer.get_env_var`, read-only in this step)
- `shared/aws/s3.py` (`S3.upload_file`)
- `shared/aws/constants.py` (`DEFAULT_REGION_NAME`, `us-east-2`)

## Files allowed to change

- `experiments/social_science_idea_generation_2026_10_21/workflow/cost.py`
- `experiments/social_science_idea_generation_2026_10_21/src/run_round.py`
- `experiments/social_science_idea_generation_2026_10_21/src/run_smoke.py`
- `experiments/social_science_idea_generation_2026_10_21/src/__init__.py` (empty, so `python -m src.run_smoke` works)
- `experiments/social_science_idea_generation_2026_10_21/pyproject.toml` and `uv.lock` (only for `uv add tiktoken`)

## Files forbidden to change

- `experiments/social_science_idea_generation_2026_10_21/src/run_study.py` (Step 4; do not create)
- `lib/load_env_vars.py` (Step 2)
- Root `pyproject.toml` and repository `shared/`
- Any other experiment folder
- Plan or proposal markdown (except this file is already written)
- Any pytest file, `tests/`, or `test_*.py`

## Phase 2 and 3: Scaffold and contracts

Gate: imports resolve from the smoke `PYTHONPATH`; public signatures match the proposal interface block; no second secret client in the experiment.

### `workflow/cost.py`

| Symbol | Contract |
| --- | --- |
| `CostEstimate` | Pydantic model. Fields: `full_input_tokens`, `full_output_tokens`, `estimated_cost_usd`, `price_page_url`, `note`. |
| `estimate_full_run_cost(round_record: RoundRecord) -> CostEstimate` | Pure function. No network. No hard-coded dollar amount from a real run. Uses constants `INPUT_USD_PER_MILLION` (2.0) and `OUTPUT_USD_PER_MILLION` (10.0) from `workflow/constants.py`. Sets `price_page_url` to `PRICE_PAGE_URL`. |

**Token sums from the smoke round:**

- `smoke_input_tokens` = sum of `turn.input_tokens` over `round_record.turns`.
- `smoke_output_tokens` = sum of `turn.output_tokens` over `round_record.turns`. OpenAI's billed `output_tokens` already includes reasoning tokens, so do not add `reasoning_tokens` again. Store `reasoning_tokens` from `output_tokens_details.reasoning_tokens` when that field is present, otherwise store 0.

**Revision output for the formula:**

- `revision_output_tokens` = `output_tokens` on the single turn whose `kind` is revision.

**Ballot input (estimated, not executed in Step 3):**

Build the text of one ballot prompt from the brief plus five copies of the smoke round's revised proposal. Use `revised_proposal(round_record)` for the proposal body. The five copies are the same text, because only round 1 exists. Count tokens for that prompt with `tiktoken.get_encoding("o200k_base")`. Add `tiktoken` with `uv add tiktoken` inside the experiment directory, which updates the experiment `pyproject.toml` and `uv.lock` only. If `o200k_base` is missing from the installed `tiktoken`, stop and do not substitute a character count. Then:

```text
ballot_input = 7 * tokens_per_ballot_prompt
full_input = 5 * smoke_input_tokens + ballot_input
full_output = 5 * smoke_output_tokens + 7 * revision_output_tokens
estimated_cost_usd = full_input / 1_000_000 * INPUT_USD_PER_MILLION + full_output / 1_000_000 * OUTPUT_USD_PER_MILLION
```

**`note` field (required wording intent):**

- State that the figure is **estimated from the smoke round** (round 1), not measured across five rounds.
- State that a prompt over **272,000 input tokens** uses the long-context schedule (2x input and 1.5x output for the **whole** request).
- State that the formula stays on the short-context rates and does not switch schedules.

Do not claim a measured dollar total in code comments or in `CostEstimate` before the smoke run completes. After smoke, `estimated_cost_usd` is computed from the formula above.

### `src/run_round.py`

| Symbol | Contract |
| --- | --- |
| `transcript_for(kind: TurnKind, brief: str, turns: list[TurnRecord]) -> str` | Builds user-visible context only. No prior rounds. Rules match the proposal table: seed gets brief only; comment gets brief, seed payload, and earlier comments in **this** round; synthesizer gets brief and every turn so far; method (first pass) gets brief and synthesized idea; critique gets brief, idea, method; revision gets brief, idea, method, critique. Serialize payloads readably (JSON or labeled sections). |
| `revised_proposal(round_record: RoundRecord) -> RevisedProposal` | Reads the revision turn's `payload` into `RevisedProposal`. |
| `run_turn(...) -> TurnRecord` | Same signature as proposal: `role`, `kind`, `response_model`, `transcript`, `thread_id`, `chat_model`. One `create_deep_agent` call via `build_role_agent`. `tools` stay empty at the harness level. Pass `metadata.thread_id` on the graph run so child runs share the thread. Record `input_tokens`, `output_tokens`, `reasoning_tokens` (0 if absent on usage), `latency_ms`. On structured parse failure or tool call when tools must be empty: retry **once**; second failure raises and aborts the round (no invented proposal). |
| `run_round(round_index: int, brief: str, run_id: str) -> RoundRecord` | Full round orchestration. |

**Round flow (round 1 in smoke; `run_round` must support any `round_index` 1..5 for Step 4):**

1. `configure_tracing(EnvVarsContainer.get_env_var("LANGSMITH_API_KEY", required=True))` before the first model call in the process (call from `run_round` or once in `run_smoke` before `run_round`; do not call twice with different keys).
2. `chat_model = build_chat_model(EnvVarsContainer.get_env_var("OPENAI_API_KEY", required=True))`.
3. `thread_id = str(langsmith.uuid7())` (one id per round).
4. `seed_role = ROLE_ORDER[round_index - 1]` (round 1 seed is the social psychologist).
5. **Seed:** one `run_turn` with seed role, kind `seed`, `ResearchIdea`.
6. **Comments:** `DISCUSSION_ITERATIONS` (2) passes. Each pass, four agents comment in rotation starting with the role **after** `seed_role` in `ROLE_ORDER`, skipping the seed. Eight comment turns total, kind `comment`. Seed does not comment on its own idea.
7. **Synthesizer:** one turn, kind `synthesis`, `ResearchIdea`.
8. **Methodologist:** first pass, kind `method`, `MethodPlan`.
9. **Critic:** kind `critique`, `Critique`.
10. **Methodologist:** revision, kind `revision`, `RevisedProposal`.

**Call count per round:** 1 + 8 + 1 + 1 + 1 + 1 = **13** model calls.

**`RoundRecord` fields:** `round_index`, `seed_role`, `thread_id`, `brief_sha256` (hash of `brief` string), `turns` ordered in execution order.

Do not pass earlier rounds' ideas into later rounds (only relevant when Step 4 runs multiple rounds; keep `transcript_for` round-local).

### `src/run_smoke.py`

| Symbol | Contract |
| --- | --- |
| `run_smoke(brief_path: Path, run_id: str) -> CostEstimate` | Read brief from path (default `inputs/brief.md`). Run **only** `run_round(1, brief, run_id)`. Call `estimate_full_run_cost`. Write JSON under `outputs/smoke/<run_id>/`. Upload to S3. Return `CostEstimate`. |
| `if __name__ == "__main__"` | Generate `run_id` if not passed via CLI (use `langsmith.uuid7()` or equivalent). Print `run_id` and `estimated_cost_usd`. Never print API keys. |

**Local paths (gitignored):**

- `outputs/smoke/<run_id>/round.json` (serialized `RoundRecord`)
- `outputs/smoke/<run_id>/cost.json` (serialized `CostEstimate`)

**S3 keys (same relative path under bucket):**

```text
s3://mind-technology-lab-experiments/experiments/social_science_idea_generation_2026_10_21/smoke/<run_id>/round.json
s3://mind-technology-lab-experiments/experiments/social_science_idea_generation_2026_10_21/smoke/<run_id>/cost.json
```

Use `S3(S3_BUCKET, region_name=DEFAULT_REGION_NAME).upload_file(local_path, key)` from `shared.aws.s3`, with `DEFAULT_REGION_NAME` from `shared.aws.constants`. Prefix matches `EXPERIMENT_NAME` in constants and `AGENTS.md` storage rule.

Add an empty `src/__init__.py` so `python -m src.run_smoke` works when `PYTHONPATH` includes the experiment directory.

## Phase 5: Implement units of work (dependency order)

One Git commit per unit. Do not batch.

| Order | Commit message intent | Deliverable |
| --- | --- | --- |
| 1 | `cost.py` contracts | `workflow/cost.py` with `CostEstimate` and full `estimate_full_run_cost` implementation (no API). |
| 2 | Round driver | `src/run_round.py` with `transcript_for`, `revised_proposal`, `run_turn`, `run_round`. |
| 3 | Smoke entrypoint | `src/run_smoke.py` and empty `src/__init__.py`. |

After commit 3, run verification (Phase 6). Do not start rounds 2 through 5. Do not call `run_vote`.

## Phase 6: Verification (smoke command)

Working directory: repository root `/workspace`.

**Command (run once after all code exists):**

```bash
PYTHONPATH=/workspace:/workspace/experiments/social_science_idea_generation_2026_10_21 uv run --project experiments/social_science_idea_generation_2026_10_21 python -m src.run_smoke
```

**Must pass:**

- Exit code 0.
- Stdout includes `run_id` and `estimated_cost_usd` (human-readable; no secrets).
- Exactly **13** model calls for round 1 (inspect LangSmith project `social-science-idea-generation` or count `turns` in `round.json`).
- One LangSmith **thread** id on the round (`thread_id` on `RoundRecord`; all turns share it).
- `outputs/smoke/<run_id>/round.json` and `cost.json` exist locally.
- Same two objects appear under `s3://mind-technology-lab-experiments/experiments/social_science_idea_generation_2026_10_21/smoke/<run_id>/`.
- Process stops after smoke (no round 2, no vote, no `study.json`).

**Must fail (regression checks):**

- Running five rounds or calling `run_vote` from smoke.
- Printing `OPENAI_API_KEY`, `LANGSMITH_API_KEY`, or any secret value.
- Adding a second Secrets Manager or env wrapper inside the experiment (keys only via `EnvVarsContainer`).
- Creating `src/run_study.py`, pytest files, or `tests/` in this step.

Optional manual check: open the LangSmith thread for the printed `thread_id` and confirm 13 child runs.

## Credentials and tracing

| Purpose | Access |
| --- | --- |
| OpenAI | `EnvVarsContainer.get_env_var("OPENAI_API_KEY", required=True)` |
| LangSmith | `EnvVarsContainer.get_env_var("LANGSMITH_API_KEY", required=True)` |
| S3 upload | Standard lab AWS credentials via boto3 (same as other experiments using `shared.aws.s3.S3`) |

Call `configure_tracing(langsmith_api_key)` before any model call. Do not print keys. Do not add experiment-local secret fetchers.

## Done when

1. Three commits land in order: `cost.py`, `run_round.py`, `run_smoke.py` plus empty `src/__init__.py`.
2. Smoke command above exits 0 with evidence (terminal output, local JSON, S3 listing or head object).
3. `cost.json` reflects the formula in [Expected results](../proposal.md#expected-results) applied to the smoke `RoundRecord`.
4. Step 4 can start only after a human accepts the smoke cost note (Decision 7); this step does not run `run_study`.

## Risks

The cost note multiplies round 1 by 5 and prices each ballot as one revision's output, so the note can miss the real five-round bill. A prompt over 272,000 input tokens uses the long-context schedule, and the formula itself stays on the short-context rates. One failed parse retry stops the round with no `round.json`. If the model calls a built-in tool, treat that call as a failed turn. The smoke run needs OpenAI, LangSmith, and S3 credentials, so a missing credential fails the step.
