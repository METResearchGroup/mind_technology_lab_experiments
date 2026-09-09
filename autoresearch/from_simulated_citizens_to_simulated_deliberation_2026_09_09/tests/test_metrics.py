from __future__ import annotations

from metrics import (
    GroupShare,
    a_share,
    direction_matches,
    is_divisive,
    mean_absolute_gap,
    movement_rate,
)


def test_a_share_ignores_invalid() -> None:
    assert a_share(["A", "B", None, "A"]) == 200.0 / 3


def test_mean_absolute_gap() -> None:
    rows = [
        GroupShare("q", "sex", "Male", 90.0, 50.0, 10),
        GroupShare("q", "sex", "Female", 80.0, 70.0, 10),
    ]
    assert mean_absolute_gap(rows) == 25.0


def test_direction_matches_skips_ties() -> None:
    rows = [
        GroupShare("q", "sex", "Male", 90.0, 50.0, 10),
        GroupShare("q", "sex", "Female", 70.0, 50.0, 10),
        GroupShare("q", "age_env", "19-29", 10.0, 80.0, 10),
        GroupShare("q", "age_env", "60+", 90.0, 40.0, 10),
    ]
    matches, total = direction_matches(rows)
    assert total == 1
    assert matches == 0


def test_divisive_cutoff() -> None:
    assert is_divisive(62.0)
    assert not is_divisive(96.0)


def test_movement_rate() -> None:
    assert movement_rate(["A", "A", "B"], ["B", "A", "B"]) == 1 / 3
