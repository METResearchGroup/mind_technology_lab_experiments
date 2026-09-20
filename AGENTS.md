# Agent instructions

This is a repo where each folder is a series of experiments that are one-off. Unless stated otherwise, each experiment is independent of the rest.

Local install, uv, pre-commit, and CI: **[SETUP.md](./SETUP.md)**. GitHub Actions is the only CI for this repository. Do not connect it to Vercel: this is a collection of independent experiments, not a web app, and Vercel Git links post failing deployment statuses that are not part of the quality checks.

## Replications and autoresearch

If a user asks for a replication or an autoresearch run, put it in the `autoresearch/` folder in a subfolder named `{paper name}_{YYYY_MM_DD}`, where the date is the date of the request in UTC. For example, a replication of "Attention Is All You Need" requested on 2026-09-09 goes in `autoresearch/attention_is_all_you_need_2026_09_09/`.

All autoresearch code shares one root-level uv environment. The repository root is a uv workspace, and each replication folder is a workspace member with its own `pyproject.toml`. Declare that replication's dependencies in its own `pyproject.toml`, then run `uv sync` from the repository root to install every member into the shared `.venv`. Do not create a separate virtual environment per replication. See [autoresearch/README.md](./autoresearch/README.md) for details.

Before kicking off a replication, do multiple parallel agent passes through the paper and repo to find the repo, if it exists, and to give an estimate of the replication cost in compute, storage, and time.

## Model training

Use HuggingFace for model access and compute. Use the `HF_TOKEN` API key.

### Default open-source LLM

For any experiments, let's default to Qwen3.5 4B. Use [this HuggingFace link](https://huggingface.co/collections/Qwen/qwen35) for more information, and [this link](https://huggingface.co/Qwen/Qwen3.5-4B) for the model weights.

### GPU compute

For GPU compute, use Hugging Face Jobs. See [this guide](https://huggingface.co/docs/huggingface_hub/en/guides/jobs) for more details.

### Storage

By default, use S3 for storage. Use the AWS access key and secret login, via `LAB_AWS_ACCESS_KEY_ID` and `LAB_AWS_ACCESS_KEY_SECRET`, renaming it as needed.

Err on the side of storing artifacts and objects in S3.

Use the following setup:

- S3 bucket: `mind-technology-lab-experiments`
- S3 prefix: use the same folder and prefix that exists locally. For example, if the folder is `autoresearch/paper-name/`, the S3 prefix is `autoresearch/paper-name/`.

## Setting up MCP servers

Project MCP servers live in `.cursor/mcp.json`. Do not put secrets in that file. The API key, ALPHAXIV_API_KEY, lives in the environment.

### AlphaXiv

Use the AlphaXiv MCP server for paper search, PDF questions, researcher lookup, and library tools. Docs: [https://www.alphaxiv.org/docs/mcp](https://www.alphaxiv.org/docs/mcp).

- Endpoint: `https://api.alphaxiv.org/mcp/v1`
- Transport: Streamable HTTP
- Auth: send `Authorization: Bearer ${env:ALPHAXIV_API_KEY}`
