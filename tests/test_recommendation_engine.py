import json, unittest
from pathlib import Path
from backend.services.recommendation_engine import recommend,skill_gaps,career_detail
ROOT=Path(__file__).parent
PROFILES=json.loads((ROOT/'sample_profiles.json').read_text(encoding='utf-8'))
class RecommendationTests(unittest.TestCase):
    def test_broad_model_family_does_not_create_an_unrelated_degree_route(self):
        from backend.services.recommendation_engine import _degree_score
        from backend.services.recommendation_engine import career_detail

        profile={
            'education_level':"Master's",'stream':'Computing','degree':'MCA',
            'specialization':'Cybersecurity','subjects':{},'aptitude':{},
            'interests':{'cybersecurity':90},'technical':{'cybersecurity':80},
            'employability':{},'career_preferences':'cybersecurity',
        }
        civil=career_detail('C09')
        cybersecurity=career_detail('C04')
        self.assertEqual(_degree_score(profile,civil),12)
        self.assertEqual(_degree_score(profile,cybersecurity),72)

        results=recommend(profile,5)
        self.assertNotIn('C09',{item['career_id'] for item in results})
        cyber_result=next(item for item in results if item['career_id']=='C04')
        self.assertEqual(cyber_result['qualification_status'],'Related direction; eligibility not verified')
        self.assertIn('not an institution-specific eligibility decision',cyber_result['additional_qualifications'])

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
        self.assertEqual(science['stages'][2]['program_options'], [])
        self.assertIn('do not connect individual undergraduate courses to Class 12 subject prerequisites',science['stages'][2]['summary'])
        self.assertTrue(science['stages'][3]['career_directions'])
        self.assertTrue(all(x['verify_locally'] for x in science['stages'][3]['career_directions']))
        self.assertIn('maintained career',science['source_note'])
        self.assertFalse(any('career_directions' in stage for stage in commerce['stages'] if stage['id']=='after_12'))
        stage_four_ids=[x['career_name'] for x in commerce['stages'][3]['career_directions']]
        self.assertEqual(len(stage_four_ids),len(set(stage_four_ids)))
        tech=next(x for x in commerce['stages'][3]['career_directions'] if x['career_id']=='C01')
        self.assertIn('longer-term',tech['route_rationale'])
        self.assertIn('Commerce',tech['route_rationale'])

    def test_class10_stage_three_never_lists_unverified_degrees_as_pathway_eligible(self):
        from backend.services.school_roadmap import build_pathway_roadmap
        for pathway in ('Science','Commerce','Arts/Humanities','Diploma/Vocational'):
            with self.subTest(pathway=pathway):
                stage=build_pathway_roadmap(pathway)['stages'][2]
                self.assertEqual(stage['program_options'], [])
                self.assertIn('do not connect individual undergraduate courses',stage['summary'])

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

    def test_degree_route_is_context_not_personalized_compatibility_evidence(self):
        from backend.services.recommendation_engine import _profile_score, career_detail
        career=career_detail('C01')
        base={'education_level':"Bachelor's",'stream':'Science','subjects':{'mathematics':75,'computer_science':75},'aptitude':{},'interests':{},'technical':{},'employability':{}}
        bca={**base,'degree':'BCA','specialization':'Software Development'}
        commerce={**base,'degree':'B.Com','specialization':'Finance'}
        self.assertEqual(_profile_score(bca,career)[0],_profile_score(commerce,career)[0])
        self.assertNotEqual(_profile_score(bca,career)[1]['degree'],_profile_score(commerce,career)[1]['degree'])
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
    def test_skill_applicability_custom_matching_and_duplicate_evidence(self):
        from backend.services.recommendation_engine import _profile_score
        from backend.skill_catalog import career_skill_guidance
        developer=career_detail('C01'); ca=career_detail('C14')
        base={'education_level':"Bachelor's",'stream':'Commerce','subjects':{},'aptitude':{},'interests':{},'technical':{},'employability':{}}
        unassessed=_profile_score(base,developer)[0]
        not_applicable={**base,'technical':{'python':0},'skill_assessments':[{'display_name':'Python','category':'technical','applicability':'not_applicable'}]}
        self.assertEqual(_profile_score(not_applicable,developer)[0],unassessed)
        explicit_zero_score,explicit_zero_parts=_profile_score({**base,'technical':{'python':0}},developer)
        self.assertEqual(explicit_zero_parts['technical'],0)
        self.assertIsNone(_profile_score(base,developer)[1]['technical'])
        self.assertEqual(explicit_zero_score,unassessed)  # published result stays provisional until the evidence threshold is met
        custom={**base,'skill_assessments':[{'display_name':'Python programming','category':'technical','applicability':'assessed','proficiency':80,'is_custom':True}]}
        custom_score,custom_parts=_profile_score(custom,developer)
        self.assertIsNone(_profile_score(base,developer)[1]['technical'])
        self.assertEqual(custom_parts['technical'],100)
        duplicate={**custom,'technical':{'python':50}}
        single={**base,'technical':{'python':50}}
        self.assertEqual(_profile_score(duplicate,developer)[0],_profile_score(single,developer)[0])
        self.assertEqual(_profile_score(custom,ca)[0],_profile_score(base,ca)[0])
        unmatched={**base,'skill_assessments':[{'display_name':'TallyPrime','category':'technical','applicability':'assessed','proficiency':100,'is_custom':True}]}
        self.assertEqual(_profile_score(unmatched,developer)[0],unassessed)
        from backend.services.eligibility import assess_eligibility
        self.assertEqual(assess_eligibility(custom,developer),assess_eligibility(base,developer))
        guidance=career_skill_guidance('C01',{'python':55,'sql':45},{})
        self.assertEqual(guidance['python']['classification'],'core')
        self.assertEqual(guidance['sql']['classification'],'optional')
        self.assertTrue(all(item['trainable'] for item in guidance.values()))

    def test_technical_skills_do_not_enter_stage_wide_ml_signal(self):
        from unittest.mock import patch
        from backend.services.recommendation_engine import recommend
        captured={}
        def predict(profile):
            captured.update(profile)
            from backend.ml.artifact_contract import ModelInferenceError
            raise ModelInferenceError('test signal unavailable')
        with patch('backend.ml.predict.predict_career_families',side_effect=predict):
            recommend({'education_level':"Bachelor's",'stream':'Commerce','subjects':{},'aptitude':{},'interests':{},'technical':{'python':100},'employability':{'communication':100}},1)
        self.assertEqual(captured['technical'],{})
        self.assertEqual(captured['employability'],{})
    def test_missing_stream_is_neutral_and_not_claimed_as_a_match(self):
        result=recommend({'education_level':"Bachelor's",'subjects':{},'aptitude':{},'interests':{},'technical':{},'employability':{}})[0]
        self.assertEqual(result['components']['stream'],60)
        self.assertEqual(result['recommendation_type'],'provisional')
        self.assertIsNone(result['combined_score'])
        self.assertFalse(any('aligned study stream' in reason for reason in result['why_matches']))

    def test_sparse_profile_is_provisional_and_stage_stream_or_degree_do_not_raise_score(self):
        from backend.services.recommendation_engine import recommend
        sparse=recommend({'education_level':"Bachelor's",'stream':'Science','degree':'BCA',
            'subjects':{},'aptitude':{},'interests':{},'technical':{},'employability':{}},5)
        self.assertTrue(sparse)
        self.assertTrue(all(item['recommendation_type']=='provisional' for item in sparse))
        self.assertTrue(all(item['combined_score'] is None and item['knowledge_score'] is None for item in sparse))
        self.assertTrue(all(item['ml_family_probability'] is None and item['ml_family_probabilities'] is None for item in sparse))
        self.assertTrue(all(item['evidence_coverage']['status']=='insufficient' for item in sparse))
        self.assertTrue(all(item['context']['education_stage']['student_stage']=="Bachelor's" for item in sparse))

    def test_two_assessed_dimensions_allow_personalized_score_across_education_stages(self):
        for key,profile in PROFILES.items():
            with self.subTest(profile=key):
                result=recommend(profile,1)[0]
                self.assertEqual(result['recommendation_type'],'personalized')
                self.assertGreaterEqual(result['evidence_coverage']['assessed_dimensions'],2)
                self.assertGreaterEqual(result['evidence_coverage']['input_count'],2)
                self.assertIsNotNone(result['combined_score'])

    def test_selected_class10_pathway_alone_is_context_not_a_personal_match(self):
        from backend.services.school_pathways import evaluate_pathway
        from backend.services.school_pathways import summarize_pathways, PATHWAY_RULES
        results=[]
        for pathway in PATHWAY_RULES:
            result=evaluate_pathway({'education_level':'10th','stream':pathway,'subjects':{},'aptitude':{},'interests':{}},pathway)
            results.append({**result,'career_id':pathway,'career_name':pathway+' stream/pathway','pathway_name':pathway})
        compared=summarize_pathways(results)
        self.assertTrue(all(item['combined_score'] is None for item in compared))
        self.assertTrue(all(item['recommendation_type']=='provisional' for item in compared))
        self.assertTrue(all(item['context']['stream_is_scoring_evidence'] is False for item in compared))

    def test_missing_and_not_applicable_skill_evidence_are_distinct(self):
        from backend.services.recommendation_engine import _evidence_coverage, _parse, _profile_score, career_detail
        career=career_detail('C01')
        required=_parse(career['technical_skills'])
        missing={'education_level':"Bachelor's",'subjects':{},'aptitude':{},'interests':{},'technical':{},'employability':{}}
        _,parts=_profile_score(missing,career)
        missing_coverage=_evidence_coverage(missing,career,parts)
        self.assertEqual(next(d for d in missing_coverage['dimensions'] if d['key']=='technical')['status'],'missing')
        na={**missing,'skill_assessments':[{'canonical_skill':key,'display_name':key,'applicability':'not_applicable'} for key in required]}
        _,na_parts=_profile_score(na,career)
        na_coverage=_evidence_coverage(na,career,na_parts)
        self.assertEqual(next(d for d in na_coverage['dimensions'] if d['key']=='technical')['status'],'not_applicable')
if __name__=='__main__': unittest.main()
