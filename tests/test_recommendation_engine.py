import json, unittest
from pathlib import Path
from backend.services.recommendation_engine import recommend,skill_gaps,career_detail
ROOT=Path(__file__).parent
PROFILES=json.loads((ROOT/'sample_profiles.json').read_text(encoding='utf-8'))
class RecommendationTests(unittest.TestCase):
    def test_school_pathway_guidance_is_evidence_sensitive(self):
        from backend.services.recommendation_engine import recommend
        science = recommend({'education_level':'10th','subjects':{'mathematics':92,'science':94},'interests':{'technology':95,'research':85},'aptitude':{'analytical_reasoning':88},'career_preferences':''},4)
        arts = recommend({'education_level':'10th','subjects':{'english':94,'social_science':91},'interests':{'communication':95,'social_service':88},'aptitude':{'verbal_reasoning':90}},4)
        commerce = recommend({'education_level':'10th','subjects':{'accountancy':92,'business_studies':90,'mathematics':82},'interests':{'business':96,'entrepreneurship':90},'career_preferences':'commerce finance'},4)
        flat = recommend({'education_level':'10th','subjects':{'mathematics':50,'science':50,'english':50,'social_science':50,'accountancy':50,'business_studies':50},'interests':{k:50 for k in ('technology','research','healthcare','innovation','business','entrepreneurship','leadership','creativity','social_service','communication','design')},'aptitude':{}},4)
        self.assertIn('Science',[x['pathway_name'] for x in science[:2]])
        self.assertFalse(science[0]['recommendation_guidance']['is_leader_clear'])
        self.assertEqual(arts[0]['pathway_name'],'Arts/Humanities')
        self.assertEqual(commerce[0]['pathway_name'],'Commerce')
        self.assertFalse(flat[0]['recommendation_guidance']['is_leader_clear'])

    def test_school_gap_status_distinguishes_missing_inputs_and_low_scores(self):
        from backend.services.school_pathways import evaluate_pathway
        empty=evaluate_pathway({'subjects':{},'aptitude':{}},'Science')
        low=evaluate_pathway({'subjects':{'mathematics':35,'science':40},'aptitude':{}},'Science')
        self.assertEqual(empty['skill_gap_status'],'insufficient_data')
        self.assertEqual(empty['skill_gaps'],[])
        self.assertEqual(low['skill_gap_status'],'some_gaps_identified')
        self.assertTrue(all(g['actions'] for g in low['skill_gaps']))

    def test_class10_roadmap_uses_catalog_routes_and_has_progression_stages(self):
        from backend.services.school_roadmap import build_pathway_roadmap
        science=build_pathway_roadmap('Science',{'interests':{'technology':85}})
        commerce=build_pathway_roadmap('Commerce')
        arts=build_pathway_roadmap('Arts/Humanities')
        vocational=build_pathway_roadmap('Diploma/Vocational')
        self.assertEqual([s['id'] for s in science['stages']],['after_10','class_11_12_or_equivalent','after_12','further_study_and_careers'])
        self.assertEqual({r['route'] for r in science['stages'][1]['route_options']},{'Science PCM','Science PCB'})
        self.assertEqual(commerce['stages'][1]['route_options'][0]['route'],'Commerce')
        self.assertEqual(arts['stages'][1]['route_options'][0]['route'],'Arts/Humanities')
        self.assertEqual(vocational['stages'][1]['route_options'][0]['route'],'Vocational/Diploma')
        self.assertTrue(science['stages'][2]['program_options'])
        self.assertTrue(science['stages'][3]['career_directions'])
        self.assertTrue(all(x['verify_locally'] for x in science['stages'][3]['career_directions']))
        self.assertIn('maintained career',science['source_note'])
        self.assertFalse(any('career_directions' in stage for stage in commerce['stages'] if stage['id']=='after_12'))
        stage_three_ids=[(x['program_text_from_career_record'],name) for x in commerce['stages'][2]['program_options'] for name in x['career_directions_in_record']]
        stage_four_ids=[x['career_name'] for x in commerce['stages'][3]['career_directions']]
        self.assertEqual(len(stage_four_ids),len(set(stage_four_ids)))
        self.assertTrue(all(name in stage_four_ids for _,name in stage_three_ids))
        tech=next(x for x in commerce['stages'][3]['career_directions'] if x['career_id']=='C01')
        self.assertIn('longer-term',tech['route_rationale'])
        self.assertIn('Commerce',tech['route_rationale'])
        bca=next(x for x in commerce['stages'][2]['program_options'] if x['program_text_from_career_record']=='BCA')
        self.assertIn('Software Developer',bca['career_directions_in_record'])

    def test_roadmap_reports_missing_class12_catalog_route(self):
        from unittest.mock import patch
        from backend.education_catalog import EDUCATION_CATALOG
        from backend.services.school_roadmap import build_pathway_roadmap
        with patch.dict(EDUCATION_CATALOG,{'12th':{'streams':[],'subjects':{}}}):
            roadmap=build_pathway_roadmap('Commerce')
        self.assertEqual(roadmap['stages'][1]['catalog_status'],'unavailable')
        self.assertEqual(roadmap['stages'][1]['route_options'],[])
        self.assertIn('no Class 11–12 subject route',roadmap['stages'][0]['summary'])

    def test_class10_roadmap_marks_unassessed_gaps_as_unavailable(self):
        from backend.services.school_pathways import evaluate_pathway
        from backend.services.school_roadmap import build_pathway_roadmap
        assessment=evaluate_pathway({'subjects':{},'aptitude':{}},'Science')
        roadmap=build_pathway_roadmap('Science',{'skill_gap_status':assessment['skill_gap_status'],'skill_gap_message':assessment['skill_gap_message']})
        self.assertEqual(assessment['skill_gap_status'],'insufficient_data')
        self.assertIn('No relevant',roadmap['unavailable_assessment'])

    def test_class10_evidence_separates_strengths_from_low_scores_and_deduplicates_subjects(self):
        from backend.services.school_pathways import evaluate_pathway
        result=evaluate_pathway({'subjects':{'english':45,'social_science':80},'interests':{'communication':85},'aptitude':{'verbal_reasoning':40}},'Arts/Humanities')
        self.assertTrue(any('social science rated 80' in item for item in result['why_matches']))
        self.assertFalse(any('english' in item and '45' in item for item in result['why_matches']))
        self.assertTrue(any('english' in item and '45' in item for item in result['factors_to_consider']))
        self.assertTrue(any('verbal reasoning' in item and '40' in item for item in result['factors_to_consider']))
        self.assertEqual(sum('english rated' in item for item in result['why_matches']+result['factors_to_consider']),1)

    def test_class10_returns_all_four_pathways_in_score_order_even_for_small_top_n(self):
        results=recommend({'education_level':'10th','subjects':{'mathematics':80,'science':82},'interests':{'technology':75}},1)
        self.assertEqual(len(results),4)
        self.assertEqual({x['pathway_name'] for x in results},{'Science','Commerce','Diploma/Vocational','Arts/Humanities'})
        scored=[x['combined_score'] for x in results if x['combined_score'] is not None]
        self.assertEqual(scored,sorted(scored,reverse=True))
        self.assertTrue(all(x['combined_score'] is None for x in results[len(scored):]))
        for result in results:
            if result['knowledge_score'] is not None and result['ml_score'] is not None:
                self.assertAlmostEqual(result['combined_score'],round(.9*result['knowledge_score']+.1*result['ml_score'],1))

    def test_degree_profile_uses_curated_degree_mapping(self):
        from backend.services.recommendation_engine import _profile_score, career_detail
        career=career_detail('C01')
        base={'education_level':"Bachelor's",'stream':'Science','subjects':{'mathematics':75,'computer_science':75},'aptitude':{},'interests':{},'technical':{},'employability':{}}
        bca={**base,'degree':'BCA','specialization':'Software Development'}
        commerce={**base,'degree':'B.Com','specialization':'Finance'}
        self.assertGreater(_profile_score(bca,career)[0],_profile_score(commerce,career)[0])
    def test_career_preferences_change_knowledge_compatibility(self):
        from backend.services.recommendation_engine import _profile_score
        career=career_detail('C01')
        profile={'education_level':"Bachelor's",'stream':'Science','subjects':{},'aptitude':{},'interests':{},'technical':{},'employability':{}}
        match=_profile_score({**profile,'career_preferences':'software developer'},career)[0]
        mismatch=_profile_score({**profile,'career_preferences':'clinical medicine'},career)[0]
        self.assertGreater(match,mismatch)
    def test_cgpa_and_percentage_use_equivalent_normalized_academic_input(self):
        from backend.services.recommendation_engine import _profile_score
        career=career_detail('C01')
        base={'education_level':"Bachelor's",'stream':'Science','subjects':{'mathematics':80},'aptitude':{},'interests':{},'technical':{},'employability':{}}
        percentage=_profile_score({**base,'academic_performance':85,'academic_scale':'percentage'},career)[0]
        cgpa=_profile_score({**base,'academic_performance':8.5,'academic_scale':'cgpa10'},career)[0]
        self.assertEqual(percentage,cgpa)

    def test_all_four_stage_acceptance_profiles_have_calculated_results(self):
        results={k:recommend(v) for k,v in PROFILES.items()}
        self.assertIn('stream/pathway',results['10th_science'][0]['career_name'])
        self.assertEqual(len(results['10th_science'][0]['roadmap']['stages']),4)
        self.assertTrue(any(('Software Developer' in x['career_name'] or 'Engineer' in x['career_name'] or 'Data' in x['career_name']) for x in results['12th_technology']))
        self.assertTrue(any(x['career_name'] in ('Software Developer','Data Analyst','Data Scientist','AI Engineer') for x in results['bachelors_analytical']))
        self.assertTrue(any(x['career_name'] in ('Research Scientist','Data Scientist','Biotechnologist') for x in results['masters_research']))
        self.assertTrue(all(0<=x['compatibility_score']<=100 for group in results.values() for x in group))
    def test_gap_is_actual_difference_and_actions_follow_skill(self):
        career=career_detail('C01'); p={'technical':{'python':45},'employability':{'problem_solving':78}}
        gaps=skill_gaps(p,career)
        py=next(x for x in gaps if x['skill']=='Python')
        self.assertEqual(py['gap'],10); self.assertEqual(py['current'],45)
        self.assertTrue(any('Python' in a for a in __import__('backend.services.recommendation_engine',fromlist=['_actions'])._actions('Python','Low')))
    def test_missing_career_requirements_are_not_reported_as_zero_gaps(self):
        from backend.services.recommendation_engine import skill_gap_analysis
        result=skill_gap_analysis({'technical':{'python':90}},{'technical_skills':'','employability_skills':''})
        self.assertEqual(result['status'],'insufficient_requirements')
        self.assertEqual(result['gaps'],[])
    def test_missing_stream_is_neutral_and_not_claimed_as_a_match(self):
        result=recommend({'education_level':"Bachelor's",'subjects':{},'aptitude':{},'interests':{},'technical':{},'employability':{}})[0]
        self.assertEqual(result['components']['stream'],60)
        self.assertFalse(any('aligned study stream' in reason for reason in result['why_matches']))
if __name__=='__main__': unittest.main()
