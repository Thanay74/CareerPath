"""Transparent profile-to-career compatibility, explanation and skill gaps."""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
KB=ROOT/'data'/'career_knowledge_base.csv'
METADATA=ROOT/'data'/'career_metadata.json'
LEVELS=['10th','12th',"Bachelor's","Master's"]
SUBJECT_SYNONYMS={'psychology':'sociology','html_css':'computer_science'}

def _parse(value):
    return {k:float(v) for k,v in (part.split(':') for part in (value or '').split(';') if ':' in part)}
def _list(value): return [x.strip() for x in (value or '').split(';') if x.strip()]
def _num(x, default=0):
    try: return max(0,min(100,float(x)))
    except (TypeError,ValueError): return default
def careers(include_inactive=False):
    from backend.services.catalog_releases import load_active_catalog
    rows=load_active_catalog(KB,METADATA).rows
    return rows if include_inactive else [row for row in rows if row.get('active',True) is not False]

def _stage_eligible(level, row):
    stage=LEVELS.index(level) if level in LEVELS else 0
    minimum=LEVELS.index(row['minimum_education_level']) if row['minimum_education_level'] in LEVELS else 3
    if stage==3: return minimum>=2
    return stage>=minimum-1


WEIGHTS={
    "academic":.12,"aptitude":.10,"interests":.14,"technical":.14,
    "employability":.08,"education":.08,"stream":.08,"degree":.16,
    "career_preferences":.20,"research_interests":.08,
}
ML_SCORE_WEIGHT=0.10
SUBJECT_GROUPS={
    "computer_science":("computer_science","programming","data_structures","database_management","computer_networks","operating_systems","web_development"),
    "mathematics":("mathematics","calculus","statistics","numerical_reasoning"),
    "physics":("physics","classical_mechanics","electronics","circuit_theory"),
    "chemistry":("chemistry","organic_chemistry","pharmaceutical_chemistry"),
    "biology":("biology","cell_biology","genetics","human_anatomy"),
    "economics":("economics","business_analytics","financial_accounting"),
    "accountancy":("accountancy","financial_accounting","cost_accounting","accounting"),
    "psychology":("psychology","sociology"),
}
DEGREE_ALIASES={
    "bca":("bca","bachelorofcomputerapplications"),
    "bcom":("bcom","bachelorofcommerce"),
    "bba":("bba","bachelorofbusinessadministration"),
    "bsc":("bsc","bachelorofscience"),
    "btechbe":("btech","bacheloroftechnology","be","bachelorofengineering"),
    "bpharm":("bpharm","bachelorofpharmacy"),
    "mca":("mca","masterofcomputerapplications"),
    "mcom":("mcom","masterofcommerce"),
    "mba":("mba","masterofbusinessadministration"),
    "msc":("msc","masterofscience"),
    "mtechme":("mtech","masteroftechnology","me","masterofengineering"),
    "ma":("ma","masterofarts"),
}
def _norm(value): return re.sub(r"[^a-z0-9]","",(value or "").lower())
def _metadata():
    from backend.services.catalog_releases import load_active_catalog
    return load_active_catalog(KB,METADATA).metadata
def _career_meta(row): return {key:row[key] for key in ('family','keywords','active','qualification_notes','sources') if key in row}
def career_family(row):
    return _career_meta(row).get('family','public_social_research')
def _observed(values):
    return {k:_num(v) for k,v in (values or {}).items() if v is not None}
def _subject_score(profile, required):
    subjects=_observed(profile.get('subjects'))
    if not required: return None
    values=[]
    for name in required:
        candidates=SUBJECT_GROUPS.get(name,(name,))
        found=[subjects[k] for k in candidates if k in subjects]
        if found: values.append(sum(found)/len(found))
    return sum(values)/len(values) if values else None
def _requirements_score(actual,requirements):
    actual=_observed(actual)
    evidence=[min(100,actual[key]/max(required,1)*100) for key,required in requirements.items() if key in actual]
    return sum(evidence)/len(evidence) if evidence else None
def _stage_score(level,minimum):
    stage=LEVELS.index(level) if level in LEVELS else 0
    required=LEVELS.index(minimum) if minimum in LEVELS else 3
    return 100 if stage>=required else max(15,75-30*(required-stage-1))
