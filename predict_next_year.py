from __future__ import annotations

from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from plot_style import apply_publication_style, save_figure
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer


apply_publication_style()


def build_future_features(master_df: pd.DataFrame, future_dates: pd.DatetimeIndex, feature_cols: list[str]) -> pd.DataFrame:
    hist = master_df.copy()
    hist["date"] = pd.to_datetime(hist["date"])
    hist["doy"] = hist["date"].dt.dayofyear

    future_df = pd.DataFrame({"date": future_dates})
    future_df["doy"] = future_df["date"].dt.dayofyear

    doy_stats = hist.groupby("doy")[feature_cols].median(numeric_only=True)
    global_stats = hist[feature_cols].median(numeric_only=True)

    for col in feature_cols:
        future_df[col] = future_df["doy"].map(doy_stats[col])
        future_df[col] = future_df[col].fillna(global_stats[col])

    return future_df.drop(columns=["doy"])


def plot_future_predictions(pred_df: pd.DataFrame, out_dir: Path) -> None:
    plt.figure(figsize=(12, 5))
    plt.plot(pred_df["date"], pred_df["pred_pm25"], label="Predicted PM2.5", linewidth=2.0, color="#1f4e79")
    plt.axhline(25.0, color="#e76f51", linestyle="--", linewidth=1.3, label="PM2.5 = 25 threshold")
    plt.title("Predicted PM2.5 for Next 12 Months")
    plt.xlabel("Date")
    plt.ylabel("PM2.5 (ug/m3)")
    plt.legend()
    plt.tight_layout()
    save_figure(out_dir / "future_pm25_timeseries.png")

    plt.figure(figsize=(12, 4))
    plt.plot(pred_df["date"], pred_df["smoke_prob"], color="#2a9d8f", linewidth=2.0, label="Smoke Impact Probability")
    plt.title("Predicted Smoke Impact Probability for Next 12 Months")
    plt.xlabel("Date")
    plt.ylabel("Probability")
    plt.ylim(0, 1)
    plt.legend()
    plt.tight_layout()
    save_figure(out_dir / "future_smoke_probability_timeseries.png")

    monthly = pred_df.copy()
    monthly["month"] = monthly["date"].dt.to_period("M").astype(str)
    monthly_summary = monthly.groupby("month", as_index=False).agg(
        mean_pred_pm25=("pred_pm25", "mean"),
        mean_smoke_prob=("smoke_prob", "mean"),
        smoke_days=("smoke_impact_pred", "sum"),
    )

    fig, ax1 = plt.subplots(figsize=(12, 5))
    ax1.bar(monthly_summary["month"], monthly_summary["mean_pred_pm25"], alpha=0.78, label="Mean PM2.5", color="#1f4e79")
    ax1.set_ylabel("Mean Predicted PM2.5")
    ax1.tick_params(axis="x", rotation=45)

    ax2 = ax1.twinx()
    ax2.plot(monthly_summary["month"], monthly_summary["mean_smoke_prob"], color="#e76f51", marker="o", linewidth=2.0, label="Mean Smoke Prob")
    ax2.set_ylabel("Mean Smoke Probability")
    ax2.set_ylim(0, 1)

    fig.suptitle("Monthly Prediction Summary (Next 12 Months)")
    fig.tight_layout()
    fig.savefig(out_dir / "future_monthly_summary.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    monthly_summary.to_csv(out_dir / "future_monthly_summary.csv", index=False)


def main() -> None:
    root = Path(__file__).resolve().parent
    processed_dir = root / "processed"
    model_dir = processed_dir / "model_outputs"
    pred_dir = model_dir / "prediction_next_year"
    pred_dir.mkdir(parents=True, exist_ok=True)

    master_df = pd.read_csv(processed_dir / "master_daily_raw.csv")
    model_ready = pd.read_csv(processed_dir / "master_daily_model_ready.csv")

    gb_artifact = joblib.load(model_dir / "gradient_boosting_model.joblib")
    feature_cols = gb_artifact["features"]
    threshold = float(gb_artifact.get("pm25_threshold", 25.0))

    max_date = pd.to_datetime(master_df["date"]).max()
    future_dates = pd.date_range(max_date + pd.Timedelta(days=1), periods=365, freq="D")

    future_features = build_future_features(master_df, future_dates, feature_cols)

    # Classification prediction using the selected boosting model artifact.
    x_future_imp = gb_artifact["imputer"].transform(future_features[feature_cols])
    smoke_prob = gb_artifact["model"].predict_proba(x_future_imp)[:, 1]

    # PM2.5 regression estimate for future dates.
    x_hist = model_ready[feature_cols].copy()
    y_hist = model_ready["pm25"].copy()
    reg_imputer = SimpleImputer(strategy="median")
    x_hist_imp = reg_imputer.fit_transform(x_hist)
    x_future_reg = reg_imputer.transform(future_features[feature_cols])

    reg = RandomForestRegressor(
        n_estimators=600,
        random_state=42,
        n_jobs=-1,
        max_depth=14,
        min_samples_leaf=2,
    )
    reg.fit(x_hist_imp, y_hist)
    pred_pm25 = reg.predict(x_future_reg)

    pred_df = pd.DataFrame(
        {
            "date": future_dates,
            "smoke_prob": smoke_prob,
            "smoke_impact_pred": (smoke_prob >= 0.5).astype(int),
            "pred_pm25": pred_pm25,
            "pm25_threshold": threshold,
        }
    )

    pred_df.to_csv(pred_dir / "next_12_month_predictions.csv", index=False)
    plot_future_predictions(pred_df, pred_dir)

    print("Prediction for next 12 months completed.")
    print(f"Saved predictions: {pred_dir / 'next_12_month_predictions.csv'}")
    print(f"Saved visualizations in: {pred_dir}")


if __name__ == "__main__":
    main()
