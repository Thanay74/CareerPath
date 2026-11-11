import unittest
from pathlib import Path

import joblib
import pandas as pd
import json

from backend.ml.kaggle_career_features import FEATURES, TARGET, validate_and_filter


ROOT = Path(__file__).resolve().parents[1]


class KaggleBenchmarkTests(unittest.TestCase):
    def test_preprocessing_filters_unplaced_and_limits_feature_contract(self):
        source = ROOT / "data/raw/kaggle_student_career_success/student_career_success_dataset.csv"
        processed = ROOT / "data/processed/kaggle_student_career_success/career_field_training.csv"
        raw = pd.read_csv(source)
        frame = validate_and_filter(pd.read_csv(processed))

        self.assertEqual(len(raw), 50000)
        self.assertEqual(len(frame), 39040)
        self.assertEqual(frame[TARGET].nunique(), 16)
        self.assertNotIn("Not Placed", set(frame[TARGET]))
        self.assertEqual([c for c in frame.columns if c != TARGET], FEATURES)
        self.assertFalse(set(["Student_ID", "Gender", "Interview_Score", "Placement_Status"]) & set(frame.columns))

    def test_saved_kaggle_model_predicts_a_career_field_label(self):
        model_path = ROOT / "backend/models/kaggle/kaggle_bachelor_career_field.joblib"
        artifact = joblib.load(model_path)
        sample_path = ROOT / "data/processed/kaggle_student_career_success/career_field_training.csv"
        sample = pd.read_csv(sample_path, nrows=1)[artifact["features"]]
        prediction = artifact["pipeline"].predict(sample)
        label = artifact["label_encoder"].inverse_transform(prediction)[0]

        self.assertIn(label, artifact["label_encoder"].classes_)
        metrics_path = ROOT / "data/processed/kaggle_career_model_metrics.json"
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        self.assertEqual(artifact["selected_model"], metrics["selected_model"])
        self.assertLess(model_path.stat().st_size, 100 * 1024 * 1024)
        self.assertIn("synthetic", artifact["scope"])


if __name__ == "__main__":
    unittest.main()
