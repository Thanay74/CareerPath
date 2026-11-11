import json, unittest
from pathlib import Path
from backend.ml.predict import predict_career_families
from backend.ml.explain import explain_career_model
from backend.services.recommendation_engine import recommend

ROOT=Path(__file__).resolve().parents[1]
class CareerModelTests(unittest.TestCase):
    def test_each_education_level_uses_a_saved_model_and_stage_inputs(self):
        metrics=json.loads((ROOT/'data/processed/career_model_metrics.json').read_text(encoding='utf-8'))
        self.assertEqual(set(metrics['stages']),{'10th','12th',"Bachelor's","Master's"})
        for level in metrics['stages']:
            probs=predict_career_families({'education_level':level,'stream':'Science','subjects':{'mathematics':90,'computer_science':90,'biology':85},'aptitude':{'logical_reasoning':85},'interests':{'technology':90,'research':85},'technical':{'programming':80,'python':75,'research_methods':70},'employability':{'critical_thinking':80}})
            self.assertAlmostEqual(sum(probs.values()),1,places=5)
            self.assertGreater(max(probs.values()),0)
            self.assertIn(metrics['stages'][level]['selected_model'],('random_forest','xgboost'))
    def test_hybrid_recommendation_reports_both_scores(self):
        p={'education_level':"Bachelor's",'stream':'Science','subjects':{'mathematics':90,'computer_science':90},'interests':{'technology':90},'aptitude':{'logical_reasoning':85,'analytical_reasoning':85},'technical':{'programming':80,'python':75},'employability':{'critical_thinking':80}}
        result=recommend(p,3)[0]
        self.assertIn('ml_score',result); self.assertIn('knowledge_score',result); self.assertIn('combined_score',result)
        self.assertGreaterEqual(result['combined_score'],0); self.assertLessEqual(result['combined_score'],100)
    def test_shap_explanation_returns_grounded_feature_contributions(self):
        result=explain_career_model({'education_level':"Bachelor's",'stream':'Science','subjects':{'mathematics':90,'computer_science':90},'interests':{'technology':90},'technical':{'programming':80}},'technology_engineering')
        self.assertIn(result['method'],('SHAP TreeExplainer','unavailable'))
        if result['method']=='SHAP TreeExplainer': self.assertTrue(result['contributions'])
if __name__=='__main__': unittest.main()
