"""Runtime checks for stage-specific career-family model artifacts."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass

from backend.ml.feature_engineering import STAGE_FEATURES

FEATURE_SCHEMA_VERSION = "career-stage-features-v1"


CAREER_FAMILIES = (
    "business_finance",
    "creative_communication",
    "health_life_sciences",
    "public_social_research",
    "technology_engineering",
)
STAGE_FILENAMES = {
    "10th": "10th_career_model.joblib",
    "12th": "12th_career_model.joblib",
    "Bachelor's": "bachelors_career_model.joblib",
    "Master's": "masters_career_model.joblib",
}


class ModelInferenceError(Exception):
    """Safe, student-facing model failure category without implementation details."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True)
class ValidatedModel:
    artifact: dict
    sha256: str
    validation_status: str
    missing_metadata: tuple[str, ...]


def expected_features(stage: str) -> list[str]:
    if stage not in STAGE_FEATURES:
        raise ModelInferenceError("unsupported_stage")
    return list(dict.fromkeys([*STAGE_FEATURES[stage], "stream"]))


def expected_schema_sha256(stage: str) -> str:
    payload = json.dumps(
        {"version": FEATURE_SCHEMA_VERSION, "education_level": stage,
         "features": expected_features(stage)},
        sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_model_artifact(artifact, stage: str, artifact_sha256: str) -> ValidatedModel:
    """Validate all available artifact structure; accept safe legacy metadata gaps."""
    if not isinstance(artifact, dict):
        raise ModelInferenceError("artifact_invalid")
    if artifact.get("education_level") != stage:
        raise ModelInferenceError("stage_mismatch")
    features = artifact.get("features")
    if not isinstance(features, list) or features != expected_features(stage):
        raise ModelInferenceError("feature_schema_mismatch")

    version = artifact.get("feature_schema_version")
    digest = artifact.get("feature_schema_sha256")
    if version is not None and version != FEATURE_SCHEMA_VERSION:
        raise ModelInferenceError("feature_schema_mismatch")
    if digest is not None and digest != expected_schema_sha256(stage):
        raise ModelInferenceError("feature_schema_mismatch")

    encoder = artifact.get("label_encoder")
    encoder_classes = getattr(encoder, "classes_", None)
    if encoder_classes is None or list(encoder_classes) != list(CAREER_FAMILIES):
        raise ModelInferenceError("class_mismatch")

    pipeline = artifact.get("pipeline")
    steps = getattr(pipeline, "named_steps", None)
    if not isinstance(steps, Mapping) or not {"preprocessor", "model"}.issubset(steps):
        raise ModelInferenceError("pipeline_invalid")
    preprocessor, estimator = steps["preprocessor"], steps["model"]
    if (not callable(getattr(preprocessor, "transform", None))
            or not callable(getattr(estimator, "predict_proba", None))
            or not callable(getattr(pipeline, "predict_proba", None))):
        raise ModelInferenceError("pipeline_invalid")
    estimator_classes = getattr(estimator, "classes_", None)
    if estimator_classes is None or list(estimator_classes) != list(range(len(CAREER_FAMILIES))):
        raise ModelInferenceError("class_mismatch")

    model_type = type(estimator).__name__
    if model_type not in {"RandomForestClassifier", "XGBClassifier"}:
        raise ModelInferenceError("pipeline_invalid")
    if artifact.get("model_type") is not None and artifact["model_type"] != model_type:
        raise ModelInferenceError("artifact_invalid")
    selected_model=artifact.get("selected_model")
    selected_types={"random_forest":"RandomForestClassifier","xgboost":"XGBClassifier"}
    if selected_model is not None and selected_types.get(selected_model) != model_type:
        raise ModelInferenceError("artifact_invalid")

    missing = tuple(key for key, value in (
        ("feature_schema_version", version), ("feature_schema_sha256", digest),
        ("model_type", artifact.get("model_type")), ("selected_model", selected_model),
    ) if value is None)
    return ValidatedModel(
        artifact=artifact,
        sha256=artifact_sha256,
        validation_status="legacy_compatible" if missing else "fully_validated",
        missing_metadata=missing,
    )
