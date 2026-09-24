# Step 3: Live Secrets Manager verification

## Goal

Confirm the production path resolves real `GITHUB_PAT_TOKEN` from secret `kova-github-pat` using default boto3 credentials. Make no product code changes unless Step 3 exposes a deterministic code bug (fix in minimal follow-up commit on same branch; do not expand scope).

Prerequisites: Steps 1 to 2 complete; full unit/static suite green.

## Files to inspect

- `/workspace/lib/load_env_vars.py`: docstring command
- `/workspace/docs/plans/2026-09-24_load-env-from-secrets-manager_cb941a/plan.md`: Verification section

## Files allowed to change

- **None** by default.
- If live call fails due to proven bug in `/workspace/shared/aws/secretsmanager.py` or `/workspace/lib/load_env_vars.py`, only those files (+ tests that lock the fix).

## Files forbidden to change

- `/workspace/experiments/**`, `/workspace/cookbooks/**`, `/workspace/autoresearch/**`
- `/workspace/AGENTS.md`, `/workspace/.github/**`, `/workspace/vercel.json`
- `/workspace/pyproject.toml` unless bugfix requires dependency pin (unlikely)
- Plan directory `/workspace/docs/plans/2026-09-24_load-env-from-secrets-manager_cb941a/**`

## Credential note (shell only)

This environment provides `AWS_ACCESS_KEY_ID` and `AWS_ACCESS_KEY_SECRET`. Boto3 default chain reads `AWS_SECRET_ACCESS_KEY`, not `AWS_ACCESS_KEY_SECRET`. **Do not** add product code to map or validate these variables. The verifier must export in shell before live command.

## Commands (run in order)

### 1. Re-run full automated gate

```bash
cd /workspace
uv sync
uv run pytest -q
uv run ruff check shared lib tests
uv run ruff format --check shared lib tests
uv run pyright
```

**Must pass:** all exit 0 as in Step 2.

### 2. Live load (real AWS)

```bash
export AWS_SECRET_ACCESS_KEY="$AWS_ACCESS_KEY_SECRET"
uv run python -c "from lib.load_env_vars import EnvVarsContainer; value = EnvVarsContainer.get_env_var('GITHUB_PAT_TOKEN', required=True); print('ok', len(value))"
```

**Must pass:**

- Exit code: `0`
- Stdout: exactly one line matching pattern `ok N` where `N` is a positive integer (token length; expect N > 0)
- Stderr: empty or benign (no secret material)
- Must **not** print the token string anywhere

Example acceptable stdout:

```text
ok 40
```

(Exact length depends on secret; only assert `N > 0` manually or with a one-line shell check.)

Optional assert in shell:

```bash
export AWS_SECRET_ACCESS_KEY="$AWS_ACCESS_KEY_SECRET"
output=$(uv run python -c "from lib.load_env_vars import EnvVarsContainer; value = EnvVarsContainer.get_env_var('GITHUB_PAT_TOKEN', required=True); print('ok', len(value))")
echo "$output"
test "$output" = "${output#ok }" && exit 1 || true
len="${output#ok }"
test "$len" -gt 0
```

Expected: last commands exit 0.

## What must fail

- Running live command **without** `export AWS_SECRET_ACCESS_KEY="$AWS_ACCESS_KEY_SECRET"` when only `AWS_ACCESS_KEY_SECRET` is set may fail with auth error; that is environment misconfiguration, not a product bug. Document in PR if encountered; do not add credential checks to product code.

- Printing token in stdout fails the step; fix docstring/command if accidental; never commit token.

## Failure triage

| Symptom | Likely cause | Action |
|---------|----------------|--------|
| `SystemExit` Could not load kova-github-pat | IAM, wrong region, bad creds | Verify shell export; confirm secret exists in `us-east-2`; no code change if creds wrong |
| `SystemExit` missing field | Secret JSON lacks key | Fix secret in AWS (out of repo) or wrong field name in allowlist (code bug) |
| `ValueError` required empty | Loader returned empty string cached | Code bug; fix loader or init |
| Unit tests pass, live fails auth | Missing `AWS_SECRET_ACCESS_KEY` export | Re-run with export only |

## Out of scope

- Rotating or creating secrets in AWS console/Terraform
- Updating AGENTS.md
- CI wiring for live AWS (unit tests remain mocked)

## Done criterion for Step 3

Live command succeeds with documented export; no secret material in logs; branch ready for PR with Steps 1 to 2 commits and any minimal bugfix commit from triage.
