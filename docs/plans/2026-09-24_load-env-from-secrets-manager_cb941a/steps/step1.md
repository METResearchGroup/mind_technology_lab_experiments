# Step 1: Shared AWS region, Secrets Manager helper, packaging, and unit tests

## Goal

Introduce generic Secrets Manager field loading at `/workspace/shared/aws/secretsmanager.py` and a region constant at `/workspace/shared/aws/aws_region.py`. Add `boto3` to root dependencies, add package docstrings under `/workspace/shared/`, and add mocked unit tests. The repo-root env container is Step 2.

## Caller (downstream contract)

The primary future caller is `/workspace/lib/load_env_vars.py` (Step 2). During singleton initialization it will call `load_secret_field(secret_id, field_name, client)` and pass `secrets_manager_client()` in production.

Out of scope for this step: env allowlist, singleton, `os.environ`, dotenv, experiment-specific secret loaders, lab AWS env var resolution, and credential preflight.

## Files to inspect

| Path | Why |
|------|-----|
| `/workspace/experiments/speedup_jev_2026_09_23/shared/secrets.py` | Message shapes, helper split, Protocol, `load_secret_field` behavior |
| `/workspace/experiments/speedup_jev_2026_09_23/shared/aws_region.py` | Region constant and docstring command shape |
| `/workspace/pyproject.toml` | Dependencies, pyright/ruff scope |
| `/workspace/.cursor/skills/implement-plan-and-open-pr/CODING_RULES.md` | NumPy docstrings, style |
| `/workspace/.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md` | Test class layout |

## Files allowed to change

- `/workspace/pyproject.toml`: add `boto3` to `[project] dependencies` only (do not add `python-dotenv`; do not change `[tool.uv] package`)
- `/workspace/shared/__init__.py` (create)
- `/workspace/shared/aws/__init__.py` (create)
- `/workspace/shared/aws/aws_region.py` (create)
- `/workspace/shared/aws/secretsmanager.py` (create)
- `/workspace/tests/test_secretsmanager.py` (create)

## Files forbidden to change

- `/workspace/lib/**` (Step 2)
- `/workspace/tests/test_load_env_vars.py` (Step 2)
- `/workspace/tests/test_scaffold.py`
- `/workspace/experiments/**`, `/workspace/cookbooks/**`, `/workspace/autoresearch/**`
- `/workspace/AGENTS.md`, `/workspace/.github/**`, `/workspace/vercel.json`
- `/workspace/docs/plans/2026-09-24_load-env-from-secrets-manager_cb941a/**`

## Contracts (must match locked design)

### `/workspace/shared/aws/aws_region.py`

- `AWS_REGION: str = "us-east-2"`
- Module docstring (NumPy style) includes runnable smoke:

```text
uv run python -c "from shared.aws.aws_region import AWS_REGION; print(AWS_REGION)"
```

Expected stdout: `us-east-2` (one line).

### `/workspace/shared/aws/secretsmanager.py`

Public API:

1. **`SecretsManagerClient`**: `typing.Protocol` with method `get_secret_value(self, SecretId: str) -> dict[str, str]` (parameter name `SecretId` matches boto3).
2. **`secrets_manager_client() -> SecretsManagerClient`**: sole place that calls `boto3.client("secretsmanager", region_name=...)` importing `AWS_REGION` from `shared.aws.aws_region`. Default credential chain only; no `resolve_aws_access_keys`, no `build_boto3_session`, no `LAB_AWS_*` / `AWS_ACCESS_KEY_SECRET` handling in code.
3. **`load_secret_field(secret_id: str, field_name: str, client: SecretsManagerClient) -> str`**: `client` is required (no default). Reads `SecretString`, parses JSON object, returns non-empty string for `field_name`.

Private helpers (names may match experiment: `_read_secret_string`, `_parse_secret_json`):

