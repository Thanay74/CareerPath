"""Inference adapters for stage-specific synthetic family model and UCI model."""
from pathlib import Path
import joblib
import pandas as pd
from backend.ml.data_loader import ROOT
from backend.ml.feature_engineering import feature_row

CAREER_MODEL_DIR=ROOT/'backend/models/career'
def predict_career_families(profile):
    level=profile.get('education_level','10th')
    path=CAREER_MODEL_DIR/f'{level.lower().replace(" ","_").replace(chr(39),"")}_career_model.joblib'
    if not path.exists(): raise FileNotFoundError(f'Career model for {level} missing; run python -m backend.ml.train_career_models')
    artifact=joblib.load(path); row=feature_row(profile,level); X=pd.DataFrame([{k:row.get(k) for k in artifact['features']}]).replace('',None)
    model=artifact['pipeline']; probs=model.predict_proba(X)[0]
    return {artifact['label_encoder'].inverse_transform([int(i)])[0]:float(p) for i,p in enumerate(probs)}

def predict_grade_band(row):
    path=ROOT/'backend/models/grade_band_pipeline.joblib'
    if not path.exists(): raise FileNotFoundError('Train the academic experiment first.')
    return joblib.load(path).predict(pd.DataFrame([row]))[0]
