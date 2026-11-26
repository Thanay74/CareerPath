"""Transparent profile-to-career compatibility, explanation and skill gaps."""
from pathlib import Path
import math
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
    "academic":.12,"academic_performance":.08,"aptitude":.10,"interests":.14,"technical":.14,
    "employability":.08,"career_preferences":.20,"research_interests":.08,
}
PERSONALIZED_DIMENSIONS = {
    "academic": "Self-reported subject-rating fit",
    "academic_performance": "Self-reported academic performance",
    "aptitude": "Aptitude assessment",
    "interests": "Interests",
    "technical": "Technical skills",
    "employability": "Employability skills",
    "preferences": "Career and research preferences",
}
MIN_EVIDENCE_DIMENSIONS = 2
MIN_EVIDENCE_INPUTS = 2
ML_SCORE_WEIGHT=0.10


def _skill_evidence(profile):
    """Return one canonical, applicable proficiency map per skill dimension."""
    from backend.skill_catalog import SKILLS, canonical_skill
    output={'technical':{},'employability':{}}
    for dimension in output:
        for name,value in (profile.get(dimension) or {}).items():
            key=canonical_skill(name)
            if key and SKILLS[key][1]==dimension and value is not None:
                output[dimension].setdefault(key,_num(value))
    blocked=set()
    custom={}
    for item in profile.get('skill_assessments') or []:
        if not isinstance(item,dict): continue
        key=canonical_skill(item.get('display_name')) or canonical_skill(item.get('canonical_skill'))
        if not key: continue
        dimension=SKILLS[key][1]
        if item.get('applicability')=='not_applicable':
            blocked.add((dimension,key))
        elif item.get('is_custom') and item.get('applicability')=='assessed' and item.get('proficiency') is not None:
            custom.setdefault((dimension,key),[]).append(_num(item['proficiency']))
    for dimension,key in blocked:
        output[dimension].pop(key,None)
    for (dimension,key),values in custom.items():
        if (dimension,key) not in blocked and key not in output[dimension] and len(values)==1:
            output[dimension][key]=values[0]
    return output


class RecommendationResults(list):
    """Results plus the model identity used for their ranking, if available."""

    def __init__(self, values=(), *, model_identity=None, model_status='available', model_failure_reason=None, model_validation_status=None, model_missing_metadata=()):
        super().__init__(values)
        self.model_identity=model_identity
        self.model_status=model_status
        self.model_failure_reason=model_failure_reason
        self.model_validation_status=model_validation_status
        self.model_missing_metadata=tuple(model_missing_metadata)
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
    score, _ = _subject_evidence(profile, required)
    return score

def _subject_evidence(profile, required):
    subjects=_observed(profile.get('subjects'))
    if not required: return None, []
    values=[]; used=[]
    for name in required:
        candidates=SUBJECT_GROUPS.get(name,(name,))
        found=[subjects[k] for k in candidates if k in subjects]
        if found:
            values.append(sum(found)/len(found))
            used.extend(k for k in candidates if k in subjects)
    return (sum(values)/len(values) if values else None), list(dict.fromkeys(used))

def _requirements_score(actual,requirements):
    score, _ = _requirements_evidence(actual, requirements)
    return score