def _degree_score(profile,row):
    degree=(profile.get('degree') or '').strip()
    if not degree: return None
    recommended=[x.strip() for x in (row.get('recommended_degrees') or '').split(';') if x.strip()]
    norm_degree=_norm(degree)
    aliases=next((v for k,v in DEGREE_ALIASES.items() if norm_degree in v or k==norm_degree),(norm_degree,))
    if any(alias and alias in _norm(item) for item in recommended for alias in aliases): return 100
    specialization=(profile.get('specialization') or '').strip().lower()
    metadata=_career_meta(row); career_terms=' '.join([row.get('career_name',''),row.get('description',''),*metadata.get('keywords',[])]).lower()
    if specialization:
        words=[w for w in re.findall(r'[a-z]+',specialization) if len(w)>3 and w not in {'applications','engineering','science','studies'}]
        if words and any(w in career_terms for w in words): return 72
    # A related domain is a viable alternative only when the career metadata supports it.
    degree_domain={'bca':'technology_engineering','mca':'technology_engineering','bcom':'business_finance','mcom':'business_finance','bba':'business_finance','mba':'business_finance','bsc':'health_life_sciences','msc':'health_life_sciences','btechbe':'technology_engineering','mtechme':'technology_engineering','bpharm':'health_life_sciences','ba':'public_social_research','ma':'public_social_research'}
    profile_family=degree_domain.get(norm_degree)
    if profile_family and profile_family==career_family(row): return 48
    return 12

def _preference_score(text,row):
    phrases=[x.strip().lower() for x in re.split(r'[,;\n]+',text or '') if x.strip()]
    if not phrases: return None
    meta=_career_meta(row)
    haystack=' '.join([row.get('career_name',''),row.get('description',''),row.get('recommended_degrees',''),*meta.get('keywords',[])]).lower()
    tokens=set(re.findall(r'[a-z0-9]+',haystack))
    synonym={'developer':'development','dev':'developer','software':'programming','programmer':'programming','finance':'financial','marketing':'advertising','ai':'artificial intelligence'}
    scores=[]
    for phrase in phrases:
        if phrase in haystack: scores.append(100); continue
        words=[w for w in re.findall(r'[a-z0-9]+',phrase) if w not in {'career','job','a','an','the','of','in','and'}]
        if not words: continue
        matched=sum(1 for w in words if w in tokens or synonym.get(w,'') in tokens)
        scores.append(100*matched/len(words))
    return sum(scores)/len(scores) if scores else 0

def _profile_score(p,row):
    meta=_career_meta(row)
    academic=_subject_score(p,_list(row.get('required_subjects')))
    if academic is not None and p.get('academic_performance') is not None:
        performance=_num(p['academic_performance'])*(10 if p.get('academic_scale')=='cgpa10' else 1)
        academic=.8*academic+.2*performance
    aptitude=_requirements_score(p.get('aptitude'),_parse(row.get('aptitude_requirements')))
    interests=_requirements_score(p.get('interests'),_parse(row.get('interest_requirements')))
    technical=_requirements_score(p.get('technical'),_parse(row.get('technical_skills')))
    employability=_requirements_score(p.get('employability'),_parse(row.get('employability_skills')))
    level=p.get('education_level','10th'); education=_stage_score(level,row.get('minimum_education_level',"Master's"))
    streams=_list(row.get('suitable_streams')); student_stream=p.get('stream','')
    stream_aliases={'Science PCB':'Science','Science PCM':'Science','Vocational/Diploma':'Diploma/Vocational','Business':'Commerce','Computing':'Science','Engineering':'Science','Pharmacy':'Science','Other':''}
    student_stream=stream_aliases.get(student_stream,student_stream)
    stream=60 if not student_stream else (100 if student_stream in streams else 20)
    degree=_degree_score(p,row)
    preference=_preference_score(p.get('career_preferences',''),row)
    research=_preference_score(p.get('research_interests',''),row)
    parts={'academic':academic,'aptitude':aptitude,'interests':interests,'technical':technical,'employability':employability,'education':education,'stream':stream,'degree':degree,'career_preferences':preference,'research_interests':research}
    applicable={name:(value,WEIGHTS[name]) for name,value in parts.items() if value is not None and not (name=='stream' and not p.get('stream'))}
    total_weight=sum(weight for _,weight in applicable.values())
    score=sum(value*weight for value,weight in applicable.values())/total_weight if total_weight else 0
    return round(max(0,min(100,score)),1),{k:(round(v,1) if v is not None else None) for k,v in parts.items()}

def skill_gap_analysis(p,row):
    actual={**(p.get('technical',{}) or {}),**(p.get('employability',{}) or {})}
    req={**_parse(row['technical_skills']),**_parse(row['employability_skills'])}
    if not req:
        return {'status':'insufficient_requirements','message':'No skill requirements are defined for this pathway, so gaps cannot be assessed.','gaps':[]}
    available={key:value for key,value in _observed(actual).items() if key in req}
    if not available:
        return {'status':'insufficient_data','message':'No relevant skill proficiency ratings are available. Missing ratings are unknown, not zero.','gaps':[]}
    gaps=[]
    for skill,required in req.items():
        if skill not in available: continue
        current=available[skill]; gap=max(0,round(required-current))
        if gap:
            severity='High' if gap>=30 else 'Moderate' if gap>=15 else 'Low'
            gaps.append({'skill':skill.replace('_',' ').title(),'current':round(current),'required':round(required),'gap':gap,'severity':severity,'missing':skill not in actual})
    gaps=sorted(gaps,key=lambda x:(-x['gap'],x['skill']))
    if gaps:
        return {'status':'some_gaps_identified','message':'Gaps are calculated only for assessed skills with a defined pathway requirement.','gaps':gaps}
    return {'status':'no_gaps_identified','message':'No gaps were identified for the assessed skills with defined requirements. Other skills may remain unassessed.','gaps':[]}

