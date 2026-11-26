import unittest
from unittest.mock import patch

import numpy as np

from backend.ml.artifact_contract import (
    CAREER_FAMILIES, ModelInferenceError, ValidatedModel, expected_features,
    expected_schema_sha256, validate_model_artifact,
)
from backend.ml import predict


class FakeEncoder:
    classes_ = np.asarray(CAREER_FAMILIES)


class RandomForestClassifier:
    classes_ = np.arange(len(CAREER_FAMILIES))

    def __init__(self, output=None):
        self.output = output if output is not None else [[0.2] * len(CAREER_FAMILIES)]

    def predict_proba(self, _frame):
        if isinstance(self.output, Exception):
            raise self.output
        return self.output


class FakePreprocessor:
    def transform(self, frame):
        return np.zeros((1, 2))

    def get_feature_names_out(self):
        return np.asarray(["numeric__problem_solving", "categorical__stream_Arts_and_Humanities"])


class FakePipeline:
    def __init__(self, output=None):
        self.named_steps = {"preprocessor": FakePreprocessor(), "model": RandomForestClassifier(output)}

    def predict_proba(self, frame):
        return self.named_steps["model"].predict_proba(frame)


def fake_artifact(stage="10th", **overrides):
    artifact = {
        "education_level": stage,
        "features": expected_features(stage),
        "feature_schema_version": "career-stage-features-v1",
        "feature_schema_sha256": expected_schema_sha256(stage),
        "model_type": "RandomForestClassifier",
        "selected_model": "random_forest",
        "label_encoder": FakeEncoder(),
        "pipeline": FakePipeline(),
    }
    artifact.update(overrides)
    return artifact


class ArtifactContractTests(unittest.TestCase):
    def test_valid_current_and_legacy_artifacts_are_distinguished(self):
        full = validate_model_artifact(fake_artifact(), "10th", "a" * 64)
        self.assertEqual(full.validation_status, "fully_validated")
        legacy = fake_artifact()
        for key in ("feature_schema_version", "feature_schema_sha256", "model_type", "selected_model"):
            legacy.pop(key)
        checked = validate_model_artifact(legacy, "10th", "b" * 64)
        self.assertEqual(checked.validation_status, "legacy_compatible")
        self.assertEqual(len(checked.missing_metadata), 4)

    def test_rejects_stage_feature_order_schema_and_class_mismatch(self):
        bad_estimator = type("BadEstimator", (), {"classes_": [0, 1], "predict_proba": lambda self, _: []})()
        bad_pipeline = FakePipeline()
        bad_pipeline.named_steps["model"] = bad_estimator
        cases = [
            (fake_artifact("12th"), "10th", "stage_mismatch"),
            (fake_artifact(features=list(reversed(expected_features("10th")))), "10th", "feature_schema_mismatch"),
            (fake_artifact(feature_schema_sha256="0" * 64), "10th", "feature_schema_mismatch"),
            (fake_artifact(label_encoder=type("BadEncoder", (), {"classes_": ["wrong"]})()), "10th", "class_mismatch"),
            (fake_artifact(pipeline=bad_pipeline), "10th", "class_mismatch"),
            (fake_artifact(features=expected_features("10th")[:-1]), "10th", "feature_schema_mismatch"),
        ]
        for artifact, stage, reason in cases:
            with self.subTest(reason=reason), self.assertRaises(ModelInferenceError) as raised:
                validate_model_artifact(artifact, stage, "c" * 64)
            self.assertEqual(raised.exception.reason, reason)