def _requirements_evidence(actual,requirements):
    actual=_observed(actual)
    evidence=[min(100,actual[key]/max(required,1)*100) for key,required in requirements.items() if key in actual]
    used=[key for key in requirements if key in actual]
    return (sum(evidence)/len(evidence) if evidence else None), used
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
    # A broad model family (for example, technology_engineering) is not
    # degree-pathway evidence. It includes unrelated roles such as software
    # and civil engineering, so do not award degree compatibility from family
    # membership alone. Keep only catalog-listed degree or specialization
    # evidence above; otherwise this route remains unverified.
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
    skill_evidence=_skill_evidence(p)
    meta=_career_meta(row)
    academic,academic_inputs=_subject_evidence(p,_list(row.get('required_subjects')))
    performance=(min(100,_num(p['academic_performance'])*(10 if p.get('academic_scale')=='cgpa10' else 1))
        if p.get('academic_performance') is not None else None)
    aptitude,aptitude_inputs=_requirements_evidence(p.get('aptitude'),_parse(row.get('aptitude_requirements')))
    interests,interest_inputs=_requirements_evidence(p.get('interests'),_parse(row.get('interest_requirements')))
    technical,technical_inputs=_requirements_evidence(skill_evidence['technical'],_parse(row.get('technical_skills')))
    employability,employability_inputs=_requirements_evidence(skill_evidence['employability'],_parse(row.get('employability_skills')))
    level=p.get('education_level','10th'); education=_stage_score(level,row.get('minimum_education_level',"Master's"))
    streams=_list(row.get('suitable_streams')); student_stream=p.get('stream','')
    stream_aliases={'Science PCB':'Science','Science PCM':'Science','Science PCMB':'Science','Vocational/Diploma':'Diploma/Vocational','Business':'Commerce','Computing':'Science','Engineering':'Science','Pharmacy':'Science','Other':''}
    student_stream=stream_aliases.get(student_stream,student_stream)
    stream=60 if not student_stream else (100 if student_stream in streams else 20)
    degree=_degree_score(p,row)
    preference=_preference_score(p.get('career_preferences',''),row)
    research=_preference_score(p.get('research_interests',''),row)
    parts={'academic':academic,'academic_performance':performance,'aptitude':aptitude,'interests':interests,'technical':technical,'employability':employability,'education':education,'stream':stream,'degree':degree,'career_preferences':preference,'research_interests':research}
    personalized={'academic':academic,'academic_performance':performance,'aptitude':aptitude,'interests':interests,'technical':technical,'employability':employability,'career_preferences':preference,'research_interests':research}
    applicable={name:(value,WEIGHTS[name]) for name,value in personalized.items() if value is not None}
    total_weight=sum(weight for _,weight in applicable.values())
    score=sum(value*weight for value,weight in applicable.values())/total_weight if total_weight else 0
    return round(max(0,min(100,score)),1),{k:(round(v,1) if v is not None else None) for k,v in parts.items()}

def _not_applicable_skill_keys(profile):
    from backend.skill_catalog import canonical_skill, SKILLS
    result={'technical':set(),'employability':set()}
    for item in profile.get('skill_assessments') or []:
        if not isinstance(item,dict) or item.get('applicability')!='not_applicable':
            continue
        key=canonical_skill(item.get('display_name')) or canonical_skill(item.get('canonical_skill'))
        if key and key in SKILLS:
            result[SKILLS[key][1]].add(key)
    return result

