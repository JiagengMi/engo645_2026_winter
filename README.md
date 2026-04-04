# ENGO 645 Project - Winter 2026

## Overview
This repository contains code and documentation for the ENGO 645 (Spatial Databases and Data Mining) project.

## Repository Contents
- `download_weather.py` - Weather data download script
- `Project*.pdf` and `*.docx` - Project documentation
- `wildfire_datasets/analyze_datasets.ipynb` - Dataset analysis notebook

## Data Files
**Note: Large data files are NOT included in this repository.** Due to GitHub's file size limits, data files should be downloaded separately and placed in the `wildfire_datasets/` directory. See project documentation for data sources.

## Quick Start

Python requirement: 3.10 or newer.

### 1) Create and activate a virtual environment
Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2) Install dependencies

```powershell
pip install -r requirements.txt
```

### 3) Run the full pipeline

```powershell
python run_project_pipeline.py
```

Fresh machine shortcut (auto-installs missing packages for selected steps):

```powershell
python run_project_pipeline.py --auto-install-missing
```

## Pipeline Options

Run selected stages only:

```powershell
python run_project_pipeline.py --skip-train --skip-eval --skip-predict --skip-spatial
```

Available flags:
- `--skip-clean`
- `--skip-train`
- `--skip-eval`
- `--skip-predict`
- `--skip-spatial`
- `--buffer-km` (default: `400`)
- `--start-date` (default: `2018-04-01`)
- `--end-date` (default: `2025-04-01`)
- `--auto-install-missing`