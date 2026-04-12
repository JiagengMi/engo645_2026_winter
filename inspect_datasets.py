from __future__ import annotations

import argparse
import json
import runpy
from pathlib import Path

import pandas as pd


RAW_GROUPS = [
    (
        "PM2.5 raw daily target",
        [Path("wildfire_datasets") / "air_quality" / "calgary_pm25_daily_2018_2024.csv"],
    ),
    (
        "Weather raw hourly inputs (combined)",
        [Path("wildfire_datasets") / "weather" / "hourly"],
    ),
    (
        "ERA5 raw hourly input",
        [Path("wildfire_datasets") / "era5" / "era5_calgary_timeseries_2018_2025.csv"],
    ),
    (
        "Fire raw points input",
        [Path("wildfire_datasets") / "DL_FIRE_J1V-C2_728034" / "fire_archive_J1V-C2_728034.csv"],
    ),
]

CLEANED_GROUPS = [
    (
        "PM2.5 cleaned daily target",
        [Path("processed") / "pm25_daily_clean.csv"],
    ),
    (
        "Weather cleaned daily features",
        [Path("processed") / "weather_daily_features.csv"],
    ),
    (
        "ERA5 cleaned daily features",
        [Path("processed") / "era5_daily_features.csv"],
    ),
    (
        "Fire cleaned daily features",
        [Path("processed") / "fire_daily_features.csv"],
    ),
    (
        "Master daily raw table",
        [Path("processed") / "master_daily_raw.csv"],
    ),
    (
        "Master daily model-ready table",
        [Path("processed") / "master_daily_model_ready.csv"],
    ),
    (
        "Training split model-ready table",
        [Path("processed") / "train_model_ready.csv"],
    ),
    (
        "Validation split model-ready table",
        [Path("processed") / "val_model_ready.csv"],
    ),
    (
        "Test split model-ready table",
        [Path("processed") / "test_model_ready.csv"],
    ),
]


def read_csv_like(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        if path.name == "era5_calgary_timeseries_2018_2025.csv":
            return pd.read_csv(path, compression="zip")
        return pd.read_csv(path)

    if path.suffix.lower() in {".json", ".geojson"}:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        if isinstance(payload, dict) and payload.get("type") == "FeatureCollection":
            records = []
            for feature in payload.get("features", []):
                row = dict(feature.get("properties") or {})
                geometry = feature.get("geometry") or {}
                row["geometry_type"] = geometry.get("type")
                records.append(row)
            return pd.DataFrame(records)

        if isinstance(payload, list):
            return pd.DataFrame(payload)

        return pd.DataFrame([payload])

    raise ValueError(f"Unsupported dataset type: {path.suffix}")


def combine_frames(frames: list[pd.DataFrame]) -> pd.DataFrame:
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False)


