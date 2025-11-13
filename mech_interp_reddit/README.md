# Mechanistic Interpretability of Reddit posts

Can we see if there are patterns in what is firing off inside of the neurons when we ask it questions?

Quick pipeline to compute relative “concept activations” on Reddit posts using ActAdd-style concept vectors over Qwen2.5. Outputs a bar chart for:
- Fairness
- Feelings
- Harms
- Honesty
- Relational Obligation
- Social Norms

## Setup (uv)

1) Create and activate a virtualenv with uv:
```
uv venv
source .venv/bin/activate
```

2) Install the project (and dev tools optionally):
```
uv pip install -e .
# optional dev tools
uv pip install -e ".[dev]"
```

## Run

Generate scores and charts for the sample posts:
```
python run_pipeline.py --question "When judging this situation, which concepts are most salient?"
# Optional: use a tiny model for quick tests
python run_pipeline.py --model sshleifer/tiny-gpt2 --question "When judging this situation, which concepts are most salient?"
# Optional: specify a different posts file
python run_pipeline.py --posts SAMPLE_REDDIT_POSTS.jsonl --question "..."
# Multi-model mode (runs each model and writes under output/<timestamp>/<model_name>/)
# Allowed: Qwen/Qwen2.5-0.5B-Instruct, Qwen/Qwen2.5-1.5B-Instruct, TinyLlama/TinyLlama-1.1B-Chat-v1.0, EleutherAI/pythia-1.4b
python run_pipeline.py --models "Qwen/Qwen2.5-0.5B-Instruct,TinyLlama/TinyLlama-1.1B-Chat-v1.0" --question "..."
```

Images and metadata will be saved under a timestamped folder:
```
mech_interp_reddit/output/YYYY_MM_DD-HH:MM:SS/
  ├── activations_<idx>.png
  └── metadata.json
```

Notes:
- The script downloads the HF model `Qwen/Qwen2.5-1.5B-Instruct` on first run.
- Adjust layers via `--layers` (default: `-4,-3,-2,-1`), and question via `--question`.
- `metadata.json` includes: `timestamp`, `model`, `git_commit_hash`, and `activation_id_to_comment_id` mapping.
- In multi-model runs, `metadata.json` also includes `models` (list of model IDs used).
- The loader accepts the provided `SAMPLE_REDDIT_POSTS.jsonl` (JSON array) with triple-quoted `submission` blocks.