def skill_gaps(p,row):
    return skill_gap_analysis(p,row)['gaps']

def _actions(skill,severity):
    s=skill.lower()
    known={'python':['Learn Python fundamentals and data types','Practice Python functions, collections and debugging','Build and document a Python portfolio project'],'sql':['Learn SQL SELECT, filtering, JOIN and GROUP BY','Practice SQL query challenges','Build a small relational database project'],'programming':['Learn core programming constructs','Practice algorithms and debugging','Build and document a small application'],'machine learning':['Review statistics and supervised learning','Train and evaluate a small model','Document a reproducible end-to-end project'],'communication':['Practice structured writing and active listening','Present a short topic weekly','Ask for feedback and revise'],'research methods':['Learn study design and source evaluation','Practice collecting and analyzing evidence','Write a concise research brief'],'ui ux':['Study accessibility and user research basics','Create wireframes and test with users','Build a case study documenting design decisions']}
    return known.get(s,[f'Learn {skill} fundamentals with a structured course or guided resource',f'Practice {skill} through weekly exercises',f'Complete a small project demonstrating {skill}'])

def recommend(profile,top_n=5):
    from backend.services.catalog_releases import catalog_read_context
    with catalog_read_context(KB,METADATA):
        return _recommend_with_catalog(profile,top_n)

