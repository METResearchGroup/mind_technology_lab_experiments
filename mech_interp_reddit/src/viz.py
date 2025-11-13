from typing import Dict, Optional
import os
import matplotlib.pyplot as plt


def plot_bar(scores: Dict[str, float], title: str, out_path: Optional[str] = None) -> None:
    concepts = list(scores.keys())
    vals = [scores[c] for c in concepts]

    # Wider figure to avoid label overlap; scale with number of concepts
    fig_width = max(8, 1.4 * len(concepts))
    fig, ax = plt.subplots(figsize=(fig_width, 4))

    bars = ax.bar(concepts, vals, color="#4C78A8")
    # Give headroom so values at 1.0 don't touch the top
    ax.set_ylim(0.0, 1.05)
    ax.set_ylabel("Relative activation (0–1)")
    ax.set_title(title, pad=18)
    # Rotate x labels slightly to improve spacing
    ax.set_xticklabels(concepts, rotation=20, ha="right")
    # Remove top spine for cleaner top boundary
    ax.spines["top"].set_visible(False)

    for bar, v in zip(bars, vals):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            min(v + 0.02, 1.04),
            f"{v:.2f}",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    fig.tight_layout()

    if out_path:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.show()


