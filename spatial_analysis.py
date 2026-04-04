from __future__ import annotations

import argparse
from pathlib import Path

import folium
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from folium.plugins import MarkerCluster
from plot_style import apply_publication_style, save_figure
from shapely.geometry import Point


CALGARY_LAT = 51.0447
CALGARY_LON = -114.0719
PROJECTED_CRS = "EPSG:3347"  # meters
apply_publication_style()


def clean_fire_csv(fire_csv: Path, start_date: str, end_date: str) -> pd.DataFrame:
    required = ["latitude", "longitude", "acq_date", "acq_time", "frp"]

    # Read header first so we can select only the required columns.
    try:
        header_cols = pd.read_csv(fire_csv, nrows=0).columns.tolist()
    except pd.errors.ParserError:
        header_cols = pd.read_csv(fire_csv, nrows=0, engine="python", on_bad_lines="skip").columns.tolist()

    normalized_to_raw: dict[str, str] = {}
    for raw in header_cols:
        norm = str(raw).strip().strip('"').lower()
        if norm not in normalized_to_raw:
            normalized_to_raw[norm] = str(raw)

    miss = [c for c in required if c not in normalized_to_raw]
    if miss:
        raise KeyError(f"Missing columns in fire CSV: {miss}")

    usecols_raw = [normalized_to_raw[c] for c in required]

    try:
        fire = pd.read_csv(fire_csv, usecols=usecols_raw, dtype=str)
    except pd.errors.ParserError:
        # Some FIRMS CSV exports contain malformed rows; the Python engine with
        # bad-line skipping is slower but more resilient.
        fire = pd.read_csv(fire_csv, usecols=usecols_raw, dtype=str, engine="python", on_bad_lines="skip")
    fire.columns = [c.strip().strip('"').lower() for c in fire.columns]

    fire["latitude"] = pd.to_numeric(fire["latitude"], errors="coerce")
    fire["longitude"] = pd.to_numeric(fire["longitude"], errors="coerce")
    fire["frp"] = pd.to_numeric(fire["frp"], errors="coerce")

    hhmm = fire["acq_time"].astype(str).str.zfill(4)
    fire["datetime"] = pd.to_datetime(
        fire["acq_date"].astype(str) + " " + hhmm.str[:2] + ":" + hhmm.str[2:],
        errors="coerce",
    )
    fire["date"] = fire["datetime"].dt.date

    start = pd.Timestamp(start_date).date()
    end = pd.Timestamp(end_date).date()
    fire = fire[(fire["date"] >= start) & (fire["date"] <= end)]
    fire = fire.dropna(subset=["latitude", "longitude", "date", "frp"])
    return fire.reset_index(drop=True)


def stage1_join(fire_df: pd.DataFrame, processed_dir: Path, out_dir: Path) -> pd.DataFrame:
    pm25 = pd.read_csv(processed_dir / "pm25_daily_clean.csv")
    weather = pd.read_csv(processed_dir / "weather_daily_features.csv")

    pm25["date"] = pd.to_datetime(pm25["date"]).dt.date
    weather["date"] = pd.to_datetime(weather["date"]).dt.date

    fire_daily = fire_df.groupby("date", as_index=False).agg(
        fire_count=("frp", "size"),
        fire_frp_sum=("frp", "sum"),
        fire_frp_mean=("frp", "mean"),
    )

    joined = pm25.merge(weather, on="date", how="left").merge(fire_daily, on="date", how="left")
    joined[["fire_count", "fire_frp_sum", "fire_frp_mean"]] = joined[["fire_count", "fire_frp_sum", "fire_frp_mean"]].fillna(0)

    joined.to_csv(out_dir / "stage1_fire_weather_pm25_join.csv", index=False)
    return joined


def load_or_create_boundary(boundary_path: Path | None, buffer_km: float) -> gpd.GeoDataFrame:
    calgary_pt = gpd.GeoDataFrame(
        {"name": ["Calgary"]},
        geometry=[Point(CALGARY_LON, CALGARY_LAT)],
        crs="EPSG:4326",
    )

    if boundary_path and boundary_path.exists():
        boundary = gpd.read_file(boundary_path)
        if boundary.crs is None:
            boundary = boundary.set_crs("EPSG:4326")
        else:
            boundary = boundary.to_crs("EPSG:4326")
        boundary["source"] = "provided_boundary"
        return boundary

    # If no municipal boundary file is provided, use a local proxy buffer around city center.
    calgary_proj = calgary_pt.to_crs(PROJECTED_CRS)
    proxy = calgary_proj.buffer(30000).to_crs("EPSG:4326")
    boundary = gpd.GeoDataFrame({"source": ["proxy_30km"]}, geometry=proxy, crs="EPSG:4326")
    return boundary


