"""SHAP explanations for the selected tree model plus truthful score rationale."""
from pathlib import Path
import joblib, pandas as pd
from backend.ml.data_loader import ROOT
from backend.ml.feature_engineering import feature_row
from backend.ml.predict import CAREER_MODEL_DIR

def explain_career_model(profile, family):
    level=profile.get('education_level','10th'); path=CAREER_MODEL_DIR/f'{level.lower().replace(" ","_").replace(chr(39),"")}_career_model.joblib'
    if not path.exists(): return {'method':'unavailable','target_family':family,'predicted_family':None,'explanation_scope':'model_family','contributions':[],'reason':'No trained stage model is available.'}
    try:
        import shap
        artifact=joblib.load(path); pipe=artifact['pipeline']; row=feature_row(profile,level)
        X=pd.DataFrame([{k:row.get(k) for k in artifact['features']}]).replace('',None)
        transformed=pipe.named_steps['preprocessor'].transform(X)
        model=pipe.named_steps['model']; probabilities=model.predict_proba(transformed)[0]
        predicted_family=artifact['label_encoder'].inverse_transform([int(probabilities.argmax())])[0]
        explainer=shap.TreeExplainer(model); values=explainer.shap_values(transformed)
        class_index=list(artifact['label_encoder'].classes_).index(family)
        if isinstance(values,list): vals=values[class_index][0]
        else:
            import numpy as np
            arr=np.asarray(values)
            vals=arr[0,:,class_index] if arr.ndim==3 else arr[0]
        names=pipe.named_steps['preprocessor'].get_feature_names_out()
        merged={}
        for name,value in zip(names,vals):
            base=name.split('__',1)[-1].split('_',1)[0] if name.startswith('cat__') else name.split('__',1)[-1]
            merged[base]=merged.get(base,0.0)+float(value)
        top=sorted(merged.items(),key=lambda x:abs(x[1]),reverse=True)[:6]
        return {'method':'SHAP TreeExplainer','model':artifact['selected_model'],'target_family':family,'target_family_probability':round(float(probabilities[class_index]),4),'predicted_family':predicted_family,'explanation_scope':'model_family','contributions':[{'feature':k,'value':round(v,4),'direction':'supports' if v>0 else 'reduces'} for k,v in top]}
    except Exception as exc:
        return {'method':'unavailable','target_family':family,'predicted_family':None,'explanation_scope':'model_family','reason':f'SHAP computation failed: {type(exc).__name__}','contributions':[]}

def explain(profile,career_id):
    from backend.services.recommendation_engine import recommend
    item=next((x for x in recommend(profile,5) if x['career_id']==career_id),None)
    if item is None: return {'career_id':career_id,'message':'Career is not in the eligible ranked results for this profile.'}
    result={'career_id':career_id,'compatibility_score':item['compatibility_score'],'knowledge_score':item.get('knowledge_score'),'ml_family_probability':item.get('ml_family_probability'),'ml_family_probabilities':item.get('ml_family_probabilities'),'ml_family':item.get('ml_family'),'components':item['components'],'reasons':item['why_matches'],'model_explanation_scope':item.get('model_explanation_scope')}
    if item.get('model_explanations'): result['model_explanations']=item['model_explanations']
    if item.get('ml_family'): result['model_explanation']=explain_career_model(profile,item['ml_family'])
    return result
