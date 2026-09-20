# Setup

Root tooling for this experiments repo. Each experiment folder is independent and may have its own `pyproject.toml`, `requirements.txt`, or frontend.

## Prerequisites

- Python 3.10+ (tooling targets 3.12)
- [uv](https://docs.astral.sh/uv/)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Install

From the repository root:

```bash
git clone https://github.com/METResearchGroup/mind_technology_lab_experiments.git
cd mind_technology_lab_experiments
uv sync --extra test
uv run pre-commit install
```

That creates `.venv` and installs ruff, pyright, complexipy, pre-commit, and pytest.

## Checks

```bash
uv run pytest
uv run pre-commit run --all-files
```

Pushes and pull requests run the same quality job in GitHub Actions (ruff, format, pyright, complexipy, pytest). Root lint does not cover nested experiment trees. Vercel deployments are not part of this repository's CI.

## Experiment folders

Work inside the relevant subdirectory and follow that experiment’s own README or install files. For the standalone experiment folders (everything outside `autoresearch/`), the root uv environment is for repo-wide tooling, not experiment runtime dependencies (torch, OpenAI, Next.js, and so on).

## Autoresearch replications

Replications live in `autoresearch/` and follow a different model from the standalone experiment folders. The repository root is a uv workspace, and each folder under `autoresearch/` is a workspace member with its own `pyproject.toml`. All members share the single root `.venv` and the root `uv.lock`.

Declare a replication's runtime dependencies in its own `pyproject.toml`, then run `uv sync` from the repository root to install every member into the shared environment:

```bash
uv sync --extra test
```

See [AGENTS.md](./AGENTS.md) for the folder naming convention and [autoresearch/README.md](./autoresearch/README.md) for details.