def stage2_spatial(
    fire_df: pd.DataFrame,
    boundary_gdf: gpd.GeoDataFrame,
    out_dir: Path,
    buffer_km: float,
) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    fire_gdf = gpd.GeoDataFrame(
        fire_df,
        geometry=gpd.points_from_xy(fire_df["longitude"], fire_df["latitude"]),
        crs="EPSG:4326",
    )

    calgary_pt = gpd.GeoDataFrame(
        {"name": ["Calgary"]},
        geometry=[Point(CALGARY_LON, CALGARY_LAT)],
        crs="EPSG:4326",
    )

    fire_proj = fire_gdf.to_crs(PROJECTED_CRS)
    calgary_proj = calgary_pt.to_crs(PROJECTED_CRS)

    buffer_geom = calgary_proj.buffer(buffer_km * 1000)
    buffer_gdf = gpd.GeoDataFrame({"buffer_km": [buffer_km]}, geometry=buffer_geom, crs=PROJECTED_CRS)

    fire_proj["distance_km"] = fire_proj.distance(calgary_proj.geometry.iloc[0]) / 1000.0
    fire_within = fire_proj[fire_proj.within(buffer_geom.iloc[0])].copy()

    nearest_daily = (
        fire_proj.groupby("date", as_index=False)["distance_km"]
        .min()
        .rename(columns={"distance_km": "nearest_fire_km"})
    )

    fire_within.to_crs("EPSG:4326").drop(columns=["geometry"]).to_csv(out_dir / "fires_within_buffer.csv", index=False)
    nearest_daily.to_csv(out_dir / "daily_nearest_fire_distance.csv", index=False)
    buffer_gdf.to_crs("EPSG:4326").to_file(out_dir / "calgary_buffer.geojson", driver="GeoJSON")
    boundary_gdf.to_file(out_dir / "calgary_boundary_or_proxy.geojson", driver="GeoJSON")

    return fire_within.to_crs("EPSG:4326"), nearest_daily


def build_interactive_map(
    fire_within_gdf: gpd.GeoDataFrame,
    boundary_gdf: gpd.GeoDataFrame,
    out_dir: Path,
    buffer_km: float,
) -> None:
    m = folium.Map(location=[CALGARY_LAT, CALGARY_LON], zoom_start=6, tiles="CartoDB positron")

    folium.Circle(
        location=[CALGARY_LAT, CALGARY_LON],
        radius=buffer_km * 1000,
        color="crimson",
        fill=True,
        fill_opacity=0.12,
        tooltip=f"{buffer_km:.0f} km buffer",
    ).add_to(m)

    folium.GeoJson(boundary_gdf.__geo_interface__, name="Calgary boundary/proxy").add_to(m)

    cluster = MarkerCluster(name="Fire points within buffer").add_to(m)
    sample = fire_within_gdf.nlargest(5000, "frp") if len(fire_within_gdf) > 5000 else fire_within_gdf

    for _, row in sample.iterrows():
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=3,
            color="orange",
            fill=True,
            fill_opacity=0.6,
            popup=f"Date: {row['date']}<br>FRP: {row['frp']:.2f}<br>Distance: {row['distance_km']:.1f} km",
        ).add_to(cluster)

    folium.LayerControl().add_to(m)
    m.save(out_dir / "fire_spatial_interactive_map.html")


def create_spatial_plots(fire_within_gdf: gpd.GeoDataFrame, nearest_daily: pd.DataFrame, out_dir: Path) -> None:
    fire_within_gdf = fire_within_gdf.copy()
    fire_within_gdf["date"] = pd.to_datetime(fire_within_gdf["date"])
    fire_within_gdf["year_month"] = fire_within_gdf["date"].dt.to_period("M").astype(str)

    monthly_counts = fire_within_gdf.groupby("year_month", as_index=False).size().rename(columns={"size": "fire_count"})

    plt.figure(figsize=(12, 4))
    plt.plot(monthly_counts["year_month"], monthly_counts["fire_count"], linewidth=1.8, color="#1f4e79")
    plt.title("Monthly Fire Counts Within Buffer")
    plt.xlabel("Month")
    plt.ylabel("Fire Count")
    plt.xticks(rotation=90)
    plt.tight_layout()
    save_figure(out_dir / "monthly_fire_counts_within_buffer.png")

    nearest_daily_plot = nearest_daily.copy()
    nearest_daily_plot["date"] = pd.to_datetime(nearest_daily_plot["date"])

    plt.figure(figsize=(12, 4))
    plt.plot(nearest_daily_plot["date"], nearest_daily_plot["nearest_fire_km"], linewidth=1.8, color="#2a9d8f")
    plt.title("Daily Nearest Fire Distance to Calgary")
    plt.xlabel("Date")
    plt.ylabel("Distance (km)")
    plt.tight_layout()
    save_figure(out_dir / "daily_nearest_fire_distance.png")


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Spatial analysis and mapping for Calgary wildfire smoke project.")
    parser.add_argument(
        "--fire-csv",
        type=Path,
        default=root / "wildfire_datasets" / "DL_FIRE_J1V-C2_728034" / "fire_archive_J1V-C2_728034.csv",
        help="Path to FIRMS fire CSV.",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=root / "processed",
        help="Directory containing cleaned daily datasets.",
    )
    parser.add_argument(
        "--boundary-path",
        type=Path,
        default=None,
        help="Optional Calgary boundary file path (GeoJSON/Shapefile).",
    )
    parser.add_argument(
        "--buffer-km",
        type=float,
        default=400.0,
        help="Buffer distance around Calgary used for spatial filtering.",
    )
    parser.add_argument("--start-date", type=str, default="2018-04-01")
    parser.add_argument("--end-date", type=str, default="2025-04-01")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = args.processed_dir / "spatial_outputs"
    out_dir.mkdir(parents=True, exist_ok=True)

    fire_df = clean_fire_csv(args.fire_csv, args.start_date, args.end_date)
    stage1_join(fire_df, args.processed_dir, out_dir)

    boundary = load_or_create_boundary(args.boundary_path, args.buffer_km)
    fire_within, nearest_daily = stage2_spatial(
        fire_df,
        boundary,
        out_dir,
        buffer_km=args.buffer_km,
    )

    build_interactive_map(fire_within, boundary, out_dir, buffer_km=args.buffer_km)
    create_spatial_plots(fire_within, nearest_daily, out_dir)

    print("Spatial analysis complete.")
    print(f"Outputs saved in: {out_dir}")


if __name__ == "__main__":
    main()
