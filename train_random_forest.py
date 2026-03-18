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

    param_grid = [
        {"n_estimators": 300, "max_depth": 10, "min_samples_leaf": 1},
        {"n_estimators": 500, "max_depth": 12, "min_samples_leaf": 1},
        {"n_estimators": 500, "max_depth": None, "min_samples_leaf": 2},
        {"n_estimators": 800, "max_depth": None, "min_samples_leaf": 1},
    ]

    best_params = param_grid[0]
    best_val_f1 = -1.0

    for params in param_grid:
        pipe = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "clf",
                    RandomForestClassifier(
                        n_estimators=params["n_estimators"],
                        max_depth=params["max_depth"],
                        min_samples_leaf=params["min_samples_leaf"],
                        random_state=42,
                        n_jobs=-1,
                        class_weight="balanced_subsample",
                    ),
                ),
            ]
        )
        pipe.fit(x_train, y_train)
        y_val_pred = pipe.predict(x_val)
        val_f1 = f1_score(y_val, y_val_pred, zero_division=0)
        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            best_params = params

    final_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            (
                "clf",
                RandomForestClassifier(
                    n_estimators=best_params["n_estimators"],
                    max_depth=best_params["max_depth"],
                    min_samples_leaf=best_params["min_samples_leaf"],
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

    y_test_prob = final_pipe.predict_proba(x_test)[:, 1]
    y_test_pred = (y_test_prob >= 0.5).astype(int)
    metrics = compute_metrics(y_test, y_test_prob, y_test_pred)

    model_path = output_dir / "random_forest_model.joblib"
    joblib.dump(
        {
            "pipeline": final_pipe,
            "features": list(x_train.columns),
            "pm25_threshold": pm25_threshold,
            "best_params": best_params,
            "trained_at": datetime.utcnow().isoformat(),
        },
        model_path,
    )

    params_str = ",".join([f"{k}={v}" for k, v in best_params.items()])
    metrics_row = {
        "model": "RandomForest",
        "pm25_threshold": pm25_threshold,
        "best_params": params_str,
        "val_f1_selected": best_val_f1,
        **metrics,
        "trained_at_utc": datetime.utcnow().isoformat(),
    }

    pd.DataFrame([metrics_row]).to_csv(output_dir / "random_forest_metrics.csv", index=False)
    update_leaderboard(output_dir, metrics_row)

    print("Random Forest training complete.")
    print(f"Saved model: {model_path}")
    print("Test metrics:")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}")


if __name__ == "__main__":
    main()
