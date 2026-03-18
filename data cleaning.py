from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


# Calgary city-center reference used for fire distance features.
CALGARY_LAT = 51.0447
CALGARY_LON = -114.0719
DEFAULT_START_DATE = pd.Timestamp("2018-04-01").date()
DEFAULT_END_DATE = pd.Timestamp("2025-04-01").date()


def _clean_col_name(col: str) -> str:
	col = col.strip().strip('"').lower()
	col = re.sub(r"[^a-z0-9]+", "_", col)
	return col.strip("_")


def _first_existing_column(df: pd.DataFrame, candidates: Iterable[str]) -> str:
	for c in candidates:
		if c in df.columns:
			return c
	raise KeyError(f"None of these columns exist: {list(candidates)}")


def filter_daily_date_range(df: pd.DataFrame, start_date: pd.Timestamp, end_date: pd.Timestamp) -> pd.DataFrame:
	start = pd.Timestamp(start_date).date()
	end = pd.Timestamp(end_date).date()
	return df[(df["date"] >= start) & (df["date"] <= end)].copy()


def haversine_km(lat1: float, lon1: float, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
	"""Vectorized great-circle distance in km from one point to arrays."""
	r = 6371.0088
	lat1_rad = np.radians(lat1)
	lon1_rad = np.radians(lon1)
	lat2_rad = np.radians(lat2)
	lon2_rad = np.radians(lon2)

	dlat = lat2_rad - lat1_rad
	dlon = lon2_rad - lon1_rad
	a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2.0) ** 2
	c = 2 * np.arcsin(np.sqrt(a))
	return r * c


