"""Train honest UCI academic grade-band experiment; never a career classifier."""
from pathlib import Path
import json
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score,precision_recall_fscore_support,confusion_matrix,classification_report
from sklearn.model_selection import train_test_split,cross_val_score,StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder,StandardScaler
from sklearn.inspection import permutation_importance
import joblib

ROOT=Path(__file__).resolve().parents[2]; SOURCE=ROOT/'data/raw/student_performance/extracted/student-mat.csv'; OUT=ROOT/'backend/models'
def main():
    if not SOURCE.exists(): raise SystemExit('UCI file missing. Run: python data/download_public_data.py')
    df=pd.read_csv(SOURCE,sep=';'); required={'G3'}
    if not required.issubset(df.columns): raise ValueError('Unexpected UCI columns; expected G3 target')
    y=pd.cut(df.G3,bins=[-1,9,13,20],labels=['low','pass','high']).astype(str)
    X=df.drop(columns=['G1','G2','G3']) # G1/G2 are temporal near-target leakage.
    cats=X.select_dtypes(include='object').columns.tolist(); nums=X.select_dtypes(exclude='object').columns.tolist()
    prep=ColumnTransformer([('num',Pipeline([('impute',SimpleImputer(strategy='median')),('scale',StandardScaler())]),nums),('cat',Pipeline([('impute',SimpleImputer(strategy='most_frequent')),('onehot',OneHotEncoder(handle_unknown='ignore'))]),cats)])
    Xtr,Xte,ytr,yte=train_test_split(X,y,test_size=.2,random_state=42,stratify=y)
    models={'majority_baseline':DummyClassifier(strategy='most_frequent'),'random_forest':RandomForestClassifier(n_estimators=300,class_weight='balanced',random_state=42,min_samples_leaf=2)}
    OUT.mkdir(exist_ok=True); report={'dataset':'UCI Student Performance, Mathematics','records':len(df),'features':list(X.columns),'target':'G3 bands: low <10, pass 10-13, high >13','excluded':['G1','G2'],'split':'stratified 80/20, random_state=42','cross_validation':'5-fold stratified on train partition','results':{}}
    best=None; best_score=-1
    for name,model in models.items():
        pipe=Pipeline([('preprocessor',prep),('model',model)])
        cv=cross_val_score(pipe,Xtr,ytr,cv=StratifiedKFold(5,shuffle=True,random_state=42),scoring='f1_macro')
        pipe.fit(Xtr,ytr); pred=pipe.predict(Xte); pr,re,f1,_=precision_recall_fscore_support(yte,pred,average='macro',zero_division=0)
        perm=permutation_importance(pipe,Xte,yte,n_repeats=10,random_state=42,scoring='f1_macro')
        report['results'][name]={'accuracy':accuracy_score(yte,pred),'precision_macro':pr,'recall_macro':re,'f1_macro':f1,'cv_f1_macro_mean':cv.mean(),'cv_f1_macro_std':cv.std(),'confusion_matrix':confusion_matrix(yte,pred,labels=['low','pass','high']).tolist(),'classification_report':classification_report(yte,pred,zero_division=0),'permutation_importance':dict(sorted(zip(X.columns,perm.importances_mean.tolist()),key=lambda x:-x[1]))}
        if name!='majority_baseline' and f1>best_score: best,best_score=pipe,f1
    joblib.dump(best,OUT/'grade_band_pipeline.joblib'); (OUT/'MODEL_REPORT_RESULTS.md').write_text('# Generated ML experiment results\n\n```json\n'+json.dumps(report,indent=2)+'\n```\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
if __name__=='__main__': main()
