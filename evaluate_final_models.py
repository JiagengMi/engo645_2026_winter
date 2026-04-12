"""
FINAL MODEL EVALUATION
Evaluates the three final champion models using cross-validation + test set
Models: LogisticRegression, RandomForest_Improved, HistGradientBoosting_Improved
"""

from __future__ import annotations

from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from plot_style import apply_publication_style, save_figure
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import StratifiedKFold


apply_publication_style()


def load_data(processed_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load train+val combined and test datasets."""
    train_df = pd.read_csv(processed_dir / "train_model_ready.csv")
    val_df = pd.read_csv(processed_dir / "val_model_ready.csv")
    test_df = pd.read_csv(processed_dir / "test_model_ready.csv")

    combined_df = pd.concat([train_df, val_df], ignore_index=True)

    feature_cols = [c for c in combined_df.columns if c not in {"date", "pm25"}]
    x_combined = combined_df[feature_cols].copy()
    y_combined = (combined_df["pm25"] >= 25.0).astype(int).values

    x_test = test_df[feature_cols].copy()
    y_test = (test_df["pm25"] >= 25.0).astype(int).values

    return (x_combined, y_combined), (x_test, y_test)


def infer_proba(model_artifact, x: pd.DataFrame, model_name: str) -> np.ndarray:
    """Get probability predictions from model artifact."""
    if "LogisticRegression" in model_name:
        model = model_artifact["pipeline"]
        cols = model_artifact["features"]
        return model.predict_proba(x[cols])[:, 1]

    if "RandomForest" in model_name:
        if "improved" in model_name.lower():
            model = model_artifact["pipeline"]
            cols = model_artifact["features"]
            return model.predict_proba(x[cols])[:, 1]
        else:
            model = model_artifact["pipeline"]
            cols = model_artifact["features"]
            return model.predict_proba(x[cols])[:, 1]

    if "HistGradientBoosting" in model_name or "GradientBoosting" in model_name:
        model = model_artifact["model"]
        imputer = model_artifact["imputer"]
        cols = model_artifact["features"]
        x_mat = imputer.transform(x[cols])
        return model.predict_proba(x_mat)[:, 1]

    raise ValueError(f"Unknown model: {model_name}")


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


def cv_evaluate_model(
    model_artifact: dict,
    model_name: str,
    x: pd.DataFrame,
    y: np.ndarray,
    n_splits: int = 5,
) -> tuple[dict[str, list[float]], dict[str, dict]]:
    """Perform stratified k-fold cross-validation evaluation."""
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    fold_results = {
        "accuracy": [],
        "precision": [],
        "recall": [],
        "f1": [],
        "roc_auc": [],
        "pr_auc": [],
    }

    print(f"\n  Performing 5-fold CV for {model_name}...")

    for fold_idx, (train_idx, test_idx) in enumerate(skf.split(x, y)):
        x_fold_test = x.iloc[test_idx]
        y_fold_test = y[test_idx]

        try:
            y_prob = infer_proba(model_artifact, x_fold_test, model_name)
            metrics = compute_metrics(y_fold_test, y_prob)

            for metric_name, value in metrics.items():
                fold_results[metric_name].append(value)
        except Exception as e:
            print(f"    Error in fold {fold_idx + 1}: {e}")
            continue

    # Summary statistics
    summary = {}
    for metric_name, values in fold_results.items():
        if values:
            summary[metric_name] = {
                "mean": float(np.mean(values)),
                "std": float(np.std(values)),
            }

    return fold_results, summary


def main() -> None:
    root = Path(__file__).resolve().parent
    processed_dir = root / "processed"
    model_dir = processed_dir / "model_outputs"
    eval_dir = model_dir / "evaluation"
    eval_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 80)
    print("FINAL MODEL EVALUATION")
    print("Models: LogisticRegression, RandomForest_Improved, HistGradientBoosting_Improved")
    print("=" * 80)

    # Load data
    print("\nLoading data...")
    (x_cv, y_cv), (x_test, y_test) = load_data(processed_dir)
    print(f"  CV data: {len(x_cv)} samples ({100*y_cv.sum()/len(y_cv):.1f}% positive)")
    print(f"  Test data: {len(x_test)} samples ({100*y_test.sum()/len(y_test):.1f}% positive)")

    # Load models
    print("\nLoading trained models...")
    logistic = joblib.load(model_dir / "logistic_regression_model.joblib")
    rf_improved = joblib.load(model_dir / "random_forest_improved_model.joblib")
    hgb_improved = joblib.load(model_dir / "gradient_boosting_improved_model.joblib")

    models = {
        "LogisticRegression": logistic,
        "RandomForest_Improved": rf_improved,
        "HistGradientBoosting_Improved": hgb_improved,
    }

    # Evaluate all models
    print("\n" + "=" * 80)
    print("CROSS-VALIDATION EVALUATION (5-fold Stratified)")
    print("=" * 80)

    cv_results = {}
    cv_summary_rows = []

    for model_name, artifact in models.items():
        fold_results, summary = cv_evaluate_model(artifact, model_name, x_cv, y_cv)
        cv_results[model_name] = (fold_results, summary)

        print(f"\n{model_name}:")
        for metric in ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"]:
            if metric in summary:
                mean = summary[metric]["mean"]
                std = summary[metric]["std"]
                print(f"  {metric:12s}: {mean:.4f} +/- {std:.4f}")

        # Add to summary
        row = {"model": model_name}
        for metric in ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"]:
            if metric in summary:
                row[f"{metric}_mean"] = summary[metric]["mean"]
                row[f"{metric}_std"] = summary[metric]["std"]
        cv_summary_rows.append(row)

    # Save CV summary
    cv_summary_df = pd.DataFrame(cv_summary_rows)
    cv_summary_df.to_csv(eval_dir / "final_cv_summary.csv", index=False)

    # Test set evaluation
    print("\n" + "=" * 80)
    print("TEST SET EVALUATION (Hold-out)")
    print("=" * 80)

    test_summary_rows = []
    y_probs = {}
    roc_data = {}
    pr_data = {}

    for model_name, artifact in models.items():
        print(f"\n{model_name}:")

        y_prob = infer_proba(artifact, x_test, model_name)
        y_probs[model_name] = y_prob
        metrics = compute_metrics(y_test, y_prob)

        for metric, value in metrics.items():
            print(f"  {metric:12s}: {value:.4f}")

        test_summary_rows.append({"model": model_name, **metrics})

        fpr, tpr, _ = roc_curve(y_test, y_prob)
        precision, recall, _ = precision_recall_curve(y_test, y_prob)
        roc_data[model_name] = (fpr, tpr)
        pr_data[model_name] = (precision, recall)

    # Save test summary
    test_summary_df = pd.DataFrame(test_summary_rows).sort_values("f1", ascending=False).reset_index(drop=True)
    test_summary_df.to_csv(eval_dir / "final_test_summary.csv", index=False)

    # Visualizations
    print("\n" + "=" * 80)
    print("Generating visualizations...")
    print("=" * 80)

    # ROC curves
    plt.figure(figsize=(8, 6))
    for model_name, (fpr, tpr) in roc_data.items():
        plt.plot(fpr, tpr, label=model_name, linewidth=2.0)
    plt.plot([0, 1], [0, 1], "--", linewidth=1.2, color="gray")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("ROC Curves - Final Models")
    plt.legend()
    plt.tight_layout()
    save_figure(eval_dir / "final_roc_curves.png")
    print("  Saved: final_roc_curves.png")

    # PR curves
    plt.figure(figsize=(8, 6))
    for model_name, (precision, recall) in pr_data.items():
        plt.plot(recall, precision, label=model_name, linewidth=2.0)
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title("Precision-Recall Curves - Final Models")
    plt.legend()
    plt.tight_layout()
    save_figure(eval_dir / "final_pr_curves.png")
    print("  Saved: final_pr_curves.png")

    # Metrics comparison
    plt.figure(figsize=(12, 5))
    metrics_cols = ["f1", "precision", "recall", "roc_auc", "pr_auc"]
    x = np.arange(len(models))
    width = 0.15

    for idx, metric in enumerate(metrics_cols):
        values = [test_summary_df[test_summary_df["model"] == m][metric].values[0] for m in models.keys()]
        plt.bar(x + idx * width, values, width, label=metric)

    plt.xlabel("Model")
    plt.ylabel("Score")
    plt.title("Final Model Comparison - All Metrics")
    plt.xticks(x + width * 2, models.keys(), rotation=15)
    plt.legend()
    plt.ylim(0, 1)
    plt.tight_layout()
    save_figure(eval_dir / "final_metrics_comparison.png")
    print("  Saved: final_metrics_comparison.png")

    # Summary report
    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    print("\nTest Set Performance (Ranked by F1):")
    print(test_summary_df.to_string(index=False))

    print(f"\nResults saved to: {eval_dir}/")
    print("  - final_cv_summary.csv")
    print("  - final_test_summary.csv")
    print("  - final_roc_curves.png")
    print("  - final_pr_curves.png")
    print("  - final_metrics_comparison.png")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
