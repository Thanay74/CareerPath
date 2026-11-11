"""Held-out and cross-validation metrics for a candidate career model."""
import numpy as np
from sklearn.metrics import accuracy_score,precision_recall_fscore_support,confusion_matrix,classification_report
from sklearn.model_selection import cross_validate
from sklearn.pipeline import Pipeline

def evaluate_cross_validation(pipeline, X_train, y_train, cv):
    """Return training-partition CV metrics without accessing a holdout set."""
    scores=cross_validate(pipeline,X_train,y_train,cv=cv,scoring={'accuracy':'accuracy','precision_macro':'precision_macro','recall_macro':'recall_macro','f1_macro':'f1_macro'},n_jobs=1,return_train_score=False)
    return {k.removeprefix('test_'):{'mean':float(np.mean(v)),'std':float(np.std(v,ddof=1))} for k,v in scores.items() if k.startswith('test_')}

def evaluate_holdout(pipeline, X_train, y_train, X_test, y_test, class_names):
    """Fit the selected pipeline on training data and evaluate the holdout once."""
    pipeline.fit(X_train,y_train); predicted=pipeline.predict(X_test)
    precision,recall,f1,_=precision_recall_fscore_support(y_test,predicted,average='macro',zero_division=0)
    details={'accuracy':float(accuracy_score(y_test,predicted)),'precision_macro':float(precision),'recall_macro':float(recall),'f1_macro':float(f1),'confusion_matrix':confusion_matrix(y_test,predicted,labels=range(len(class_names))).tolist(),'classification_report':classification_report(y_test,predicted,labels=range(len(class_names)),target_names=list(class_names),zero_division=0,output_dict=True)}
    return pipeline,details

def evaluate_candidate(pipeline,X_train,y_train,X_test,y_test,cv,class_names):
    """Compatibility helper for benchmarks that report CV and holdout together."""
    cv_metrics=evaluate_cross_validation(pipeline,X_train,y_train,cv)
    pipeline,holdout_metrics=evaluate_holdout(pipeline,X_train,y_train,X_test,y_test,class_names)
    legacy_cv_metrics={f'test_{key}':value for key,value in cv_metrics.items()}
    return pipeline,{**holdout_metrics,'cv':legacy_cv_metrics}
