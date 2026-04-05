from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path


MIN_PYTHON = (3, 10)


def check_python_version() -> None:
    if sys.version_info < MIN_PYTHON:
        required = ".".join(str(v) for v in MIN_PYTHON)
        found = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        raise SystemExit(
            f"Python {required}+ is required for this project. Found: {found}."
        )


def module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def required_modules_for_args(args: argparse.Namespace) -> set[str]:
    mods: set[str] = set()

    if not args.skip_clean:
        mods.update({"numpy", "pandas"})

    if not args.skip_train:
        mods.update({"numpy", "pandas", "sklearn", "joblib"})

    if not args.skip_eval:
        mods.update({"numpy", "pandas", "joblib", "matplotlib", "seaborn", "sklearn"})

    if not args.skip_predict:
        mods.update({"numpy", "pandas", "joblib", "matplotlib", "seaborn", "sklearn"})

    if not args.skip_spatial:
        mods.update({"numpy", "pandas", "matplotlib", "folium", "geopandas", "shapely"})

    return mods


def ensure_dependencies(root: Path, args: argparse.Namespace) -> None:
    needed = required_modules_for_args(args)
    missing = sorted(m for m in needed if not module_available(m))
    if not missing:
        return

    print("\nMissing Python packages detected for requested steps:")
    for mod in missing:
        print(f"  - {mod}")

    req_path = root / "requirements.txt"
    if args.auto_install_missing and req_path.exists():
        print("\nAttempting automatic install from requirements.txt...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(req_path)], check=True)

        still_missing = sorted(m for m in needed if not module_available(m))
        if still_missing:
            print("\nSome modules are still missing after installation:")
            for mod in still_missing:
                print(f"  - {mod}")
            raise SystemExit(2)
        print("Dependency install complete.")
        return

    print("\nInstall dependencies first, then rerun:")
    print(f"  {sys.executable} -m pip install -r {req_path}")
    print("Or run this script with --auto-install-missing")
    raise SystemExit(2)


def ensure_required_paths(root: Path, args: argparse.Namespace) -> None:
    wildfire = root / "wildfire_datasets"
    processed = root / "processed"
    missing: list[str] = []

    def expect_file(path: Path) -> None:
        if not path.exists() or not path.is_file():
            missing.append(str(path))

    def expect_dir(path: Path) -> None:
        if not path.exists() or not path.is_dir():
            missing.append(str(path))

    if not args.skip_clean or not args.skip_spatial:
        expect_file(wildfire / "DL_FIRE_J1V-C2_728034" / "fire_archive_J1V-C2_728034.csv")

    if not args.skip_clean:
        expect_file(wildfire / "air_quality" / "calgary_pm25_daily_2018_2024.csv")
        expect_dir(wildfire / "weather" / "hourly")
        expect_file(wildfire / "era5" / "era5_calgary_timeseries_2018_2025.csv")

    if args.skip_clean and not args.skip_train:
        expect_file(processed / "train_model_ready.csv")
        expect_file(processed / "val_model_ready.csv")
        expect_file(processed / "test_model_ready.csv")

    if args.skip_clean and not args.skip_spatial:
        expect_file(processed / "pm25_daily_clean.csv")
        expect_file(processed / "weather_daily_features.csv")

    if args.skip_train and (not args.skip_eval or not args.skip_predict):
        model_dir = processed / "model_outputs"
        expect_file(model_dir / "logistic_regression_model.joblib")
        expect_file(model_dir / "random_forest_improved_model.joblib")
        expect_file(model_dir / "gradient_boosting_improved_model.joblib")

    if missing:
        print("\nMissing required files/directories for selected steps:")
        for p in missing:
            print(f"  - {p}")
        raise SystemExit(2)


def run_step(step_name: str, script_path: Path, extra_args: list[str] | None = None) -> None:
    cmd = [sys.executable, str(script_path)]
    if extra_args:
        cmd.extend(extra_args)

    print(f"\n=== Running: {step_name} ===")
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="One-click runner for the wildfire smoke project pipeline.")
    parser.add_argument("--skip-clean", action="store_true", help="Skip data cleaning and feature engineering step.")
    parser.add_argument("--skip-train", action="store_true", help="Skip all model training steps.")
    parser.add_argument("--skip-eval", action="store_true", help="Skip evaluation and visualization step.")
    parser.add_argument("--skip-predict", action="store_true", help="Skip next-year prediction step.")
    parser.add_argument("--skip-spatial", action="store_true", help="Skip spatial analysis and mapping step.")
    parser.add_argument("--buffer-km", type=float, default=400.0, help="Spatial analysis buffer in km.")
    parser.add_argument("--start-date", type=str, default="2018-04-01", help="Start date for cleaning/spatial scripts.")
    parser.add_argument("--end-date", type=str, default="2025-04-01", help="End date for cleaning/spatial scripts.")
    parser.add_argument(
        "--auto-install-missing",
        action="store_true",
        help="Automatically install missing Python packages from requirements.txt before running.",
    )
    return parser.parse_args()


def main() -> None:
    check_python_version()
    args = parse_args()
    root = Path(__file__).resolve().parent

    ensure_required_paths(root, args)
    ensure_dependencies(root, args)

    if not args.skip_clean:
        run_step(
            "Data Cleaning",
            root / "data cleaning.py",
            ["--start-date", args.start_date, "--end-date", args.end_date],
        )

    if not args.skip_train:
        run_step("Train Logistic Regression", root / "train_logistic_regression.py")
        run_step("Train Random Forest (Improved)", root / "train_random_forest_improved.py")
        run_step("Train Gradient Boosting (Improved)", root / "train_gradient_boosting_improved.py")

    if not args.skip_eval:
        run_step("Final Model Evaluation (CV + Test)", root / "evaluate_final_models.py")

    if not args.skip_predict:
        run_step("Prediction for Next Year", root / "predict_next_year.py")

    if not args.skip_spatial:
        run_step(
            "Spatial Analysis and Interactive Mapping",
            root / "spatial_analysis.py",
            [
                "--start-date",
                args.start_date,
                "--end-date",
                args.end_date,
                "--buffer-km",
                str(args.buffer_km),
            ],
        )

    print("\nAll requested pipeline steps completed successfully.")


if __name__ == "__main__":
    main()
