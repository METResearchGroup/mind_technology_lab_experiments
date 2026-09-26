# Step 2: Repo-root env container and unit tests

## Goal

Add `/workspace/lib/load_env_vars.py` with thread-safe singleton initialization that loads allowlisted secrets via `shared.aws.secretsmanager`, caches values in memory, and exposes `EnvVarsContainer.get_env_var(name, required=False) -> str`. Extend Pyright include. Add `/workspace/tests/test_load_env_vars.py` with a monkeypatched loader and singleton reset.

Prerequisite: Step 1 merged or committed on branch `cursor/load-env-vars-secrets-manager-dc31`.

## Caller

Any agent script or module at repo root that needs `GITHUB_PAT_TOKEN` without reading `.env` or `os.environ` directly:

```python
from lib.load_env_vars import EnvVarsContainer

token = EnvVarsContainer.get_env_var("GITHUB_PAT_TOKEN", required=True)
```

Out of scope: writing secrets into `os.environ`, loading HF or social keys from mirrorView allowlist, multiple secret ids beyond the single AGENTS.md-documented mapping, and AWS calls inside `get_env_var` after init.

## Files to inspect

| Path | Why |
|------|-----|
| `https://github.com/METResearchGroup/mirrorView-task/blob/main/lib/load_env_vars.py` (or raw) | Singleton structure, `get_env_var` required/optional/unknown behavior, ValueError message shapes |
| `/workspace/shared/aws/secretsmanager.py` | `load_secret_field`, `secrets_manager_client` |
| `/workspace/docs/plans/2026-09-24_load-env-from-secrets-manager_cb941a/plan.md` | Locked allowlist |
| `/workspace/pyproject.toml` | Pyright `include` |

## Files allowed to change

- `/workspace/lib/__init__.py` (create)
- `/workspace/lib/load_env_vars.py` (create)
- `/workspace/pyproject.toml`: `[tool.pyright] include = ["shared", "lib", "tests"]` (replace or extend; must include all three)
- `/workspace/tests/test_load_env_vars.py` (create)

## Files forbidden to change

- `/workspace/shared/aws/secretsmanager.py` except bugfixes proven by failing Step 1 tests (prefer no change)
- `/workspace/tests/test_secretsmanager.py` except bugfixes
- `/workspace/tests/test_scaffold.py`
- `/workspace/experiments/**`, `/workspace/cookbooks/**`, `/workspace/autoresearch/**`
- `/workspace/AGENTS.md`, `/workspace/.github/**`, `/workspace/vercel.json`
- Plan directory under `/workspace/docs/plans/2026-09-24_load-env-from-secrets-manager_cb941a/`

## Contracts: `/workspace/lib/load_env_vars.py`

### Public API

- **Class `EnvVarsContainer`**
  - **`classmethod get_env_var(cls, name: str, required: bool = False) -> str`**

### Control flow (mirror mirrorView)

- Class-level singleton with double-checked locking (`threading.Lock` on instance creation and on init), same structural pattern as mirrorView `EnvVarsContainer` (`_get_instance`, `_ensure_initialized`, `_initialize_env_vars`).
- First `get_env_var` triggers init once per process.

### Allowlist (only entries; do not add HF_TOKEN or mirrorView social keys)

| Env name key in cache | Secrets Manager secret id | JSON field name |
|----------------------|---------------------------|-----------------|
| `GITHUB_PAT_TOKEN` | `kova-github-pat` | `GITHUB_PAT_TOKEN` |

Implementation hint: map env var name → `(secret_id, field_name)`; for this allowlist field name equals env var name.

### Initialization behavior

- For each allowlisted env name, call `load_secret_field(secret_id, field_name, secrets_manager_client())` once.
- Store returned string in internal cache dict (mirrorView used `dict[str, str | None]`; here values are loaded strings, and a missing SM field exits the process via `SystemExit` from the loader, not ValueError at init).
- **Do not** call `load_dotenv`, **do not** read `.env`, **do not** use `python-dotenv`, **do not** assign `os.environ`.
- **Do not** call AWS inside `get_env_var`; only init path calls Secrets Manager (via shared helper).

