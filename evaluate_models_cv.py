"""
Enhanced model evaluation using Stratified K-Fold Cross-Validation.
Provides more robust performance estimates especially for imbalanced datasets.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from plot_style import apply_publication_style, save_figure
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import StratifiedKFold


apply_publication_style()


def load_full_dataset(processed_dir: Path) -> pd.DataFrame:
    """Load train + val + test combined dataset."""
    train_df = pd.read_csv(processed_dir / "train_model_ready.csv")
    val_df = pd.read_csv(processed_dir / "val_model_ready.csv")
    test_df = pd.read_csv(processed_dir / "test_model_ready.csv")
    return pd.concat([train_df, val_df, test_df], ignore_index=True)


def load_test_split(processed_dir: Path) -> pd.DataFrame:
    """Load only test split for final hold-out evaluation."""
    return pd.read_csv(processed_dir / "test_model_ready.csv")


def prepare_xy(df: pd.DataFrame, threshold: float) -> tuple[pd.DataFrame, pd.Series]:
    feature_cols = [c for c in df.columns if c not in {"date", "pm25"}]
    x = df[feature_cols].copy()
    y = (df["pm25"] >= threshold).astype(int)
    return x, y


def infer_proba(model_artifact, x: pd.DataFrame, model_name: str) -> np.ndarray:
    """Get probability predictions from trained model artifact."""
    if model_name in {"LogisticRegression", "RandomForest"}:
        model = model_artifact["pipeline"]
        cols = model_artifact["features"]
        return model.predict_proba(x[cols])[:, 1]

    if model_name in {"XGBoost", "LightGBM", "GradientBoosting", "SklearnHistGradientBoosting"}:
        model = model_artifact["model"]
        imputer = model_artifact["imputer"]
        cols = model_artifact["features"]
        x_mat = imputer.transform(x[cols])
        return model.predict_proba(x_mat)[:, 1]

    raise ValueError(f"Unsupported model name: {model_name}")


def compute_metrics(y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.5) -> dict[str, float]:
    """Compute classification metrics."""
    y_pred = (y_prob >= threshold).astype(int)
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
        "pr_auc": float(average_precision_score(y_true, y_prob)),
    }


def stratified_cv_evaluation(
    model_artifact: dict,
    model_name: str,
    x: pd.DataFrame,
    y: np.ndarray,
    n_splits: int = 5,
    threshold: float = 0.5,
) -> tuple[dict[str, list[float]], dict[str, float]]:
    """
    Perform stratified k-fold cross-validation evaluation.

    Returns:
        fold_results: dict of metric -> list of fold scores
        summary: dict of metric -> (mean, std, min, max)
    """
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    fold_results = {
        "accuracy": [],
        "precision": [],
        "recall": [],
        "f1": [],
        "roc_auc": [],
        "pr_auc": [],
    }

    print(f"\n{'='*60}")
    print(f"Cross-validation for: {model_name}")
    print(f"{'='*60}")

    for fold_idx, (train_idx, test_idx) in enumerate(skf.split(x, y)):
        x_fold_train = x.iloc[train_idx]
        y_fold_train = y[train_idx]
        x_fold_test = x.iloc[test_idx]
        y_fold_test = y[test_idx]

        # Compute metrics on fold test set
        try:
            y_prob = infer_proba(model_artifact, x_fold_test, model_name)
            metrics = compute_metrics(y_fold_test, y_prob, threshold)

            print(f"\nFold {fold_idx + 1}/{n_splits}:")
            print(f"  Samples - Train: {len(train_idx)}, Test: {len(test_idx)}")
            print(f"  Positive (test): {y_fold_test.sum()}/{len(test_idx)} ({100*y_fold_test.sum()/len(test_idx):.1f}%)")
            print(f"  F1: {metrics['f1']:.4f}, Precision: {metrics['precision']:.4f}, Recall: {metrics['recall']:.4f}")

            for metric_name, value in metrics.items():
                fold_results[metric_name].append(value)

        except Exception as e:
            print(f"  Error in fold {fold_idx + 1}: {e}")
            continue

    # Compute summary statistics
    summary = {}
    for metric_name, values in fold_results.items():
        if values:
            summary[metric_name] = {
                "mean": float(np.mean(values)),
                "std": float(np.std(values)),
                "min": float(np.min(values)),
                "max": float(np.max(values)),
            }

    return fold_results, summary


def plot_cv_results(
    cv_results: dict[str, tuple[dict, dict]], out_path: Path
) -> None:
    """Plot cross-validation results with error bars."""
    metrics = ["f1", "precision", "recall", "roc_auc", "pr_auc"]
    fig, axes = plt.subplots(1, len(metrics), figsize=(18, 4))

    for ax, metric in zip(axes, metrics):
        models = []
        means = []
        stds = []

        for model_name, (_, summary) in cv_results.items():
            if metric in summary:
                models.append(model_name)
                means.append(summary[metric]["mean"])
                stds.append(summary[metric]["std"])

        x_pos = np.arange(len(models))
        ax.bar(x_pos, means, yerr=stds, capsize=5, alpha=0.7, color="steelblue")
        ax.set_xticks(x_pos)
        ax.set_xticklabels(models, rotation=45, ha="right")
        ax.set_ylabel("Score")
        ax.set_title(f"{metric.upper()}\n(mean ± std)")
        ax.set_ylim(0, 1)

    plt.tight_layout()
    save_figure(out_path)


def plot_cv_distributions(
    cv_results: dict[str, dict], out_path: Path
) -> None:
    """Plot distributions of cross-validation scores as box plots."""
    metrics = ["f1", "precision", "recall", "roc_auc", "pr_auc"]
    fig, axes = plt.subplots(1, len(metrics), figsize=(18, 4))

    for ax, metric in zip(axes, metrics):
        data_to_plot = []
        labels = []

        for model_name, fold_results in cv_results.items():
            if metric in fold_results:
                data_to_plot.append(fold_results[metric])
                labels.append(model_name)

        ax.boxplot(data_to_plot, labels=labels)
        ax.set_ylabel("Score")
        ax.set_title(f"{metric.upper()}\n(CV Distribution)")
        ax.set_ylim(0, 1)
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")

    plt.tight_layout()
    save_figure(out_path)


def create_cv_summary_table(
    cv_results: dict[str, tuple[dict, dict]], out_path: Path
) -> pd.DataFrame:
    """Create detailed summary table of CV results."""
    rows = []
    for model_name, (fold_results, summary) in cv_results.items():
        row = {"model": model_name}
        for metric in ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"]:
            if metric in summary:
                mean = summary[metric]["mean"]
                std = summary[metric]["std"]
                row[f"{metric}_mean"] = mean
                row[f"{metric}_std"] = std
                row[f"{metric}_display"] = f"{mean:.4f} ± {std:.4f}"
        rows.append(row)

    df = pd.DataFrame(rows).sort_values("f1_mean", ascending=False).reset_index(drop=True)
    df.to_csv(out_path, index=False)
    return df


def main() -> None:
    root = Path(__file__).resolve().parent
    processed_dir = root / "processed"
    model_dir = processed_dir / "model_outputs"
    eval_dir = model_dir / "evaluation"
    eval_dir.mkdir(parents=True, exist_ok=True)

    # Load models and data
    print("\nLoading trained models...")
    logistic = joblib.load(model_dir / "logistic_regression_model.joblib")
    rf = joblib.load(model_dir / "random_forest_model.joblib")
    gb = joblib.load(model_dir / "gradient_boosting_model.joblib")

    threshold = float(logistic.get("pm25_threshold", 25.0))
    print(f"PM2.5 threshold: {threshold} ug/m3")

    model_artifacts = {
        "LogisticRegression": logistic,
        "RandomForest": rf,
        str(gb.get("backend", "GradientBoosting")): gb,
    }

    # PART 1: Cross-validation evaluation on train+val dataset
    print("\n" + "=" * 70)
    print("PART 1: STRATIFIED K-FOLD CROSS-VALIDATION (on train+val data)")
    print("=" * 70)

    combined_df = pd.concat(
        [
            pd.read_csv(processed_dir / "train_model_ready.csv"),
            pd.read_csv(processed_dir / "val_model_ready.csv"),
        ],
        ignore_index=True,
    )
    x_combined, y_combined = prepare_xy(combined_df, threshold=threshold)

    cv_results = {}
    for model_name, artifact in model_artifacts.items():
        fold_results, summary = stratified_cv_evaluation(
            artifact, model_name, x_combined, y_combined, n_splits=5, threshold=0.5
        )
        cv_results[model_name] = (fold_results, summary)

        print(f"\n{model_name} - Summary (5-Fold CV):")
        for metric in ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"]:
            if metric in summary:
                mean = summary[metric]["mean"]
                std = summary[metric]["std"]
                print(f"  {metric:12s}: {mean:.4f} ± {std:.4f}")

    # Save CV results
    cv_summary_df = create_cv_summary_table(cv_results, eval_dir / "cv_summary.csv")
    print(f"\nCV summary saved to: {eval_dir / 'cv_summary.csv'}")

    # Create visualizations for CV
    plot_cv_results(cv_results, eval_dir / "cv_results_bars.png")
    print(f"CV bar plot saved to: {eval_dir / 'cv_results_bars.png'}")

    plot_cv_distributions(
        {name: fold_results for name, (fold_results, _) in cv_results.items()},
        eval_dir / "cv_results_distributions.png",
    )
    print(f"CV distribution plot saved to: {eval_dir / 'cv_results_distributions.png'}")

    # PART 2: Final hold-out test set evaluation
    print("\n" + "=" * 70)
    print("PART 2: FINAL HOLD-OUT TEST SET EVALUATION")
    print("=" * 70)

    test_df = load_test_split(processed_dir)
    x_test, y_test = prepare_xy(test_df, threshold=threshold)

    summary_rows: list[dict] = []
    y_probs: dict[str, np.ndarray] = {}
    roc_data: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    pr_data: dict[str, tuple[np.ndarray, np.ndarray]] = {}

    for model_name, artifact in model_artifacts.items():
        prob = infer_proba(artifact, x_test, model_name)
        y_probs[model_name] = prob
        metrics = compute_metrics(y_test.values, prob)
        summary_rows.append({"model": model_name, **metrics})

        print(f"\n{model_name}:")
        for metric, value in metrics.items():
            print(f"  {metric:12s}: {value:.4f}")

        fpr, tpr, _ = roc_curve(y_test.values, prob)
        precision_vals, recall_vals, _ = precision_recall_curve(y_test.values, prob)
        roc_data[model_name] = (fpr, tpr)
        pr_data[model_name] = (precision_vals, recall_vals)

    summary_df = pd.DataFrame(summary_rows).sort_values("f1", ascending=False).reset_index(drop=True)
    summary_df.to_csv(eval_dir / "test_set_evaluation.csv", index=False)
    print(f"\nTest set evaluation saved to: {eval_dir / 'test_set_evaluation.csv'}")

    # Test set visualizations
    plot_roc_curves(roc_data, eval_dir / "roc_curves_test.png")
    plot_pr_curves(pr_data, eval_dir / "pr_curves_test.png")
    plot_confusion_matrices(y_test, y_probs, eval_dir / "confusion_matrices_test.png")

    print(f"\nTest visualizations saved to: {eval_dir}/")

    # Summary report
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("\nCross-Validation (train+val, 5-fold):")
    print(cv_summary_df.to_string(index=False))
    print("\n\nFinal Hold-Out Test Set:")
    print(summary_df.to_string(index=False))

    print(f"\nAll results saved to: {eval_dir}/")
    print("\nGenerated files:")
    print("  - cv_summary.csv: CV results with mean ± std")
    print("  - cv_results_bars.png: CV results with error bars")
    print("  - cv_results_distributions.png: CV score distributions")
    print("  - test_set_evaluation.csv: Final test set metrics")
    print("  - roc_curves_test.png: ROC curves on test set")
    print("  - pr_curves_test.png: Precision-Recall curves on test set")
    print("  - confusion_matrices_test.png: Confusion matrices on test set")


def plot_roc_curves(curve_data: dict[str, tuple[np.ndarray, np.ndarray]], out_path: Path) -> None:
    plt.figure(figsize=(7, 6))
    for model_name, (fpr, tpr) in curve_data.items():
        plt.plot(fpr, tpr, label=model_name, linewidth=2.0)
    plt.plot([0, 1], [0, 1], "--", linewidth=1.2, color="#444444")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("ROC Curves - Test Set")
    plt.legend()
    plt.tight_layout()
    save_figure(out_path)


def plot_pr_curves(curve_data: dict[str, tuple[np.ndarray, np.ndarray]], out_path: Path) -> None:
    plt.figure(figsize=(7, 6))
    for model_name, (precision, recall) in curve_data.items():
        plt.plot(recall, precision, label=model_name, linewidth=2.0)
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title("Precision-Recall Curves - Test Set")
    plt.legend()
    plt.tight_layout()
    save_figure(out_path)


def plot_confusion_matrices(y_true: pd.Series, y_probs: dict[str, np.ndarray], out_path: Path) -> None:
    names = list(y_probs.keys())
    fig, axes = plt.subplots(1, len(names), figsize=(5 * len(names), 4))
    if len(names) == 1:
        axes = [axes]

    for ax, name in zip(axes, names):
        y_pred = (y_probs[name] >= 0.5).astype(int)
        cm = confusion_matrix(y_true.values, y_pred)
        sns.heatmap(cm, annot=True, fmt="d", cmap="YlGnBu", cbar=False, ax=ax)
        ax.set_title(name)
        ax.set_xlabel("Predicted")
        ax.set_ylabel("True")

    plt.tight_layout()
    save_figure(out_path)


if __name__ == "__main__":
    main()