class InferenceOutputTests(unittest.TestCase):
    def _validated(self, output):
        artifact = fake_artifact(pipeline=FakePipeline(output))
        return ValidatedModel(artifact, "d" * 64, "legacy_compatible", ())

    def test_valid_probabilities_keep_encoder_class_order_and_identity(self):
        with patch.object(predict, "load_active_stage_model", return_value=self._validated([[0.1, 0.2, 0.3, 0.15, 0.25]])):
            result = predict.predict_career_families({"education_level": "10th"})
        self.assertEqual(list(result), list(CAREER_FAMILIES))
        self.assertAlmostEqual(result["health_life_sciences"], 0.3)
        self.assertEqual(result.model_identity, "d" * 64)

    def test_rejects_invalid_probability_shapes_values_sums_and_prediction_errors(self):
        invalid = [
            ([[0.2] * 4], "probability_shape_invalid"),
            ([[0.2, 0.2, 0.2, 0.2, 0.2], [0.2] * 5], "probability_shape_invalid"),
            ([[float("nan"), 0.25, 0.25, 0.25, 0.25]], "probability_values_invalid"),
            ([[float("inf"), 0.0, 0.0, 0.0, 0.0]], "probability_values_invalid"),
            ([[-0.1, 0.3, 0.3, 0.3, 0.2]], "probability_values_invalid"),
            ([[0.1, 0.1, 0.1, 0.1, 0.1]], "probability_sum_invalid"),
            (RuntimeError("private diagnostic"), "prediction_failed"),
        ]
        for output, reason in invalid:
            with self.subTest(reason=reason), patch.object(predict, "load_active_stage_model", return_value=self._validated(output)):
                with self.assertRaises(ModelInferenceError) as raised:
                    predict.predict_career_families({"education_level": "10th"})
                self.assertEqual(raised.exception.reason, reason)

    def test_missing_and_corrupt_artifacts_fail_without_detail(self):
        with patch.object(predict, "CAREER_MODEL_DIR") as model_dir, patch.object(predict.Path, "read_bytes", side_effect=FileNotFoundError):
            model_dir.__truediv__.return_value = predict.Path("missing.joblib")
            with self.assertRaises(ModelInferenceError) as missing:
                predict.load_active_stage_model("10th")
        self.assertEqual(missing.exception.reason, "model_missing")
        with patch.object(predict, "CAREER_MODEL_DIR") as model_dir, patch.object(predict.Path, "read_bytes", return_value=b"opaque"), patch.object(predict.joblib, "load", side_effect=ValueError("secret path")):
            model_dir.__truediv__.return_value = predict.Path("corrupt.joblib")
            with self.assertRaises(ModelInferenceError) as corrupt:
                predict.load_active_stage_model("10th")
        self.assertEqual(corrupt.exception.reason, "artifact_unreadable")
        self.assertNotIn("secret", str(corrupt.exception))


class DeterministicFallbackTests(unittest.TestCase):
    def test_model_failure_returns_explicit_compatibility_only_pathway(self):
        from backend.services.recommendation_engine import _recommend_with_catalog

        with patch("backend.ml.predict.predict_career_families", side_effect=ModelInferenceError("model_missing")):
            results = _recommend_with_catalog({
                "education_level": "10th",
                "subjects": {"mathematics": 70, "science": 65},
                "interests": {"technology": 60},
            }, 4)
        self.assertEqual(results.model_status, "unavailable")
        self.assertIsNone(results.model_identity)
        self.assertTrue(results)
        for item in results:
            self.assertEqual(item["ml_status"], "unavailable")
            self.assertIsNone(item["ml_family_probability"])
            self.assertIsNone(item["ml_family_probabilities"])
            self.assertEqual(item["ranking_method"], "compatibility_only_ml_unavailable")
            self.assertIn("compatibility-only", " ".join(item["why_matches"]))

    def test_incomplete_probability_mapping_cannot_become_a_zero_family_score(self):
        from backend.services.recommendation_engine import _recommend_with_catalog

        with patch("backend.ml.predict.predict_career_families", return_value={"business_finance": 1.0}):
            results = _recommend_with_catalog({"education_level": "10th", "subjects": {"mathematics": 60}}, 4)
        self.assertEqual(results.model_status, "unavailable")
        self.assertEqual(results.model_failure_reason, "probability_values_invalid")
        self.assertTrue(all(item["ml_family_probability"] is None for item in results))

    def test_later_stage_uses_compatibility_only_when_model_is_missing(self):
        from backend.services.recommendation_engine import _recommend_with_catalog

        profile={"education_level":"Bachelor's","stream":"Science","degree":"BSc",
            "subjects":{"mathematics":70},"technical":{"python":60}}
        with patch("backend.ml.predict.predict_career_families", side_effect=ModelInferenceError("model_missing")):
            results=_recommend_with_catalog(profile,3)
        self.assertEqual(results.model_status,"unavailable")
        self.assertTrue(results)
        self.assertTrue(all(item["ranking_method"]=="compatibility_only_ml_unavailable" for item in results))
        self.assertTrue(all(item["ml_family_probability"] is None and item["ml_family"] is None for item in results))


