import os, tempfile, unittest, shutil, json, threading
from pathlib import Path
from unittest.mock import patch
from backend import app as application

class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); application.DB_PATH=Path(self.tmp.name)/'test.sqlite3'
        from backend.services import recommendation_engine
        self.original_kb=recommendation_engine.KB; self.original_metadata=recommendation_engine.METADATA
        recommendation_engine.KB=Path(self.tmp.name)/'careers.csv'; shutil.copyfile(self.original_kb,recommendation_engine.KB)
        recommendation_engine.METADATA=Path(self.tmp.name)/'career_metadata.json'; shutil.copyfile(self.original_metadata,recommendation_engine.METADATA)
        from backend.services import catalog_releases
        self.release_config=(catalog_releases.RELEASES_DIR,catalog_releases.ACTIVE_MANIFEST,catalog_releases.MANAGED_MARKER,catalog_releases.ACTIVATION_LOCK)
        catalog_releases.RELEASES_DIR=Path(self.tmp.name)/'releases'; catalog_releases.ACTIVE_MANIFEST=Path(self.tmp.name)/'active.json'; catalog_releases.MANAGED_MARKER=Path(self.tmp.name)/'managed.json'; catalog_releases.ACTIVATION_LOCK=Path(self.tmp.name)/'activation.lock'
        application.init_db()
        conn=application.connect_db()
        application.seed_education_catalog(conn); application.seed_aptitude_questions(conn); conn.commit(); conn.close()
        self.original_drafts=application.CAREER_DRAFT_DIR; application.CAREER_DRAFT_DIR=Path(self.tmp.name)/'drafts'
        self.client=application.app.test_client()
    def tearDown(self):
        from backend.services import recommendation_engine
        from backend.services import catalog_releases
        recommendation_engine.KB=self.original_kb; recommendation_engine.METADATA=self.original_metadata
        catalog_releases.RELEASES_DIR,catalog_releases.ACTIVE_MANIFEST,catalog_releases.MANAGED_MARKER,catalog_releases.ACTIVATION_LOCK=self.release_config
        application.CAREER_DRAFT_DIR=self.original_drafts
        self.tmp.cleanup()
    def test_registration_login_and_invalid_input(self):
        r=self.client.post('/api/register',json={'email':'student@example.com','password':'password123'}); self.assertEqual(r.status_code,201); data=r.get_json()
        login=self.client.post('/api/login',json={'email':'student@example.com','password':'password123'}); self.assertEqual(login.status_code,200)
        normalized_login=self.client.post('/api/login',json={'email':'  STUDENT@example.com  ','password':'password123'}); self.assertEqual(normalized_login.status_code,200)
        self.assertEqual(self.client.post('/api/login',json={'email':'student@example.com','password':'wrong'}).status_code,401)
        self.assertEqual(self.client.post('/api/register',json={'email':'bad','password':'x'}).status_code,400)
        self.assertEqual(self.client.post('/api/student/profile',json={'student_id':data['student_id'],'education_level':'Doctorate'}).status_code,400)
        self.assertEqual(self.client.post('/api/recommend',json={'profile':{'education_level':'10th','subjects':{'biology':None}},'top_n':0}).status_code,401)
        self.assertEqual(self.client.post('/api/recommend',json={'profile':{'education_level':'10th','subjects':{'biology':None}}}).get_json(),{'error':'A valid student bearer token and student_id are required'})
        self.assertEqual(self.client.post('/api/recommend',json={'student_id':data['student_id'],'top_n':0},headers={'Authorization':'Bearer '+data['token']}).status_code,400)
    def test_authenticated_identity_logout_and_relogin(self):
        reg=self.client.post('/api/register',json={'email':'identity@example.com','password':'password123'}).get_json()
        headers={'Authorization':'Bearer '+reg['token']}
        identity=self.client.get('/api/auth/me',headers=headers)
        self.assertEqual(identity.status_code,200)
        self.assertEqual(identity.get_json(),{'email':'identity@example.com','role':'student','student_id':reg['student_id']})
        self.assertEqual(self.client.post('/api/auth/logout',headers=headers).status_code,200)
        self.assertEqual(self.client.get('/api/auth/me',headers=headers).status_code,401)
        relogin=self.client.post('/api/login',json={'email':'identity@example.com','password':'password123'}).get_json()
        self.assertTrue(relogin['token'])
        self.assertEqual(self.client.get('/api/auth/me',headers={'Authorization':'Bearer '+relogin['token']}).status_code,200)
        self.assertEqual(self.client.get('/api/admin/dashboard',headers={'Authorization':'Bearer '+relogin['token']}).status_code,403)
    def test_profile_assess_recommend_and_gap_flow(self):
        reg=self.client.post('/api/register',json={'email':'flow@example.com','password':'password123'}).get_json(); sid=reg['student_id']
        headers={'Authorization':'Bearer '+reg['token']}
        profile={'student_id':sid,'education_level':'Bachelor\'s','stream':'Science','subjects':{'mathematics':90,'computer_science':95}}
        self.assertEqual(self.client.post('/api/student/profile',json=profile,headers=headers).status_code,200)
        self.assertEqual(self.client.post('/api/assessment/aptitude',json={'student_id':sid,'scores':{'logical_reasoning':90}},headers=headers).status_code,400)
        self.assertEqual(self.client.post('/api/assessment/interests',json={'student_id':sid,'scores':{'technology':90}},headers=headers).status_code,200)
        self.assertEqual(self.client.post('/api/assessment/skills',json={'student_id':sid,'technical':{'python':65},'employability':{'teamwork':70}},headers=headers).status_code,200)
        saved=self.client.get('/api/student/profile?student_id='+sid,headers=headers)
        self.assertEqual(saved.status_code,200); self.assertEqual(saved.get_json()['profile']['technical']['python'],65)
        self.assertEqual(self.client.get('/api/student/profile?student_id='+sid).status_code,401)
        rec=self.client.post('/api/recommend',json={'student_id':sid},headers=headers).get_json()['recommendations']; self.assertTrue(rec); self.assertIn('compatibility_score',rec[0])
        self.assertEqual(self.client.get('/api/recommendations?student_id='+sid,headers=headers).status_code,200)
        self.assertEqual(self.client.get('/api/skill-gap?student_id='+sid,headers=headers).status_code,200)
        self.assertEqual(self.client.get('/api/improvement-plan?student_id='+sid,headers=headers).status_code,200)
        self.assertEqual(self.client.get('/api/career/C01').status_code,200)
    def test_recommend_rejects_missing_invalid_expired_and_other_student_tokens(self):
        first=self.client.post('/api/register',json={'email':'recommend-owner@example.com','password':'password123'}).get_json()
        second=self.client.post('/api/register',json={'email':'recommend-other@example.com','password':'password123'}).get_json()
        payload={'student_id':first['student_id'],'profile':{'education_level':'Master\'s','subjects':{'biology':100}}}
        denied=[
            self.client.post('/api/recommend',json=payload),
            self.client.post('/api/recommend',json=payload,headers={'Authorization':'Bearer invalid-token'}),
        ]
        with self.client.application.app_context():
            application.db().execute('UPDATE users SET token=NULL WHERE user_id=(SELECT user_id FROM students WHERE student_id=?)',(first['student_id'],)); application.db().commit()
        denied.append(self.client.post('/api/recommend',json=payload,headers={'Authorization':'Bearer '+first['token']}))
        for response in denied:
            self.assertEqual(response.status_code,401)
            self.assertEqual(set(response.get_json()),{'error'})
        other_owner=self.client.post('/api/recommend',json=payload,headers={'Authorization':'Bearer '+second['token']})
        self.assertEqual(other_owner.status_code,403)
        self.assertEqual(set(other_owner.get_json()),{'error'})
        with self.client.application.app_context():
            self.assertEqual(application.db().execute('SELECT COUNT(*) AS n FROM recommendation_events').fetchone()['n'],0)
    def test_authenticated_recommendation_needs_no_aptitude_and_saved_results_are_owner_only(self):
        owner=self.client.post('/api/register',json={'email':'recommend-no-aptitude@example.com','password':'password123'}).get_json()
        other=self.client.post('/api/register',json={'email':'recommend-reader@example.com','password':'password123'}).get_json()
        headers={'Authorization':'Bearer '+owner['token']}
        response=self.client.post('/api/recommend',json={'student_id':owner['student_id'],'top_n':3},headers=headers)
        self.assertEqual(response.status_code,200,response.get_json())
        self.assertTrue(response.get_json()['recommendations'])
        owned=self.client.get('/api/recommendations?student_id='+owner['student_id'],headers=headers)
        self.assertEqual(owned.status_code,200)
        self.assertEqual(owned.get_json()['recommendations'],response.get_json()['recommendations'])
        denied=self.client.get('/api/recommendations?student_id='+owner['student_id'],headers={'Authorization':'Bearer '+other['token']})
        self.assertEqual(denied.status_code,403)
        missing_token=self.client.get('/api/recommendations?student_id='+owner['student_id'])
        self.assertEqual(missing_token.status_code,401)
        with self.client.application.app_context():
            self.assertEqual(application.db().execute('SELECT COUNT(*) AS n FROM aptitude_attempts WHERE student_id=?',(owner['student_id'],)).fetchone()['n'],0)
    def test_profile_and_aptitude_history_are_scoped_to_authenticated_student(self):
        first=self.client.post('/api/register',json={'email':'profile-scope-a@example.com','password':'password123'}).get_json()
        second=self.client.post('/api/register',json={'email':'profile-scope-b@example.com','password':'password123'}).get_json()
        first_headers={'Authorization':'Bearer '+first['token']}
        second_headers={'Authorization':'Bearer '+second['token']}
        saved=self.client.post('/api/student/profile',json={'student_id':first['student_id'],'education_level':"Bachelor's",'stream':'Science','degree':'BCA','specialization':'Computer Applications','subjects':{'programming':87}},headers=first_headers)
        self.assertEqual(saved.status_code,200)
        self.assertEqual(self.client.get('/api/student/profile?student_id='+first['student_id'],headers=first_headers).get_json()['profile']['subjects']['programming'],87)
        self.assertEqual(self.client.get('/api/student/profile?student_id='+first['student_id'],headers=second_headers).status_code,401)
        self.assertEqual(self.client.get('/api/aptitude/history?student_id='+first['student_id'],headers=second_headers).status_code,401)
        second_profile=self.client.get('/api/student/profile?student_id='+second['student_id'],headers=second_headers).get_json()['profile']
        self.assertEqual(second_profile['subjects'],{})
        self.assertEqual(second_profile['interests'],{})
        self.assertEqual(second_profile['technical'],{})
        self.assertEqual(second_profile['employability'],{})
        self.assertEqual(second_profile['aptitude'],{})
    def test_dynamic_education_catalog_and_profile_details_persist(self):
        catalog=self.client.get('/api/education/catalog').get_json()['levels']
        self.assertIn('BCA',catalog["Bachelor's"]['degrees'])
        self.assertIn('programming',catalog["Bachelor's"]['subjects']['BCA'])
        self.assertIn('financial_accounting',catalog["Bachelor's"]['subjects']['B.Com'])
        self.assertIn('MCA',catalog["Master's"]['degrees'])
        self.assertIn('mathematics',catalog['10th']['subjects']['default'])
        self.assertIn('biology',catalog['12th']['subjects']['Science PCB'])
        self.assertNotIn('biology',catalog["Bachelor's"]['subjects']['B.Com'])
        reg=self.client.post('/api/register',json={'email':'degree@example.com','password':'password123'}).get_json(); headers={'Authorization':'Bearer '+reg['token']}
        saved=self.client.post('/api/student/profile',json={'student_id':reg['student_id'],'education_level':"Bachelor's",'stream':'Science','degree':'BCA','specialization':'Data Analytics','study_period':'Year 2','academic_performance':8.25,'academic_scale':'cgpa10','career_preferences':'software, data science','subjects':{'programming':88,'custom_lab':73}},headers=headers)
        self.assertEqual(saved.status_code,200)
        profile=self.client.get('/api/student/profile?student_id='+reg['student_id'],headers=headers).get_json()['profile']
        self.assertEqual(profile['degree'],'BCA'); self.assertEqual(profile['specialization'],'Data Analytics'); self.assertEqual(profile['academic_scale'],'cgpa10'); self.assertEqual(profile['academic_performance'],8.25); self.assertEqual(profile['career_preferences'],'software, data science'); self.assertEqual(profile['subjects']['programming'],88); self.assertEqual(profile['subjects']['custom_lab'],73)
        recommendations=self.client.post('/api/recommend',json={'student_id':reg['student_id'],'top_n':3},headers=headers)
        self.assertEqual(recommendations.status_code,200); self.assertTrue(recommendations.get_json()['recommendations'])
    def test_profile_rejects_cross_level_and_cross_degree_catalog_values(self):
        reg=self.client.post('/api/register',json={'email':'catalog-validation@example.com','password':'password123'}).get_json()
        headers={'Authorization':'Bearer '+reg['token']}; sid=reg['student_id']
        valid={'student_id':sid,'education_level':"Bachelor's",'stream':'Science','degree':'BCA','specialization':'Computer Applications'}
        self.assertEqual(self.client.post('/api/student/profile',json=valid,headers=headers).status_code,200)
        invalid_profiles=[
            {'education_level':'10th','stream':'Science PCB'},
            {'education_level':"Bachelor's",'stream':'Science','degree':'Imaginary Degree'},
            {'education_level':"Bachelor's",'stream':'Science','degree':'BCA','specialization':'Finance'},
            {'education_level':"Master's",'stream':'Computing','degree':'BCA'},
            {'education_level':'12th','stream':'Commerce','degree':'B.Com'},
        ]
        for invalid in invalid_profiles:
            with self.subTest(profile=invalid):
                response=self.client.post('/api/student/profile',json={'student_id':sid,**invalid},headers=headers)
                self.assertEqual(response.status_code,400)
        custom={'student_id':sid,'education_level':"Bachelor's",'stream':'Other','degree':'Custom Applied Course','specialization':'Custom Focus'}
        self.assertEqual(self.client.post('/api/student/profile',json=custom,headers=headers).status_code,200)
    def test_requested_education_scenarios_return_calculated_recommendations(self):
        cases=[
            {'education_level':'10th','stream':'Science','subjects':{'mathematics':80,'science':75}},
            {'education_level':'12th','stream':'Science PCB','subjects':{'biology':90,'chemistry':80,'physics':70}},
            {'education_level':'12th','stream':'Science PCM','subjects':{'mathematics':90,'physics':80,'chemistry':75}},
            {'education_level':"Bachelor's",'stream':'Science','degree':'BCA','specialization':'Software Development','subjects':{'programming':90,'data_structures':80}},
            {'education_level':"Bachelor's",'stream':'Commerce','degree':'B.Com','specialization':'Finance','subjects':{'financial_accounting':90,'economics':80}},
            {'education_level':"Bachelor's",'stream':'Business','degree':'BBA','specialization':'Marketing','subjects':{'marketing':90,'principles_of_management':80}},
            {'education_level':"Bachelor's",'stream':'Science','degree':'B.Sc','specialization':'Computer Science','subjects':{'programming':90,'algorithms':80}},
            {'education_level':"Bachelor's",'stream':'Engineering','degree':'B.Tech/BE','specialization':'Computer Science','subjects':{'programming':90,'software_engineering':80}},
            {'education_level':"Master's",'stream':'Computing','degree':'MCA','specialization':'Data Science','subjects':{'machine_learning':85,'advanced_programming':90}},
            {'education_level':"Master's",'stream':'Business','degree':'MBA','specialization':'Finance','subjects':{'corporate_finance':90,'strategic_management':80}},
        ]
        for index,profile in enumerate(cases):
            with self.subTest(profile=profile):
                account=self.client.post('/api/register',json={'email':f'scenario{index}@example.com','password':'password123'}).get_json(); sid=account['student_id']; headers={'Authorization':'Bearer '+account['token']}
                saved=self.client.post('/api/student/profile',json={'student_id':sid,**profile},headers=headers)
                self.assertEqual(saved.status_code,200)
                started=self.client.post('/api/aptitude/attempts',json={'student_id':sid,'education_level':profile['education_level']},headers=headers)
                self.assertEqual(started.status_code,201); attempt=started.get_json()
                self.assertTrue(all('correct_option' not in q and 'explanation' not in q for q in attempt['questions']))
                answers={q['question_id']:'A' for q in attempt['questions']}
                submitted=self.client.post(f"/api/aptitude/attempts/{attempt['attempt_id']}/submit",json={'student_id':sid,'answers':answers},headers=headers)
                self.assertEqual(submitted.status_code,200)
                response=self.client.post('/api/recommend',json={'student_id':sid,'top_n':3},headers=headers)
                self.assertEqual(response.status_code,200)
                results=response.get_json()['recommendations']; self.assertTrue(results)
                self.assertTrue(all('combined_score' in result and 'skill_gaps' in result and 'improvement_suggestions' in result for result in results))
        for level in ('10th','12th',"Bachelor's","Master's"):
            self.assertEqual(self.client.get('/api/aptitude/questions?education_level='+level).get_json()['question_count'],25)
    def test_aptitude_answers_are_private_scored_and_persisted(self):
        reg=self.client.post('/api/register',json={'email':'aptitude@example.com','password':'password123'}).get_json(); sid=reg['student_id']; headers={'Authorization':'Bearer '+reg['token']}
        self.assertEqual(self.client.get('/api/aptitude/questions?education_level=10th').status_code,200)
        public=self.client.get('/api/aptitude/questions?education_level=10th').get_json()
        self.assertEqual(public['question_count'],25); self.assertNotIn('correct_option',public['questions'][0]); self.assertNotIn('explanation',public['questions'][0])
        attempt_response=self.client.post('/api/aptitude/attempts',json={'student_id':sid,'education_level':'10th'},headers=headers)
        self.assertEqual(attempt_response.status_code,201); attempt=attempt_response.get_json(); self.assertEqual(len(attempt['questions']),25)
        self.assertEqual(self.client.get('/api/aptitude/attempts/%s?student_id=%s'%(attempt['attempt_id'],sid),headers=headers).status_code,200)
        from backend.aptitude_bank import QUESTIONS
        answers={q['question_id']:q['correct_option'] for q in QUESTIONS}
        submitted=self.client.post('/api/aptitude/attempts/%s/submit'%attempt['attempt_id'],json={'student_id':sid,'answers':answers},headers=headers)
        self.assertEqual(submitted.status_code,200); result=submitted.get_json()['attempt']; self.assertEqual(result['overall_score'],100)
        self.assertEqual(len(result['responses']),25); self.assertEqual(len(result['domains']),7)
        loaded=self.client.get('/api/student/profile?student_id='+sid,headers=headers).get_json()['profile']
        self.assertEqual(loaded['aptitude']['logical_reasoning'],100)
        self.assertEqual(self.client.post('/api/assessment/aptitude',json={'student_id':sid,'scores':loaded['aptitude']},headers=headers).status_code,200)
        self.assertEqual(self.client.get('/api/aptitude/history?student_id='+sid,headers=headers).get_json()['attempts'][0]['status'],'completed')
        relogin=self.client.post('/api/login',json={'email':'aptitude@example.com','password':'password123'}).get_json()
        relogin_headers={'Authorization':'Bearer '+relogin['token']}
        after_login=self.client.get('/api/aptitude/attempts/%s?student_id=%s'%(attempt['attempt_id'],sid),headers=relogin_headers)
        self.assertEqual(after_login.status_code,200); self.assertEqual(after_login.get_json()['attempt']['overall_score'],100)
        self.assertEqual(self.client.post('/api/aptitude/attempts/%s/submit'%attempt['attempt_id'],json={'student_id':sid,'answers':answers},headers=headers).status_code,409)
    def test_mysql_adapter_uses_named_rows_and_mysql_placeholders(self):
        class Cursor:
            rowcount=1; lastrowid=7
            def execute(self,sql,params): self.sql=sql; self.params=params
            def fetchone(self): return {'student_id':'STU000007'}
        class Raw:
            def cursor(self): self.cur=Cursor(); return self.cur
        raw=Raw(); result=application.MySQLConnection(raw).execute('SELECT student_id FROM students WHERE user_id=?',(7,))
        self.assertEqual(raw.cur.sql,'SELECT student_id FROM students WHERE user_id=%s')
        self.assertEqual(raw.cur.params,(7,)); self.assertEqual(result.fetchone()['student_id'],'STU000007')
    def test_admin_endpoints_require_admin_role_and_return_model_stats(self):
        reg=self.client.post('/api/register',json={'email':'admin-test@example.com','password':'password123'}).get_json()
        headers={'Authorization':'Bearer '+reg['token']}
        self.assertEqual(self.client.get('/api/admin/dashboard',headers=headers).status_code,403)
        with self.client.application.app_context():
            application.db().execute("UPDATE users SET role='admin' WHERE email=?",('admin-test@example.com',)); application.db().commit()
        data=self.client.get('/api/admin/dashboard',headers=headers)
        self.assertEqual(data.status_code,200); self.assertIn('model_performance',data.get_json())
        self.assertEqual(self.client.get('/api/admin/users',headers=headers).status_code,200)
        skills=self.client.get('/api/admin/skills',headers=headers)
        self.assertEqual(skills.status_code,200); self.assertTrue(skills.get_json()['skills'])
        self.assertIn('required_level',skills.get_json()['skills'][0])
        model_data=self.client.get('/api/admin/models',headers=headers)
        self.assertEqual(model_data.status_code,200); self.assertFalse(model_data.get_json()['empirically_validated'])
        self.assertTrue(model_data.get_json()['baseline'])
        registry=self.client.get('/api/admin/datasets',headers=headers)
        self.assertEqual(registry.status_code,200); self.assertFalse(registry.get_json()['user_collected_survey_data_available'])
        self.assertTrue(registry.get_json()['datasets'])
        user_id=self.client.get('/api/admin/users',headers=headers).get_json()['users'][0]['user_id']
        self.assertEqual(self.client.patch(f'/api/admin/users/{user_id}/role',json={'role':'student'},headers=headers).status_code,409)
        self.assertEqual(self.client.patch(f'/api/admin/users/{user_id}/status',json={'is_active':False},headers=headers).status_code,409)
        question={'question_id':'QTEST01','domain':'logical_reasoning','difficulty':'Foundational','question_text':'Which item completes the pattern?','options':[{'id':'A','text':'Option A'},{'id':'B','text':'Option B'}],'correct_option':'A','explanation':'This is a test item.','education_levels':['10th']}
        created=self.client.post('/api/admin/aptitude-questions',json=question,headers=headers)
        self.assertEqual(created.status_code,201)
        self.assertEqual(self.client.get('/api/aptitude/questions?education_level=10th').get_json()['question_count'],26)
        self.assertEqual(self.client.delete('/api/admin/aptitude-questions/QTEST01',headers=headers).status_code,200)
        self.assertEqual(self.client.get('/api/aptitude/questions?education_level=10th').get_json()['question_count'],25)
        self.assertTrue(self.client.get('/api/admin/audit',headers=headers).get_json()['events'])
    def test_admin_can_edit_career_and_skill_criteria_in_knowledge_base(self):
        from backend.services.recommendation_engine import career_detail
        reg=self.client.post('/api/register',json={'email':'career-admin@example.com','password':'password123'}).get_json(); headers={'Authorization':'Bearer '+reg['token']}
        with self.client.application.app_context(): application.db().execute("UPDATE users SET role='admin' WHERE email=?",('career-admin@example.com',)); application.db().commit()
        original=career_detail('C01')
        r=self.client.patch('/api/admin/careers/C01',json={'description':'Updated from admin panel','technical_skills':{'python':81}},headers=headers)
        self.assertEqual(r.status_code,200); self.assertTrue(r.get_json()['staged']); self.assertEqual(r.get_json()['career']['description'],'Updated from admin panel')
        self.assertEqual(career_detail('C01')['description'],original['description'])
        draft=r.get_json()['draft']
        self.assertEqual(self.client.get('/api/admin/career-drafts',headers=headers).get_json()['drafts'][0]['draft_id'],draft['draft_id'])
        published=self.client.post(f"/api/admin/career-drafts/{draft['draft_id']}/publish",headers=headers)
        self.assertEqual(published.status_code,200,published.get_json())
        self.assertTrue(published.get_json()['release_id'])
        self.assertEqual(career_detail('C01')['technical_skills'],'python:81')
        self.assertEqual(self.client.get('/api/admin/career-drafts',headers=headers).get_json()['drafts'],[])
        release_list=self.client.get('/api/admin/career-releases',headers=headers)
        self.assertEqual(release_list.status_code,200)
        release_rows=release_list.get_json()['releases']
        active=next(item for item in release_rows if item['active'])
        baseline=next(item for item in release_rows if not item['active'])
        restored=self.client.post(f"/api/admin/career-releases/{baseline['release_id']}/restore",json={'expected_fingerprint':active['fingerprint']},headers=headers)
        self.assertEqual(restored.status_code,200,restored.get_json())
        self.assertEqual(career_detail('C01')['technical_skills'],original['technical_skills'])

    def test_invalid_staged_catalog_cannot_be_published(self):
        from backend.services.recommendation_engine import career_detail
        reg=self.client.post('/api/register',json={'email':'draft-admin@example.com','password':'password123'}).get_json(); headers={'Authorization':'Bearer '+reg['token']}
        with self.client.application.app_context(): application.db().execute("UPDATE users SET role='admin' WHERE email=?",('draft-admin@example.com',)); application.db().commit()
        original=career_detail('C01')
        staged=self.client.patch('/api/admin/careers/C01',json={'description':'Draft change'},headers=headers).get_json()['draft']
        path=application.CAREER_DRAFT_DIR/(staged['draft_id']+'.json')
        draft=json.loads(path.read_text(encoding='utf-8')); draft['rows'][0]['technical_skills']='python:101'; path.write_text(json.dumps(draft),encoding='utf-8')
        response=self.client.post(f"/api/admin/career-drafts/{staged['draft_id']}/publish",headers=headers)
        self.assertEqual(response.status_code,400); self.assertEqual(career_detail('C01')['description'],original['description'])

    def test_stale_catalog_snapshot_is_rejected_without_draft(self):
        rows,fingerprint,error=application._career_catalog_snapshot()
        self.assertIsNone(error)
        from backend.services import recommendation_engine
        catalog_path=recommendation_engine.KB
        original=catalog_path.read_bytes()
        try:
            catalog_path.write_bytes(original+b'\n')
            draft,message=application._stage_career_catalog('update','C01',rows,'Computer Programmer',fingerprint)
            self.assertIsNone(draft)
            self.assertIn('catalog changed',message)
            self.assertEqual(list(application.CAREER_DRAFT_DIR.glob('*.json')),[])
        finally:
            catalog_path.write_bytes(original)

    def test_concurrent_stage_requests_create_only_one_draft(self):
        rows,fingerprint,error=application._career_catalog_snapshot()
        self.assertIsNone(error)
        barrier=threading.Barrier(2); results=[]
        def stage():
            barrier.wait()
            results.append(application._stage_career_catalog('update','C01',rows,'Computer Programmer',fingerprint))
        workers=[threading.Thread(target=stage) for _ in range(2)]
        for worker in workers: worker.start()
        for worker in workers: worker.join(5)
        self.assertTrue(all(not worker.is_alive() for worker in workers))
        self.assertEqual(sum(draft is not None for draft,message in results),1)
        self.assertEqual(len(list(application.CAREER_DRAFT_DIR.glob('*.json'))),1)

    def test_duplicate_publish_requests_activate_once(self):
        from backend.services.recommendation_engine import career_detail
        reg=self.client.post('/api/register',json={'email':'publish-race@example.com','password':'password123'}).get_json()
        headers={'Authorization':'Bearer '+reg['token']}
        with self.client.application.app_context():
            application.db().execute("UPDATE users SET role='admin' WHERE email=?",('publish-race@example.com',)); application.db().commit()
        staged=self.client.patch('/api/admin/careers/C01',json={'description':'Safe pending edit'},headers=headers).get_json()['draft']
        baseline=career_detail('C01'); statuses=[]
        def publish():
            with application.app.test_client() as client:
                statuses.append(client.post(f"/api/admin/career-drafts/{staged['draft_id']}/publish",headers=headers).status_code)
        workers=[threading.Thread(target=publish) for _ in range(2)]
        for worker in workers: worker.start()
        for worker in workers: worker.join(5)
        self.assertTrue(all(not worker.is_alive() for worker in workers))
        self.assertEqual(sorted(statuses),[200,404])
        self.assertEqual(career_detail('C01')['description'],'Safe pending edit')
        self.assertFalse((application.CAREER_DRAFT_DIR/(staged['draft_id']+'.json')).exists())

    def test_stale_admin_draft_cannot_replace_a_newer_active_release(self):
        from backend.services.recommendation_engine import career_detail
        reg=self.client.post('/api/register',json={'email':'stale-publish@example.com','password':'password123'}).get_json()
        headers={'Authorization':'Bearer '+reg['token']}
        with self.client.application.app_context():
            application.db().execute("UPDATE users SET role='admin' WHERE email=?",('stale-publish@example.com',)); application.db().commit()
        staged_response=self.client.patch('/api/admin/careers/C01',json={'description':'Stale proposed description'},headers=headers)
        self.assertEqual(staged_response.status_code,200)
        staged=staged_response.get_json()['draft']
        from backend.services import recommendation_engine,catalog_releases
        current=catalog_releases.load_active_catalog(recommendation_engine.KB,recommendation_engine.METADATA)
        newer=[dict(row) for row in current.rows]; newer[0]['description']='Newer active description'
        new_release=catalog_releases.publish_catalog(newer,current.fingerprint,recommendation_engine.KB,recommendation_engine.METADATA)
        response=self.client.post(f"/api/admin/career-drafts/{staged['draft_id']}/publish",headers=headers)
        self.assertEqual(response.status_code,409)
        self.assertEqual(career_detail('C01')['description'],'Newer active description')
        self.assertTrue((application.CAREER_DRAFT_DIR/(staged['draft_id']+'.json')).exists())

    def _admin_headers_for_test(self,email):
        registered=self.client.post('/api/register',json={'email':email,'password':'password123'}).get_json()
        with self.client.application.app_context():
            application.db().execute("UPDATE users SET role='admin' WHERE email=?",(email,)); application.db().commit()
        return {'Authorization':'Bearer '+registered['token']}

    def _career_admin_state(self):
        from backend.services import catalog_releases, recommendation_engine
        def tree(path):
            path=Path(path)
            return {str(item.relative_to(path)):item.read_bytes() for item in path.rglob('*') if item.is_file()} if path.exists() else {}
        with self.client.application.app_context():
            audit_count=application.db().execute('SELECT COUNT(*) AS n FROM admin_audit_logs').fetchone()['n']
        pointer=catalog_releases.ACTIVE_MANIFEST
        return {
            'career_csv':recommendation_engine.KB.read_bytes(),
            'career_metadata':recommendation_engine.METADATA.read_bytes(),
            'pointer':Path(pointer).read_bytes() if Path(pointer).exists() else None,
            'releases':tree(catalog_releases.RELEASES_DIR),
            'drafts':tree(application.CAREER_DRAFT_DIR),
            'admin_audit_count':audit_count,
        }

    def test_all_career_admin_routes_deny_non_admins_without_catalog_mutation(self):
        student=self.client.post('/api/register',json={'email':'career-route-student@example.com','password':'password123'}).get_json()
        inactive=self.client.post('/api/register',json={'email':'career-route-inactive@example.com','password':'password123'}).get_json()
        with self.client.application.app_context():
            application.db().execute("UPDATE users SET role='admin',is_active=0 WHERE email=?",('career-route-inactive@example.com',)); application.db().commit()
        student_headers={'Authorization':'Bearer '+student['token']}
        inactive_headers={'Authorization':'Bearer '+inactive['token']}
        create_payload={'career_name':'Denied career','description':'Denied','minimum_education_level':'10th','suitable_streams':'Science','required_subjects':'','aptitude_requirements':'','technical_skills':'','employability_skills':'','interest_requirements':'','recommended_degrees':'','optional_certifications':'','family':'technology_engineering'}
        routes=[
            ('GET','/api/admin/careers',None),
            ('PATCH','/api/admin/careers/C01',{'description':'denied edit'}),
            ('POST','/api/admin/careers',create_payload),
            ('DELETE','/api/admin/careers/C01',None),
            ('GET','/api/admin/career-drafts',None),
            ('POST','/api/admin/career-drafts/'+'a'*24+'/publish',None),
            ('GET','/api/admin/career-releases',None),
            ('POST','/api/admin/career-releases/'+'a'*64+'/restore',{'expected_fingerprint':'0'*64}),
            ('DELETE','/api/admin/career-drafts/'+'a'*24,None),
        ]
        for method,path,payload in routes:
            for role,headers in [('anonymous',{}),('student',student_headers),('inactive admin',inactive_headers)]:
                with self.subTest(method=method,path=path,role=role):
                    before=self._career_admin_state()
                    response=self.client.open(path,method=method,json=payload,headers=headers)
                    self.assertEqual(response.status_code,403,response.get_json())
                    self.assertEqual(self._career_admin_state(),before)

    def test_active_admin_can_use_each_career_draft_and_release_route(self):
        headers=self._admin_headers_for_test('career-route-admin@example.com')
        self.assertEqual(self.client.get('/api/admin/careers',headers=headers).status_code,200)

        edited=self.client.patch('/api/admin/careers/C01',json={'description':'Staged authorized edit'},headers=headers)
        self.assertEqual(edited.status_code,200)
        draft_id=edited.get_json()['draft']['draft_id']
        self.assertEqual(self.client.get('/api/admin/career-drafts',headers=headers).status_code,200)
        discarded=self.client.delete(f'/api/admin/career-drafts/{draft_id}',headers=headers)
        self.assertEqual(discarded.status_code,200)

        created=self.client.post('/api/admin/careers',json={'career_name':'Authorized Test Career','description':'Temporary isolated test record','minimum_education_level':'10th','suitable_streams':'Science','required_subjects':'','aptitude_requirements':'','technical_skills':'','employability_skills':'','interest_requirements':'','recommended_degrees':'','optional_certifications':'','family':'technology_engineering'},headers=headers)
        self.assertEqual(created.status_code,201,created.get_json())
        self.assertEqual(self.client.delete(f"/api/admin/career-drafts/{created.get_json()['draft']['draft_id']}",headers=headers).status_code,200)

        deactivated=self.client.delete('/api/admin/careers/C01',headers=headers)
        self.assertEqual(deactivated.status_code,200)
        publish_id=deactivated.get_json()['draft']['draft_id']
        published=self.client.post(f'/api/admin/career-drafts/{publish_id}/publish',headers=headers)
        self.assertEqual(published.status_code,200,published.get_json())
        releases=self.client.get('/api/admin/career-releases',headers=headers)
        self.assertEqual(releases.status_code,200)
        active=next(row for row in releases.get_json()['releases'] if row['active'])
        rollback=next(row for row in releases.get_json()['releases'] if not row['active'])
        restored=self.client.post(f"/api/admin/career-releases/{rollback['release_id']}/restore",json={'expected_fingerprint':active['fingerprint']},headers=headers)
        self.assertEqual(restored.status_code,200,restored.get_json())

    def test_publish_reports_committed_when_pointer_directory_fsync_fails(self):
        from backend.services import catalog_releases
        from backend.services.recommendation_engine import KB,METADATA
        headers=self._admin_headers_for_test('post-switch-publish@example.com')
        initial=catalog_releases.load_active_catalog(KB,METADATA)
        catalog_releases.publish_catalog(initial.rows,initial.fingerprint,KB,METADATA)
        staged=self.client.patch('/api/admin/careers/C01',json={'description':'Committed despite fsync warning'},headers=headers).get_json()['draft']
        real_fsync_directory=catalog_releases._fsync_directory
        def fail_pointer_directory(path):
            if Path(path)==catalog_releases.ACTIVE_MANIFEST.parent:
                raise OSError('injected directory fsync failure')
            return real_fsync_directory(path)
        with patch.object(catalog_releases,'_fsync_directory',side_effect=fail_pointer_directory):
            response=self.client.post(f"/api/admin/career-drafts/{staged['draft_id']}/publish",headers=headers)
        self.assertEqual(response.status_code,200,response.get_json())
        body=response.get_json()
        self.assertTrue(body['published']); self.assertEqual(body['activation_status'],'committed')
        self.assertIn('durability is uncertain',body['activation_warning'])
        self.assertFalse((application.CAREER_DRAFT_DIR/(staged['draft_id']+'.json')).exists())
        from backend.services.recommendation_engine import career_detail
        self.assertEqual(career_detail('C01')['description'],'Committed despite fsync warning')

    def test_restore_audit_failure_reports_committed_active_release(self):
        from backend.services import catalog_releases
        headers=self._admin_headers_for_test('restore-audit-failure@example.com')
        first=self.client.patch('/api/admin/careers/C01',json={'description':'First isolated release'},headers=headers).get_json()['draft']
        self.assertEqual(self.client.post(f"/api/admin/career-drafts/{first['draft_id']}/publish",headers=headers).status_code,200)
        first_releases=self.client.get('/api/admin/career-releases',headers=headers).get_json()['releases']
        first_release=next(row for row in first_releases if row['active'])
        second=self.client.patch('/api/admin/careers/C01',json={'description':'Second isolated release'},headers=headers).get_json()['draft']
        self.assertEqual(self.client.post(f"/api/admin/career-drafts/{second['draft_id']}/publish",headers=headers).status_code,200)
        active=self.client.get('/api/admin/career-releases',headers=headers).get_json()['releases']
        current=next(row for row in active if row['active'])
        with patch.object(application,'record_admin_action',side_effect=RuntimeError('injected audit failure')):
            response=self.client.post(f"/api/admin/career-releases/{first_release['release_id']}/restore",json={'expected_fingerprint':current['fingerprint']},headers=headers)
        self.assertEqual(response.status_code,200,response.get_json())
        body=response.get_json()
        self.assertTrue(body['restored']); self.assertEqual(body['activation_status'],'committed')
        self.assertEqual(body['release_id'],first_release['release_id'])
        self.assertIn('audit event could not be recorded',body['audit_warning'])
        pointer=json.loads(Path(catalog_releases.ACTIVE_MANIFEST).read_text(encoding='utf-8'))
        self.assertEqual(pointer['release_id'],first_release['release_id'])
        from backend.services.recommendation_engine import career_detail
        self.assertEqual(career_detail('C01')['description'],'First isolated release')

if __name__=='__main__': unittest.main()
