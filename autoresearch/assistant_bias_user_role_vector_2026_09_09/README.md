# Assistant bias user role vector (2026-09-09)

Mini-replication of [Investigating Assistant Bias in LLM User Simulators Using a Role Vector](https://arxiv.org/abs/2609.00608).

The paper extracts a user role vector by contrasting hidden states from user reflections and assistant reflections on the same chat, then steers a simulator along that vector.

## What ran here

The local CPU check still uses planted hidden states (48 synthetic dialogues, recovered cosine 0.998). The real Qwen 3.5 4B forward pass and steered generation run on Hugging Face Jobs, not on this Cloud Agent VM.

The Jobs script:

1. Loads `Qwen/Qwen3.5-4B`.
2. Builds the three Appendix E.1 reflection prompts on 8 hand-crafted chats (not LMSYS-Chat-1M).
3. Reads the residual stream at the last prompt token on layer 11 (first-response-token position).
4. Takes the user-minus-assistant mean (equation 1).
5. Steers generation with `h + α ‖h‖ v̂` on that layer (equation 2).
6. Scores first messages with the lexical user-likeness stand-in.
7. Writes JSON to the Hub and to S3.

Completed Jobs run (`6aa1a13221047bf1b03706b7`, A100 80GB, 125 seconds):

- User-reflection projection onto the vector: 0.37
- Assistant-reflection projection: -1.09
- Lexical mean user-likeness: 3.00 at α=-0.3, 3.41 at α=0.2
- Artifacts: `data/qwen_run.json`, [Hub dataset](https://huggingface.co/datasets/mtorres98/assistant-bias-user-role-vector-qwen-run), `s3://mind-technology-lab-experiments/autoresearch/assistant_bias_user_role_vector_2026_09_09/qwen_run.json`

Style scores are still not GPT-5 Mini. Disengagement and SimulatorArena are not rerun.

## Commands

From the repository root:

```bash
uv sync --extra test
uv run pytest -q tests/test_user_role_vector.py
PYTHONPATH=autoresearch/assistant_bias_user_role_vector_2026_09_09 uv run python -m user_role_vector
```

Qwen GPU job (needs `HF_TOKEN`; S3 uses `AWS_ACCESS_KEY_ID` plus `AWS_ACCESS_KEY_SECRET`):

```bash
hf jobs uv run \
  --flavor a100-large \
  --timeout 2h \
  --secrets HF_TOKEN \
  --secrets AWS_ACCESS_KEY_ID \
  --secrets AWS_ACCESS_KEY_SECRET \
  --env AWS_DEFAULT_REGION=us-east-2 \
  --name qwen-user-role-vector \
  --detach \
  autoresearch/assistant_bias_user_role_vector_2026_09_09/scripts/qwen_role_vector_job.py
```

`l4x1` and `a10g-large` sat in scheduling in this environment. `a100-large` started in seconds.

Dashboard:

```bash
cd autoresearch/assistant_bias_user_role_vector_2026_09_09/dashboard
npm install
npm run dev
```

## Files

- `user_role_vector/` Python implementation, planted-direction experiment, and Qwen job inputs
- `scripts/qwen_role_vector_job.py` self-contained Hugging Face Jobs UV script
- `data/` paper tables plus mini-replication JSON
- `dashboard/` Next.js UI
