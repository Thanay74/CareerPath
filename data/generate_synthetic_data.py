"""Reproducible synthetic development profiles. Seeded; never real-student data."""
from pathlib import Path
import csv, random

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'synthetic'
SEED = 20260929

APT = ['logical_reasoning','numerical_reasoning','verbal_reasoning','spatial_reasoning','analytical_reasoning','problem_solving','attention_to_detail']
INT = ['technology','research','creativity','entrepreneurship','leadership','healthcare','business','social_service','communication','design','innovation']
TECH = ['programming','python','java','javascript','sql','data_analysis','machine_learning','web_development','cybersecurity','cloud_computing','accounting','finance','graphic_design','ui_ux','electronics','hardware','research_methods']
EMP = ['communication','teamwork','leadership','adaptability','time_management','problem_solving','critical_thinking','presentation','decision_making','professionalism']
SUB = ['physics','chemistry','biology','mathematics','computer_science','english','accountancy','business_studies','economics','history','geography','political_science','sociology']
CAREERS = [
('C01','Software Developer','Designs, builds, tests and maintains software applications.','Bachelor\'s','Science;Commerce','mathematics;computer_science','logical_reasoning:65;numerical_reasoning:55;problem_solving:70','programming:65;python:55;sql:45','problem_solving:65;teamwork:55','technology:65;innovation:55','BCA;BSc Computer Science;BE/BTech Computer Science','Cloud or programming certifications'),
('C02','Data Scientist','Uses statistics, programming and domain knowledge to extract insights.','Master\'s','Science;Commerce','mathematics;computer_science','numerical_reasoning:75;analytical_reasoning:75;logical_reasoning:65','python:70;data_analysis:70;machine_learning:60;sql:60','critical_thinking:70;communication:55','research:70;technology:60','BSc Statistics/Computer Science;MSc Data Science','Cloud and analytics certifications'),
('C03','AI Engineer','Develops and deploys machine learning and AI systems.','Master\'s','Science','mathematics;computer_science','numerical_reasoning:75;analytical_reasoning:75;problem_solving:75','python:75;machine_learning:75;programming:70;cloud_computing:45','critical_thinking:65;teamwork:55','technology:75;innovation:70;research:55','BTech Computer Science;MTech/ MSc AI or Data Science','Cloud ML certifications'),
('C04','Cybersecurity Analyst','Monitors systems and reduces information security risk.','Bachelor\'s','Science','mathematics;computer_science','logical_reasoning:70;analytical_reasoning:70;attention_to_detail:75','cybersecurity:70;programming:45;networking:50','professionalism:65;problem_solving:70','technology:70;innovation:45','BSc/BTech Computer Science;BCA','Security certifications'),
('C05','Web Developer','Builds accessible websites and web applications.','Bachelor\'s','Science;Commerce;Arts/Humanities','computer_science;mathematics','logical_reasoning:55;spatial_reasoning:55;problem_solving:60','javascript:65;web_development:70;html_css:60','communication:50;time_management:55','technology:55;creativity:55;design:45','BCA;BSc Computer Science;Diploma in Web Development','Web platform certifications'),
('C06','Data Analyst','Prepares and interprets data to support decisions.','Bachelor\'s','Science;Commerce','mathematics;economics','numerical_reasoning:65;analytical_reasoning:70;attention_to_detail:65','sql:65;data_analysis:70;python:40','communication:60;presentation:55','business:55;research:55;technology:50','BSc Statistics;BCom;BCA','BI tool certifications'),
('C07','UI/UX Designer','Researches user needs and designs usable digital products.','Bachelor\'s','Science;Commerce;Arts/Humanities','english;computer_science','spatial_reasoning:70;verbal_reasoning:55;analytical_reasoning:60','ui_ux:70;graphic_design:55;web_development:35','communication:65;teamwork:60','design:75;creativity:70;technology:45','BDes;BSc Design;BA Design','UX research certification'),
('C08','Mechanical Engineer','Designs and improves machines, products and manufacturing systems.','Bachelor\'s','Science','physics;mathematics','spatial_reasoning:75;numerical_reasoning:65;problem_solving:70','electronics:40;hardware:60;programming:35','teamwork:55;critical_thinking:65','innovation:55;technology:55','BE/BTech Mechanical Engineering','CAD certifications'),
('C09','Civil Engineer','Plans and supervises infrastructure and built environments.','Bachelor\'s','Science','physics;mathematics;geography','spatial_reasoning:70;numerical_reasoning:65;attention_to_detail:65','hardware:35;data_analysis:35','teamwork:65;decision_making:55','innovation:45;social_service:40','BE/BTech Civil Engineering','Project management certifications'),
('C10','Electrical Engineer','Designs electrical systems, equipment and power solutions.','Bachelor\'s','Science','physics;mathematics','numerical_reasoning:70;spatial_reasoning:65;problem_solving:70','electronics:70;hardware:65;programming:40','attention_to_detail:65;teamwork:55','technology:60;innovation:55','BE/BTech Electrical Engineering','Electrical safety certifications'),
('C11','Doctor','Diagnoses illness and provides patient care after regulated medical training.','Master\'s','Science','biology;chemistry;physics','analytical_reasoning:70;verbal_reasoning:65;attention_to_detail:75','research_methods:45','communication:70;professionalism:80;decision_making:70','healthcare:85;social_service:60;research:45','MBBS followed by licensed postgraduate training','Specialty training; licensing as required'),
('C12','Pharmacist','Supports safe and effective use of medicines.','Bachelor\'s','Science','chemistry;biology','attention_to_detail:75;analytical_reasoning:65;verbal_reasoning:55','research_methods:40;data_analysis:35','communication:60;professionalism:75','healthcare:70;research:45','BPharm; PharmD where applicable','Registration/licensing as applicable'),
('C13','Biotechnologist','Applies biological science and technology to research and products.','Bachelor\'s','Science','biology;chemistry','analytical_reasoning:70;attention_to_detail:75;numerical_reasoning:55','research_methods:65;data_analysis:45','teamwork:55;critical_thinking:65','research:75;healthcare:45;innovation:55','BSc Biotechnology; BTech Biotechnology','Laboratory safety certifications'),
('C14','Chartered Accountant','Provides audit, accounting, tax and financial reporting services.','Bachelor\'s','Commerce','accountancy;mathematics;business_studies','numerical_reasoning:75;attention_to_detail:80;analytical_reasoning:65','accounting:75;finance:60;sql:30','professionalism:75;communication:60;time_management:70','business:70;entrepreneurship:40','BCom plus professional CA examinations','Professional qualification and membership'),
('C15','Financial Analyst','Evaluates financial performance, markets and investment options.','Bachelor\'s','Commerce;Science','accountancy;mathematics;economics','numerical_reasoning:75;analytical_reasoning:70;attention_to_detail:65','finance:70;accounting:55;data_analysis:55','communication:60;decision_making:60','business:65;research:45','BCom; BBA Finance; BSc Economics','Finance certifications'),
('C16','Business Analyst','Connects business needs with data, processes and technology.','Bachelor\'s','Commerce;Science;Arts/Humanities','business_studies;economics;mathematics','verbal_reasoning:70;analytical_reasoning:70;problem_solving:65','data_analysis:50;sql:40','communication:75;presentation:65;teamwork:65','business:70;communication:70;technology:40','BBA; BCom; BSc; later MBA optional','Business analysis certifications'),
('C17','Entrepreneur','Builds and operates a venture around a product or service.','Bachelor\'s','Commerce;Science;Arts/Humanities','business_studies;economics;english','decision_making:70;problem_solving:70;verbal_reasoning:60','finance:45;data_analysis:35','leadership:75;adaptability:80;communication:70','entrepreneurship:80;innovation:75;business:65','Any undergraduate degree; practical venture experience','Incubation and business programs'),
('C18','Teacher','Plans instruction and supports student learning.','Bachelor\'s','Science;Commerce;Arts/Humanities','english;history;mathematics','verbal_reasoning:70;attention_to_detail:60;analytical_reasoning:55','research_methods:35','communication:80;presentation:70;professionalism:70','social_service:70;communication:75;leadership:45','Subject degree plus BEd or applicable teacher preparation','Teacher eligibility/licensing as applicable'),
('C19','Research Scientist','Designs studies, analyzes evidence and communicates findings.','Master\'s','Science;Arts/Humanities','mathematics;biology;chemistry','analytical_reasoning:80;attention_to_detail:75;numerical_reasoning:70','research_methods:80;data_analysis:65','critical_thinking:80;communication:60','research:85;innovation:60','Relevant BSc/BA then MSc; PhD often required for independent research','Research methods and domain training'),
('C20','Psychologist','Studies behavior and supports mental health within qualified scope.','Master\'s','Arts/Humanities;Science','psychology;biology;english','verbal_reasoning:75;analytical_reasoning:65;attention_to_detail:60','research_methods:50;data_analysis:35','communication:80;professionalism:80;critical_thinking:65','social_service:75;healthcare:60;research:55','BA/BSc Psychology; advanced accredited training','Registration/licensing varies by jurisdiction'),
('C21','Lawyer','Advises clients and represents legal interests after required legal education.','Bachelor\'s','Arts/Humanities;Commerce','english;history;political_science','verbal_reasoning:80;logical_reasoning:75;attention_to_detail:70','research_methods:55','communication:80;professionalism:80;decision_making:65','social_service:50;leadership:45;business:40','Integrated LLB or LLB after degree','Bar enrollment and licensing as applicable'),
('C22','Journalist','Researches, verifies and communicates news and stories.','Bachelor\'s','Arts/Humanities;Commerce','english;history;political_science','verbal_reasoning:80;attention_to_detail:70;analytical_reasoning:65','graphic_design:30;data_analysis:35','communication:85;adaptability:70;professionalism:70','communication:85;creativity:65;social_service:50','BA Journalism; BA English/Media','Digital journalism training'),
('C23','Graphic Designer','Creates visual communication for print and digital media.','Bachelor\'s','Arts/Humanities;Commerce;Science','english;computer_science','spatial_reasoning:75;attention_to_detail:65;creativity:75','graphic_design:75;ui_ux:45','communication:60;time_management:60','design:80;creativity:80;innovation:55','BDes; BA/BSc Visual Communication','Design software certifications'),
('C24','Digital Marketing Specialist','Plans and measures online campaigns and audience growth.','Bachelor\'s','Commerce;Arts/Humanities;Science','business_studies;english;mathematics','verbal_reasoning:70;analytical_reasoning:65;creativity:60','data_analysis:45;graphic_design:35;web_development:30','communication:70;adaptability:70','business:70;creativity:60;communication:70','BBA Marketing; BCom; BA Communications','Platform certifications'),
('C25','Public Administration Officer','Supports public policy design, delivery and administration.','Bachelor\'s','Arts/Humanities;Commerce;Science','political_science;history;economics','verbal_reasoning:75;analytical_reasoning:70;decision_making:70','research_methods:45;data_analysis:35','communication:75;professionalism:80;decision_making:75','social_service:75;leadership:60;business:45','Bachelor degree; competitive public service examinations','Public administration training'),
]

