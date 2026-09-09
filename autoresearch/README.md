# autoresearch

This folder holds paper replications and autoresearch runs.

## Where to put a replication

When someone asks for a replication or an autoresearch run, create a new folder
here named:

```
{paper_name}_{YYYY_MM_DD}
```

`paper_name` is a short, lowercase, underscore separated version of the paper
title. `YYYY_MM_DD` is the date of the request in UTC. For example, a request
made on 2026-09-09 to replicate "Attention Is All You Need" goes in:

```
autoresearch/attention_is_all_you_need_2026_09_09/
```

## Shared environment

Every folder in `autoresearch/` is a member of the root uv workspace. All members
share one virtual environment (`.venv` at the repository root) and one lock file
(`uv.lock` at the repository root).

Each replication folder has its own `pyproject.toml`. Declare that replication's
runtime dependencies there. Then run `uv sync` from the repository root to install
every workspace member into the shared environment.

```bash
# from the repository root
uv sync --all-packages --extra test
```

Because the environment is shared, you do not create a separate virtual
environment per replication. Add dependencies to the replication's own
`pyproject.toml` and re-run `uv sync`.

## Starting a new replication

Copy `example_paper_2026_09_09/` as a starting point, rename it to follow the
convention above, edit its `pyproject.toml`, and run `uv sync` from the root.
The `example_paper_2026_09_09/` folder is only a template and can be deleted.
