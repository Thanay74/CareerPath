import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd

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

    def test_explicit_training_output_isolated_and_canonical_artifacts_preserved(self):
        root = Path(train_career_models.ROOT)
        canonical = [
            *sorted((root / "backend/models/career").glob("*.joblib")),
            root / "data/processed/career_model_metrics.json",
        ]
        before = {path: _sha256(path) for path in canonical}
        stages = list(train_career_models.STAGE_FEATURES)
        labels = ["business_finance", "creative_communication"]
        records = []
        for stage in stages:
            for label in labels:
                record = {"education_level": stage, "career_family": label, "stream": "Science"}
                record.update({feature: 50 for feature in train_career_models.STAGE_FEATURES[stage]})
                records.append(record)
        frame = pd.DataFrame(records)

        with tempfile.TemporaryDirectory(prefix="careerpath_ml_test_", dir=Path(__file__).resolve().parent) as temporary:
            output = Path(temporary) / "new-artifacts"

            def fake_dump(_artifact, path):
                Path(path).write_bytes(b"isolated-test-artifact")

            cv = {"random_forest": {"f1_macro": {"mean": 0.8, "std": 0.01}},
                  "xgboost": {"f1_macro": {"mean": 0.7, "std": 0.02}}}
            with patch.object(train_career_models, "load_career_data", return_value=frame), \
                 patch.object(train_career_models, "candidates", return_value={"random_forest": object(), "xgboost": object()}), \
                 patch.object(train_career_models, "train_test_split", side_effect=lambda X, y, **_kwargs: (X, X, y, y)), \
                 patch.object(train_career_models, "evaluate_and_select", return_value=("random_forest", {"fake_pipeline": True}, cv, {"accuracy": 0.75})), \
                 patch.object(train_career_models.joblib, "dump", side_effect=fake_dump):
                result = train_career_models.main(output)

            self.assertTrue((output / "career_model_metrics.json").is_file())
            self.assertEqual(len(list(output.glob("*_career_model.joblib"))), 4)
            saved = json.loads((output / "career_model_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(set(saved["stages"]), set(stages))
            self.assertEqual(result["output_mode"], "isolated")
            self.assertEqual(result["output_directory"], str(output.resolve()))
            self.assertEqual({path: _sha256(path) for path in canonical}, before)

    def test_explicit_training_output_rejects_existing_or_canonical_targets(self):
        with tempfile.TemporaryDirectory(prefix="careerpath_ml_test_", dir=Path(__file__).resolve().parent) as temporary:
            existing = Path(temporary) / "already-here"
            existing.mkdir()
            with self.assertRaises(FileExistsError):
                train_career_models._output_targets(existing)
        with self.assertRaises(ValueError):
            train_career_models._output_targets(train_career_models.MODEL_DIR)
        with self.assertRaises(ValueError):
            train_career_models._output_targets(train_career_models.METRICS.parent)


if __name__ == "__main__":
    unittest.main()

