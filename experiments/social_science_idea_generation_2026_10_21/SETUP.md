# Setup

This experiment is standalone. Install from this folder instead of the repository root.

```bash
cd experiments/social_science_idea_generation_2026_10_21 && uv sync
```

The command creates a local `.venv` for this experiment, and it does not change the root workspace lock.

## Region

`us-east-2`

## Model

`gpt-6-sol`

## LangSmith

The LangSmith project name is `social-science-idea-generation`.

## Keys

Scripts read keys with `EnvVarsContainer.get_env_var` from `lib/load_env_vars.py`.

- `OPENAI_API_KEY`
- `LANGSMITH_API_KEY`

The experiment does not build a Secrets Manager client. Run scripts with the repository root and this folder on `PYTHONPATH`.
