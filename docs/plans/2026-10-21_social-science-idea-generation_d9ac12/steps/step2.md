# Step 2: Connect keys, the model, and LangSmith

Implements [proposal.md](../proposal.md) **Step 2** (lines 256 to 258) and the key-loading design in **Model, price, and keys** (lines 21 to 29), **The Python driver** (lines 13 to 19, harness profile only), **Tracing** (lines 88 to 90), and the allowlist plus agent signatures in **Schema and key interfaces** (lines 170 to 191).

This step does **not** call the model. It does **not** add pytest, `tests/`, or `test_*.py`.

---

## Goal

1. Extend `ALLOWLIST` in `lib/load_env_vars.py` with OpenAI and LangSmith rows while keeping the GitHub row.
2. Add `workflow/tracing.py` with `configure_tracing`.
3. Add `workflow/agents.py` with `build_chat_model`, `build_role_agent`, and the two `EnvVarsContainer.get_env_var(..., required=True)` call sites (exact names below).
4. Prove wiring with offline commands (allowlist print and import check).

**Done when:** pass/fail at the bottom holds, two commits are pushed, and no forbidden file changed.

---

## Workflow (implement-from-spec, Phase 4 skipped)

Follow [implement-from-spec](/tmp/ai_tools/skills/implement-from-spec/SKILL.md) phase order. **Skip Phase 4 (test design).** Use Phase 6 gates with the commands in this document instead of pytest.

| Phase | Work in this step | Gate |
|-------|-------------------|------|
| 1 Scope | Caller is Step 3 `run_smoke` / `run_round` (not implemented here). This step only supplies keys, tracing env, and agent factories. | Caller named; file tree matches allowed list; out-of-scope listed below. |
| 2 Scaffold | Create `workflow/tracing.py` and `workflow/agents.py` with imports and stub bodies if needed so imports resolve. | `PYTHONPATH` import check prints `ok`. |
| 3 Contracts | Final signatures match proposal and this step. No `run_turn` yet. | Signatures stable; commit allowlist separately from workflow files. |
| ~~4 Test design~~ | **Skipped** (forbidden for this plan). | N/A |
| 5 Implement | Fill allowlist, docstrings, `configure_tracing`, `build_chat_model`, `build_role_agent`, and key call sites. | Commands below pass. |
| 6 Done | No model invocation; no secret printed; no experiment-side Secrets Manager client. | Pass/fail section. |

**Commits (two, in order):**

1. `lib/load_env_vars.py` (and `lib/__init__.py` docstring only if updated): allowlist rows plus length-only docstring examples.
2. `experiments/social_science_idea_generation_2026_10_21/workflow/tracing.py` and `workflow/agents.py`.

---

## Scope

### In scope

| Path | Change |
|------|--------|
| `lib/load_env_vars.py` | `ALLOWLIST` rows and module docstring only. |
| `lib/__init__.py` | Module docstring length-check examples only (if it duplicates the loader command). |
| `experiments/social_science_idea_generation_2026_10_21/workflow/tracing.py` | **Create** `configure_tracing`. |
| `experiments/social_science_idea_generation_2026_10_21/workflow/agents.py` | **Create** `build_chat_model`, `build_role_agent`, key call sites. |

### Out of scope

- `shared/aws/secretsmanager.py` (no edits).
- Root `pyproject.toml`.
- `workflow/cost.py`, `src/run_round.py`, `src/run_smoke.py`, `src/run_study.py` (later steps).
- Any test files.
- `build_secrets_client`, `load_openai_api_key`, `load_langsmith_api_key`.
- Calling `secrets_manager_client` or `load_secret_field` from the experiment package (they remain inside `_initialize_env_vars` only).
- Invoking the chat model or `create_deep_agent` `.invoke` / `.ainvoke` in verification commands.

### Preconditions

- Step 1 should exist so `workflow` is a package under `experiments/social_science_idea_generation_2026_10_21/` with `RoleSpec` in `workflow/roles.py` and Pydantic models in `workflow/schemas.py`. If Step 1 is not merged yet, create only the minimal `workflow/__init__.py` needed for imports; do not implement Step 1 schemas in this step.

### Runtime layout

Scripts use:

```text
PYTHONPATH=/workspace:/workspace/experiments/social_science_idea_generation_2026_10_21
uv run --project experiments/social_science_idea_generation_2026_10_21 ...
```

So `from lib.load_env_vars import EnvVarsContainer` and `from workflow.agents import ...` both resolve.

