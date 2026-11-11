"""Stage-specific feature contracts for career-family prediction."""
APTITUDE=["logical_reasoning","numerical_reasoning","verbal_reasoning","spatial_reasoning","analytical_reasoning","problem_solving","attention_to_detail"]
INTERESTS=["technology","research","creativity","entrepreneurship","leadership","healthcare","business","social_service","communication","design","innovation"]
EMPLOYABILITY=["communication","teamwork","leadership","adaptability","time_management","problem_solving","critical_thinking","presentation","decision_making","professionalism"]
SUBJECTS_10=["physics","chemistry","biology","mathematics","computer_science","english","accountancy","business_studies","economics","history","geography","political_science","sociology"]
SUBJECTS_12=["physics","chemistry","biology","mathematics","computer_science","english","accountancy","business_studies","economics","history","political_science","sociology"]
SUBJECTS_BACHELOR=["mathematics","computer_science","biology","chemistry","accountancy","economics","english","political_science"]
SUBJECTS_MASTER=["mathematics","computer_science","biology","chemistry","economics","english","political_science"]
TECH_FOUNDATION=["programming","python","javascript","web_development","graphic_design","ui_ux","electronics","hardware","accounting","finance"]
TECH_PRE_UNDERGRAD=["programming","python","java","javascript","sql","data_analysis","web_development","cybersecurity","accounting","finance","graphic_design","ui_ux","electronics","hardware"]
TECH_PROFESSIONAL=["programming","python","java","javascript","sql","data_analysis","machine_learning","web_development","cybersecurity","cloud_computing","accounting","finance","graphic_design","ui_ux","electronics","hardware","research_methods"]
TECH_ADVANCED=["programming","python","sql","data_analysis","machine_learning","cybersecurity","cloud_computing","finance","ui_ux","electronics","hardware","research_methods"]
STAGE_FEATURES={level:list(dict.fromkeys(features)) for level,features in {
 "10th":APTITUDE+INTERESTS+EMPLOYABILITY+TECH_FOUNDATION+SUBJECTS_10,
 "12th":APTITUDE+INTERESTS+EMPLOYABILITY+TECH_PRE_UNDERGRAD+SUBJECTS_12,
 "Bachelor's":APTITUDE+INTERESTS+EMPLOYABILITY+TECH_PROFESSIONAL+SUBJECTS_BACHELOR,
 "Master's":APTITUDE+INTERESTS+EMPLOYABILITY+TECH_ADVANCED+SUBJECTS_MASTER,
}.items()}
def feature_row(profile,level=None):
    level=level or profile.get('education_level','10th'); result={name:None for name in STAGE_FEATURES[level]}
    for group in ('subjects','aptitude','interests','technical','employability'):
        result.update({k:v for k,v in (profile.get(group) or {}).items() if k in result})
    result['stream']=profile.get('stream') or 'unspecified'
    return result
