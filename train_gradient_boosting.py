from __future__ import annotations

from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.ensemble import HistGradientBoostingClassifier
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


def train_with_xgboost(x_train: np.ndarray, y_train: np.ndarray, x_val: np.ndarray, y_val: np.ndarray):
    from xgboost import XGBClassifier

    candidates = [
        {"n_estimators": 300, "max_depth": 4, "learning_rate": 0.05, "subsample": 0.8, "colsample_bytree": 0.8},
        {"n_estimators": 500, "max_depth": 4, "learning_rate": 0.03, "subsample": 0.8, "colsample_bytree": 0.8},
        {"n_estimators": 400, "max_depth": 6, "learning_rate": 0.05, "subsample": 0.9, "colsample_bytree": 0.8},
    ]

    best_model = None
    best_params = candidates[0]
    best_f1 = -1.0

    for p in candidates:
        model = XGBClassifier(
            objective="binary:logistic",
            eval_metric="logloss",
            random_state=42,
            n_jobs=-1,
            **p,
        )
        model.fit(x_train, y_train)
        val_pred = model.predict(x_val)
        val_f1 = f1_score(y_val, val_pred, zero_division=0)
        if val_f1 > best_f1:
            best_f1 = val_f1
            best_params = p
            best_model = model

    return best_model, best_params, best_f1, "XGBoost"


def train_with_lightgbm(x_train: np.ndarray, y_train: np.ndarray, x_val: np.ndarray, y_val: np.ndarray):
    from lightgbm import LGBMClassifier

    candidates = [
        {"n_estimators": 300, "max_depth": -1, "learning_rate": 0.05, "subsample": 0.8, "colsample_bytree": 0.8},
        {"n_estimators": 500, "max_depth": -1, "learning_rate": 0.03, "subsample": 0.8, "colsample_bytree": 0.8},
        {"n_estimators": 400, "max_depth": 8, "learning_rate": 0.05, "subsample": 0.9, "colsample_bytree": 0.8},
    ]

    best_model = None
    best_params = candidates[0]
    best_f1 = -1.0

    for p in candidates:
        model = LGBMClassifier(
            objective="binary",
            random_state=42,
            n_jobs=-1,
            **p,
        )
        model.fit(x_train, y_train)
        val_pred = model.predict(x_val)
        val_f1 = f1_score(y_val, val_pred, zero_division=0)
        if val_f1 > best_f1:
            best_f1 = val_f1
            best_params = p
            best_model = model

    return best_model, best_params, best_f1, "LightGBM"


def train_with_sklearn_hgb(x_train: np.ndarray, y_train: np.ndarray, x_val: np.ndarray, y_val: np.ndarray):
    candidates = [
        {"learning_rate": 0.05, "max_depth": 6, "max_iter": 300, "min_samples_leaf": 20},
        {"learning_rate": 0.03, "max_depth": 8, "max_iter": 500, "min_samples_leaf": 20},
        {"learning_rate": 0.05, "max_depth": 10, "max_iter": 400, "min_samples_leaf": 30},
    ]

    best_model = None
    best_params = candidates[0]
    best_f1 = -1.0

    for p in candidates:
        model = HistGradientBoostingClassifier(
            random_state=42,
            **p,
        )
        model.fit(x_train, y_train)
        val_pred = model.predict(x_val)
        val_f1 = f1_score(y_val, val_pred, zero_division=0)
        if val_f1 > best_f1:
            best_f1 = val_f1
            best_params = p
            best_model = model

    return best_model, best_params, best_f1, "SklearnHistGradientBoosting"


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

    # Tree boosters do not need scaling; use median imputation to handle any residual missing values.
    imputer = SimpleImputer(strategy="median")
    x_train = imputer.fit_transform(x_train_df)
    x_val = imputer.transform(x_val_df)
    x_test = imputer.transform(x_test_df)

    model = None
    best_params = {}
    best_val_f1 = -1.0
    model_name = ""

    try:
        model, best_params, best_val_f1, model_name = train_with_xgboost(x_train, y_train.to_numpy(), x_val, y_val.to_numpy())
    except Exception:
        try:
            model, best_params, best_val_f1, model_name = train_with_lightgbm(
                x_train,
                y_train.to_numpy(),
                x_val,
                y_val.to_numpy(),
            )
        except Exception:
            model, best_params, best_val_f1, model_name = train_with_sklearn_hgb(
                x_train,
                y_train.to_numpy(),
                x_val,
                y_val.to_numpy(),
            )

    x_trainval = np.vstack([x_train, x_val])
    y_trainval = np.concatenate([y_train.to_numpy(), y_val.to_numpy()])

    # Retrain using best selected hyperparameters on train+val.
    if model_name == "XGBoost":
        from xgboost import XGBClassifier

        final_model = XGBClassifier(
            objective="binary:logistic",
            eval_metric="logloss",
            random_state=42,
            n_jobs=-1,
            **best_params,
        )
    elif model_name == "LightGBM":
        from lightgbm import LGBMClassifier

        final_model = LGBMClassifier(
            objective="binary",
            random_state=42,
            n_jobs=-1,
            **best_params,
        )
    else:
        final_model = HistGradientBoostingClassifier(
            random_state=42,
            **best_params,
        )

    final_model.fit(x_trainval, y_trainval)

    y_test_prob = final_model.predict_proba(x_test)[:, 1]
    y_test_pred = (y_test_prob >= 0.5).astype(int)
    metrics = compute_metrics(y_test, y_test_prob, y_test_pred)

    artifact = {
        "imputer": imputer,
        "model": final_model,
        "features": list(x_train_df.columns),
        "pm25_threshold": pm25_threshold,
        "best_params": best_params,
        "backend": model_name,
        "trained_at": datetime.utcnow().isoformat(),
    }

    model_path = output_dir / "gradient_boosting_model.joblib"
    joblib.dump(artifact, model_path)

    params_str = ",".join([f"{k}={v}" for k, v in best_params.items()])
    metrics_row = {
        "model": model_name,
        "pm25_threshold": pm25_threshold,
        "best_params": params_str,
        "val_f1_selected": best_val_f1,
        **metrics,
        "trained_at_utc": datetime.utcnow().isoformat(),
    }

    pd.DataFrame([metrics_row]).to_csv(output_dir / "gradient_boosting_metrics.csv", index=False)
    update_leaderboard(output_dir, metrics_row)

    print(f"{model_name} training complete.")
    print(f"Saved model: {model_path}")
    print("Test metrics:")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}")


if __name__ == "__main__":
    main()