def _recommend_with_catalog(profile,top_n=5):
    level=profile.get('education_level','10th')
    from backend.ml.predict import predict_career_families
    family_probs=predict_career_families(profile)
    if level=='10th':
        from backend.services.school_pathways import PATHWAY_RULES, evaluate_pathway, summarize_pathways
        from backend.services.school_roadmap import build_pathway_roadmap
        from backend.ml.explain import explain_career_model
        results=[]
        for name,rule in PATHWAY_RULES.items():
            evaluation=evaluate_pathway(profile,name,family_probs)
            model_explanations=[
                explain_career_model(profile,family)
                for family in rule['families']
            ]
            evidence=[*evaluation['why_matches']]
            if evaluation['ml_score'] is not None:
                evidence.append(f"Grouped experimental ML family signal: {evaluation['ml_score']:.1f}/100 (10% of the score; synthetic labels).")
            results.append({
                'career_id':'PATH-'+str(len(results)+1),
                'career_name':name+' stream/pathway',
                'pathway_name':name,
                'description':rule['description'],
                'compatibility_score':evaluation['combined_score'],
                'combined_score':evaluation['combined_score'],
                'ranking_score':evaluation['combined_score'],
                'knowledge_score':evaluation['knowledge_score'],
                'ml_score':evaluation['ml_score'],
                'ml_family_probability':evaluation['ml_score'],
                'ml_used_in_ranking':evaluation['knowledge_score'] is not None and evaluation['ml_score'] is not None,
                'ranking_method':'hybrid_90_10_experimental_model' if evaluation['combined_score'] is not None else 'insufficient_assessment_evidence',
                'ml_family_probabilities':family_probs,
                'model_explanations':model_explanations,
                'model_explanation_scope':'Each explanation describes its named model-family signal only; it does not explain pathway compatibility or guarantee fit.',
                'why_matches':evidence,
                'factors_to_consider':evaluation['factors_to_consider'],
                'components':evaluation['components'],
                'evidence_count':evaluation['evidence_count'],
                'evidence_domains':evaluation['evidence_domains'],
                'score_label':'Exploratory compatibility estimate — not a probability of success or admission',
                'required_skills':{},
                'required_subjects':list(rule['subjects']),
                'skill_gaps':evaluation['skill_gaps'],
                'skill_gap_status':evaluation['skill_gap_status'],
                'skill_gap_message':evaluation['skill_gap_message'],
                'available_requirements':evaluation['available_requirements'],
                'improvement_suggestions':evaluation['improvement_suggestions'],
                'education_path':name+' or an equivalent subject/program option offered locally',
                'qualification_status':'Confirm board, school, and local program eligibility',
                'additional_qualifications':'Subject combinations, admission requirements, and program recognition vary. Confirm current details with the relevant school or recognized institution; this suggestion does not guarantee admission.',
                'minimum_education_level':'10th',
                'suitable_streams':[name],
                'rules_version':evaluation['rules_version'],
                'roadmap':build_pathway_roadmap(name,{**profile,'skill_gap_status':evaluation['skill_gap_status'],'skill_gap_message':evaluation['skill_gap_message']}),
            })
        # Class 10 comparison must include every configured pathway even when a
        # caller requests a smaller top_n; the UI needs the same complete order
        # for leading option, alternatives, and its expandable comparison.
        return summarize_pathways(results)
    catalog_rows=careers()
    metadata={row['career_id']:_career_meta(row) for row in catalog_rows}
    ranked=[]; explanation_cache={}
    for c in catalog_rows:
        score,parts=_profile_score(profile,c)
        eligible=_stage_eligible(level,c)
        if not eligible: continue
        family=career_family(c); meta=metadata.get(c['career_id'],{})
        ml_probability=round(family_probs.get(family,0)*100,1)
        combined=round((1-ML_SCORE_WEIGHT)*score+ML_SCORE_WEIGHT*ml_probability,1)
        direct_degree=parts.get('degree')==100
        stage_met=parts.get('education',0)>=100
        if direct_degree and stage_met: qualification_status='Direct education match'
        elif level in LEVELS and LEVELS.index(level)<LEVELS.index(c['minimum_education_level']): qualification_status='Further education required'
        elif parts.get('degree') is not None and parts.get('degree')>=45: qualification_status='Related pathway; verify qualifications'
        else: qualification_status='Additional qualification required'
        extra=meta.get('qualification_notes') or ('See the listed recommended qualification pathway and confirm admission or professional requirements with the relevant institution.' if qualification_status!='Direct education match' else '')
        evidence=[(name,value) for name,value in parts.items() if value is not None and name not in ('education','stream')]
        why=[f'{name.replace("_"," ").title()} fit ({value:.0f}/100) based on assessed profile data' for name,value in sorted(evidence,key=lambda x:x[1],reverse=True)[:3] if value>=55]
        if direct_degree: why.insert(0,f'{profile.get("degree")} matches the career knowledge base pathway')
        if profile.get('stream') and profile['stream'] in _list(c.get('suitable_streams')): why.append(f'{profile["stream"]} is an aligned study stream')
        if qualification_status!='Direct education match': why.append(qualification_status+'. '+extra)
        if not evidence: why.append('No relevant subject, aptitude or skill ratings have been provided yet; this is preliminary pathway guidance.')
        gap_analysis=skill_gap_analysis(profile,c); gaps=gap_analysis['gaps']
        if family not in explanation_cache:
            from backend.ml.explain import explain_career_model
            explanation_cache[family]=explain_career_model(profile,family)
        why.append(f'Experimental synthetic-data ML family likelihood: {ml_probability:.1f}% (10% of combined score; interpret cautiously)')
        actions=[{'skill':g['skill'],'severity':g['severity'],'actions':_actions(g['skill'],g['severity'])} for g in gaps[:4]]
        if not actions and gap_analysis['status']=='insufficient_data': actions=[{'skill':'Assessment','severity':'Informational','actions':['Rate relevant current skills or complete the related assessment before interpreting this gap analysis.','Ask a teacher, counselor, or mentor which practice activities fit your current level.']}]
        ranked.append({'career_id':c['career_id'],'career_name':c['career_name'],'description':c['description'],'compatibility_score':combined,'combined_score':combined,'ranking_score':combined,'knowledge_score':score,'ml_score':ml_probability,'ml_family_probability':ml_probability,'ml_used_in_ranking':True,'ranking_method':'hybrid_90_10_experimental_model','ml_family':family,'ml_family_probabilities':family_probs,'model_explanation':explanation_cache[family],'model_explanation_scope':f'This explanation describes the {family} model-family signal only; it does not independently explain {c["career_name"]} compatibility.','why_matches':why,'required_skills':{**_parse(c['technical_skills']),**_parse(c['employability_skills'])},'required_subjects':_list(c['required_subjects']),'optional_certifications':c['optional_certifications'],'skill_gaps':gaps,'skill_gap_status':gap_analysis['status'],'skill_gap_message':gap_analysis['message'],'improvement_suggestions':actions,'education_path':c['recommended_degrees'],'qualification_status':qualification_status,'additional_qualifications':extra,'qualification_sources':meta.get('sources',[]),'minimum_education_level':c['minimum_education_level'],'suitable_streams':_list(c['suitable_streams']),'components':parts})
    return sorted(ranked,key=lambda x:(-x['ranking_score'],x['career_name']))[:max(1,min(5,int(top_n)))]

def career_detail(cid): return next((c for c in careers() if c['career_id']==cid),None)
