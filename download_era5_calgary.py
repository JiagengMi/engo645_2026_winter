import os
import cdsapi


SAVE_DIR = r"F:\04-UoC master\OneDrive - University of Calgary\02-UoC\26winter_ENGO645_Spatial Databases and Data Mining\04_project_645\wildfire_datasets\era5"
os.makedirs(SAVE_DIR, exist_ok=True)

OUTPUT_FILE = os.path.join(SAVE_DIR, "era5_calgary_timeseries_2018_2025.csv")


client = cdsapi.Client()

dataset = "reanalysis-era5-single-levels-timeseries"


request = {
    "location": {
        "latitude": 51.0447,
        "longitude": -114.0719,
    },


    "date": ["2018-01-01/2025-12-31"],


    "variable": [
        "10m_u_component_of_wind",
        "10m_v_component_of_wind",
        "2m_temperature",
        "2m_dewpoint_temperature",
        "surface_pressure",
    ],

    "data_format": "csv",
}

print("Downloading ERA5 timeseries...")

client.retrieve(dataset, request).download(OUTPUT_FILE)

print(f"Saved to: {OUTPUT_FILE}")