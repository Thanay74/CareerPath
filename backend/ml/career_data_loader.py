"""Loads only explicitly synthetic career-family training examples."""
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
def load_career_data(path=None):
    source = Path(path) if path else ROOT / "data/synthetic/career_training_profiles.csv"
    frame = pd.read_csv(source)
    required = {"education_level", "career_family"}
    if not required.issubset(frame.columns): raise ValueError(f"Missing required columns: {required-set(frame.columns)}")
    if frame["career_family"].isna().any(): raise ValueError("Career family labels cannot be missing")
    return frame