def _evidence_coverage(profile,row,parts):
    required_subjects=_list(row.get('required_subjects'))
    _academic_score,academic_inputs=_subject_evidence(profile,required_subjects)
    apt_requirements=_parse(row.get('aptitude_requirements'))
    interest_requirements=_parse(row.get('interest_requirements'))
    skill_evidence=_skill_evidence(profile)
    na_skills=_not_applicable_skill_keys(profile)
    technical_requirements=_parse(row.get('technical_skills'))
    employability_requirements=_parse(row.get('employability_skills'))
    _apt_score,aptitude_inputs=_requirements_evidence(profile.get('aptitude'),apt_requirements)
    _interest_score,interest_inputs=_requirements_evidence(profile.get('interests'),interest_requirements)
    _technical_score,technical_inputs=_requirements_evidence(skill_evidence['technical'],technical_requirements)
    _employability_score,employability_inputs=_requirements_evidence(skill_evidence['employability'],employability_requirements)

    def dimension(key,label,requirements,used,not_applicable=(),no_requirement_reason='No assessment requirement is listed for this career.'):
        requirements=list(requirements)
        used=list(dict.fromkeys(used))
        not_applicable=[name for name in requirements if name in set(not_applicable)]
        missing=[name for name in requirements if name not in used and name not in not_applicable]
        score=parts.get(key)
        if score is not None:
            status='assessed'
        elif not requirements or (requirements and not missing and len(not_applicable)==len(requirements)):
            status='not_applicable'
        else:
            status='missing'
        return {'key':key,'label':label,'status':status,'score':score,
            'inputs_used':used,'missing_inputs':missing,'not_applicable_inputs':not_applicable,
            'reason':no_requirement_reason if not requirements else None}

    preferences_used=[]
    if parts.get('career_preferences') is not None: preferences_used.append('career_preferences')
    if parts.get('research_interests') is not None: preferences_used.append('research_interests')
    preference_values=[parts[key] for key in preferences_used]
    preference_score=sum(preference_values)/len(preference_values) if preference_values else None
    dimensions=[
        dimension('academic',PERSONALIZED_DIMENSIONS['academic'],required_subjects,academic_inputs),
        {'key':'academic_performance','label':PERSONALIZED_DIMENSIONS['academic_performance'],
            'status':'assessed' if profile.get('academic_performance') is not None else 'missing',
            'score':parts.get('academic_performance'),'inputs_used':['academic_performance'] if profile.get('academic_performance') is not None else [],
            'missing_inputs':[] if profile.get('academic_performance') is not None else ['academic_performance'],'not_applicable_inputs':[],'reason':None},
        dimension('aptitude',PERSONALIZED_DIMENSIONS['aptitude'],apt_requirements,aptitude_inputs),
        dimension('interests',PERSONALIZED_DIMENSIONS['interests'],interest_requirements,interest_inputs),
        dimension('technical',PERSONALIZED_DIMENSIONS['technical'],technical_requirements,technical_inputs,na_skills['technical']),
        dimension('employability',PERSONALIZED_DIMENSIONS['employability'],employability_requirements,employability_inputs,na_skills['employability']),
        {'key':'preferences','label':PERSONALIZED_DIMENSIONS['preferences'],
            'status':'assessed' if preference_score is not None else 'missing','score':round(preference_score,1) if preference_score is not None else None,
            'inputs_used':preferences_used,'missing_inputs':[] if preferences_used else ['career_preferences or research_interests'],
            'not_applicable_inputs':[],'reason':None},
    ]
    assessed=sum(item['status']=='assessed' for item in dimensions)
    input_count=sum(len(item['inputs_used']) for item in dimensions)
    sufficient=assessed>=MIN_EVIDENCE_DIMENSIONS and input_count>=MIN_EVIDENCE_INPUTS
    coverage_percent=round(100*assessed/len(dimensions)) if dimensions else 0
    missing_labels=[item['label'] for item in dimensions if item['status']=='missing']
    not_applicable_labels=[item['label'] for item in dimensions if item['status']=='not_applicable']
    if sufficient:
        summary=f'{assessed} of {len(dimensions)} assessment areas contributed using {input_count} provided inputs.'
    else:
        summary=(f'Only {assessed} of {len(dimensions)} assessment areas contributed using {input_count} provided inputs. '
            f'A personalized score needs at least {MIN_EVIDENCE_DIMENSIONS} areas and {MIN_EVIDENCE_INPUTS} inputs; this is a provisional pathway suggestion.')
    return {'status':'sufficient' if sufficient else 'insufficient','sufficient':sufficient,
        'assessed_dimensions':assessed,'total_dimensions':len(dimensions),'coverage_percent':coverage_percent,
        'input_count':input_count,'minimum_dimensions_required':MIN_EVIDENCE_DIMENSIONS,
        'minimum_inputs_required':MIN_EVIDENCE_INPUTS,'dimensions':dimensions,
        'missing_dimensions':missing_labels,'not_applicable_dimensions':not_applicable_labels,'summary':summary}

def skill_gap_analysis(p,row):
    skill_evidence=_skill_evidence(p)
    actual={**skill_evidence['technical'],**skill_evidence['employability']}
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