class ExplanationContractTests(unittest.TestCase):
    def _model(self, model_type="RandomForestClassifier", output=None):
        estimator_type = type(model_type, (), {
            "classes_": np.arange(len(CAREER_FAMILIES)),
            "predict_proba": lambda self, _x: output or [[0.2] * len(CAREER_FAMILIES)],
        })
        artifact = fake_artifact(model_type=model_type, pipeline=type("Pipeline", (), {
            "named_steps": {"preprocessor": FakePreprocessor(), "model": estimator_type()},
        })())
        return ValidatedModel(artifact, "e" * 64, "fully_validated", ())

    def test_probability_and_raw_margin_output_spaces_and_feature_alignment(self):
        import sys
        from types import SimpleNamespace
        from backend.ml.explain import explain_career_model

        values = np.asarray([[[0, 0, 0, 0, 1], [0, 0, 0, 0, 2]]], dtype=float)
        shap_module = SimpleNamespace(TreeExplainer=lambda _model: SimpleNamespace(shap_values=lambda _x: values))
        profile = {"education_level": "10th"}
        with patch("backend.ml.explain.load_active_stage_model", return_value=self._model()), patch.dict(sys.modules, {"shap": shap_module}):
            rf = explain_career_model(profile, CAREER_FAMILIES[-1], "e" * 64)
        self.assertEqual(rf["output_space"], "probability")
        self.assertEqual([item["feature"] for item in rf["contributions"]], ["stream_Arts_and_Humanities", "problem_solving"])
        with patch("backend.ml.explain.load_active_stage_model", return_value=self._model("XGBClassifier")), patch.dict(sys.modules, {"shap": shap_module}):
            xgb = explain_career_model(profile, CAREER_FAMILIES[-1], "e" * 64)
        self.assertEqual(xgb["output_space"], "raw_margin")

    def test_unavailable_and_changed_model_explanations_are_explicit(self):
        from backend.ml.explain import explain_career_model

        profile = {"education_level": "10th"}
        with patch("backend.ml.explain.load_active_stage_model", side_effect=ModelInferenceError("model_missing")):
            missing = explain_career_model(profile, CAREER_FAMILIES[0])
        self.assertEqual(missing["method"], "unavailable")
        self.assertEqual(missing["output_space"], "unavailable")
        with patch("backend.ml.explain.load_active_stage_model", return_value=self._model()):
            changed = explain_career_model(profile, CAREER_FAMILIES[0], "f" * 64)
        self.assertEqual(changed["reason"], "model_changed_during_recommendation")

    def test_misaligned_shap_dimensions_are_unavailable(self):
        import sys
        from types import SimpleNamespace
        from backend.ml.explain import explain_career_model

        shap_module = SimpleNamespace(TreeExplainer=lambda _model: SimpleNamespace(shap_values=lambda _x: np.zeros((1, 1, 2))))
        with patch("backend.ml.explain.load_active_stage_model", return_value=self._model()), patch.dict(sys.modules, {"shap": shap_module}):
            result = explain_career_model({"education_level": "10th"}, CAREER_FAMILIES[0])
        self.assertEqual(result["method"], "unavailable")
        self.assertEqual(result["reason"], "explanation_alignment_invalid")


if __name__ == "__main__":
    unittest.main()
