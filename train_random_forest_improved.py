"""
Improved Random Forest Training - Step 1 Regularization
Targets: Reduce model complexity to prevent overfitting
- Smaller max_depth (5-10 instead of 10-None)
- Larger min_samples_leaf (10-30 instead of 1-2)
- Add min_samples_split constraint
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline


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


def compute_metrics(y_true: pd.Series, y_prob: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
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


def main() -> None:
    root = Path(__file__).resolve().parent
    processed_dir = root / "processed"
    output_dir = processed_dir / "model_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    pm25_threshold = 25.0
    train_df, val_df, test_df = load_splits(processed_dir)

    x_train, y_train = prepare_xy(train_df, threshold=pm25_threshold)
    x_val, y_val = prepare_xy(val_df, threshold=pm25_threshold)
    x_test, y_test = prepare_xy(test_df, threshold=pm25_threshold)
    x_train, x_val, x_test = align_feature_columns(x_train, x_val, x_test)

    # Improved Regularization Grid
    # Targets: Shallower trees + more conservative leaf constraints
    param_grid = [
        # Config 1: Shallow with strict constraints
        {"n_estimators": 200, "max_depth": 5, "min_samples_leaf": 15, "min_samples_split": 30},
        # Config 2: Moderate depth but strict leaf size
        {"n_estimators": 300, "max_depth": 7, "min_samples_leaf": 20, "min_samples_split": 40},
        # Config 3: Slightly deeper with aggressive leaf constraint
        {"n_estimators": 300, "max_depth": 10, "min_samples_leaf": 30, "min_samples_split": 60},
        # Config 4: Very conservative approach
        {"n_estimators": 400, "max_depth": 5, "min_samples_leaf": 25, "min_samples_split": 50},
    ]

    best_params = param_grid[0]
    best_val_f1 = -1.0
    all_results = []

    print("\n" + "=" * 70)
    print("IMPROVED RANDOM FOREST TRAINING - Regularization Focused")
    print("=" * 70)

    for idx, params in enumerate(param_grid):
        print(f"\nEvaluating Config {idx + 1}: {params}")

        pipe = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "clf",
                    RandomForestClassifier(
                        n_estimators=params["n_estimators"],
                        max_depth=params["max_depth"],
                        min_samples_leaf=params["min_samples_leaf"],
                        min_samples_split=params.get("min_samples_split", 2),
                        random_state=42,
                        n_jobs=-1,
                        class_weight="balanced_subsample",
                    ),
                ),
            ]
        )
        pipe.fit(x_train, y_train)

        # Validation metrics
        y_val_prob = pipe.predict_proba(x_val)[:, 1]
        y_val_pred = (y_val_prob >= 0.5).astype(int)
        val_f1 = f1_score(y_val, y_val_pred, zero_division=0)
        val_metrics = compute_metrics(y_val, y_val_prob, y_val_pred)

        print(f"  Val F1: {val_f1:.4f}, Precision: {val_metrics['precision']:.4f}, Recall: {val_metrics['recall']:.4f}")

        all_results.append({
            "config": idx + 1,
            "params": params,
            "val_f1": val_f1,
            "val_metrics": val_metrics,
        })

        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            best_params = params
            print(f"  [NEW BEST]")

    print(f"\nBest Config Selected: {best_params}")
    print(f"Best Val F1: {best_val_f1:.4f}")

    # Train final model on combined train+val
    final_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            (
                "clf",
                RandomForestClassifier(
                    n_estimators=best_params["n_estimators"],
                    max_depth=best_params["max_depth"],
                    min_samples_leaf=best_params["min_samples_leaf"],
                    min_samples_split=best_params.get("min_samples_split", 2),
                    random_state=42,
                    n_jobs=-1,
                    class_weight="balanced_subsample",
                ),
            ),
        ]
    )

    x_trainval = pd.concat([x_train, x_val], axis=0).reset_index(drop=True)
    y_trainval = pd.concat([y_train, y_val], axis=0).reset_index(drop=True)
    final_pipe.fit(x_trainval, y_trainval)

    # Test metrics
    y_test_prob = final_pipe.predict_proba(x_test)[:, 1]
    y_test_pred = (y_test_prob >= 0.5).astype(int)
    metrics = compute_metrics(y_test, y_test_prob, y_test_pred)

    # Save model
    model_path = output_dir / "random_forest_improved_model.joblib"
    joblib.dump(
        {
            "pipeline": final_pipe,
            "features": list(x_train.columns),
            "pm25_threshold": pm25_threshold,
            "best_params": best_params,
            "trained_at": datetime.utcnow().isoformat(),
            "model_version": "improved_v1_regularization",
        },
        model_path,
    )

    # Save metrics
    params_str = ",".join([f"{k}={v}" for k, v in best_params.items()])
    metrics_row = {
        "model": "RandomForest_Improved_V1",
        "model_version": "regularized",
        "pm25_threshold": pm25_threshold,
        "best_params": params_str,
        "val_f1_selected": best_val_f1,
        **metrics,
        "trained_at_utc": datetime.utcnow().isoformat(),
    }

    pd.DataFrame([metrics_row]).to_csv(output_dir / "random_forest_improved_metrics.csv", index=False)
    update_leaderboard(output_dir, metrics_row)

    print("\n" + "=" * 70)
    print("Improved Random Forest training complete!")
    print("=" * 70)
    print(f"Saved model: {model_path}")
    print("\nTest Set Metrics:")
    for k, v in metrics.items():
        print(f"  {k:12s}: {v:.4f}")

    print(f"\nComparison Note:")
    print(f"  This is a REGULARIZED version with stricter constraints")
    print(f"  Expect: Lower CV performance but better test generalization")
    print(f"  Saved as separate model artifact for comparison")


if __name__ == "__main__":
    main()