def recommend_with_catalog_fingerprint(profile,top_n=5):
    """Generate results and bind them to the exact catalog snapshot used."""
    from backend.services.catalog_releases import catalog_read_context
    with catalog_read_context(KB,METADATA) as snapshot:
        return _recommend_with_catalog(profile,top_n),snapshot.fingerprint

def _recommend_with_catalog(profile,top_n=5):
    level=profile.get('education_level','10th')
    skill_evidence=_skill_evidence(profile)
    # The current ML feature contract is stage-wide, not course-aware. Keep
    # self-reported skills in the career-specific compatibility scorer only so
    # an unrelated skill cannot shift the experimental family signal.
    model_profile={**profile,**skill_evidence,'technical':{},'employability':{}}
    from backend.ml.predict import predict_career_families
    from backend.ml.artifact_contract import CAREER_FAMILIES, ModelInferenceError
    try:
        family_probs=predict_career_families(model_profile)
        values=list(family_probs.values()) if isinstance(family_probs,dict) else []
        if (set(family_probs) != set(CAREER_FAMILIES)
                or any(not isinstance(value,(int,float)) or not math.isfinite(value) or value<0 or value>1 for value in values)
                or not math.isclose(sum(values),1.0,rel_tol=0.0,abs_tol=1e-6)):
            raise ModelInferenceError('probability_values_invalid')
        model_identity=getattr(family_probs,'model_identity',None)
        model_validation_status=getattr(family_probs,'validation_status',None)
        model_missing_metadata=getattr(family_probs,'missing_metadata',())
        model_status='available'
        model_failure_reason=None
    except ModelInferenceError as exc:
        family_probs=None
        model_identity=None
        model_validation_status=None
        model_missing_metadata=()
        model_status='unavailable'
        model_failure_reason=exc.reason
    if level=='10th':
        from backend.services.school_pathways import PATHWAY_RULES, evaluate_pathway, summarize_pathways
        from backend.services.school_roadmap import build_pathway_roadmap
        from backend.ml.explain import explain_career_model
        results=[]
        for name,rule in PATHWAY_RULES.items():
            evaluation=evaluate_pathway(profile,name,family_probs)
            model_explanations=[
                explain_career_model(profile,family,model_identity)
                for family in rule['families']
            ] if model_status=='available' and evaluation['evidence_coverage']['sufficient'] else []
            evidence=[*evaluation['why_matches']]
            if evaluation['ml_score'] is not None:
                evidence.append(f"Experimental model-family signal trained on synthetic data: {evaluation['ml_score']:.1f}/100. It is not a probability of success or admission.")
            elif model_status=='unavailable':
                evidence.append('The model-family signal is unavailable; this is compatibility-only guidance.')
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
                'recommendation_type':evaluation['recommendation_type'],
                'evidence_coverage':evaluation['evidence_coverage'],
                'ml_used_in_ranking':evaluation['knowledge_score'] is not None and evaluation['ml_score'] is not None,
                'ranking_method':('insufficient_assessment_evidence' if not evaluation['evidence_coverage']['sufficient']
                    else 'hybrid_90_10_experimental_model' if evaluation['ml_score'] is not None
                    else 'compatibility_only_ml_unavailable' if model_status=='unavailable'
                    else 'insufficient_assessment_evidence'),
                'ml_family_probabilities':family_probs if evaluation['evidence_coverage']['sufficient'] else None,
                'model_explanations':model_explanations,
                'model_explanation_scope':'Each experimental, synthetic-data-based explanation describes its named model-family classification only; it does not explain pathway compatibility or predict admission or career success.',
                'ml_signal_label':'Experimental model-family signal trained on synthetic data; not a probability of career success or admission.',
                'ml_status':model_status,
                'ml_failure_reason':model_failure_reason,
                'model_validation_status':model_validation_status,
                'model_metadata_unverified':list(model_missing_metadata),
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
        return RecommendationResults(summarize_pathways(results),model_identity=model_identity,
            model_status=model_status,model_failure_reason=model_failure_reason,
            model_validation_status=model_validation_status,model_missing_metadata=model_missing_metadata)
    catalog_rows=careers()
    metadata={row['career_id']:_career_meta(row) for row in catalog_rows}
    from backend.services.eligibility import assess_eligibility,ELIGIBILITY_ORDER
    # Apply documented eligibility exclusions before personalized score/model
    # ranking. Unverified candidates remain exploratory and are clearly marked.
    eligibility_by_id={row['career_id']:assess_eligibility(profile,row) for row in catalog_rows}
    catalog_rows=[row for row in catalog_rows if eligibility_by_id[row['career_id']]['status']!='not_currently_eligible']
    ranked=[]; explanation_cache={}
    for c in catalog_rows:
        if not _stage_eligible(level,c): continue
        eligibility=eligibility_by_id[c['career_id']]
        score,parts=_profile_score(profile,c)
        evidence_coverage=_evidence_coverage(profile,c,parts)
        evidence_sufficient=evidence_coverage['sufficient']
        family=career_family(c); meta=metadata.get(c['career_id'],{})
        ml_probability=(round(family_probs.get(family,0)*100,1)
                        if family_probs is not None and evidence_sufficient else None)
        personalized_score=score if evidence_sufficient else None
        combined=(round((1-ML_SCORE_WEIGHT)*personalized_score+ML_SCORE_WEIGHT*ml_probability,1)
                  if ml_probability is not None else personalized_score)
        direct_degree=parts.get('degree')==100
        stage_met=parts.get('education',0)>=100
        if eligibility['status']=='eligible_now': qualification_status=eligibility['label']
        elif direct_degree and stage_met: qualification_status='Catalog-listed degree route; admission eligibility not verified'
        elif level in LEVELS and LEVELS.index(level)<LEVELS.index(c['minimum_education_level']): qualification_status='Future career pathway; further education required; admission eligibility not verified'
        elif parts.get('degree') is not None and parts.get('degree')>=45: qualification_status='Related direction; eligibility not verified'
        else: qualification_status='Eligibility not verified; additional qualifications may be required'
        extra=meta.get('qualification_notes') or 'The maintained career record is guidance, not an institution-specific eligibility decision. Confirm required subjects, recognized qualifications, entrance tests, and licensing rules with the relevant institution or regulator.'
        evidence=[(name,value) for name,value in parts.items() if value is not None and name in PERSONALIZED_DIMENSIONS and name!='preferences']
        if parts.get('career_preferences') is not None or parts.get('research_interests') is not None:
            pref_values=[parts[k] for k in ('career_preferences','research_interests') if parts.get(k) is not None]
            evidence.append(('preferences',sum(pref_values)/len(pref_values)))
        why=[f'{PERSONALIZED_DIMENSIONS.get(name,name.replace("_"," ").title())} ({value:.0f}/100) uses information you provided' for name,value in sorted(evidence,key=lambda x:x[1],reverse=True)[:3] if value>=55]
        why.append(qualification_status+'. '+extra)
        if eligibility['status']=='eligibility_not_verified':
            why.append(eligibility['explanation'])
        if not evidence_sufficient: why.append(evidence_coverage['summary'])
        elif not evidence: why.append('No relevant subject, aptitude or skill ratings have been provided yet; this is preliminary pathway guidance.')
        gap_analysis=skill_gap_analysis(profile,c); gaps=gap_analysis['gaps']
        if evidence_sufficient and model_status=='available' and family not in explanation_cache:
            from backend.ml.explain import explain_career_model
            explanation_cache[family]=explain_career_model(profile,family,model_identity)
        if ml_probability is not None:
            why.append(f'Experimental model-family signal trained on synthetic data: {ml_probability:.1f}/100. It is not a probability of success or admission.')
        elif not evidence_sufficient:
            why.append('The experimental model-family signal is not shown until enough personal assessment information is available.')
        else:
            why.append('The model-family signal is unavailable; this is compatibility-only guidance.')
        actions=[{'skill':g['skill'],'severity':g['severity'],'actions':_actions(g['skill'],g['severity'])} for g in gaps[:4]]
        if not actions and gap_analysis['status']=='insufficient_data': actions=[{'skill':'Assessment','severity':'Informational','actions':['Rate relevant current skills or complete the related assessment before interpreting this gap analysis.','Ask a teacher, counselor, or mentor which practice activities fit your current level.']}]
        sources=list(dict.fromkeys([*meta.get('sources',[]),*eligibility.get('evidence',[])]))
        from backend.skill_catalog import career_skill_guidance
        required_skills={**_parse(c['technical_skills']),**_parse(c['employability_skills'])}
        stream_aligned=bool(profile.get('stream') and parts.get('stream')==100)
        degree_component=parts.get('degree')
        degree_route_status='catalog_listed' if direct_degree else 'related_but_unverified' if degree_component is not None and degree_component>=45 else 'unverified'
        ranked.append({'career_id':c['career_id'],'career_name':c['career_name'],'description':c['description'],'compatibility_score':combined,'combined_score':combined,'ranking_score':combined,'knowledge_score':personalized_score,'ml_score':ml_probability,'ml_family_probability':ml_probability,'ml_used_in_ranking':ml_probability is not None,'ranking_method':'insufficient_assessment_evidence' if not evidence_sufficient else 'hybrid_90_10_experimental_model' if ml_probability is not None else 'compatibility_only_ml_unavailable','recommendation_type':'personalized' if evidence_sufficient else 'provisional','evidence_coverage':evidence_coverage,'ml_family':family if ml_probability is not None else None,'ml_family_probabilities':family_probs if evidence_sufficient else None,'model_explanation':explanation_cache.get(family),'model_explanation_scope':f'This is an experimental model-family signal learned from synthetic data. It is not a probability of career success or admission. It describes the {family} family only.','ml_signal_label':'Experimental model-family signal trained on synthetic data; not a probability of career success or admission.','ml_status':model_status,'ml_failure_reason':model_failure_reason,'model_validation_status':model_validation_status,'model_metadata_unverified':list(model_missing_metadata),'why_matches':why,'required_skills':required_skills,'skill_guidance':career_skill_guidance(c['career_id'],_parse(c['technical_skills']),_parse(c['employability_skills']),{**skill_evidence['technical'],**skill_evidence['employability']}),'required_subjects':_list(c['required_subjects']),'optional_certifications':c['optional_certifications'],'skill_gaps':gaps,'skill_gap_status':gap_analysis['status'],'skill_gap_message':gap_analysis['message'],'improvement_suggestions':actions,'education_path':c['recommended_degrees'],'qualification_status':qualification_status,'eligibility':eligibility,'additional_qualifications':extra,'qualification_sources':sources,'minimum_education_level':c['minimum_education_level'],'suitable_streams':_list(c['suitable_streams']),'context':{'education_stage':{'student_stage':level,'career_minimum_stage':c['minimum_education_level'],'status':'meets_catalog_minimum' if stage_met else 'further_education_expected'},'stream_suitability':{'student_stream':profile.get('stream') or None,'suitable_streams':_list(c.get('suitable_streams')),'status':'aligned' if stream_aligned else 'not_provided_or_unaligned'},'degree_route':{'student_degree':profile.get('degree') or None,'catalog_match':direct_degree,'status':degree_route_status}},'components':parts})
    ordered=sorted(ranked,key=lambda x:(ELIGIBILITY_ORDER.get(x['eligibility']['status'],99),-(x['ranking_score'] if x['ranking_score'] is not None else -1),x['career_name']))[:max(1,min(5,int(top_n)))]
    return RecommendationResults(ordered,model_identity=model_identity,model_status=model_status,
        model_failure_reason=model_failure_reason,model_validation_status=model_validation_status,
        model_missing_metadata=model_missing_metadata)

def career_detail(cid): return next((c for c in careers() if c['career_id']==cid),None)
