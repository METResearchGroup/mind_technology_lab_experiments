"""Run all seven smoke scorers and write the RESULTS smoke table.

Run from the experiment folder:

    uv run python -m models.smoke_tests
"""

from pathlib import Path

from models.smoke_tests import bedrock, jev, perspective_api
from models.smoke_tests.table import (
    SMOKE_STOP_MESSAGE,
    build_smoke_table,
    render_smoke_markdown,
)

RESULTS_PATH = Path(__file__).resolve().parents[2] / "RESULTS.md"
SMOKE_HEADING = "## Smoke"


def main() -> None:
    records = []
    records.extend(jev.score_smoke_texts())
    records.extend(perspective_api.score_smoke_texts())
    records.extend(bedrock.score_smoke_texts())
    rows = build_smoke_table(records)
    markdown = render_smoke_markdown(rows)
    _write_results_smoke_section(markdown)
    print(markdown)
    print(SMOKE_STOP_MESSAGE)


def _write_results_smoke_section(table_markdown: str) -> None:
    body = (
        "# Results\n\n"
        "Sample comparison tables are empty until Step 7.\n\n"
        f"{SMOKE_HEADING}\n\n"
        f"{table_markdown}\n\n"
        "Jev estimated cost is `unknown` because TypeSafe has no public token price.\n"
    )
    RESULTS_PATH.write_text(body, encoding="utf-8")


if __name__ == "__main__":
    main()
