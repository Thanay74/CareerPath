import unittest
from backend.ml.data_loader import load_data,features_target
from backend.ml.predict import predict_grade_band
from backend.services.recommendation_engine import recommend
class MLPipelineTests(unittest.TestCase):
    def test_uci_preprocessing_has_no_target_leakage(self):
        df=load_data(); X,y=features_target(df)
        self.assertEqual(len(df),395); self.assertEqual(len(X),len(y))
        self.assertFalse({'G1','G2','G3'} & set(X.columns))
        self.assertEqual(set(y.unique()),{'low','pass','high'})
    def test_trained_pipeline_predicts_one_grade_band(self):
        df=load_data(); X,_=features_target(df)
        value=predict_grade_band(X.iloc[0].to_dict())
        self.assertIn(value,{'low','pass','high'})
    def test_recommender_uses_aptitude_not_requirement_as_student_input(self):
        p={'education_level':"Bachelor's",'stream':'Science','career_preferences':'software developer','aptitude':{'logical_reasoning':40},'subjects':{'mathematics':70,'computer_science':70},'interests':{},'technical':{},'employability':{}}
        result=next(x for x in recommend(p,5) if x['career_id']=='C01')
        self.assertLess(result['components']['aptitude'],65)
if __name__=='__main__': unittest.main()
