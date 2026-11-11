"""Compare RF/XGBoost per education stage using synthetic training data only."""
from pathlib import Path
import json, warnings
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
from backend.ml.career_data_loader import load_career_data
from backend.ml.feature_engineering import STAGE_FEATURES
from backend.ml.career_preprocessing import make_career_preprocessor
from backend.ml.career_evaluation import evaluate_cross_validation, evaluate_holdout

ROOT=Path(__file__).resolve().parents[2]; MODEL_DIR=ROOT/'backend/models/career'; METRICS=ROOT/'data/processed/career_model_metrics.json'
SEED=20260929
def candidates():
    result={'random_forest':RandomForestClassifier(n_estimators=240,min_samples_leaf=2,class_weight='balanced',random_state=SEED,n_jobs=-1)}
    try:
        from xgboost import XGBClassifier
        result['xgboost']=XGBClassifier(n_estimators=180,max_depth=5,learning_rate=.07,subsample=.85,colsample_bytree=.85,reg_lambda=1.2,objective='multi:softprob',eval_metric='mlogloss',random_state=SEED,n_jobs=2)
    except ImportError as exc: warnings.warn(f'XGBoost unavailable, skipping: {exc}')
    return result
def build_pipeline(features, model):
    return Pipeline([('preprocessor',make_career_preprocessor(features)),('model',model)])

def select_candidate_by_cv(cv_metrics):
    """Choose a model using only each candidate's training-partition CV macro-F1."""
    if not cv_metrics:
        raise ValueError('At least one candidate CV result is required.')
    return max(cv_metrics, key=lambda name: cv_metrics[name]['f1_macro']['mean'])

def evaluate_and_select(candidates, features, X_train, y_train, X_test, y_test, cv, class_names):
    """Cross-validate all candidates, select on CV only, then test the winner."""
    pipelines={name:build_pipeline(features,model) for name,model in candidates.items()}
    cv_metrics={name:evaluate_cross_validation(pipe,X_train,y_train,cv)
                for name,pipe in pipelines.items()}
    selected_name=select_candidate_by_cv(cv_metrics)
    selected_pipeline,held_out_metrics=evaluate_holdout(
        pipelines[selected_name],X_train,y_train,X_test,y_test,class_names
    )
    return selected_name,selected_pipeline,cv_metrics,held_out_metrics

def main():
    frame=load_career_data(); MODEL_DIR.mkdir(parents=True,exist_ok=True); METRICS.parent.mkdir(parents=True,exist_ok=True)
    all_results={'dataset':'data/synthetic/career_training_profiles.csv','provenance':'synthetic development data; not real student outcomes','random_seed':SEED,'test_size':.2,'cv_folds':5,'stages':{}}
    model_choices=candidates()
    if len(model_choices)<2: raise RuntimeError('Both Random Forest and XGBoost are required. Install backend/requirements.txt dependencies.')
    for level,features in STAGE_FEATURES.items():
        subset=frame[frame.education_level==level].copy(); X=subset[features+['stream']].replace('',np.nan); enc=LabelEncoder(); y=enc.fit_transform(subset.career_family)
        Xtr,Xte,ytr,yte=train_test_split(X,y,test_size=.2,random_state=SEED,stratify=y); cv=StratifiedKFold(n_splits=5,shuffle=True,random_state=SEED)
        stage={'records':len(subset),'classes':enc.classes_.tolist(),'features':features+['stream'],'results':{}}
        # The test partition is evaluated once, after CV-only selection.
        best_name,best_pipe,candidate_cv_metrics,held_out_metrics=evaluate_and_select(
            model_choices,features+['stream'],Xtr,ytr,Xte,yte,cv,enc.classes_
        )
        stage['selection_metric']='mean 5-fold training-partition CV macro-F1'
        stage['results']={name:{'cross_validation':metrics,'selected':name==best_name}
                          for name,metrics in candidate_cv_metrics.items()}
        stage['final_held_out_test']={'selected_model':best_name,**held_out_metrics}
        artifact={'pipeline':best_pipe,'label_encoder':enc,'features':features+['stream'],'education_level':level,'selected_model':best_name,'random_seed':SEED,'training_data':'synthetic only'}
        joblib.dump(artifact,MODEL_DIR/f'{level.lower().replace(" ","_").replace(chr(39),"")}_career_model.joblib')
        stage['selected_model']=best_name; stage['saved_model']=f'{level.lower().replace(" ","_").replace(chr(39),"")}_career_model.joblib'; all_results['stages'][level]=stage
    METRICS.write_text(json.dumps(all_results,indent=2),encoding='utf-8')
    print(json.dumps(all_results,indent=2))
if __name__=='__main__': main()
