"""Compare RF/XGBoost per education stage using synthetic training data only."""
from pathlib import Path
import argparse, hashlib, json, warnings
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
from backend.ml.artifact_contract import FEATURE_SCHEMA_VERSION

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

def _output_targets(output_dir):
    """Resolve an optional fresh isolated output root without touching active paths."""
    if output_dir is None:
        return MODEL_DIR, METRICS, False
    requested=Path(output_dir).expanduser().absolute()
    target=requested.resolve()
    if requested.is_symlink():
        raise ValueError('Refusing a symlink output directory.')
    protected=(MODEL_DIR.resolve(), METRICS.parent.resolve())
    for path in protected:
        if target==path or target in path.parents or path in target.parents:
            raise ValueError('Explicit output directory must not overlap active model or metrics locations.')
    if requested.exists() or target.exists():
        raise FileExistsError(f'Explicit output directory must be new and absent: {target}')
    return target, target/'career_model_metrics.json', True

def main(output_dir=None):
    model_dir,metrics_path,isolated=_output_targets(output_dir)
    # Reserve a new explicit destination before any training or artifact write.
    model_dir.mkdir(parents=True,exist_ok=not isolated)
    if not isolated:
        metrics_path.parent.mkdir(parents=True,exist_ok=True)
    source=ROOT/'data/synthetic/career_training_profiles.csv'
    dataset_sha256=hashlib.sha256(source.read_bytes()).hexdigest()
    frame=load_career_data(source)
    all_results={'dataset':'data/synthetic/career_training_profiles.csv','dataset_sha256':dataset_sha256,'provenance':'synthetic development data; not real student outcomes','random_seed':SEED,'test_size':.2,'cv_folds':5,'selection_metric':'mean 5-fold training-partition CV macro-F1','training_procedure':'Stratified 80/20 split; candidate selection by mean stratified five-fold macro-F1 on training partition only; selected candidate evaluated once on untouched holdout.','feature_schema_version':FEATURE_SCHEMA_VERSION,'output_mode':'isolated' if isolated else 'default','output_directory':str(model_dir.resolve()),'stages':{}}
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
        schema_payload=json.dumps({'version':FEATURE_SCHEMA_VERSION,'education_level':level,'features':features+['stream']},sort_keys=True,separators=(',',':')).encode('utf-8')
        feature_schema_sha256=hashlib.sha256(schema_payload).hexdigest()
        selected_cv_macro_f1=candidate_cv_metrics[best_name]['f1_macro']['mean']
        model_type=type(best_pipe.named_steps['model']).__name__ if hasattr(best_pipe,'named_steps') else type(best_pipe).__name__
        artifact={'pipeline':best_pipe,'label_encoder':enc,'features':features+['stream'],'education_level':level,'selected_model':best_name,'model_type':model_type,'random_seed':SEED,'training_data':'synthetic only','training_dataset_sha256':dataset_sha256,'feature_schema_version':FEATURE_SCHEMA_VERSION,'feature_schema_sha256':feature_schema_sha256,'selection_metric':all_results['selection_metric'],'training_procedure':all_results['training_procedure'],'selected_cv_macro_f1':selected_cv_macro_f1}
        filename=f'{level.lower().replace(" ","_").replace(chr(39),"")}_career_model.joblib'
        artifact_path=model_dir/filename
        joblib.dump(artifact,artifact_path)
        stage.update({'selected_model':best_name,'selected_cv_macro_f1':selected_cv_macro_f1,'saved_model':filename,'artifact_sha256':hashlib.sha256(artifact_path.read_bytes()).hexdigest(),'model_type':model_type,'training_dataset_sha256':dataset_sha256,'feature_schema_version':FEATURE_SCHEMA_VERSION,'feature_schema_sha256':feature_schema_sha256})
        all_results['stages'][level]=stage
    metrics_path.write_text(json.dumps(all_results,indent=2),encoding='utf-8')
    print(json.dumps(all_results,indent=2))
    return all_results

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Train stage-specific synthetic career-family models.')
    parser.add_argument('--output-dir',help='Write four artifacts and metrics to a fresh isolated directory; default paths are unchanged.')
    main(parser.parse_args().output_dir)
