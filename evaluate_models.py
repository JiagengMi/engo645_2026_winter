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
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)


apply_publication_style()


def load_test_split(processed_dir: Path) -> pd.DataFrame:
    return pd.read_csv(processed_dir / "test_model_ready.csv")


def prepare_xy(df: pd.DataFrame, threshold: float) -> tuple[pd.DataFrame, pd.Series]:
    feature_cols = [c for c in df.columns if c not in {"date", "pm25"}]
    x = df[feature_cols].copy()
    y = (df["pm25"] >= threshold).astype(int)
    return x, y


def infer_proba(model_artifact, x: pd.DataFrame, model_name: str) -> np.ndarray:
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


def compute_metrics(y_true: pd.Series, y_prob: np.ndarray, threshold: float = 0.5) -> dict[str, float]:
    y_pred = (y_prob >= threshold).astype(int)
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
        "pr_auc": float(average_precision_score(y_true, y_prob)),
    }


def plot_metric_bars(summary_df: pd.DataFrame, out_path: Path) -> None:
    plot_cols = ["f1", "precision", "recall", "roc_auc", "pr_auc"]
    melted = summary_df.melt(id_vars=["model"], value_vars=plot_cols, var_name="metric", value_name="value")
    plt.figure(figsize=(10, 5))
    sns.barplot(data=melted, x="metric", y="value", hue="model")
    plt.ylim(0, 1)
    plt.title("Model Comparison on Test Set")
    plt.tight_layout()
    save_figure(out_path)


def plot_roc_curves(curve_data: dict[str, tuple[np.ndarray, np.ndarray]], out_path: Path) -> None:
    plt.figure(figsize=(7, 6))
    for model_name, (fpr, tpr) in curve_data.items():
        plt.plot(fpr, tpr, label=model_name, linewidth=2.0)
    plt.plot([0, 1], [0, 1], "--", linewidth=1.2, color="#444444")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("ROC Curves")
    plt.legend()
    plt.tight_layout()
    save_figure(out_path)


def plot_pr_curves(curve_data: dict[str, tuple[np.ndarray, np.ndarray]], out_path: Path) -> None:
    plt.figure(figsize=(7, 6))
    for model_name, (precision, recall) in curve_data.items():
        plt.plot(recall, precision, label=model_name, linewidth=2.0)
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title("Precision-Recall Curves")
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
        cm = confusion_matrix(y_true, y_pred)
        sns.heatmap(cm, annot=True, fmt="d", cmap="YlGnBu", cbar=False, ax=ax)
        ax.set_title(name)
        ax.set_xlabel("Predicted")
        ax.set_ylabel("True")

    plt.tight_layout()
    save_figure(out_path)


def main() -> None:
    root = Path(__file__).resolve().parent
    processed_dir = root / "processed"
    model_dir = processed_dir / "model_outputs"
    eval_dir = model_dir / "evaluation"
    eval_dir.mkdir(parents=True, exist_ok=True)

    logistic = joblib.load(model_dir / "logistic_regression_model.joblib")
    rf = joblib.load(model_dir / "random_forest_model.joblib")
    gb = joblib.load(model_dir / "gradient_boosting_model.joblib")

    threshold = float(logistic.get("pm25_threshold", 25.0))
    test_df = load_test_split(processed_dir)
    x_test, y_test = prepare_xy(test_df, threshold=threshold)

    model_artifacts = {
        "LogisticRegression": logistic,
        "RandomForest": rf,
        str(gb.get("backend", "GradientBoosting")): gb,
    }

    summary_rows: list[dict] = []
    y_probs: dict[str, np.ndarray] = {}
    roc_data: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    pr_data: dict[str, tuple[np.ndarray, np.ndarray]] = {}

    for name, artifact in model_artifacts.items():
        prob = infer_proba(artifact, x_test, name)
        y_probs[name] = prob
        metrics = compute_metrics(y_test, prob)
        summary_rows.append({"model": name, **metrics})

        fpr, tpr, _ = roc_curve(y_test, prob)
        precision, recall, _ = precision_recall_curve(y_test, prob)
        roc_data[name] = (fpr, tpr)
        pr_data[name] = (precision, recall)

    summary_df = pd.DataFrame(summary_rows).sort_values("f1", ascending=False).reset_index(drop=True)
    summary_df.to_csv(eval_dir / "evaluation_summary.csv", index=False)

    plot_metric_bars(summary_df, eval_dir / "metric_bars.png")
    plot_roc_curves(roc_data, eval_dir / "roc_curves.png")
    plot_pr_curves(pr_data, eval_dir / "pr_curves.png")
    plot_confusion_matrices(y_test, y_probs, eval_dir / "confusion_matrices.png")

    print("Evaluation completed.")
    print(f"Saved summary: {eval_dir / 'evaluation_summary.csv'}")
    print(f"Saved visualizations in: {eval_dir}")


if __name__ == "__main__":
    main()
