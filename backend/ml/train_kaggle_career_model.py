"""Compare RF and XGBoost on the downloaded Kaggle synthetic career data.

This is a university-level benchmark only. It does not replace the four
stage-specific CareerPath recommendation models.
"""
from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, OneHotEncoder

from backend.ml.career_evaluation import evaluate_candidate
from backend.ml.kaggle_career_features import (
    CATEGORICAL_FEATURES,
    FEATURES,
    TARGET,
    validate_and_filter,
)

ROOT = Path(__file__).resolve().parents[2]
SOURCE_DATA = ROOT / "data/raw/kaggle_student_career_success/student_career_success_dataset.csv"
DATA = ROOT / "data/processed/kaggle_student_career_success/career_field_training.csv"
MODEL_PATH = ROOT / "backend/models/kaggle/kaggle_bachelor_career_field.joblib"
METRICS_PATH = ROOT / "data/processed/kaggle_career_model_metrics.json"
SEED = 20261010


def candidates():
    from xgboost import XGBClassifier

    return {
        "random_forest": RandomForestClassifier(
            n_estimators=120,
            max_depth=16,
            min_samples_split=16,
            min_samples_leaf=8,
            class_weight="balanced_subsample",
            random_state=SEED,
            n_jobs=-1,
        ),
        "xgboost": XGBClassifier(
            n_estimators=180,
            max_depth=6,
            learning_rate=0.07,
            subsample=0.85,
            colsample_bytree=0.85,
            reg_lambda=1.2,
            objective="multi:softprob",
            eval_metric="mlogloss",
            random_state=SEED,
            n_jobs=2,
        ),
    }


def build_pipeline(model):
    categorical = [name for name in FEATURES if name in CATEGORICAL_FEATURES]
    numeric = [name for name in FEATURES if name not in CATEGORICAL_FEATURES]
    preprocessor = ColumnTransformer(
        [
            ("numeric", SimpleImputer(strategy="median", add_indicator=True), numeric),
            (
                "categorical",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="most_frequent")),
                        ("encode", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical,
            ),
        ]
    )
    return Pipeline([("preprocessor", preprocessor), ("model", model)])


def main():
    if not SOURCE_DATA.exists() or not DATA.exists():
        raise FileNotFoundError(
            "Missing the Kaggle source or processed training CSV. Run "
            "python -m backend.ml.preprocess_kaggle_career after downloading it."
        )
    frame = validate_and_filter(pd.read_csv(DATA))
    X = frame[FEATURES]
    encoder = LabelEncoder()
    y = encoder.fit_transform(frame[TARGET])
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=SEED,
        stratify=y,
    )
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    reports = {
        "dataset": "data/raw/kaggle_student_career_success/student-career-success-prediction-dataset.zip",
        "source_csv": "data/raw/kaggle_student_career_success/student_career_success_dataset.csv",
        "processed_csv": "data/processed/kaggle_student_career_success/career_field_training.csv",
        "provenance": "Kaggle-published synthetic university student records; not real student outcomes",
        "scope": "Bachelor's/university career-field benchmark; not used for 10th, 12th, or Master's models",
        "target": TARGET,
        "excluded_target_value": "Not Placed; this task predicts a field conditional on the synthetic row being placed",
        "features": FEATURES,
        "excluded_fields": [
            "Student_ID", "Age", "Gender", "Academic_Performance", "Interview_Score",
            "Employability_Score", "Placement_Status", "Company_Tier", "Career_Field",
            "Placement_Mode", "Starting_Salary_USD",
        ],
        "records_total": int(len(pd.read_csv(SOURCE_DATA))),
        "records_labeled_placed": int(len(frame)),
        "class_counts": {str(k): int(v) for k, v in frame[TARGET].value_counts().sort_index().items()},
        "random_seed": SEED,
        "test_size": 0.2,
        "cv_folds": 5,
        "selection_metric": "mean 5-fold training-partition macro F1; the held-out test partition is used only for final evaluation",
        "results": {},
    }
    best_name = None
    best_f1 = -1.0
    best_pipeline = None
    for name, model in candidates().items():
        pipeline, metrics = evaluate_candidate(
            build_pipeline(model), X_train, y_train, X_test, y_test, cv, encoder.classes_
        )
        reports["results"][name] = metrics
        cv_f1 = metrics["cv"]["test_f1_macro"]["mean"]
        if cv_f1 > best_f1:
            best_name, best_f1, best_pipeline = name, cv_f1, pipeline

    reports["selected_model"] = best_name
    reports["interpretation"] = (
        "Scores measure agreement with the source's synthetic rule-generated labels only; "
        "they are not estimates of real-world student career accuracy."
    )
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "pipeline": best_pipeline,
            "label_encoder": encoder,
            "features": FEATURES,
            "target": TARGET,
            "scope": "synthetic Kaggle university career-field benchmark; not production recommender",
            "selected_model": best_name,
            "random_seed": SEED,
        },
        MODEL_PATH,
    )
    METRICS_PATH.write_text(json.dumps(reports, indent=2), encoding="utf-8")
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
