"""
Improved Histogram Gradient Boosting Training - Step 2 Regularization
Targets: Add L2 regularization and reduce learning rate
- Lower learning_rate (0.01-0.02 instead of 0.03-0.05)
- Add l2_regularization (0.01, 0.1, 1.0)
- Reduce max_depth (4-6 instead of 6-10)
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def load_splits(processed_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train_df = pd.read_csv(processed_dir / "train_model_ready.csv")
    val_df = pd.read_csv(processed_dir / "val_model_ready.csv")
    test_df = pd.read_csv(processed_dir / "test_model_ready.csv")
    return train_df, val_df, test_df


def prepare_xy(df: pd.DataFrame, threshold: float) -> tuple[pd.DataFrame, pd.Series]:
    feature_cols = [c for c in df.columns if c not in {"date", "pm25"}]
    x = df[feature_cols].copy()
    y = (df["pm25"] >= threshold).astype(int)
    return x, y


def align_feature_columns(
    x_train: pd.DataFrame,
    x_val: pd.DataFrame,
    x_test: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    keep_cols = [c for c in x_train.columns if not x_train[c].isna().all()]
    return x_train[keep_cols].copy(), x_val[keep_cols].copy(), x_test[keep_cols].copy()


def compute_metrics(y_true: np.ndarray, y_prob: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
        "pr_auc": float(average_precision_score(y_true, y_prob)),
    }


def update_leaderboard(output_dir: Path, row: dict) -> None:
    leaderboard_path = output_dir / "model_comparison.csv"
    if leaderboard_path.exists():
        board = pd.read_csv(leaderboard_path)
        board = board[board["model"] != row["model"]]
        board = pd.concat([board, pd.DataFrame([row])], ignore_index=True)
    else:
        board = pd.DataFrame([row])

    board = board.sort_values("f1", ascending=False).reset_index(drop=True)
    board.to_csv(leaderboard_path, index=False)


def train_sklearn_hgb_improved(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    y_val: np.ndarray,
) -> tuple[HistGradientBoostingClassifier, dict, float]:
    """
    Train HistGradientBoosting with improved regularization.
    Key improvements:
    - Lower learning rate for more stable training
    - L2 regularization to prevent overfitting
    - Smaller trees (lower max_depth)
    """

    candidates = [
        # Config 1: Conservative - low LR + strong L2
        {"learning_rate": 0.01, "max_depth": 4, "max_iter": 300, "l2_regularization": 1.0},
        # Config 2: Balanced - moderate LR + moderate L2
        {"learning_rate": 0.02, "max_depth": 5, "max_iter": 400, "l2_regularization": 0.1},
        # Config 3: Moderate - slightly higher LR + weaker L2
        {"learning_rate": 0.02, "max_depth": 4, "max_iter": 500, "l2_regularization": 0.01},
        # Config 4: Aggressive tuning - different depth + LR combo
        {"learning_rate": 0.015, "max_depth": 5, "max_iter": 350, "l2_regularization": 0.5},
    ]

    best_model = None
    best_params = candidates[0]
    best_f1 = -1.0
    all_results = []

    print("\n" + "=" * 70)
    print("IMPROVED HISTOGRAM GRADIENT BOOSTING - L2 Regularization Focused")
    print("=" * 70)

    for idx, p in enumerate(candidates):
        print(f"\nEvaluating Config {idx + 1}: {p}")

        model = HistGradientBoostingClassifier(
            random_state=42,
            **p,
        )
        model.fit(x_train, y_train)

        # Validation metrics
        y_val_prob = model.predict_proba(x_val)[:, 1]
        y_val_pred = model.predict(x_val)
        val_f1 = f1_score(y_val, y_val_pred, zero_division=0)
        val_metrics = compute_metrics(y_val, y_val_prob, y_val_pred)

        print(f"  Val F1: {val_f1:.4f}, Precision: {val_metrics['precision']:.4f}, Recall: {val_metrics['recall']:.4f}")

        all_results.append({
            "config": idx + 1,
            "params": p,
            "val_f1": val_f1,
            "val_metrics": val_metrics,
        })

        if val_f1 > best_f1:
            best_f1 = val_f1
            best_params = p
            best_model = model
            print(f"  [NEW BEST]")

    print(f"\nBest Config Selected: {best_params}")
    print(f"Best Val F1: {best_f1:.4f}")

    return best_model, best_params, best_f1


def main() -> None:
    root = Path(__file__).resolve().parent
    processed_dir = root / "processed"
    output_dir = processed_dir / "model_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    pm25_threshold = 25.0
    train_df, val_df, test_df = load_splits(processed_dir)

    x_train_df, y_train = prepare_xy(train_df, threshold=pm25_threshold)
    x_val_df, y_val = prepare_xy(val_df, threshold=pm25_threshold)
    x_test_df, y_test = prepare_xy(test_df, threshold=pm25_threshold)
    x_train_df, x_val_df, x_test_df = align_feature_columns(x_train_df, x_val_df, x_test_df)

    # Imputation for tree models
    imputer = SimpleImputer(strategy="median")
    x_train = imputer.fit_transform(x_train_df)
    x_val = imputer.transform(x_val_df)
    x_test = imputer.transform(x_test_df)

    # Train improved model
    best_model, best_params, best_val_f1 = train_sklearn_hgb_improved(
        x_train,
        y_train.to_numpy(),
        x_val,
        y_val.to_numpy(),
    )

    # Train final model on combined train+val
    x_trainval = np.vstack([x_train, x_val])
    y_trainval = np.concatenate([y_train.to_numpy(), y_val.to_numpy()])

    final_model = HistGradientBoostingClassifier(
        random_state=42,
        **best_params,
    )
    final_model.fit(x_trainval, y_trainval)

    # Test metrics
    y_test_prob = final_model.predict_proba(x_test)[:, 1]
    y_test_pred = final_model.predict(x_test)
    metrics = compute_metrics(y_test.to_numpy(), y_test_prob, y_test_pred)

    # Save model
    model_path = output_dir / "gradient_boosting_improved_model.joblib"
    joblib.dump(
        {
            "model": final_model,
            "imputer": imputer,
            "features": list(x_train_df.columns),
            "pm25_threshold": pm25_threshold,
            "best_params": best_params,
            "backend": "SklearnHistGradientBoosting_Improved",
            "trained_at": datetime.utcnow().isoformat(),
            "model_version": "improved_v1_l2_regularization",
        },
        model_path,
    )

    # Save metrics
    params_str = ",".join([f"{k}={v}" for k, v in best_params.items()])
    metrics_row = {
        "model": "HistGradientBoosting_Improved_V1",
        "model_version": "l2_regularized",
        "pm25_threshold": pm25_threshold,
        "best_params": params_str,
        "val_f1_selected": best_val_f1,
        **metrics,
        "trained_at_utc": datetime.utcnow().isoformat(),
    }

    pd.DataFrame([metrics_row]).to_csv(output_dir / "gradient_boosting_improved_metrics.csv", index=False)
    update_leaderboard(output_dir, metrics_row)

    print("\n" + "=" * 70)
    print("Improved Histogram Gradient Boosting training complete!")
    print("=" * 70)
    print(f"Saved model: {model_path}")
    print("\nTest Set Metrics:")
    for k, v in metrics.items():
        print(f"  {k:12s}: {v:.4f}")

    print(f"\nComparison Note:")
    print(f"  This is a REGULARIZED version with L2 penalty + lower LR")
    print(f"  Expect: Lower CV performance but better test generalization")
    print(f"  Saved as separate model artifact for comparison")


if __name__ == "__main__":
    main()
