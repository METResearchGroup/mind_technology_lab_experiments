"""Perspective smoke on three stored labeled rows.

Run from the experiment folder:

    uv run python -m models.smoke_tests.perspective_api
"""

from models.perspective_api import PerspectiveApiEngine
from shared.data import (
    PERSPECTIVE_SMOKE_SOURCE_ROW_IDS,
    download_perspective_labels_csv,
    load_perspective_labels_frame,
)
from shared.records import PredictionRecord


def score_smoke_texts() -> list[PredictionRecord]:
    """Classify the three locked stored Perspective rows."""
    labels = load_perspective_labels_frame(download_perspective_labels_csv())
    by_id = {
        str(row.source_row_id): str(row.text) for row in labels.itertuples(index=False)
    }
    engine = PerspectiveApiEngine()
    records: list[PredictionRecord] = []
    for source_row_id in PERSPECTIVE_SMOKE_SOURCE_ROW_IDS:
        text = by_id[source_row_id]
        records.append(engine.label_one(text))
    return records


def main() -> None:
    records = score_smoke_texts()
    print(f"Perspective smoke scored {len(records)} texts")


if __name__ == "__main__":
    main()
