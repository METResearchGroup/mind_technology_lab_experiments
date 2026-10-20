"""Upload artifacts to the lab S3 prefix (implemented in step 7).

Run from the experiment folder:

    uv run python scripts/upload_s3.py
"""

from __future__ import annotations

S3_PREFIX = "s3://mind-technology-lab-experiments/experiments/safety_decision_models_2026_10_19/"


def main() -> None:
    """Stub until step 7 implements uploads (skips Do-Not-Answer question text)."""
    print(f"upload_s3 stub: target prefix {S3_PREFIX}")


if __name__ == "__main__":
    main()
