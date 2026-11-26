"""Read-only validation of artifacts from an explicitly supplied isolated run."""
import hashlib
import json
import os
import unittest
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from backend.ml.feature_engineering import STAGE_FEATURES


OUTPUT = Path(os.environ["CAREERPATH_ML_VALIDATION_DIR"]) if os.environ.get("CAREERPATH_ML_VALIDATION_DIR") else None
ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/synthetic/career_training_profiles.csv"


@unittest.skipUnless(OUTPUT, "Set CAREERPATH_ML_VALIDATION_DIR to a completed isolated training output.")
class IsolatedCareerArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.metrics = json.loads((OUTPUT / "career_model_metrics.json").read_text(encoding="utf-8"))
        cls.dataset_hash = hashlib.sha256(DATASET.read_bytes()).hexdigest()

    def test_all_stage_artifacts_have_matching_lineage_and_feature_schema(self):
        self.assertEqual(set(self.metrics["stages"]), set(STAGE_FEATURES))
        self.assertEqual(self.metrics["dataset_sha256"], self.dataset_hash)
        for level, features in STAGE_FEATURES.items():
            with self.subTest(stage=level):
                stage = self.metrics["stages"][level]
                path = OUTPUT / stage["saved_model"]
                self.assertTrue(path.is_file())
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), stage["artifact_sha256"])
                artifact = joblib.load(path)
                self.assertEqual(artifact["education_level"], level)
                self.assertEqual(artifact["selected_model"], stage["selected_model"])
                self.assertEqual(artifact["training_dataset_sha256"], self.dataset_hash)
                self.assertEqual(artifact["features"], features + ["stream"])
                self.assertEqual(artifact["feature_schema_version"], self.metrics["feature_schema_version"])
                self.assertEqual(artifact["feature_schema_sha256"], stage["feature_schema_sha256"])
                self.assertEqual(artifact["selected_cv_macro_f1"], stage["selected_cv_macro_f1"])
                self.assertEqual(artifact["training_procedure"], self.metrics["training_procedure"])
                self.assertEqual(type(artifact["pipeline"].named_steps["model"]).__name__, artifact["model_type"])
                schema = json.dumps(
                    {"version": artifact["feature_schema_version"], "education_level": level,
                     "features": features + ["stream"]},
                    sort_keys=True, separators=(",", ":"),
                ).encode("utf-8")
                self.assertEqual(hashlib.sha256(schema).hexdigest(), artifact["feature_schema_sha256"])

    def test_all_stage_artifacts_return_valid_family_probabilities(self):
        for level, features in STAGE_FEATURES.items():
            with self.subTest(stage=level):
                artifact = joblib.load(OUTPUT / self.metrics["stages"][level]["saved_model"])
                row = {name: 55.0 for name in features}
                row["stream"] = "Science"
                probabilities = np.asarray(artifact["pipeline"].predict_proba(pd.DataFrame([row])[artifact["features"]]))
                classes = artifact["label_encoder"].classes_
                self.assertEqual(probabilities.shape, (1, len(classes)))
                self.assertTrue(np.isfinite(probabilities).all())
                self.assertTrue(((probabilities >= 0) & (probabilities <= 1)).all())
                self.assertAlmostEqual(float(probabilities.sum()), 1.0, places=5)
                self.assertEqual(set(classes), set(self.metrics["stages"][level]["classes"]))

    def test_shap_contributions_are_finite_and_match_feature_and_class_axes(self):
        import shap

        for level, features in STAGE_FEATURES.items():
            with self.subTest(stage=level):
                artifact = joblib.load(OUTPUT / self.metrics["stages"][level]["saved_model"])
                pipeline = artifact["pipeline"]
                row = {name: 55.0 for name in features}
                row["stream"] = "Science"
                frame = pd.DataFrame([row])[artifact["features"]]
                transformed = pipeline.named_steps["preprocessor"].transform(frame)
                model = pipeline.named_steps["model"]
                explainer = shap.TreeExplainer(model)
                contributions = explainer.shap_values(transformed)
                class_count = len(artifact["label_encoder"].classes_)
                feature_count = len(pipeline.named_steps["preprocessor"].get_feature_names_out())
                self.assertEqual(list(model.classes_), list(range(class_count)))
                if isinstance(contributions, list):
                    self.assertEqual(len(contributions), class_count)
                    class_values = [np.asarray(item) for item in contributions]
                    for class_contribution in contributions:
                        self.assertTrue(np.isfinite(np.asarray(class_contribution)).all())
                else:
                    values = np.asarray(contributions)
                    self.assertEqual(values.shape, (1, feature_count, class_count))
                    self.assertTrue(np.isfinite(values).all())
                    class_values = [values[:, :, index] for index in range(class_count)]
                expected = np.asarray(explainer.expected_value).reshape(-1)
                self.assertEqual(expected.size, class_count)
                if type(model).__name__ == "XGBClassifier":
                    model_output = np.asarray(model.predict(transformed, output_margin=True))[0]
                else:
                    model_output = np.asarray(model.predict_proba(transformed))[0]
                self.assertEqual(model_output.size, class_count)
                for class_index, values in enumerate(class_values):
                    self.assertEqual(values.shape, (1, feature_count))
                    self.assertAlmostEqual(
                        float(expected[class_index] + values[0].sum()),
                        float(model_output[class_index]),
                        delta=1e-3,
                        msg=f"SHAP contributions must reconstruct class {artifact['label_encoder'].classes_[class_index]}.",
                    )


if __name__ == "__main__":
    unittest.main()