### `get_env_var` semantics (match mirrorView)

| Situation | `required=False` | `required=True` |
|-----------|------------------|-----------------|
| Name not in allowlist / not in cache | return `""` | `ValueError`: `{name} is required but is missing. Please set the {name} environment variable.` |
| Cached value `None` (if used) | return `""` | same missing message |
| Cached empty or whitespace-only string | return `""` | `ValueError`: `{name} is required but is empty. Please set the {name} environment variable to a non-empty value.` |
| Cached non-empty string | return `str(raw)` | return `str(raw)` |

Unknown names are not in cache, so they behave as missing (mirrorView only populated keys from its type map).

### Module docstring

NumPy style. Include **exact** runnable verification (prints length only):

```text
uv run python -c "from lib.load_env_vars import EnvVarsContainer; value = EnvVarsContainer.get_env_var('GITHUB_PAT_TOKEN', required=True); print('ok', len(value))"
```

Document that live run needs AWS credentials; do not document `AWS_ACCESS_KEY_SECRET` mapping in product code (plan Step 3 covers shell export).

### `/workspace/lib/__init__.py`

Package docstring only (NumPy style).

## Tests: `/workspace/tests/test_load_env_vars.py`

- Use `pytest` and `unittest.mock.patch` (or pytest-mock).
- **Reset singleton between tests**: set `EnvVarsContainer._instance = None` and reset `_initialized` on instance if needed; document helper fixture `reset_env_container` in file or `conftest.py` under `/workspace/tests/` only if shared (YAGNI: local autouse fixture in test file is fine).

Monkeypatch target: `shared.aws.secretsmanager.load_secret_field` (patch where used: `lib.load_env_vars.load_secret_field` if imported bound; prefer patch on `lib.load_env_vars.load_secret_field` after `from shared.aws.secretsmanager import load_secret_field` in module under test, use `patch("lib.load_env_vars.load_secret_field")`).

**Class `TestGetEnvVar`** (one class per public method `get_env_var`):

1. **`test_required_present`**: patch returns `"fake-token"` for `("kova-github-pat", "GITHUB_PAT_TOKEN", ...)`; assert `get_env_var("GITHUB_PAT_TOKEN", required=True) == "fake-token"`.
2. **`test_required_missing_unknown_name`**: no patch needed for unknown; assert `pytest.raises(ValueError)` with message containing `UNKNOWN_VAR is required but is missing`.
3. **`test_required_empty_cached`**: patch returns `""` or `"   "`; assert empty raises required-but-empty ValueError when `required=True`.
4. **`test_optional_missing_unknown`**: `get_env_var("NOT_IN_ALLOWLIST", required=False) == ""`.
5. **`test_optional_missing_allowlisted_empty`**: patch returns `""`; optional returns `""`.
6. **`test_initialization_calls_load_secret_field`**: patch `load_secret_field` and optionally `secrets_manager_client`; first `get_env_var("GITHUB_PAT_TOKEN")`; assert `load_secret_field` called once with args `("kova-github-pat", "GITHUB_PAT_TOKEN", client)` where client is whatever `secrets_manager_client()` returned (can mock both).

Assert `load_secret_field` not called again on second `get_env_var` for same process (optional strong test).

Do not call real AWS in tests.

## Implement-from-spec phases

Same as Step 1: scaffold `lib` modules → contracts → failing tests → implement until green; one commit per phase gate.

## What must pass (end of Step 2)

```bash
cd /workspace
uv sync
uv run pytest -q
```

Expected: exit 0; includes `tests/test_scaffold.py`, `tests/test_secretsmanager.py`, `tests/test_load_env_vars.py` all passing.

```bash
uv run ruff check shared lib tests
uv run ruff format --check shared lib tests
```

Expected: exit 0 both.

```bash
uv run pyright
```

Expected: exit 0; typechecks `shared`, `lib`, `tests` per updated `include`.

## What must fail (before Step 2 complete)

- Import `lib.load_env_vars` before file exists.
- Tests in `tests/test_load_env_vars.py` until implementation green.

## Out of scope

- Live AWS verification (Step 3).
- Changing AGENTS.md to reference new module (forbidden path anyway).
