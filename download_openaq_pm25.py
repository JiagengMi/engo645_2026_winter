import os
import requests
import pandas as pd
from typing import List, Dict, Any

API_KEY = "160cf56f5922d021525416463d15c4b39e0ebf258c0b414e76bba5f4dbf518c8"

SAVE_DIR = r"F:\04-UoC master\OneDrive - University of Calgary\02-UoC\26winter_ENGO645_Spatial Databases and Data Mining\04_project_645\wildfire_datasets\air_quality\openaq"
os.makedirs(SAVE_DIR, exist_ok=True)

BASE_URL = "https://api.openaq.org/v3"
HEADERS = {
    "X-API-Key": API_KEY,
    "Accept": "application/json",
}

# Calgary downtown approximate coordinates
# OpenAQ examples use coordinates + radius for nearby station search
CALGARY_LAT = 51.0447
CALGARY_LON = -114.0719
SEARCH_RADIUS_M = 25000  # 25 km
PM25_PARAMETER_ID = 2

DATE_FROM = "2018-04-01"
DATE_TO = "2025-04-01"


def get_json(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    r = requests.get(url, headers=HEADERS, params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def find_pm25_locations_near_calgary(limit: int = 1000) -> pd.DataFrame:
    """
    Find locations near Calgary that measure PM2.5.
    """
    url = f"{BASE_URL}/locations"
    params = {
        "coordinates": f"{CALGARY_LAT},{CALGARY_LON}",
        "radius": SEARCH_RADIUS_M,
        "parameters_id": PM25_PARAMETER_ID,
        "limit": limit,
        "page": 1,
    }

    rows: List[Dict[str, Any]] = []

    while True:
        data = get_json(url, params)
        results = data.get("results", [])
        if not results:
            break

        for item in results:
            rows.append({
                "location_id": item.get("id"),
                "location_name": item.get("name"),
                "provider": (item.get("provider") or {}).get("name"),
                "owner": (item.get("owner") or {}).get("name"),
                "latitude": (item.get("coordinates") or {}).get("latitude"),
                "longitude": (item.get("coordinates") or {}).get("longitude"),
                "is_mobile": item.get("isMobile"),
                "datetime_first_utc": ((item.get("datetimeFirst") or {}).get("utc")),
                "datetime_last_utc": ((item.get("datetimeLast") or {}).get("utc")),
                "sensors": item.get("sensors", []),
            })

        meta = data.get("meta", {})
        page = int(meta.get("page", params["page"]) or params["page"])

        if len(results) < limit:
            break

        params["page"] = page + 1

    df = pd.DataFrame(rows)
    return df


def extract_pm25_sensors(locations_df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract PM2.5 sensors from location objects.
    """
    sensor_rows: List[Dict[str, Any]] = []

    for _, row in locations_df.iterrows():
        sensors = row["sensors"] if isinstance(row["sensors"], list) else []
        for s in sensors:
            parameter = s.get("parameter") or {}
            if parameter.get("id") == PM25_PARAMETER_ID:
                sensor_rows.append({
                    "location_id": row["location_id"],
                    "location_name": row["location_name"],
                    "sensor_id": s.get("id"),
                    "parameter_id": parameter.get("id"),
                    "parameter_name": parameter.get("name"),
                    "units": parameter.get("units"),
                    "coverage_datetime_from": ((s.get("datetimeFirst") or {}).get("utc")),
                    "coverage_datetime_to": ((s.get("datetimeLast") or {}).get("utc")),
                })

    return pd.DataFrame(sensor_rows)


def choose_best_sensor(sensors_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Choose one sensor automatically.
    Current rule:
    1. earliest coverage start
    2. latest coverage end
    """
    if sensors_df.empty:
        raise ValueError("No PM2.5 sensors found near Calgary.")

    df = sensors_df.copy()
    df["coverage_datetime_from"] = pd.to_datetime(df["coverage_datetime_from"], errors="coerce")
    df["coverage_datetime_to"] = pd.to_datetime(df["coverage_datetime_to"], errors="coerce")

    df = df.sort_values(
        by=["coverage_datetime_from", "coverage_datetime_to"],
        ascending=[True, False]
    )
    return df.iloc[0].to_dict()


def download_sensor_daily_pm25(sensor_id: int, date_from: str, date_to: str, limit: int = 1000) -> pd.DataFrame:
    """
    Download daily PM2.5 averages for one sensor.
    Stop paging when returned rows are fewer than the page limit.
    """
    url = f"{BASE_URL}/sensors/{sensor_id}/days"
    params = {
        "datetime_from": date_from,
        "datetime_to": date_to,
        "limit": limit,
        "page": 1,
    }

    rows = []

    while True:
        data = get_json(url, params)
        results = data.get("results", [])

        if not results:
            print(f"No results returned on page {params['page']}")
            break

        for item in results:
            period = item.get("period") or {}
            dt_from = period.get("datetimeFrom") or {}
            dt_to = period.get("datetimeTo") or {}
            parameter = item.get("parameter") or {}

            rows.append({
                "date_utc_from": dt_from.get("utc"),
                "date_local_from": dt_from.get("local"),
                "date_utc_to": dt_to.get("utc"),
                "date_local_to": dt_to.get("local"),
                "value": item.get("value"),
                "unit": parameter.get("units"),
                "parameter_name": parameter.get("name"),
            })

        page = int((data.get("meta", {}) or {}).get("page", params["page"]) or params["page"])
        print(f"Downloaded page {page}, page rows: {len(results)}, total rows so far: {len(rows)}")

        # Last page: fewer rows than requested limit
        if len(results) < limit:
            break

        params["page"] = page + 1

    df = pd.DataFrame(rows)
    return df


def main():
    print("Step 1: finding PM2.5 locations near Calgary...")
    locations_df = find_pm25_locations_near_calgary()
    if locations_df.empty:
        raise ValueError("No OpenAQ locations found near Calgary.")

    locations_out = os.path.join(SAVE_DIR, "calgary_pm25_locations.csv")
    locations_df.drop(columns=["sensors"], errors="ignore").to_csv(locations_out, index=False)
    print(f"Saved locations: {locations_out}")

    print("Step 2: extracting PM2.5 sensors...")
    sensors_df = extract_pm25_sensors(locations_df)
    if sensors_df.empty:
        raise ValueError("No PM2.5 sensors found in returned Calgary locations.")

    sensors_out = os.path.join(SAVE_DIR, "calgary_pm25_sensors.csv")
    sensors_df.to_csv(sensors_out, index=False)
    print(f"Saved sensors: {sensors_out}")

    best_sensor = choose_best_sensor(sensors_df)
    sensor_id = int(best_sensor["sensor_id"])
    location_name = best_sensor["location_name"]

    print(f"Chosen sensor_id = {sensor_id} at location = {location_name}")

    print("Step 3: downloading daily PM2.5 data...")
    pm25_df = download_sensor_daily_pm25(sensor_id, DATE_FROM, DATE_TO)
    if pm25_df.empty:
        raise ValueError("No daily PM2.5 data returned for the selected sensor.")

    pm25_df["sensor_id"] = sensor_id
    pm25_df["location_name"] = location_name
    pm25_df["date"] = pd.to_datetime(
    pm25_df["date_local_from"],
    utc=True,
    errors="coerce"
    ).dt.date

    pm25_out = os.path.join(SAVE_DIR, "calgary_pm25_daily_2018_2024.csv")
    pm25_df.to_csv(pm25_out, index=False)
    print(f"Saved PM2.5 daily data: {pm25_out}")

    print("\nDone.")
    print(f"Selected station: {location_name}")
    print(f"Selected sensor: {sensor_id}")
    print(f"Rows downloaded: {len(pm25_df)}")


if __name__ == "__main__":
    main()