def bearing_deg(lat1: float, lon1: float, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
	"""Bearing from point1 to point2, degrees clockwise from north (0-360)."""
	lat1_rad = np.radians(lat1)
	lon1_rad = np.radians(lon1)
	lat2_rad = np.radians(lat2)
	lon2_rad = np.radians(lon2)

	dlon = lon2_rad - lon1_rad
	x = np.sin(dlon) * np.cos(lat2_rad)
	y = np.cos(lat1_rad) * np.sin(lat2_rad) - np.sin(lat1_rad) * np.cos(lat2_rad) * np.cos(dlon)
	initial = np.degrees(np.arctan2(x, y))
	return (initial + 360.0) % 360.0


def angular_diff_deg(a: np.ndarray, b: np.ndarray) -> np.ndarray:
	"""Smallest absolute angular difference between directions a and b."""
	return np.abs((a - b + 180.0) % 360.0 - 180.0)


def read_pm25_daily(pm25_path: Path) -> pd.DataFrame:
	df = pd.read_csv(pm25_path)
	df.columns = [_clean_col_name(c) for c in df.columns]

	date_col = _first_existing_column(df, ["date", "date_local_from", "date_utc_from"])
	value_col = _first_existing_column(df, ["value", "pm25", "pm2_5"])
	station_col = "location_name" if "location_name" in df.columns else None

	df["date"] = pd.to_datetime(df[date_col], errors="coerce").dt.date
	df["pm25"] = pd.to_numeric(df[value_col], errors="coerce")

	agg = {"pm25": "mean"}
	if station_col is not None:
		agg[station_col] = "nunique"

	out = df.groupby("date", as_index=False).agg(agg)
	if station_col is not None:
		out = out.rename(columns={station_col: "pm25_station_count"})

	return out.sort_values("date").reset_index(drop=True)


def read_weather_hourly_to_daily(weather_hourly_dir: Path) -> pd.DataFrame:
	weather_files = sorted(weather_hourly_dir.glob("weather_*.csv"))
	if not weather_files:
		raise FileNotFoundError(f"No hourly weather files found in: {weather_hourly_dir}")

	frames: list[pd.DataFrame] = []
	for fp in weather_files:
		df = pd.read_csv(fp)
		df.columns = [_clean_col_name(c) for c in df.columns]
		frames.append(df)

	weather = pd.concat(frames, ignore_index=True)

	dt_col = _first_existing_column(weather, ["date_time_lst", "date_time", "date_time_local"])
	weather["datetime"] = pd.to_datetime(weather[dt_col], errors="coerce")
	weather["date"] = weather["datetime"].dt.date

	candidate_numeric = [
		"temp_c",
		"dew_point_temp_c",
		"rel_hum",
		"precip_amount_mm",
		"wind_spd_km_h",
		"stn_press_kpa",
		"visibility_km",
	]

	for c in candidate_numeric:
		if c in weather.columns:
			weather[c] = pd.to_numeric(weather[c], errors="coerce")

	agg_map = {}
	if "temp_c" in weather.columns:
		agg_map["temp_c"] = ["mean", "max", "min"]
	if "dew_point_temp_c" in weather.columns:
		agg_map["dew_point_temp_c"] = ["mean"]
	if "rel_hum" in weather.columns:
		agg_map["rel_hum"] = ["mean", "max", "min"]
	if "precip_amount_mm" in weather.columns:
		agg_map["precip_amount_mm"] = ["sum", "max"]
	if "wind_spd_km_h" in weather.columns:
		agg_map["wind_spd_km_h"] = ["mean", "max"]
	if "stn_press_kpa" in weather.columns:
		agg_map["stn_press_kpa"] = ["mean"]
	if "visibility_km" in weather.columns:
		agg_map["visibility_km"] = ["mean", "min"]

	daily = weather.groupby("date", as_index=False).agg(agg_map)
	daily.columns = ["_".join([p for p in col if p]) if isinstance(col, tuple) else col for col in daily.columns]
	daily = daily.rename(columns={"date_": "date"})

	rename_map = {
		"temp_c_mean": "wx_temp_mean_c",
		"temp_c_max": "wx_temp_max_c",
		"temp_c_min": "wx_temp_min_c",
		"dew_point_temp_c_mean": "wx_dewpoint_mean_c",
		"rel_hum_mean": "wx_rh_mean_pct",
		"rel_hum_max": "wx_rh_max_pct",
		"rel_hum_min": "wx_rh_min_pct",
		"precip_amount_mm_sum": "wx_precip_total_mm",
		"precip_amount_mm_max": "wx_precip_max_mm",
		"wind_spd_km_h_mean": "wx_windspd_mean_kmh",
		"wind_spd_km_h_max": "wx_windspd_max_kmh",
		"stn_press_kpa_mean": "wx_pressure_mean_kpa",
		"visibility_km_mean": "wx_visibility_mean_km",
		"visibility_km_min": "wx_visibility_min_km",
	}
	daily = daily.rename(columns={k: v for k, v in rename_map.items() if k in daily.columns})

	return daily.sort_values("date").reset_index(drop=True)


def read_era5_hourly_to_daily(era5_path: Path) -> pd.DataFrame:
	# CDS "csv" download is a zip container with a CSV inside.
	era5 = pd.read_csv(era5_path, compression="zip")
	era5.columns = [_clean_col_name(c) for c in era5.columns]

	dt_col = _first_existing_column(era5, ["valid_time", "time", "datetime"])
	era5["datetime"] = pd.to_datetime(era5[dt_col], errors="coerce")
	era5["date"] = era5["datetime"].dt.date

	for c in ["u10", "v10", "t2m", "d2m", "sp"]:
		if c in era5.columns:
			era5[c] = pd.to_numeric(era5[c], errors="coerce")

	if not {"u10", "v10"}.issubset(set(era5.columns)):
		raise KeyError("ERA5 must contain u10 and v10 columns.")

	era5["era5_wind_speed_ms"] = np.sqrt(era5["u10"] ** 2 + era5["v10"] ** 2)
	era5["era5_wind_from_deg"] = (270.0 - np.degrees(np.arctan2(era5["v10"], era5["u10"]))) % 360.0

	agg_map = {
		"u10": "mean",
		"v10": "mean",
		"era5_wind_speed_ms": ["mean", "max"],
	}
	if "t2m" in era5.columns:
		agg_map["t2m"] = ["mean", "max", "min"]
	if "d2m" in era5.columns:
		agg_map["d2m"] = ["mean"]
	if "sp" in era5.columns:
		agg_map["sp"] = ["mean"]

	daily = era5.groupby("date", as_index=False).agg(agg_map)
	daily.columns = ["_".join([p for p in col if p]) if isinstance(col, tuple) else col for col in daily.columns]
	daily = daily.rename(columns={"date_": "date"})

	daily["era5_wind_from_deg"] = (270.0 - np.degrees(np.arctan2(daily["v10_mean"], daily["u10_mean"]))) % 360.0

	if "t2m_mean" in daily.columns:
		daily["era5_t2m_mean_c"] = daily["t2m_mean"] - 273.15
		daily["era5_t2m_max_c"] = daily["t2m_max"] - 273.15
		daily["era5_t2m_min_c"] = daily["t2m_min"] - 273.15
		daily = daily.drop(columns=[c for c in ["t2m_mean", "t2m_max", "t2m_min"] if c in daily.columns])

	if "d2m_mean" in daily.columns:
		daily["era5_d2m_mean_c"] = daily["d2m_mean"] - 273.15
		daily = daily.drop(columns=["d2m_mean"])

	if "sp_mean" in daily.columns:
		daily["era5_sp_mean_hpa"] = daily["sp_mean"] / 100.0
		daily = daily.drop(columns=["sp_mean"])

	daily = daily.rename(
		columns={
			"u10_mean": "era5_u10_mean_ms",
			"v10_mean": "era5_v10_mean_ms",
			"era5_wind_speed_ms_mean": "era5_wind_speed_mean_ms",
			"era5_wind_speed_ms_max": "era5_wind_speed_max_ms",
		}
	)

	return daily.sort_values("date").reset_index(drop=True)


def _parse_fire_datetime(acq_date: pd.Series, acq_time: pd.Series) -> pd.Series:
	hhmm = acq_time.astype(str).str.strip().str.zfill(4)
	return pd.to_datetime(
		acq_date.astype(str).str.strip() + " " + hhmm.str[:2] + ":" + hhmm.str[2:],
		errors="coerce",
	)


def read_fire_points(fire_path: Path) -> pd.DataFrame:
	fire = pd.read_csv(fire_path)
	fire.columns = [_clean_col_name(c) for c in fire.columns]

	required_cols = ["latitude", "longitude", "acq_date", "acq_time", "frp"]
	missing = [c for c in required_cols if c not in fire.columns]
	if missing:
		raise KeyError(f"Fire file missing required columns: {missing}")

	fire["latitude"] = pd.to_numeric(fire["latitude"], errors="coerce")
	fire["longitude"] = pd.to_numeric(fire["longitude"], errors="coerce")
	fire["frp"] = pd.to_numeric(fire["frp"], errors="coerce")
	fire["datetime"] = _parse_fire_datetime(fire["acq_date"], fire["acq_time"])
	fire["date"] = fire["datetime"].dt.date

	fire = fire.dropna(subset=["latitude", "longitude", "date"])
	return fire.reset_index(drop=True)


def build_fire_features(
	fire: pd.DataFrame,
	era5_daily: pd.DataFrame,
	radius_km: float = 400.0,
	upwind_sector_deg: float = 45.0,
) -> pd.DataFrame:
	fire = fire.copy()

	fire["distance_km"] = haversine_km(
		CALGARY_LAT,
		CALGARY_LON,
		fire["latitude"].to_numpy(),
		fire["longitude"].to_numpy(),
	)
	fire = fire[fire["distance_km"] <= radius_km].copy()

	fire["bearing_from_calgary_deg"] = bearing_deg(
		CALGARY_LAT,
		CALGARY_LON,
		fire["latitude"].to_numpy(),
		fire["longitude"].to_numpy(),
	)

	merged = fire.merge(
		era5_daily[["date", "era5_wind_from_deg"]],
		on="date",
		how="left",
	)

	merged["wind_fire_angle_diff_deg"] = angular_diff_deg(
		merged["bearing_from_calgary_deg"].to_numpy(),
		merged["era5_wind_from_deg"].to_numpy(),
	)
	merged["is_upwind"] = merged["wind_fire_angle_diff_deg"] <= upwind_sector_deg

	safe_dist = merged["distance_km"] + 1.0
	merged["frp_over_distance"] = merged["frp"] / safe_dist
	merged["transport_weight"] = np.maximum(np.cos(np.radians(merged["wind_fire_angle_diff_deg"])), 0.0)
	merged["smoke_transport_index_row"] = merged["frp"] * merged["transport_weight"] / (safe_dist**2)

	all_daily = merged.groupby("date", as_index=False).agg(
		fire_count=("frp", "size"),
		fire_frp_sum=("frp", "sum"),
		fire_frp_mean=("frp", "mean"),
		fire_nearest_km=("distance_km", "min"),
		fire_mean_km=("distance_km", "mean"),
		fire_frp_dist_weighted_sum=("frp_over_distance", "sum"),
		fire_smoke_transport_index=("smoke_transport_index_row", "sum"),
	)

	upwind = merged[merged["is_upwind"]].groupby("date", as_index=False).agg(
		upwind_fire_count=("frp", "size"),
		upwind_fire_frp_sum=("frp", "sum"),
		upwind_fire_nearest_km=("distance_km", "min"),
	)

	daily = all_daily.merge(upwind, on="date", how="left")
	daily["upwind_fire_count"] = daily["upwind_fire_count"].fillna(0)
	daily["upwind_fire_frp_sum"] = daily["upwind_fire_frp_sum"].fillna(0)

	return daily.sort_values("date").reset_index(drop=True)


def build_master_daily_dataset(
	pm25_daily: pd.DataFrame,
	weather_daily: pd.DataFrame,
	era5_daily: pd.DataFrame,
	fire_daily: pd.DataFrame,
	start_date: pd.Timestamp,
	end_date: pd.Timestamp,
) -> pd.DataFrame:
	date_spine = pd.DataFrame(
		{"date": pd.date_range(pd.Timestamp(start_date), pd.Timestamp(end_date), freq="D").date}
	)

	master = (
		date_spine.merge(pm25_daily, on="date", how="left")
		.merge(weather_daily, on="date", how="left")
		.merge(era5_daily, on="date", how="left")
		.merge(fire_daily, on="date", how="left")
	)

	fire_cols = [c for c in master.columns if c.startswith("fire_") or c.startswith("upwind_")]
	for c in fire_cols:
		if c in {"fire_nearest_km", "upwind_fire_nearest_km"}:
			continue
		master[c] = master[c].fillna(0)

	for c in ["fire_nearest_km", "upwind_fire_nearest_km"]:
		if c in master.columns:
			max_seen = master[c].max(skipna=True)
			fallback = float(max_seen) if pd.notna(max_seen) else 500.0
			master[c] = master[c].fillna(fallback)

	master = master.sort_values("date").reset_index(drop=True)
	return master


def make_model_ready(master: pd.DataFrame, dropna_target: bool = True) -> pd.DataFrame:
	df = master.copy()
	if dropna_target:
		df = df[df["pm25"].notna()].copy()

	numeric_cols = [c for c in df.columns if c != "date" and pd.api.types.is_numeric_dtype(df[c])]
	feature_cols = [c for c in numeric_cols if c != "pm25"]

	# Forward-fill to preserve time ordering, then use robust median fallback.
	df[feature_cols] = df[feature_cols].ffill()
	for c in feature_cols:
		if df[c].isna().any():
			df[c] = df[c].fillna(df[c].median())

	if df["pm25"].isna().any():
		df = df[df["pm25"].notna()].copy()

	return df.reset_index(drop=True)


def add_scaled_features(df: pd.DataFrame) -> pd.DataFrame:
	out = df.copy()
	numeric_cols = [c for c in out.columns if c not in {"date", "pm25"} and pd.api.types.is_numeric_dtype(out[c])]
	if not numeric_cols:
		return out

	means = out[numeric_cols].mean()
	stds = out[numeric_cols].std(ddof=0).replace(0, 1.0)
	scaled = (out[numeric_cols] - means) / stds
	scaled.columns = [f"z_{c}" for c in scaled.columns]
	return pd.concat([out, scaled], axis=1)


def run_pipeline(
	pm25_path: Path,
	weather_hourly_dir: Path,
	era5_path: Path,
	fire_path: Path,
	output_dir: Path,
	radius_km: float,
	upwind_sector_deg: float,
	start_date: pd.Timestamp,
	end_date: pd.Timestamp,
) -> None:
	output_dir.mkdir(parents=True, exist_ok=True)

	print("[1/5] Cleaning PM2.5 daily target...")
	pm25_daily = read_pm25_daily(pm25_path)
	pm25_daily = filter_daily_date_range(pm25_daily, start_date, end_date)

	print("[2/5] Aggregating weather hourly -> daily features...")
	weather_daily = read_weather_hourly_to_daily(weather_hourly_dir)
	weather_daily = filter_daily_date_range(weather_daily, start_date, end_date)

	print("[3/5] Processing ERA5 and deriving wind features...")
	era5_daily = read_era5_hourly_to_daily(era5_path)
	era5_daily = filter_daily_date_range(era5_daily, start_date, end_date)

	print("[4/5] Cleaning fire data + spatial/upwind feature engineering...")
	fire_points = read_fire_points(fire_path)
	fire_daily = build_fire_features(
		fire_points,
		era5_daily,
		radius_km=radius_km,
		upwind_sector_deg=upwind_sector_deg,
	)
	fire_daily = filter_daily_date_range(fire_daily, start_date, end_date)

	print("[5/5] Integrating all datasets and preparing model-ready table...")
	master = build_master_daily_dataset(
		pm25_daily,
		weather_daily,
		era5_daily,
		fire_daily,
		start_date=start_date,
		end_date=end_date,
	)
	model_ready = make_model_ready(master, dropna_target=True)
	model_ready_scaled = add_scaled_features(model_ready)

	pm25_daily.to_csv(output_dir / "pm25_daily_clean.csv", index=False)
	weather_daily.to_csv(output_dir / "weather_daily_features.csv", index=False)
	era5_daily.to_csv(output_dir / "era5_daily_features.csv", index=False)
	fire_daily.to_csv(output_dir / "fire_daily_features.csv", index=False)
	master.to_csv(output_dir / "master_daily_raw.csv", index=False)
	model_ready.to_csv(output_dir / "master_daily_model_ready.csv", index=False)
	model_ready_scaled.to_csv(output_dir / "master_daily_model_ready_scaled.csv", index=False)

	print("\nPipeline complete.")
	print(f"Rows in model-ready dataset: {len(model_ready)}")
	print(f"Date range enforced: {pd.Timestamp(start_date).date()} to {pd.Timestamp(end_date).date()}")
	print(f"Output folder: {output_dir}")


def parse_args() -> argparse.Namespace:
	root = Path(__file__).resolve().parent
	default_output = root / "wildfire_datasets" / "processed"

	parser = argparse.ArgumentParser(
		description="Clean, integrate, and feature-engineer Calgary PM2.5 wildfire dataset."
	)
	parser.add_argument(
		"--pm25",
		type=Path,
		default=root / "wildfire_datasets" / "air_quality" / "calgary_pm25_daily_2018_2024.csv",
		help="Path to PM2.5 daily CSV.",
	)
	parser.add_argument(
		"--weather-hourly-dir",
		type=Path,
		default=root / "wildfire_datasets" / "weather" / "hourly",
		help="Directory containing hourly weather CSV files.",
	)
	parser.add_argument(
		"--era5",
		type=Path,
		default=root / "wildfire_datasets" / "era5" / "era5_calgary_timeseries_2018_2025.csv",
		help="Path to ERA5 file (zip container with CSV entry from CDS).",
	)
	parser.add_argument(
		"--fire",
		type=Path,
		default=root / "wildfire_datasets" / "DL_FIRE_J1V-C2_728034" / "fire_archive_J1V-C2_728034.csv",
		help="Path to VIIRS fire CSV.",
	)
	parser.add_argument(
		"--output-dir",
		type=Path,
		default=default_output,
		help="Folder for cleaned and model-ready outputs.",
	)
	parser.add_argument(
		"--radius-km",
		type=float,
		default=400.0,
		help="Fire filtering radius around Calgary in km.",
	)
	parser.add_argument(
		"--upwind-sector-deg",
		type=float,
		default=45.0,
		help="Half-angle for upwind fire sector in degrees.",
	)
	parser.add_argument(
		"--start-date",
		type=str,
		default="2018-04-01",
		help="Inclusive start date (YYYY-MM-DD).",
	)
	parser.add_argument(
		"--end-date",
		type=str,
		default="2025-04-01",
		help="Inclusive end date (YYYY-MM-DD).",
	)
	return parser.parse_args()


def main() -> None:
	args = parse_args()
	start_date = pd.Timestamp(args.start_date)
	end_date = pd.Timestamp(args.end_date)
	if end_date < start_date:
		raise ValueError("--end-date must be on or after --start-date")

	run_pipeline(
		pm25_path=args.pm25,
		weather_hourly_dir=args.weather_hourly_dir,
		era5_path=args.era5,
		fire_path=args.fire,
		output_dir=args.output_dir,
		radius_km=args.radius_km,
		upwind_sector_deg=args.upwind_sector_deg,
		start_date=start_date,
		end_date=end_date,
	)


if __name__ == "__main__":
	main()
