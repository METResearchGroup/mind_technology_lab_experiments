"""Live Perspective smoke on the three fixed texts.

Run from the experiment folder:

    uv run python -m models.smoke_tests.perspective_api
"""

from models.perspective_api import PerspectiveApiEngine
from models.smoke_tests.texts import SMOKE_TEXTS
from shared.records import PredictionRecord


def score_smoke_texts() -> list[PredictionRecord]:
    """Classify SMOKE_TEXTS with Perspective MORAL_OUTRAGE."""
    engine = PerspectiveApiEngine()
    return [engine.label_one(text) for text in SMOKE_TEXTS]


def main() -> None:
    records = score_smoke_texts()
    print(f"Perspective smoke scored {len(records)} texts")


if __name__ == "__main__":
    main()
