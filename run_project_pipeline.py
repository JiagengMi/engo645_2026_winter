from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parent

    if not args.skip_clean:
        run_step(
            "Data Cleaning",
            root / "data cleaning.py",
            ["--start-date", args.start_date, "--end-date", args.end_date],
        )

    if not args.skip_train:
        run_step("Train Logistic Regression", root / "train_logistic_regression.py")
        run_step("Train Random Forest", root / "train_random_forest.py")
        run_step("Train Gradient Boosting", root / "train_gradient_boosting.py")

    if not args.skip_eval:
        run_step("Evaluation and Visualization", root / "evaluate_models.py")

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
