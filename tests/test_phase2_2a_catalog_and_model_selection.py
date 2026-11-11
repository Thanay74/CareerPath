import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from data import generate_synthetic_data
from backend.ml import train_career_models


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Phase22aRegressionTests(unittest.TestCase):
    def test_synthetic_generator_only_writes_inside_synthetic_output(self):
        isolated_test_root = Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory(dir=isolated_test_root) as temp_dir:
            root = Path(temp_dir) / "data"
            output = root / "synthetic"
            root.mkdir()
            canonical_catalog = root / "career_knowledge_base.csv"
            metadata = root / "career_metadata.json"
            canonical_catalog.write_text("preserve canonical career catalog\n", encoding="utf-8")
            metadata.write_text('{"preserve": true}\n', encoding="utf-8")
            before = (_sha256(canonical_catalog), _sha256(metadata))

            with patch.object(generate_synthetic_data, "ROOT", root), patch.object(
                generate_synthetic_data, "OUT", output
            ):
                generate_synthetic_data.main(n=2)

            self.assertEqual((_sha256(canonical_catalog), _sha256(metadata)), before)
            self.assertEqual(
                sorted(path.name for path in output.glob("*.csv")),
                ["aptitude_scores.csv", "employability_skills.csv", "interest_scores.csv", "students.csv", "technical_skills.csv"],
            )

    def test_selection_uses_cv_metrics_only(self):
        cv_metrics = {
            "random_forest": {"f1_macro": {"mean": 0.81, "std": 0.02}},
            "xgboost": {"f1_macro": {"mean": 0.84, "std": 0.01}},
        }
        self.assertEqual(train_career_models.select_candidate_by_cv(cv_metrics), "xgboost")

    def test_holdout_evaluation_occurs_once_after_cv_selection(self):
        events = []

        def fake_build_pipeline(features, model):
            return model

        def fake_cv(pipeline, X_train, y_train, cv):
            events.append(("cv", pipeline))
            return {"f1_macro": {"mean": {"rf": 0.71, "xgb": 0.89}[pipeline], "std": 0.0}}

        def fake_holdout(pipeline, X_train, y_train, X_test, y_test, class_names):
            events.append(("holdout", pipeline))
            return pipeline, {"f1_macro": 0.01 if pipeline == "xgb" else 0.99}

        with patch.object(train_career_models, "build_pipeline", fake_build_pipeline), patch.object(
            train_career_models, "evaluate_cross_validation", fake_cv
        ), patch.object(train_career_models, "evaluate_holdout", fake_holdout):
            selected, _, metrics, holdout = train_career_models.evaluate_and_select(
                {"rf": "rf", "xgb": "xgb"}, ["feature"], [1], [1], [2], [2], "cv", ["a", "b"]
            )

        self.assertEqual(selected, "xgb")
        self.assertEqual([event[0] for event in events], ["cv", "cv", "holdout"])
        self.assertEqual(events[-1], ("holdout", "xgb"))
        self.assertEqual(holdout["f1_macro"], 0.01)
        self.assertEqual(metrics["rf"]["f1_macro"]["mean"], 0.71)


if __name__ == "__main__":
    unittest.main()

