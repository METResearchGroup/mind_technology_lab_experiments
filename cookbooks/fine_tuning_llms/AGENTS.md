# Fine-tuning LLMs cookbook

Install the cookbook packages from the repository root before you run anything in this folder:

```bash
uv sync --extra fine_tuning_llms
```

Run all code from the repository root. Use this form, with `{path}` replaced by the script path from the root:

```bash
uv run python {path}
```

Example:

```bash
uv run python cookbooks/fine_tuning_llms/huggingface_fine_tuning_trl/train.py
```

Do not create a separate virtual environment in this folder, and do not run scripts with a working directory inside this cookbook.
