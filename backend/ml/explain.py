"""SHAP explanations for broad career-family signals, not compatibility scores."""
import numpy as np
import pandas as pd

from backend.ml.artifact_contract import ModelInferenceError
from backend.ml.feature_engineering import feature_row
from backend.ml.predict import load_active_stage_model


def explain_career_model(profile, family, expected_model_identity=None):
    level=profile.get('education_level','10th')
    try:
        validated=load_active_stage_model(level)
        if expected_model_identity and validated.sha256 != expected_model_identity:
            return {'method':'unavailable','target_family':family,'predicted_family':None,
                'explanation_scope':'model_family','output_space':'unavailable',
                'reason':'model_changed_during_recommendation','contributions':[]}
        artifact=validated.artifact
        classes=list(artifact['label_encoder'].classes_)
        if family not in classes:
            raise ModelInferenceError('class_mismatch')
        class_index=classes.index(family)
        row=feature_row(profile,level)
        X=pd.DataFrame([{key:row.get(key) for key in artifact['features']}]).replace('',None)
        pipe=artifact['pipeline']
        transformed=pipe.named_steps['preprocessor'].transform(X)
        model=pipe.named_steps['model']
        probabilities=np.asarray(model.predict_proba(transformed),dtype=float)
        if (probabilities.shape != (1,len(classes)) or not np.isfinite(probabilities).all()
                or (probabilities < 0).any() or (probabilities > 1).any()
                or not np.isclose(float(probabilities[0].sum()),1.0,rtol=0.0,atol=1e-6)):
            raise ModelInferenceError('probability_values_invalid')
        import shap
        values=shap.TreeExplainer(model).shap_values(transformed)
        if hasattr(values,'values'):
            values=values.values
        if isinstance(values,list):
            if class_index >= len(values):
                raise ModelInferenceError('explanation_alignment_invalid')
            class_values=np.asarray(values[class_index])
            class_values=class_values[0] if class_values.ndim > 1 else class_values
        else:
            array=np.asarray(values)
            if array.ndim == 3:
                if array.shape[0] != 1 or array.shape[2] != len(classes):
                    raise ModelInferenceError('explanation_alignment_invalid')
                class_values=array[0,:,class_index]
            elif array.ndim == 2 and array.shape[0] == 1:
                class_values=array[0]
            else:
                raise ModelInferenceError('explanation_alignment_invalid')
        names=list(pipe.named_steps['preprocessor'].get_feature_names_out())
        if len(class_values) != len(names) or not np.isfinite(class_values).all():
            raise ModelInferenceError('explanation_alignment_invalid')
        # Keep one-hot category identity intact instead of truncating at underscores.
        readable=[name.split('__',1)[-1] for name in names]
        contributions=[{'feature':name,'value':round(float(value),4),
            'direction':'supports' if value>0 else 'reduces'}
            for name,value in zip(readable,class_values)]
        contributions=sorted(contributions,key=lambda item:abs(item['value']),reverse=True)[:6]
        estimator_name=type(model).__name__
        output_space='raw_margin' if estimator_name.startswith('XGB') else 'probability'
        return {'method':'SHAP TreeExplainer','model':artifact.get('selected_model',estimator_name),
            'target_family':family,
            'target_family_probability':round(float(probabilities[0,class_index]),4),
            'predicted_family':classes[int(probabilities[0].argmax())],
            'explanation_scope':'model_family','output_space':output_space,
            'model_identity':validated.sha256,
            'contributions':contributions}
    except ModelInferenceError as exc:
        reason=exc.reason
    except Exception:
        reason='explanation_unavailable'
    return {'method':'unavailable','target_family':family,'predicted_family':None,
        'explanation_scope':'model_family','output_space':'unavailable',
        'reason':reason,'contributions':[]}


def explain(profile,career_id):
    from backend.services.recommendation_engine import recommend
    item=next((x for x in recommend(profile,5) if x['career_id']==career_id),None)
    if item is None: return {'career_id':career_id,'message':'Career is not in the eligible ranked results for this profile.'}
    result={'career_id':career_id,'compatibility_score':item['compatibility_score'],'knowledge_score':item.get('knowledge_score'),'ml_family_probability':item.get('ml_family_probability'),'ml_family_probabilities':item.get('ml_family_probabilities'),'ml_family':item.get('ml_family'),'components':item['components'],'reasons':item['why_matches'],'model_explanation_scope':item.get('model_explanation_scope')}
    if item.get('model_explanations'): result['model_explanations']=item['model_explanations']
    if item.get('ml_family'): result['model_explanation']=explain_career_model(profile,item['ml_family'])
    return result
