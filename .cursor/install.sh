#!/usr/bin/env bash
# Idempotent bootstrap for the repo-wide uv tooling environment.
# Mirrors SETUP.md and the CI quality job (.github/workflows/ci.yml).
# Experiment folders keep their own runtime dependencies and secrets; this
# script only prepares the shared root tooling (ruff, pyright, complexipy,
# pytest, pre-commit).
set -euo pipefail

# Install uv if the base image does not already provide it.
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="$HOME/.local/bin:$PATH"

# Create .venv and install the test extra pinned by uv.lock.
uv sync --extra test --frozen

# Register the pre-commit git hook (developer convenience only). This is
# best-effort: the CI quality gate and local checks run `pre-commit run`
# directly, and Cloud Agent VMs manage their own core.hooksPath, so a failure
# here must not abort environment setup.
if ! uv run --extra test pre-commit install >/dev/null 2>&1; then
  echo "note: skipped 'pre-commit install' (git hooks unavailable in this environment); use 'uv run pre-commit run --all-files'"
fi