---

## 1. Allowlist (`lib/load_env_vars.py`)

### Current behavior (do not change logic)

- `_initialize_env_vars` loops `ALLOWLIST`, uses `secrets_manager_client()` and `load_secret_field(secret_id, field_name, client)` from `shared.aws.secretsmanager`.
- `EnvVarsContainer.get_env_var(name, required=True)` is the **only** read API. Unknown name or empty value with `required=True` raises `ValueError`. Messages must **not** include the secret value (existing messages already comply).
- Region stays `DEFAULT_REGION_NAME` (`us-east-2`) via the shared client.

### ALLOWLIST

Settled shape (proposal lines 172 to 177). **Keep** the GitHub row. **Add** two rows with the same tuple shape `(secret_id, json_field_name)`:

```python
ALLOWLIST: Final[dict[str, tuple[str, str]]] = {
    "GITHUB_PAT_TOKEN": ("github-pat-token", "GH_TOKEN"),
    "OPENAI_API_KEY": ("openai-api-key", "OPENAI_API_KEY"),
    "LANGSMITH_API_KEY": ("langsmith-api-key", "LANGSMITH_API_KEY"),
}
```

Secret ids and fields match proposal **Model, price, and keys** (OpenAI: `openai-api-key` / `OPENAI_API_KEY`; LangSmith: `langsmith-api-key` / `LANGSMITH_API_KEY`).

### Module docstring

Keep the existing GitHub length-only example. Add the same pattern for `OPENAI_API_KEY` and `LANGSMITH_API_KEY`. Each command must print `ok` and `len(value)`, never the value.

Mirror the same examples in `lib/__init__.py` only if that file still duplicates the one-liner for GitHub.

---

## 2. Tracing (`workflow/tracing.py`)

### `configure_tracing(langsmith_api_key: str) -> None`

Per proposal **Tracing** (lines 88 to 90):

- Set process environment **before any model call** in later steps:
  - `LANGSMITH_TRACING` = `"true"`
  - `LANGSMITH_API_KEY` = the argument
  - `LANGSMITH_PROJECT` = `"social-science-idea-generation"`
- Use `os.environ[...]` (or equivalent) because LangSmith reads these from the process environment. This is not a Secrets Manager fetch.
- Do **not** log or print the key.

Thread id helpers (`langsmith.uuid7`) belong in this module in a later step when `run_round` exists; optional stub is out of scope unless Step 1 already added names.

---

## 3. Agents (`workflow/agents.py`)

### Imports

- `from lib.load_env_vars import EnvVarsContainer`
- `ChatOpenAI` from `langchain_openai` (or the import path pinned in the experiment `pyproject.toml`).
- `create_deep_agent` and harness types from `deepagents` per installed version.
- `RoleSpec` from `workflow.roles`.
- Pydantic `BaseModel` for `response_model` typing.
- Return type for the agent: `CompiledStateGraph` (or the type `create_deep_agent` returns in the installed version).

### Key call sites (exact lines)

These two lines must appear in `agents.py` (not in a separate secrets module). They must **not** run at import time, so the import check works without AWS:

```python
openai_api_key = EnvVarsContainer.get_env_var("OPENAI_API_KEY", required=True)
langsmith_api_key = EnvVarsContainer.get_env_var("LANGSMITH_API_KEY", required=True)
```

Place them in a function that Step 3 will call before model use (for example a small `read_allowlisted_keys()` returning `(openai_api_key, langsmith_api_key)`). Do **not** name helpers `load_openai_api_key` or `load_langsmith_api_key`. Do not add `build_secrets_client`.

### `build_chat_model(api_key: str) -> ChatOpenAI`

Per proposal **The Python driver** and **Model, price, and keys**:

```python
ChatOpenAI(
    model="gpt-6-sol",
    api_key=api_key,
    use_responses_api=True,
    reasoning={"effort": "medium"},
    # cap total output at 25_000 tokens (proposal and OpenAI reasoning guide reserve)
    max_tokens=25_000,  # or the parameter name required by the pinned langchain-openai version
)
```

- Do **not** set `reasoning.mode`; leave default `standard`.
- Use the experiment's constant for `25_000` if `workflow/constants.py` already defines `MAX_OUTPUT_TOKENS`; otherwise literal `25_000` is acceptable in Step 2 only.
- This step must not invoke the model in verification.

### `build_role_agent(role, response_model, chat_model)`

