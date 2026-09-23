"""Send one single-post Jev request to confirm the TypeSafe key works.

Run from the experiment folder:

    uv run python scripts/check_typesafe_key.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from typesafe_sdk import Noul, RetryPolicy, TypeSafeClient

EXPERIMENT_ROOT = Path(__file__).resolve().parent.parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

from shared.brady_definition import BRADY_MORAL_OUTRAGE_INSTRUCTIONS  # noqa: E402
from shared.data import load_sample  # noqa: E402
from shared.secrets import load_typesafe_api_key  # noqa: E402

JEV_MODEL_ID = "jev-1.13.0"
JEV_QUESTION_ID = "moral_outrage"
NOUL_DECIMAL_PLACES = 4
REQUEST_TIMEOUT_SECONDS = 30.0


def _first_post_text() -> str:
    """Return the text of the first sample post."""
    sample = load_sample()
    return str(sample.iloc[0]["text"])


def _build_client() -> TypeSafeClient:
    """Build a TypeSafe client with SDK retries disabled."""
    return TypeSafeClient(
        api_key=load_typesafe_api_key(),
        model=JEV_MODEL_ID,
        retry=RetryPolicy(max_retries=0),
        timeout=REQUEST_TIMEOUT_SECONDS,
    )


def _score_one_post(client: TypeSafeClient, text: str) -> object:
    """Score one post with the Brady moral-outrage question."""
    return client.system_one(
        state=text,
        questions={
            JEV_QUESTION_ID: Noul(instructions=BRADY_MORAL_OUTRAGE_INSTRUCTIONS)
        },
        model=JEV_MODEL_ID,
    )


def main() -> None:
    """Load the key, score the first sample post, and print an ok line."""
    response = _score_one_post(_build_client(), _first_post_text())
    answer = response.answers[JEV_QUESTION_ID]
    noul = round(float(answer.noul), NOUL_DECIMAL_PLACES)
    input_tokens = response.usage.input_tokens
    print(f"ok model={response.model} noul={noul} input_tokens={input_tokens}")


if __name__ == "__main__":
    main()