| Condition | Raise | Message must |
|-----------|--------|----------------|
| `ClientError` from `get_secret_value` | `SystemExit` | Include secret id; include `{exc}`; no secret body |
| Missing/empty `SecretString` in response | `SystemExit` | `Secret {secret_id} has no SecretString.` |
| Invalid JSON | `SystemExit` | `Secret {secret_id} is not valid JSON.` |
| JSON not a dict | `SystemExit` | `Secret {secret_id} is not a JSON object.` |
| Missing or empty field | `SystemExit` | `Secret {secret_id} is missing {field_name}.` |

Success path: return field string; never log or print secret values.

Do not copy `load_typesafe_api_key`, `main`, or TypeSafe constants from the experiment file.

### Package inits

- `/workspace/shared/__init__.py`: package docstring only (NumPy style); no re-export requirement.
- `/workspace/shared/aws/__init__.py`: package docstring only.

## Implement-from-spec phases (this step)

Follow `/workspace/.cursor/skills/implement-from-spec/SKILL.md`. Suggested commits:

1. **Scope + scaffold:** create empty modules and `boto3` dependency; imports resolve.
2. **Contracts:** Protocol, signatures, stub bodies.
3. **Tests:** `/workspace/tests/test_secretsmanager.py` failing for right reasons.
4. **Implement:** fill helpers and public functions until green.

One commit per phase gate minimum; do not batch scaffold + full implementation in one commit.

## Tests: `/workspace/tests/test_secretsmanager.py`

Rules: pytest; no network; no real boto3 client; fake implementing `SecretsManagerClient`.

**One test class per public function** (UNIT_TESTING_STANDARDS):

| Class | Function under test |
|-------|---------------------|
| `TestSecretsManagerClient` | Optional: Protocol structural test with fake, or document Protocol tested via fakes in other classes |
| `TestSecretsManagerClientFactory` | `secrets_manager_client`: mock `boto3.client` assert called with `service_name="secretsmanager"` and `region_name="us-east-2"` |
| `TestLoadSecretField` | `load_secret_field` |

`TestLoadSecretField` cases (Arrange-Act-Assert):

1. **Success**: fake returns `{"SecretString": '{"GITHUB_PAT_TOKEN": "ghp_test_value"}'}`; assert result equals expected string.
2. **Missing field**: JSON `{}` or missing key; expect `SystemExit` with message containing secret id and field name; no token in message.
3. **Invalid JSON**: `SecretString` not JSON; expect `SystemExit` invalid JSON message.
4. **ClientError**: fake raises `botocore.exceptions.ClientError` with minimal valid `response`/`operation_name`; expect `SystemExit` message `Could not load {secret_id} from Secrets Manager:` prefix (match experiment shape).

Use `pytest.raises(SystemExit)` for failure cases.

Do not test `secrets_manager_client()` against live AWS in unit tests.

## What must pass (end of Step 1)

```bash
cd /workspace
uv sync
```

Expected: exit 0; lockfile updated if needed; `boto3` installed.

```bash
uv run pytest -q tests/test_secretsmanager.py
```

Expected: exit 0; all tests in file passed; no skipped network tests.

```bash
uv run ruff check shared tests/test_secretsmanager.py
uv run ruff format --check shared tests/test_secretsmanager.py
```

Expected: exit 0 both.

```bash
uv run python -c "from shared.aws.aws_region import AWS_REGION; print(AWS_REGION)"
```

Expected stdout: `us-east-2`

## What must fail (before implementation complete)

- `uv run pytest -q tests/test_secretsmanager.py`: fails with missing module or failing tests until Step 1 implementation done.
- Import `shared.aws.secretsmanager` before files exist: `ModuleNotFoundError`.

## What must NOT be required yet

- `uv run pytest -q tests/test_load_env_vars.py`: file may not exist.
- `uv run pyright` clean on `lib/`: lib not created.
- Live Secrets Manager command: Step 3.

## Out of scope

- `/workspace/lib/load_env_vars.py`
- Pyright `include` for `shared`/`lib` (Step 2): optional to add `shared` in Step 1 if implementer wants early pyright; locked design says Step 2 adds both `shared` and `lib` to include. Prefer Step 2 for pyright include change to avoid partial config.