Per proposal **The Python driver** (lines 15 to 17) and signature block (lines 187 to 191):

- Call `create_deep_agent` with `tools=[]` (empty list removes domain tools only; filesystem tools still exist unless excluded via harness profile).
- `system_prompt` = `role.system_prompt` (from `RoleSpec`).
- `response_format` = the Pydantic `response_model` type for the turn.
- Register a **HarnessProfile** for model key `openai:gpt-6-sol` with:
  - `general_purpose_subagent` disabled (or the 0.7+ field name that disables the general subagent).
  - Filesystem tools excluded: `ls`, `read_file`, `write_file`, `edit_file`, `delete`, `glob`, `grep`.
  - No skills, memory files, sandbox, or todo list (driver owns turn order).

**API verification (mandatory):** Before coding profile fields, inspect the **installed** `deepagents` package (version pinned in the experiment `pyproject.toml`). Read 0.7+ docs or source for `HarnessProfile` / `create_deep_agent` kwargs. If field names differ from the proposal text, **stop**, record the actual names in the commit message or a one-line comment in `agents.py`, and use those names only. Do not invent a parallel client or duplicate harness API.

Pass `chat_model` into `create_deep_agent` per that package's documented parameter (often `model=`).

---

## Verification commands

Run from repository root unless noted.

### Required: allowlist keys (no network)

```bash
cd /workspace && uv run python -c "from lib.load_env_vars import ALLOWLIST; print(sorted(ALLOWLIST))"
```

**Expected stdout:** a sorted list of exactly three top-level keys: `GITHUB_PAT_TOKEN`, `LANGSMITH_API_KEY`, `OPENAI_API_KEY` (order in the printed list is alphabetical). No other allowlist names.

### Required: import check (no model call)

```bash
PYTHONPATH=/workspace:/workspace/experiments/social_science_idea_generation_2026_10_21 \
  uv run --project experiments/social_science_idea_generation_2026_10_21 \
  python -c "from workflow.agents import build_chat_model, build_role_agent; from workflow.tracing import configure_tracing; print('ok')"
```

**Expected stdout:** `ok`

### Optional: live length check (only if AWS credentials can read Secrets Manager)

Must not print secret values:

```bash
uv run python -c "from lib.load_env_vars import EnvVarsContainer; value = EnvVarsContainer.get_env_var('OPENAI_API_KEY', required=True); print('ok', len(value))"
uv run python -c "from lib.load_env_vars import EnvVarsContainer; value = EnvVarsContainer.get_env_var('LANGSMITH_API_KEY', required=True); print('ok', len(value))"
```

**Expected:** `ok` and a positive integer for each. Failure here does **not** block Step 2 if the required commands pass.

---

## Pass / fail

| Pass | Fail |
|------|------|
| Three allowlist rows; GitHub row unchanged | Extra allowlist entries or missing new rows |
| Experiment imports `build_chat_model`, `build_role_agent`, `configure_tracing` | Import runs `get_env_var` at module import time and breaks offline import check |
| No model API call in this step | Any invoke/chat completion in verification or module init |
| No new secret client in experiment code | `secrets_manager_client` / `load_secret_field` imported in `workflow/` |
| No key material in logs or stdout | Printing or logging key values |
| `shared/aws/secretsmanager.py` untouched | Any edit to forbidden paths |
| Two commits as specified | Single squashed commit or pytest added |

---

## Risks and unresolved items

| Item | Mitigation |
|------|------------|
| `deepagents` harness API drift vs proposal field names | Inspect installed package before implementing `build_role_agent`; document actual field names if they differ. |
| `ChatOpenAI` output cap parameter name (`max_tokens` vs `max_completion_tokens`) | Match pinned `langchain-openai` docs for Responses API + `gpt-6-sol`. |
| Step 1 package layout missing | Minimal `workflow/__init__.py` only; do not fold Step 1 into Step 2. |
| Accidental secret fetch on import | Keep the two `get_env_var` lines inside a function not called from import check. |

---

## Executive summary (for parent agent)

- **Path:** `docs/plans/2026-10-21_social-science-idea-generation_d9ac12/steps/step2.md`
- **Unresolved:** Exact `HarnessProfile` / `create_deep_agent` keyword names until `deepagents` is installed in the experiment env; exact `ChatOpenAI` max-output kwarg for the pinned LangChain version.
- **Risks:** Import-time key fetch breaks offline checks; printing keys during optional AWS verification; editing `secretsmanager.py` or calling the model in Step 2.
