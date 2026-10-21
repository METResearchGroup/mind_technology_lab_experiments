# ruff: noqa: E501
"""Fixed model, price, and storage names for this experiment.

Run from the repository root:

    PYTHONPATH=/workspace:/workspace/experiments/social_science_idea_generation_2026_10_21 \\
      uv run --project experiments/social_science_idea_generation_2026_10_21 \\
      python -c "from workflow.constants import MODEL_ID; print(MODEL_ID)"
"""

MODEL_ID = "gpt-6-sol"
REASONING_EFFORT = "medium"
MAX_OUTPUT_TOKENS = 25_000
LANGSMITH_PROJECT = "social-science-idea-generation"
S3_BUCKET = "mind-technology-lab-experiments"
EXPERIMENT_NAME = "social_science_idea_generation_2026_10_21"
DISCUSSION_ITERATIONS = 2
INPUT_USD_PER_MILLION = 2.0
OUTPUT_USD_PER_MILLION = 10.0
PRICE_PAGE_URL = "https://developers.openai.com/api/docs/models/gpt-6-sol"