def load_grouped_dataset(root: Path, targets: list[Path]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []

    for target in targets:
        path = root / target
        if path.is_dir():
            csv_files = sorted(path.glob("*.csv"))
            for csv_file in csv_files:
                frames.append(read_csv_like(csv_file))
            continue

        if path.exists():
            frames.append(read_csv_like(path))

    df = combine_frames(frames)
    if not df.empty:
        df = df.reindex(sorted(df.columns), axis=1)
    return df


def load_cleaning_functions(root: Path) -> dict[str, object]:
    script_path = root / "data cleaning.py"
    if not script_path.exists():
        raise FileNotFoundError(f"Missing cleaning script: {script_path}")
    return runpy.run_path(str(script_path))


def build_cleaned_datasets(root: Path) -> dict[str, pd.DataFrame]:
    cleaning = load_cleaning_functions(root)

    pm25_path = root / "wildfire_datasets" / "air_quality" / "calgary_pm25_daily_2018_2024.csv"
    weather_hourly_dir = root / "wildfire_datasets" / "weather" / "hourly"
    era5_path = root / "wildfire_datasets" / "era5" / "era5_calgary_timeseries_2018_2025.csv"
    fire_path = root / "wildfire_datasets" / "DL_FIRE_J1V-C2_728034" / "fire_archive_J1V-C2_728034.csv"

    start_date = pd.Timestamp("2018-04-01")
    end_date = pd.Timestamp("2025-04-01")
    radius_km = 400.0
    upwind_sector_deg = 45.0
    train_ratio = 0.70
    val_ratio = 0.15

    read_pm25_daily = cleaning["read_pm25_daily"]
    read_weather_hourly_to_daily = cleaning["read_weather_hourly_to_daily"]
    read_era5_hourly_to_daily = cleaning["read_era5_hourly_to_daily"]
    read_fire_points = cleaning["read_fire_points"]
    build_fire_features = cleaning["build_fire_features"]
    build_master_daily_dataset = cleaning["build_master_daily_dataset"]
    make_model_ready = cleaning["make_model_ready"]
    split_time_series_dataset = cleaning["split_time_series_dataset"]
    filter_daily_date_range = cleaning["filter_daily_date_range"]

    pm25_daily = filter_daily_date_range(read_pm25_daily(pm25_path), start_date, end_date)
    weather_daily = filter_daily_date_range(read_weather_hourly_to_daily(weather_hourly_dir), start_date, end_date)
    era5_daily = filter_daily_date_range(read_era5_hourly_to_daily(era5_path), start_date, end_date)

    fire_points = read_fire_points(fire_path)
    fire_daily = build_fire_features(
        fire_points,
        era5_daily,
        radius_km=radius_km,
        upwind_sector_deg=upwind_sector_deg,
    )
    fire_daily = filter_daily_date_range(fire_daily, start_date, end_date)

    fire_date_spine = pd.DataFrame({"date": pd.date_range(start_date, end_date, freq="D").date})
    fire_daily = fire_date_spine.merge(fire_daily, on="date", how="left")
    for c in [
        "fire_count",
        "fire_frp_sum",
        "fire_frp_mean",
        "fire_mean_km",
        "fire_frp_dist_weighted_sum",
        "fire_smoke_transport_index",
        "upwind_fire_count",
        "upwind_fire_frp_sum",
    ]:
        if c in fire_daily.columns:
            fire_daily[c] = fire_daily[c].fillna(0)
    for c in ["fire_nearest_km", "upwind_fire_nearest_km"]:
        if c in fire_daily.columns:
            max_seen = fire_daily[c].max(skipna=True)
            fallback = float(max_seen) if pd.notna(max_seen) else radius_km
            fire_daily[c] = fire_daily[c].fillna(fallback)

    master = build_master_daily_dataset(
        pm25_daily,
        weather_daily,
        era5_daily,
        fire_daily,
        start_date=start_date,
        end_date=end_date,
    )
    model_ready = make_model_ready(master, dropna_target=True)
    train_df, val_df, test_df = split_time_series_dataset(
        model_ready,
        train_ratio=train_ratio,
        val_ratio=val_ratio,
    )

    return {
        "PM2.5 cleaned daily target": pm25_daily,
        "Weather cleaned daily features": weather_daily,
        "ERA5 cleaned daily features": era5_daily,
        "Fire cleaned daily features": fire_daily,
        "Master daily raw table": master,
        "Master daily model-ready table": model_ready,
        "Training split model-ready table": train_df,
        "Validation split model-ready table": val_df,
        "Test split model-ready table": test_df,
    }


def print_dataset_report(root: Path, label: str, df: pd.DataFrame, source_paths: list[Path], head_rows: int) -> None:
    print(f"\n[{label}]")
    print("sources:")
    for source in source_paths:
        display_path = source.relative_to(root) if source.is_absolute() else source
        print(f"  - {display_path}")

    if df.empty:
        print("status: missing or empty")
        return

    print(f"shape: {df.shape[0]} rows x {df.shape[1]} columns")
    print("head:")
    print(df.head(head_rows).to_string(index=False))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print grouped size and head comparisons for project datasets before and after cleaning."
    )
    parser.add_argument(
        "--head-rows",
        type=int,
        default=5,
        help="Number of rows to show for each dataset head.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parent

    print("=" * 80)
    print("RAW DATASET GROUPS")
    print("=" * 80)
    for label, targets in RAW_GROUPS:
        df = load_grouped_dataset(root, targets)
        print_dataset_report(root, label, df, targets, args.head_rows)

    print("\n" + "=" * 80)
    print("CLEANED / TRAIN-READY DATASET GROUPS")
    print("=" * 80)
    cleaned_datasets = build_cleaned_datasets(root)
    for label, targets in CLEANED_GROUPS:
        df = cleaned_datasets.get(label, pd.DataFrame())
        print_dataset_report(root, label, df, targets, args.head_rows)


if __name__ == "__main__":
    main()