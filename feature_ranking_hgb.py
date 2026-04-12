from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.metrics import f1_score


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute feature ranking for the final HistGradientBoosting model."
    )
    parser.add_argument(
        "--n-repeats",
        type=int,
        default=20,
        help="Number of permutation repeats for each feature.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=20,
        help="Number of top features to print in terminal.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parent
    processed_dir = root / "processed"
    model_dir = processed_dir / "model_outputs"
    eval_dir = model_dir / "evaluation"
    eval_dir.mkdir(parents=True, exist_ok=True)

    model_artifact_path = model_dir / "gradient_boosting_improved_model.joblib"
    if not model_artifact_path.exists():
        raise FileNotFoundError(
            "Missing HGB model artifact. Run train_gradient_boosting_improved.py first."
        )

    test_path = processed_dir / "test_model_ready.csv"
    if not test_path.exists():
        raise FileNotFoundError(
            "Missing test_model_ready.csv. Run data cleaning pipeline first."
        )

    artifact = joblib.load(model_artifact_path)
    model = artifact["model"]
    imputer = artifact["imputer"]
    feature_cols = artifact["features"]
    pm25_threshold = float(artifact.get("pm25_threshold", 25.0))

    test_df = pd.read_csv(test_path)
    x_test_df = test_df[feature_cols].copy()
    y_test = (test_df["pm25"] >= pm25_threshold).astype(int).to_numpy()

    x_test = imputer.transform(x_test_df)

    y_prob = model.predict_proba(x_test)[:, 1]
    y_pred = (y_prob >= 0.5).astype(int)
    baseline_f1 = f1_score(y_test, y_pred, zero_division=0)

    result = permutation_importance(
        estimator=model,
        X=x_test,
        y=y_test,
        scoring="f1",
        n_repeats=args.n_repeats,
        random_state=42,
        n_jobs=-1,
    )

    ranking = pd.DataFrame(
        {
            "feature": feature_cols,
            "importance_mean": result.importances_mean,
            "importance_std": result.importances_std,
        }
    ).sort_values("importance_mean", ascending=False)

    ranking_path = eval_dir / "hgb_feature_ranking.csv"
    ranking.to_csv(ranking_path, index=False)

    top_n = min(args.top_n, len(ranking))
    print("\n" + "=" * 80)
    print("HGB FEATURE RANKING (Permutation Importance, scoring=F1)")
    print("=" * 80)
    print(f"Model file: {model_artifact_path}")
    print(f"Baseline test F1: {baseline_f1:.4f}")
    print(f"Saved ranking: {ranking_path}")
    print(f"\nTop {top_n} features:")
    print(ranking.head(top_n).to_string(index=False))


if __name__ == "__main__":
    main()