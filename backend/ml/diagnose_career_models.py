"""Reproduce held-out majority-class baselines without changing model artifacts."""
from pathlib import Path
import json

import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split

from backend.ml.career_data_loader import load_career_data
from backend.ml.feature_engineering import STAGE_FEATURES

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "data/processed/career_model_diagnostic.json"
SEED = 20260929


def evaluate_baselines():
    frame = load_career_data()
    report = {
        "dataset": "data/synthetic/career_training_profiles.csv",
        "provenance": "synthetic development data; not real student outcomes",
        "random_seed": SEED,
        "test_size": 0.2,
        "method": "DummyClassifier(strategy='prior') on the same stratified held-out split as the RF/XGBoost comparison",
        "limitation": "The synthetic target family was generated from family-specific feature archetypes; these scores do not establish real-world career accuracy.",
        "stages": {},
    }
    for level, features in STAGE_FEATURES.items():
        subset = frame[frame.education_level == level]
        X = subset[features + ["stream"]].replace("", np.nan)
        y = subset.career_family
        _, X_test, _, y_test = train_test_split(X, y, test_size=0.2, random_state=SEED, stratify=y)
        baseline = DummyClassifier(strategy="prior")
        X_train = X.drop(index=X_test.index)
        y_train = y.drop(index=X_test.index)
        baseline.fit(X_train, y_train)
        predicted = baseline.predict(X_test)
        labels = sorted(y.unique())
        report["stages"][level] = {
            "records": int(len(subset)),
            "classes": labels,
            "majority_class": str(y_train.value_counts().idxmax()),
            "accuracy": float(accuracy_score(y_test, predicted)),
            "precision_macro": float(precision_score(y_test, predicted, labels=labels, average="macro", zero_division=0)),
            "recall_macro": float(recall_score(y_test, predicted, labels=labels, average="macro", zero_division=0)),
            "f1_macro": float(f1_score(y_test, predicted, labels=labels, average="macro", zero_division=0)),
            "classification_report": classification_report(y_test, predicted, labels=labels, output_dict=True, zero_division=0),
            "confusion_matrix": confusion_matrix(y_test, predicted, labels=labels).tolist(),
        }
    return report


def main():
    result = evaluate_baselines()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