def write(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

def req(s): return {k:float(v) for k,v in (x.split(':') for x in s.split(';') if x)}

def main(n=240):
    OUT.mkdir(parents=True,exist_ok=True); rng=random.Random(SEED)
    tables={k:[] for k in ['students','aptitude_scores','interest_scores','technical_skills','employability_skills']}
    levels=['10th','12th',"Bachelor's", "Master's"]
    for i in range(n):
        sid=f'SYN{i+1:04d}'; level=rng.choice(levels); latent=rng.choice(CAREERS); stream=rng.choice(latent[4].split(';'))
        cs_bias=stream=='Science'; biz_bias=stream=='Commerce'; arts_bias=stream=='Arts/Humanities'
        academic={s:max(25,min(98,rng.gauss(72+(12*cs_bias if s in ('mathematics','physics','computer_science') else 0)+(12*biz_bias if s in ('accountancy','economics','business_studies') else 0)+(12*arts_bias if s in ('english','history','sociology') else 0),11))) for s in SUB}
        applicable={'Science':{'physics','chemistry','biology','mathematics','computer_science','english'},'Commerce':{'mathematics','english','accountancy','business_studies','economics'},'Arts/Humanities':{'english','economics','history','geography','political_science','sociology'}}
        subjects={s:(round(v,1) if rng.random()>.08 else '') if level=='10th' or s in applicable.get(stream,set()) else '' for s,v in academic.items()}
        stu=dict(student_id=sid,education_level=level,age={'10th':15,'12th':17,"Bachelor's":20,"Master's":23}[level]+rng.randint(-1,2),gender=rng.choice(['female','male','nonbinary','prefer_not_to_say']),stream=stream,**subjects)
        tables['students'].append(stu)
        intreq=req(latent[9]); techreq=req(latent[7]); aptreq=req(latent[6]); empreq=req(latent[8])
        for key, cols, rr, bias in [('aptitude_scores',APT,aptreq,0),('interest_scores',INT,intreq,0),('technical_skills',TECH,techreq,0),('employability_skills',EMP,empreq,0)]:
            row={'student_id':sid}
            for col in cols:
                target=rr.get(col, 45)
                if key=='aptitude_scores': target=65 if col in aptreq else 55
                elif key=='employability_skills': target=65 if col in rr else 55
                elif key=='technical_skills': target=55 if col in rr else 18
                elif key=='interest_scores': target=70 if col in rr else 30
                row[col]=round(max(0,min(100,rng.gauss(target,13)))) if (key!='technical_skills' or target>25 or rng.random()>.72) else ''
            tables[key].append(row)
    for name, rows in tables.items():
        fields=list(rows[0]); write(OUT/f'{name}.csv',rows,fields)

if __name__=='__main__': main()
