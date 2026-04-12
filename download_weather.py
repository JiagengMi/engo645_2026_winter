import os
import requests
import pandas as pd
import time
from io import StringIO


save_dir = r"F:\04-UoC master\OneDrive - University of Calgary\02-UoC\26winter_ENGO645_Spatial Databases and Data Mining\04_project_645\wildfire_datasets\weather\hourly"

os.makedirs(save_dir, exist_ok=True)

base_url = "https://climate.weather.gc.ca/climate_data/bulk_data_e.html"
climate_id = "3031092"

for year in range(2025, 2026):
    for month in range(1, 13):

        params = {
            "format": "csv",
            "timeframe": 1,
            "climate_id": climate_id,
            "Year": year,
            "Month": month,
            "Day": 1
        }

        print(f"Downloading {year}-{month}...")

        try:
            response = requests.get(base_url, params=params)

            if "Longitude" in response.text:

                file_name = f"weather_{year}_{month:02d}.csv"
                file_path = os.path.join(save_dir, file_name)

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(response.text)

                print(f"Saved: {file_name}")

            else:
                print(f"Failed (not CSV): {year}-{month}")

        except Exception as e:
            print(f"Error at {year}-{month}: {e}")

        time.sleep(1)