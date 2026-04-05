"""
Compare original vs improved models using cross-validation
Shows improvement in generalization gap
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold


def load_full_dataset(processed_dir: Path) -> tuple[pd.DataFrame, np.ndarray]:
    """Load train + val combined dataset for CV."""
    train_df = pd.read_csv(processed_dir / "train_model_ready.csv")
    val_df = pd.read_csv(processed_dir / "val_model_ready.csv")
    df = pd.concat([train_df, val_df], ignore_index=True)

    feature_cols = [c for c in df.columns if c not in {"date", "pm25"}]
    x = df[feature_cols].copy()
    y = (df["pm25"] >= 25.0).astype(int).values
    return x, y


def load_test_set(processed_dir: Path) -> tuple[pd.DataFrame, np.ndarray]:
    """Load test set."""
    df = pd.read_csv(processed_dir / "test_model_ready.csv")
    feature_cols = [c for c in df.columns if c not in {"date", "pm25"}]
    x = df[feature_cols].copy()
    y = (df["pm25"] >= 25.0).astype(int).values
    return x, y


def infer_proba(model_artifact, x: pd.DataFrame, model_name: str) -> np.ndarray:
    """Get probability predictions from model artifact."""
    if "improved" in model_name.lower():
        if "randomforest" in model_name.lower():
            model = model_artifact["pipeline"]
            cols = model_artifact["features"]
            return model.predict_proba(x[cols])[:, 1]
        else:  # HistGradientBoosting
            model = model_artifact["model"]
            imputer = model_artifact["imputer"]
            cols = model_artifact["features"]
            x_mat = imputer.transform(x[cols])
            return model.predict_proba(x_mat)[:, 1]
    else:
        if "RandomForest" in model_name:
            model = model_artifact["pipeline"]
            cols = model_artifact["features"]
            return model.predict_proba(x[cols])[:, 1]
        else:  # HistGradientBoosting
            model = model_artifact["model"]
            imputer = model_artifact["imputer"]
            cols = model_artifact["features"]
            x_mat = imputer.transform(x[cols])
            return model.predict_proba(x_mat)[:, 1]


def compute_metrics(y_true: np.ndarray, y_prob: np.ndarray) -> dict:
    """Compute all metrics."""
    y_pred = (y_prob >= 0.5).astype(int)
    return {
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
        "pr_auc": float(average_precision_score(y_true, y_prob)),
    }


def cv_evaluate_model(model_artifact, model_name: str, x: pd.DataFrame, y: np.ndarray, n_splits: int = 5) -> tuple[dict, dict]:
    """Cross-validation evaluation."""
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    fold_results = {"f1": [], "precision": [], "recall": [], "roc_auc": [], "pr_auc": []}

    for fold_idx, (train_idx, test_idx) in enumerate(skf.split(x, y)):
        x_fold_test = x.iloc[test_idx]
        y_fold_test = y[test_idx]

        try:
            y_prob = infer_proba(model_artifact, x_fold_test, model_name)
            metrics = compute_metrics(y_fold_test, y_prob)
            for metric_name, value in metrics.items():
                fold_results[metric_name].append(value)
        except Exception as e:
            print(f"  Error in fold {fold_idx + 1}: {e}")
            continue

    # Summary
    summary = {k: {"mean": np.mean(v), "std": np.std(v)} for k, v in fold_results.items()}
    return fold_results, summary


def test_evaluate_model(model_artifact, model_name: str, x: pd.DataFrame, y: np.ndarray) -> dict:
    """Evaluate on test set."""
    y_prob = infer_proba(model_artifact, x, model_name)
    return compute_metrics(y, y_prob)


def main() -> None:
    root = Path(__file__).resolve().parent
    processed_dir = root / "processed"
    model_dir = processed_dir / "model_outputs"
    eval_dir = model_dir / "evaluation"

    print("\n" + "=" * 80)
    print("COMPARISON: Original vs Improved Models")
    print("=" * 80)

    # Load data
    x_cv, y_cv = load_full_dataset(processed_dir)
    x_test, y_test = load_test_set(processed_dir)

    # Load models
    print("\nLoading models...")
    rf_original = joblib.load(model_dir / "random_forest_model.joblib")
    hgb_original = joblib.load(model_dir / "gradient_boosting_model.joblib")
    rf_improved = joblib.load(model_dir / "random_forest_improved_model.joblib")
    hgb_improved = joblib.load(model_dir / "gradient_boosting_improved_model.joblib")

    models = {
        "RandomForest_Original": rf_original,
        "RandomForest_Improved": rf_improved,
        "HistGradientBoosting_Original": hgb_original,
        "HistGradientBoosting_Improved": hgb_improved,
    }

    # Evaluate all models
    results_summary = []

    for model_name in ["RandomForest_Original", "RandomForest_Improved",
                       "HistGradientBoosting_Original", "HistGradientBoosting_Improved"]:
        print(f"\n{'='*80}")
        print(f"Model: {model_name}")
        print(f"{'='*80}")

        artifact = models[model_name]

        # CV evaluation
        print(f"Cross-Validation (5-fold)...")
        fold_results, cv_summary = cv_evaluate_model(artifact, model_name, x_cv, y_cv)

        for metric in ["f1", "precision", "recall", "roc_auc", "pr_auc"]:
            mean = cv_summary[metric]["mean"]
            std = cv_summary[metric]["std"]
            print(f"  CV {metric:12s}: {mean:.4f} +/- {std:.4f}")

        # Test evaluation
        print(f"\nTest Set Evaluation...")
        test_metrics = test_evaluate_model(artifact, model_name, x_test, y_test)
        for metric, value in test_metrics.items():
            print(f"  Test {metric:10s}: {value:.4f}")

        # Calculate gap
        print(f"\nGeneralization Gap:")
        gaps = []
        for metric in ["f1", "precision", "recall", "roc_auc", "pr_auc"]:
            cv_mean = cv_summary[metric]["mean"]
            test_value = test_metrics[metric]
            gap = cv_mean - test_value
            gaps.append(gap)
            print(f"  {metric:12s} gap: {gap:+.4f} ({100*gap/cv_mean if cv_mean > 0 else 0:+.1f}%)")

        avg_gap = np.mean(gaps)
        print(f"  Average Gap: {avg_gap:.4f}")

        results_summary.append({
            "Model": model_name,
            "CV_F1_Mean": cv_summary["f1"]["mean"],
            "CV_F1_Std": cv_summary["f1"]["std"],
            "Test_F1": test_metrics["f1"],
            "F1_Gap": cv_summary["f1"]["mean"] - test_metrics["f1"],
            "Avg_Gap": avg_gap,
        })

    # Summary table
    print("\n" + "=" * 80)
    print("SUMMARY COMPARISON TABLE")
    print("=" * 80)

    summary_df = pd.DataFrame(results_summary)
    print(summary_df.to_string(index=False))

    # Calculate improvements
    print("\n" + "=" * 80)
    print("IMPROVEMENT ANALYSIS")
    print("=" * 80)

    rf_orig_gap = results_summary[0]["Avg_Gap"]
    rf_impr_gap = results_summary[1]["Avg_Gap"]
    rf_gap_reduction = rf_orig_gap - rf_impr_gap
    rf_gap_pct = (rf_gap_reduction / rf_orig_gap * 100) if rf_orig_gap > 0 else 0

    hgb_orig_gap = results_summary[2]["Avg_Gap"]
    hgb_impr_gap = results_summary[3]["Avg_Gap"]
    hgb_gap_reduction = hgb_orig_gap - hgb_impr_gap
    hgb_gap_pct = (hgb_gap_reduction / hgb_orig_gap * 100) if hgb_orig_gap > 0 else 0

    print(f"\nRandomForest:")
    print(f"  Original Avg Gap: {rf_orig_gap:.4f}")
    print(f"  Improved Avg Gap: {rf_impr_gap:.4f}")
    print(f"  Reduction: {rf_gap_reduction:.4f} ({rf_gap_pct:.1f}%)")

    print(f"\nHistGradientBoosting:")
    print(f"  Original Avg Gap: {hgb_orig_gap:.4f}")
    print(f"  Improved Avg Gap: {hgb_impr_gap:.4f}")
    print(f"  Reduction: {hgb_gap_reduction:.4f} ({hgb_gap_pct:.1f}%)")

    # Save summary
    summary_df.to_csv(eval_dir / "improvement_comparison.csv", index=False)
    print(f"\nResults saved to: {eval_dir / 'improvement_comparison.csv'}")


if __name__ == "__main__":
    main()
