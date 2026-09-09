# Assistant bias user role vector (2026-09-09)

Mini-replication of [Investigating Assistant Bias in LLM User Simulators Using a Role Vector](https://arxiv.org/abs/2609.00608).

The paper extracts a user role vector by contrasting hidden states from user reflections and assistant reflections on the same chat, then steers a simulator along that vector.

## What ran here

This folder does not load Qwen 3.5 9B or Qwen3.5-4B. There is no GPU in this environment. The code implements the paper’s formulas on planted hidden states:

1. Filter dialogues to 2–50 non-empty user/assistant turns.
2. Build the three reflection prompts from Appendix E.1.
3. Drop reflections labeled `not_represented`.
4. Average paired activations and take the user-minus-assistant mean (equation 1).
5. Steer with `h + α ‖h‖ v̂` (equation 2).

On 48 synthetic dialogues the recovered direction matches the planted user direction with cosine 0.998.

## Commands

From the repository root:

```bash
uv sync --extra test
uv run pytest -q tests/test_user_role_vector.py
PYTHONPATH=autoresearch/assistant_bias_user_role_vector_2026_09_09 uv run python -m user_role_vector
```

Dashboard:

```bash
cd autoresearch/assistant_bias_user_role_vector_2026_09_09/dashboard
npm install
npm run dev
```

## Files

- `user_role_vector/` Python implementation and planted-direction experiment
- `data/` paper tables plus mini-replication JSON
- `dashboard/` Next.js UI
