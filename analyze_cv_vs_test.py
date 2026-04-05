"""
Detailed comparison analysis: Cross-Validation vs Hold-Out Test Set
Reveals potential overfitting and generalization gaps
"""

from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from plot_style import apply_publication_style, save_figure

apply_publication_style()


def load_results(eval_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load CV summary and test evaluation results."""
    cv_df = pd.read_csv(eval_dir / "cv_summary.csv")
    test_df = pd.read_csv(eval_dir / "test_set_evaluation.csv")
    return cv_df, test_df


def create_comparison_table(cv_df: pd.DataFrame, test_df: pd.DataFrame, eval_dir: Path) -> pd.DataFrame:
    """Create detailed comparison between CV and test set performance."""

    metrics = ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"]
    rows = []

    for idx, row in test_df.iterrows():
        model_name = row["model"]
        cv_row = cv_df[cv_df["model"] == model_name].iloc[0]

        for metric in metrics:
            cv_mean = cv_row[f"{metric}_mean"]
            test_value = row[metric]
            gap = cv_mean - test_value
            gap_pct = (gap / cv_mean * 100) if cv_mean > 0 else 0

            rows.append({
                "Model": model_name,
                "Metric": metric.upper(),
                "CV_Mean": f"{cv_mean:.4f}",
                "Test": f"{test_value:.4f}",
                "Gap": f"{gap:.4f}",
                "Gap_%": f"{gap_pct:.1f}%",
                "Overfitting_Signal": "HIGH" if gap > 0.15 else ("MED" if gap > 0.05 else "LOW"),
            })

    comp_df = pd.DataFrame(rows)
    comp_df.to_csv(eval_dir / "cv_vs_test_comparison.csv", index=False)
    return comp_df


def plot_cv_vs_test_comparison(cv_df: pd.DataFrame, test_df: pd.DataFrame, eval_dir: Path) -> None:
    """Plot side-by-side comparison of CV vs Test performance."""

    metrics = ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"]
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()

    for ax, metric in zip(axes, metrics):
        models = test_df["model"].tolist()
        x = np.arange(len(models))
        width = 0.35

        # CV values (mean)
        cv_means = []
        cv_stds = []
        for model in models:
            cv_row = cv_df[cv_df["model"] == model].iloc[0]
            cv_means.append(cv_row[f"{metric}_mean"])
            cv_stds.append(cv_row[f"{metric}_std"])

        # Test values
        test_values = test_df[metric].tolist()

        # Plot
        ax.bar(x - width/2, cv_means, width, label="CV (mean)", alpha=0.8, yerr=cv_stds, capsize=5)
        ax.bar(x + width/2, test_values, width, label="Test Set", alpha=0.8)

        ax.set_ylabel("Score")
        ax.set_title(f"{metric.upper()}\nCV vs Test Set")
        ax.set_xticks(x)
        ax.set_xticklabels(models, rotation=45, ha="right")
        ax.set_ylim(0, 1.05)
        ax.legend()
        ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    save_figure(eval_dir / "cv_vs_test_comparison.png")


def calculate_generalization_gap(cv_df: pd.DataFrame, test_df: pd.DataFrame) -> dict:
    """Calculate average generalization gap per model."""

    metrics = ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"]
    gaps = {}

    for idx, row in test_df.iterrows():
        model_name = row["model"]
        cv_row = cv_df[cv_df["model"] == model_name].iloc[0]

        model_gaps = []
        for metric in metrics:
            cv_mean = cv_row[f"{metric}_mean"]
            test_value = row[metric]
            gap = cv_mean - test_value
            model_gaps.append(gap)

        gaps[model_name] = {
            "mean_gap": np.mean(model_gaps),
            "max_gap": np.max(model_gaps),
            "max_gap_metric": metrics[np.argmax(model_gaps)],
        }

    return gaps


def plot_generalization_gaps(gaps: dict, eval_dir: Path) -> None:
    """Plot generalization gaps across models."""

    models = list(gaps.keys())
    mean_gaps = [gaps[m]["mean_gap"] for m in models]
    max_gaps = [gaps[m]["max_gap"] for m in models]

    fig, ax = plt.subplots(figsize=(10, 6))

    x = np.arange(len(models))
    width = 0.35

    ax.bar(x - width/2, mean_gaps, width, label="Mean Gap Across Metrics", alpha=0.8)
    ax.bar(x + width/2, max_gaps, width, label="Max Gap (Single Metric)", alpha=0.8)

    ax.set_ylabel("Generalization Gap (CV - Test)")
    ax.set_title("Generalization Gap Analysis\n(Higher = More Overfitting)")
    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=45, ha="right")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    ax.axhline(y=0.05, color="red", linestyle="--", linewidth=1, label="Warning Threshold (5%)")

    plt.tight_layout()
    save_figure(eval_dir / "generalization_gaps.png")


def generate_analysis_report(cv_df: pd.DataFrame, test_df: pd.DataFrame,
                             comp_df: pd.DataFrame, gaps: dict, eval_dir: Path) -> None:
    """Generate text analysis report."""

    report = []
    report.append("=" * 80)
    report.append("CV vs TEST SET COMPARISON ANALYSIS")
    report.append("=" * 80)

    report.append("\n1. EXECUTIVE SUMMARY\n")
    report.append("This analysis compares model performance on:")
    report.append("  - Cross-Validation (CV): 5-fold stratified split on train+val data")
    report.append("  - Test Set: Final hold-out test set (unseen during training)")
    report.append("\nKey Finding: Significant gap between CV and Test suggests OVERFITTING")

    report.append("\n\n2. MODEL-LEVEL ANALYSIS\n")

    for model_name in test_df["model"].tolist():
        report.append(f"\n{model_name}")
        report.append("-" * 60)

        gap_info = gaps[model_name]
        cv_row = cv_df[cv_df["model"] == model_name].iloc[0]
        test_row = test_df[test_df["model"] == model_name].iloc[0]

        report.append(f"Average Generalization Gap: {gap_info['mean_gap']:.4f}")
        report.append(f"Maximum Gap (on {gap_info['max_gap_metric'].upper()}): {gap_info['max_gap']:.4f}")

        if gap_info['mean_gap'] > 0.1:
            report.append("Overfitting Level: SEVERE - Model significantly overfit to train+val data")
        elif gap_info['mean_gap'] > 0.05:
            report.append("Overfitting Level: MODERATE - Model shows signs of overfitting")
        else:
            report.append("Overfitting Level: MINIMAL - Good generalization observed")

        report.append(f"\nF1 Score Performance:")
        report.append(f"  CV Mean F1: {cv_row['f1_mean']:.4f}")
        report.append(f"  Test F1:    {test_row['f1']:.4f}")
        report.append(f"  Gap:        {cv_row['f1_mean'] - test_row['f1']:.4f}")

    report.append("\n\n3. KEY FINDINGS\n")

    # Identify most overfit metric
    all_gaps = []
    for idx, row in test_df.iterrows():
        model = row["model"]
        cv_row = cv_df[cv_df["model"] == model].iloc[0]
        metrics = ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"]
        for metric in metrics:
            gap = cv_row[f"{metric}_mean"] - row[metric]
            all_gaps.append((model, metric, gap))

    all_gaps.sort(key=lambda x: x[2], reverse=True)

    report.append("Largest Performance Gaps (most overfitting):")
    for model, metric, gap in all_gaps[:5]:
        report.append(f"  {model} - {metric.upper()}: {gap:.4f}")

    # Model ranking by generalization
    report.append("\n\nModel Ranking by Generalization Quality:")
    sorted_models = sorted(gaps.items(), key=lambda x: x[1]["mean_gap"])
    for rank, (model, gap_data) in enumerate(sorted_models, 1):
        report.append(f"  {rank}. {model}: avg gap = {gap_data['mean_gap']:.4f}")

    report.append("\n\n4. RECOMMENDATIONS\n")

    worst_model = sorted_models[-1][0]
    report.append(f"Most Overfit Model: {worst_model}")
    report.append("\nActions to Address Overfitting:")
    report.append("  1. Reduce model complexity (prune trees, reduce depth)")
    report.append("  2. Increase regularization (L1/L2 penalty)")
    report.append("  3. Use class weights to balance the imbalanced dataset better")
    report.append("  4. Increase training data or apply data augmentation")
    report.append("  5. Use ensemble methods with diverse weak learners")
    report.append("  6. Implement early stopping based on validation performance")

    report.append("\n" + "=" * 80)

    report_text = "\n".join(report)

    # Save to file
    with open(eval_dir / "cv_vs_test_analysis_report.txt", "w") as f:
        f.write(report_text)

    # Print to console
    print(report_text)


def main() -> None:
    root = Path(__file__).resolve().parent
    eval_dir = root / "processed" / "model_outputs" / "evaluation"

    print("\nLoading results...")
    cv_df, test_df = load_results(eval_dir)

    print("Creating comparison table...")
    comp_df = create_comparison_table(cv_df, test_df, eval_dir)

    print("Calculating generalization gaps...")
    gaps = calculate_generalization_gap(cv_df, test_df)

    print("Generating visualizations...")
    plot_cv_vs_test_comparison(cv_df, test_df, eval_dir)
    plot_generalization_gaps(gaps, eval_dir)

    print("Generating analysis report...")
    generate_analysis_report(cv_df, test_df, comp_df, gaps, eval_dir)

    print(f"\nAnalysis complete. Results saved to {eval_dir}/")
    print("\nGenerated files:")
    print("  - cv_vs_test_comparison.csv: Detailed comparison table")
    print("  - cv_vs_test_comparison.png: Visual comparison chart")
    print("  - generalization_gaps.png: Overfitting visualization")
    print("  - cv_vs_test_analysis_report.txt: Detailed analysis report")


if __name__ == "__main__":
    main()
