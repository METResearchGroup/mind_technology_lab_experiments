"""Live Bedrock smoke on the three fixed texts for each locked model.

Run from the experiment folder:

    uv run python -m models.smoke_tests.bedrock
"""

from models.bedrock import BedrockEngine
from models.smoke_tests.texts import SMOKE_TEXTS
from shared.records import BEDROCK_MODEL_IDS, PredictionRecord


def score_smoke_texts() -> list[PredictionRecord]:
    """Classify SMOKE_TEXTS with each of the five Bedrock model IDs."""
    records: list[PredictionRecord] = []
    for model_id in BEDROCK_MODEL_IDS:
        print(f"Bedrock smoke scoring {model_id}", flush=True)
        engine = BedrockEngine(model_id)
        try:
            records.extend(engine.label_one(text) for text in SMOKE_TEXTS)
        except Exception as exc:
            raise SystemExit(f"Bedrock smoke failed for {model_id}: {exc}") from exc
    return records


def main() -> None:
    records = score_smoke_texts()
    print(f"Bedrock smoke scored {len(records)} texts")


if __name__ == "__main__":
    main()
