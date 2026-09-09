# Agent instructions

This is a repo where each folder is a series of experiments that are one-off. Unless stated otherwise, each experiment is independent of the rest.

Local install, uv, pre-commit, and CI: **[SETUP.md](./SETUP.md)**.

## Replications and autoresearch

If a user asks for a replication or an autoresearch run, put it in the `autoresearch/` folder in a subfolder named `{paper name}_{YYYY_MM_DD}`, where the date is the date of the request in UTC. For example, a replication of "Attention Is All You Need" requested on 2026-09-09 goes in `autoresearch/attention_is_all_you_need_2026_09_09/`.

All autoresearch code shares one root-level uv environment. The repository root is a uv workspace, and each replication folder is a workspace member with its own `pyproject.toml`. Declare that replication's dependencies in its own `pyproject.toml`, then run `uv sync` from the repository root to install every member into the shared `.venv`. Do not create a separate virtual environment per replication. See [autoresearch/README.md](./autoresearch/README.md) for details.
