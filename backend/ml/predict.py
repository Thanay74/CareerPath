"""Inference adapters for stage-specific synthetic family model and UCI model."""
from pathlib import Path
from io import BytesIO
import hashlib
import joblib
import numpy as np
import pandas as pd
from backend.ml.data_loader import ROOT
from backend.ml.feature_engineering import feature_row
from backend.ml.artifact_contract import (
    ModelInferenceError, STAGE_FILENAMES, validate_model_artifact,
)

CAREER_MODEL_DIR=ROOT/'backend/models/career'


class FamilyProbabilities(dict):
    """Probability mapping with the exact artifact identity used for inference."""

    def __init__(self, *args, model_identity=None, validation_status=None, missing_metadata=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.model_identity = model_identity
        self.validation_status = validation_status
        self.missing_metadata = tuple(missing_metadata)


def model_artifact_identity(level):
    """Return a stable hash of the active stage artifact without deserializing it."""
    filename = STAGE_FILENAMES.get(level)
    if filename is None:
        return None
    try:
        content = (CAREER_MODEL_DIR / filename).read_bytes()
    except OSError:
        return None
    return hashlib.sha256(content).hexdigest()


def load_active_stage_model(level):
    filename=STAGE_FILENAMES.get(level)
    if filename is None:
        raise ModelInferenceError('unsupported_stage')
    path=CAREER_MODEL_DIR/filename
    try:
        artifact_bytes=path.read_bytes()
    except FileNotFoundError:
        raise ModelInferenceError('model_missing') from None
    except OSError:
        raise ModelInferenceError('artifact_unreadable') from None
    digest=hashlib.sha256(artifact_bytes).hexdigest()
    try:
        loaded=joblib.load(BytesIO(artifact_bytes))
    except Exception:
        raise ModelInferenceError('artifact_unreadable') from None
    validated=validate_model_artifact(loaded,level,digest)
    return validated


def predict_career_families(profile):
    level=profile.get('education_level','10th')
    validated=load_active_stage_model(level)
    loaded=validated.artifact
    try:
        row=feature_row(profile,level)
        X=pd.DataFrame([{key:row.get(key) for key in loaded['features']}]).replace('',None)
        probabilities=np.asarray(loaded['pipeline'].predict_proba(X),dtype=float)
    except Exception:
        raise ModelInferenceError('prediction_failed') from None
    expected_shape=(1,len(loaded['label_encoder'].classes_))
    if probabilities.shape != expected_shape:
        raise ModelInferenceError('probability_shape_invalid')
    values=probabilities[0]
    if not np.isfinite(values).all() or (values < 0).any() or (values > 1).any():
        raise ModelInferenceError('probability_values_invalid')
    if not np.isclose(float(values.sum()),1.0,rtol=0.0,atol=1e-6):
        raise ModelInferenceError('probability_sum_invalid')
    labels=list(loaded['label_encoder'].classes_)
    return FamilyProbabilities(
        {label:float(value) for label,value in zip(labels,values)},
        model_identity=validated.sha256,
        validation_status=validated.validation_status,
        missing_metadata=validated.missing_metadata,
    )

def predict_grade_band(row):
    path=ROOT/'backend/models/grade_band_pipeline.joblib'
    if not path.exists(): raise FileNotFoundError('Train the academic experiment first.')
    return joblib.load(path).predict(pd.DataFrame([row]))[0]
