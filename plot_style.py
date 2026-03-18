from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import seaborn as sns


PALETTE = ["#1f4e79", "#2a9d8f", "#e76f51", "#6d597a", "#f4a261"]


def apply_publication_style() -> None:
    """Unified figure style for report/defense-ready visualizations."""
    sns.set_theme(style="whitegrid", context="talk", palette=PALETTE)
    plt.rcParams.update(
        {
            "figure.figsize": (10, 5),
            "figure.dpi": 120,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "font.family": "serif",
            "font.size": 11,
            "axes.titlesize": 14,
            "axes.labelsize": 12,
            "axes.titleweight": "bold",
            "axes.facecolor": "#fcfcfc",
            "axes.edgecolor": "#333333",
            "axes.linewidth": 0.8,
            "grid.color": "#d9d9d9",
            "grid.linewidth": 0.8,
            "legend.frameon": True,
            "legend.framealpha": 0.9,
            "legend.edgecolor": "#cccccc",
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
        }
    )


def save_figure(path: Path) -> None:
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()
