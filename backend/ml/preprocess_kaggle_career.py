"""Create the non-destructive, benchmark-only Kaggle training table."""
from pathlib import Path

import pandas as pd

from backend.ml.kaggle_career_features import FEATURES, TARGET, validate_and_filter

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/raw/kaggle_student_career_success/student_career_success_dataset.csv"
OUTPUT = ROOT / "data/processed/kaggle_student_career_success/career_field_training.csv"


def main():
    if not SOURCE.exists():
        raise FileNotFoundError(f"Missing original Kaggle CSV: {SOURCE}")
    clean = validate_and_filter(pd.read_csv(SOURCE))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    clean[FEATURES + [TARGET]].to_csv(OUTPUT, index=False)
    print(f"Wrote {len(clean)} placed records and {len(FEATURES)} features to {OUTPUT}")


if __name__ == "__main__":
    main()
