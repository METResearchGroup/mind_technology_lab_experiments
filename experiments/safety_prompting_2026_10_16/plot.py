# ruff: noqa: E501
"""Write the grouped bar chart of complete-refusal rates.

Run from the repository root after grader.py --all:

    uv run --project experiments/safety_prompting_2026_10_16 python -m experiments.safety_prompting_2026_10_16.grader --write-summary
"""

from __future__ import annotations

from pathlib import Path

CONTROL_LABEL = "Control"
BOLD_LABEL = "Bold prompt"
SHAME_LABEL = "Shame prompt"
CONTROL_COLOR = "#8a8a8a"
BOLD_COLOR = "#3d5a80"
SHAME_COLOR = "#c44536"
SERIES = (
    (CONTROL_LABEL, CONTROL_COLOR),
    (BOLD_LABEL, BOLD_COLOR),
    (SHAME_LABEL, SHAME_COLOR),
)
X_AXIS_LABEL = "Dataset"
Y_AXIS_LABEL = "Percentage refusal"


def write_refusal_chart(
    rows: list[tuple[str, float, float, float]],
    path: Path,
) -> None:
    """Write a grouped bar chart as SVG.

    Parameters
    ----------
    rows
        One tuple per dataset: label, then percent refused for Control, the
        bold prompt, and the shame prompt. Percents are on a 0 to 100 scale.
    path
        Destination SVG path. Parent directories are created when missing.
    """
    if not rows:
        raise ValueError("refusal chart needs at least one dataset")
    width = 720
    height = 420
    margin_left = 96
    margin_right = 24
    margin_top = 78
    margin_bottom = 72
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom
    y_max = 100.0
    group_width = plot_width / len(rows)
    series_count = len(SERIES)
    bar_gap = 6.0
    bar_width = min(
        28.0, (group_width * 0.72 - bar_gap * (series_count - 1)) / series_count
    )
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="360" y="24" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="16" fill="#1a1a1a">Complete refusal rate by dataset</text>',
        *_legend_row(48),
        f'<text x="28" y="{margin_top + plot_height / 2}" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="13" fill="#333333" transform="rotate(-90 28 {margin_top + plot_height / 2})">{_escape(Y_AXIS_LABEL)}</text>',
    ]
    for tick in range(0, 101, 20):
        y = margin_top + plot_height * (1 - tick / y_max)
        parts.append(
            f'<line x1="{margin_left}" y1="{y:.1f}" x2="{width - margin_right}" y2="{y:.1f}" stroke="#e6e6e6" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{margin_left - 8}" y="{y + 4:.1f}" text-anchor="end" font-family="Helvetica, Arial, sans-serif" font-size="11" fill="#333333">{tick}</text>'
        )
    axis_bottom = margin_top + plot_height
    parts.append(
        f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{axis_bottom}" stroke="#333333" stroke-width="1"/>'
    )
    parts.append(
        f'<line x1="{margin_left}" y1="{axis_bottom}" x2="{width - margin_right}" y2="{axis_bottom}" stroke="#333333" stroke-width="1"/>'
    )
    for index, (label, *values) in enumerate(rows):
        if len(values) != series_count:
            raise ValueError(
                f"{label} has {len(values)} values, expected {series_count}"
            )
        center = margin_left + group_width * (index + 0.5)
        group_span = series_count * bar_width + (series_count - 1) * bar_gap
        origin = center - group_span / 2
        for series_index, value in enumerate(values):
            color = SERIES[series_index][1]
            x = origin + series_index * (bar_width + bar_gap)
            parts.append(
                _bar(x, axis_bottom, bar_width, plot_height, value, y_max, color)
            )
            parts.append(
                _value_label(x + bar_width / 2, axis_bottom, plot_height, value, y_max)
            )
        parts.append(
            f'<text x="{center:.1f}" y="{axis_bottom + 22}" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="12" fill="#1a1a1a">{_escape(label)}</text>'
        )
    parts.append(
        f'<text x="{margin_left + plot_width / 2}" y="{height - 16}" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="13" fill="#333333">{_escape(X_AXIS_LABEL)}</text>'
    )
    parts.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts) + "\n")


def _bar(
    x: float,
    axis_bottom: float,
    bar_width: float,
    plot_height: float,
    value: float,
    y_max: float,
    color: str,
) -> str:
    height = plot_height * (value / y_max)
    y = axis_bottom - height
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{height:.1f}" fill="{color}"/>'


def _value_label(
    x: float,
    axis_bottom: float,
    plot_height: float,
    value: float,
    y_max: float,
) -> str:
    height = plot_height * (value / y_max)
    y = axis_bottom - height - 6
    return f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="11" fill="#1a1a1a">{value:.1f}</text>'


def _legend_row(y: float) -> list[str]:
    widths = [30 + 7 * len(label) for _color, label in SERIES]
    gap = 28.0
    total = sum(widths) + gap * (len(SERIES) - 1)
    cursor = (720 - total) / 2
    items: list[str] = []
    for (label, color), item_width in zip(SERIES, widths, strict=True):
        items.append(_legend(cursor, y, color, label))
        cursor += item_width + gap
    return items


def _legend(x: float, y: float, color: str, label: str) -> str:
    return (
        f'<rect x="{x}" y="{y - 10}" width="12" height="12" fill="{color}"/>'
        f'<text x="{x + 18}" y="{y}" font-family="Helvetica, Arial, sans-serif" font-size="12" fill="#1a1a1a">{_escape(label)}</text>'
    )


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
