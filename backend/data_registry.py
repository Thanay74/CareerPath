"""Read-only registry of datasets documented for this project."""
from pathlib import Path
import csv

ROOT=Path(__file__).resolve().parents[1]
DATASETS=[
    {"dataset_id":"uci_student_math","name":"UCI Student Performance (Math)","path":"data/raw/student_performance/extracted/student-mat.csv","source":"UCI Machine Learning Repository, Student Performance (ID 320), DOI 10.24432/C5TG7T","source_url":"https://doi.org/10.24432/C5TG7T","data_class":"public_real_student_records","purpose":"Separate academic grade-band experiment only; contains school performance fields, not career recommendations.","required_columns":["school","sex","G1","G2","G3"]},
    {"dataset_id":"uci_student_portuguese","name":"UCI Student Performance (Portuguese)","path":"data/raw/student_performance/extracted/student-por.csv","source":"UCI Machine Learning Repository, Student Performance (ID 320), DOI 10.24432/C5TG7T","source_url":"https://doi.org/10.24432/C5TG7T","data_class":"public_real_student_records","purpose":"Preserved public source file; academic analysis only, not used to train career-family recommendations.","required_columns":["school","sex","G1","G2","G3"]},
    {"dataset_id":"kaggle_career_source","name":"Kaggle Student Career Success source", "path":"data/raw/kaggle_student_career_success/student_career_success_dataset.csv","source":"Mobeen Fatima, Kaggle Student Career Success Prediction Dataset","source_url":"https://www.kaggle.com/datasets/mobeenfatimah/student-career-success-prediction-dataset","data_class":"synthetic","purpose":"Preserved Kaggle synthetic source; separate Bachelor's career-field benchmark only.","required_columns":["Career_Field"]},
    {"dataset_id":"kaggle_career_processed","name":"Kaggle career-field processed benchmark", "path":"data/processed/kaggle_student_career_success/career_field_training.csv","source":"Derived from the Kaggle dataset above; processing described in DATA_SOURCES.md","source_url":"https://www.kaggle.com/datasets/mobeenfatimah/student-career-success-prediction-dataset","data_class":"synthetic","purpose":"Separate held-out/CV career-field benchmark; not used by the four-stage recommendation service.","required_columns":["Career_Field"]},
    {"dataset_id":"career_training_profiles","name":"CareerPath career-family training profiles", "path":"data/synthetic/career_training_profiles.csv","source":"Generated locally by data/generate_career_training_data.py (seed 20260929)","source_url":"","data_class":"synthetic","purpose":"Four stage model development/evaluation; generated family labels are not real student outcomes.","required_columns":["education_level","stream","career_family"]},
    {"dataset_id":"synthetic_students","name":"CareerPath synthetic student fixtures", "path":"data/synthetic/students.csv","source":"Generated locally by data/generate_synthetic_data.py","source_url":"","data_class":"synthetic","purpose":"Development/test fixtures only.","required_columns":["student_id","education_level"]}
]

def inspect_datasets():
    result=[]
    for entry in DATASETS:
        path=ROOT/entry['path']; found=path.is_file(); columns=[]; records=None; valid=False; validation_error='File missing'
        if found:
            try:
                with path.open(encoding='utf-8-sig',newline='') as source:
                    first=source.readline(); delimiter=';' if first.count(';')>first.count(',') else ','
                    source.seek(0); reader=csv.reader(source,delimiter=delimiter); columns=next(reader,[])
                    records=sum(1 for _ in reader); missing=[x for x in entry['required_columns'] if x not in columns]
                    valid=not missing; validation_error='' if valid else 'Missing required columns: '+', '.join(missing)
            except (OSError,UnicodeError,csv.Error,StopIteration) as exc:
                validation_error='Unreadable CSV ('+type(exc).__name__+')'
        result.append({**entry,'exists':found,'record_count':records,'feature_count':len(columns),'columns':columns,'validated':valid,'validation_status':'valid' if valid else validation_error,'file_size_bytes':path.stat().st_size if found else None})
    return {'datasets':result,'user_collected_survey_data_available':False,'uploads_enabled':False}
