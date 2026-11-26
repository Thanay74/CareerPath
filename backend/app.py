"""Flask REST API. SQLite for local setup; MySQL through DATABASE_URL."""
from flask import Flask,request,jsonify,g
from flask_cors import CORS
from pathlib import Path
import hashlib,hmac,secrets,sqlite3,json,re,os
from datetime import datetime,timezone
from urllib.parse import urlparse,unquote
from backend.database_config import resolve_database_target, DatabaseTargetError
from backend.interprocess_lock import interprocess_file_lock
from backend.services.recommendation_engine import recommend,recommend_with_catalog_fingerprint,career_detail
from backend.recommendation_snapshots import (decode_history,encode_history,new_snapshot,
    recommendation_input_fingerprint,select_current_snapshot,FORMAT,FORMAT_VERSION)
from backend.academic_history import empty_academic_history,validate_academic_history
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError: pass

ROOT=Path(__file__).resolve().parents[1]
DATABASE_URL=os.environ.get('DATABASE_URL','')
_DATABASE_CONFIG_ERROR=None
try:
    DATABASE_TARGET=resolve_database_target(DATABASE_URL,os.environ.get('CAREERPATH_DB'),allow_default=True,project_root=ROOT)
except DatabaseTargetError as exc:
    # Keep imports and read-only catalog validation available, but never switch
    # an invalid configured URL to a different database silently.
    DATABASE_TARGET=None
    _DATABASE_CONFIG_ERROR=str(exc)
DB_PATH=DATABASE_TARGET.sqlite_path if DATABASE_TARGET and DATABASE_TARGET.sqlite_path else ROOT/'careerpath.sqlite3'
USE_MYSQL=bool(DATABASE_TARGET and DATABASE_TARGET.mysql)
app=Flask(__name__); CORS(app)

class HybridRow(dict):
    def __getitem__(self,key): return list(self.values())[key] if isinstance(key,int) else super().__getitem__(key)
class MySQLResult:
    def __init__(self,cursor): self.cursor=cursor; self.rowcount=cursor.rowcount; self.lastrowid=cursor.lastrowid
    def fetchone(self):
        row=self.cursor.fetchone()
        return HybridRow(row) if row is not None else None
    def fetchall(self): return [HybridRow(row) for row in self.cursor.fetchall()]
class MySQLConnection:
    def __init__(self,raw): self.raw=raw
    def execute(self,sql,params=()):
        cur=self.raw.cursor(); cur.execute(sql.replace('?','%s'),params); return MySQLResult(cur)
    def commit(self): self.raw.commit()
    def rollback(self): self.raw.rollback()
    def close(self): self.raw.close()
def connect_db():
    if _DATABASE_CONFIG_ERROR:
        raise RuntimeError('Database configuration is invalid; refusing to connect') from DatabaseTargetError(_DATABASE_CONFIG_ERROR)
    if USE_MYSQL:
        try: import pymysql
        except ImportError as ex: raise RuntimeError('Install backend/requirements.txt to enable MySQL') from ex
        u=urlparse(DATABASE_URL); return MySQLConnection(pymysql.connect(host=u.hostname or 'localhost',port=u.port or 3306,user=unquote(u.username or ''),password=unquote(u.password or ''),database=(u.path or '/careerpath').lstrip('/'),charset='utf8mb4',autocommit=False,cursorclass=pymysql.cursors.DictCursor))
    conn=sqlite3.connect(DB_PATH); conn.row_factory=sqlite3.Row; conn.execute('PRAGMA foreign_keys=ON'); return conn
def unpack(value): return json.loads(value) if isinstance(value,(str,bytes,bytearray)) else value
def db():
    if 'db' not in g: g.db=connect_db()
    return g.db
@app.teardown_appcontext
def close_db(_):
    conn=g.pop('db',None)
    if conn: conn.close()

def seed_aptitude_questions(conn):
    from backend.aptitude_bank import QUESTIONS
    for q in QUESTIONS:
        params=(q['question_id'],q['domain'],q['difficulty'],q['question_text'],json.dumps(q['options']),q['correct_option'],q['explanation'],json.dumps(q['education_levels']))
        if USE_MYSQL:
            conn.execute('INSERT INTO aptitude_questions(question_id,domain,difficulty,question_text,options_json,correct_option,explanation,education_levels_json) VALUES(?,?,?,?,?,?,?,?) ON DUPLICATE KEY UPDATE education_levels_json=VALUES(education_levels_json),is_active=TRUE',params)
        else:
            conn.execute('INSERT INTO aptitude_questions(question_id,domain,difficulty,question_text,options_json,correct_option,explanation,education_levels_json) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(question_id) DO UPDATE SET education_levels_json=excluded.education_levels_json,is_active=1',params)

def seed_education_catalog(conn):
    from backend.education_catalog import EDUCATION_CATALOG
    for level,catalog in EDUCATION_CATALOG.items():
        program_type='degree' if catalog.get('degrees') else 'stream'
        names=catalog.get('degrees') or catalog.get('streams',[])
        programs={}
        for name in names:
            row=conn.execute('SELECT program_id FROM education_programs WHERE education_level=? AND program_name=?',(level,name)).fetchone()
            if row: program_id=row['program_id']
            else: program_id=conn.execute('INSERT INTO education_programs(education_level,program_name,program_type) VALUES(?,?,?)',(level,name,program_type)).lastrowid
            programs[name]=program_id
        for degree,items in catalog.get('specializations',{}).items():
            if degree not in programs: continue
            for name in items:
                row=conn.execute('SELECT specialization_id FROM education_specializations WHERE program_id=? AND specialization_name=?',(programs[degree],name)).fetchone()
                spec_id=row['specialization_id'] if row else conn.execute('INSERT INTO education_specializations(program_id,specialization_name) VALUES(?,?)',(programs[degree],name)).lastrowid
        def attach(program_name,specialization,subject_keys):
            if program_name not in programs: return
            program_id=programs[program_name]
            spec_id=None
            if specialization:
                spec=conn.execute('SELECT specialization_id FROM education_specializations WHERE program_id=? AND specialization_name=?',(program_id,specialization)).fetchone()
                if not spec: return
                spec_id=spec['specialization_id']
            for key in subject_keys:
                label=key.replace('_',' ').title()
                subject=conn.execute('SELECT subject_id FROM education_subjects WHERE subject_key=?',(key,)).fetchone()
                subject_id=subject['subject_id'] if subject else conn.execute('INSERT INTO education_subjects(subject_key,subject_name) VALUES(?,?)',(key,label)).lastrowid
                if spec_id is None:
                    sql='INSERT IGNORE INTO education_program_subjects(program_id,subject_id) VALUES(?,?)' if USE_MYSQL else 'INSERT OR IGNORE INTO education_program_subjects(program_id,subject_id) VALUES(?,?)'
                    conn.execute(sql,(program_id,subject_id))
                else:
                    sql='INSERT IGNORE INTO education_specialization_subjects(specialization_id,subject_id) VALUES(?,?)' if USE_MYSQL else 'INSERT OR IGNORE INTO education_specialization_subjects(specialization_id,subject_id) VALUES(?,?)'
                    conn.execute(sql,(spec_id,subject_id))
        if level=='10th':
            for name in names: attach(name,'',catalog['subjects'].get('default',[]))
        elif level=='12th':
            for name in names: attach(name,'',catalog['subjects'].get(name,[]))
        else:
            for degree in names:
                attach(degree,'',catalog['subjects'].get(degree,[]))
                for key,subject_keys in catalog['subjects'].items():
                    if key.startswith(degree+'|'): attach(degree,key.split('|',1)[1],subject_keys)

def init_db():
    # Refuse the destructive legacy rename before executing any DDL. A reviewed,
    # data-preserving migration must replace this guard before legacy support.
    if USE_MYSQL:
        conn=connect_db()
        legacy=conn.execute("SELECT COUNT(*) AS n FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='assessments'").fetchone()['n']
        if legacy:
            columns={r['COLUMN_NAME'] for r in conn.execute("SELECT COLUMN_NAME FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='assessments'").fetchall()}
            if columns and 'assessment_type' not in columns:
                conn.close(); raise RuntimeError('Legacy assessments schema detected; setup stopped before DDL. A reviewed data-preserving migration is required.')
        conn.execute("CREATE TABLE IF NOT EXISTS users(user_id BIGINT PRIMARY KEY AUTO_INCREMENT,email VARCHAR(255) UNIQUE NOT NULL,password_hash VARCHAR(255) NOT NULL,token VARCHAR(128) UNIQUE,role ENUM('student','admin') NOT NULL DEFAULT 'student',is_active BOOLEAN NOT NULL DEFAULT TRUE,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        conn.execute("CREATE TABLE IF NOT EXISTS students(student_id VARCHAR(64) PRIMARY KEY,user_id BIGINT UNIQUE,education_level VARCHAR(32) NOT NULL,age TINYINT NULL,gender VARCHAR(40) NULL,stream VARCHAR(64) NULL,academic_history JSON NULL,FOREIGN KEY(user_id) REFERENCES users(user_id))")
        conn.execute('CREATE TABLE IF NOT EXISTS academic_records(student_id VARCHAR(64),subject_name VARCHAR(64),score DECIMAL(5,2),PRIMARY KEY(student_id,subject_name),FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE)')
        user_cols={r['COLUMN_NAME'] for r in conn.execute("SELECT COLUMN_NAME FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='users'").fetchall()}
        if 'role' not in user_cols: conn.execute("ALTER TABLE users ADD COLUMN role ENUM('student','admin') NOT NULL DEFAULT 'student'")
        if 'is_active' not in user_cols: conn.execute('ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE')
        if 'created_at' not in user_cols: conn.execute('ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        stu_cols={r['COLUMN_NAME'] for r in conn.execute("SELECT COLUMN_NAME FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='students'").fetchall()}
        if 'profile_updated_at' not in stu_cols: conn.execute('ALTER TABLE students ADD COLUMN profile_updated_at TIMESTAMP NULL')
        for name,ddl in [('age','TINYINT NULL'),('gender','VARCHAR(40) NULL'),('stream','VARCHAR(128) NULL'),('degree','VARCHAR(255) NULL'),('specialization','VARCHAR(255) NULL'),('study_period','VARCHAR(64) NULL'),('academic_performance','DECIMAL(5,2) NULL'),('academic_scale',"VARCHAR(16) NOT NULL DEFAULT 'percentage'"),('research_interests','TEXT NULL'),('career_preferences','TEXT NULL'),('academic_history','JSON NULL')]:
            if name not in stu_cols: conn.execute(f'ALTER TABLE students ADD COLUMN {name} {ddl}')
        if 'profile_json' in stu_cols: conn.execute('ALTER TABLE students MODIFY profile_json JSON NULL')
        assessment_cols={r['COLUMN_NAME'] for r in conn.execute("SELECT COLUMN_NAME FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='assessments'").fetchall()}
        if assessment_cols and 'assessment_type' not in assessment_cols:
            conn.execute('RENAME TABLE assessments TO assessments_legacy_json')
        conn.execute("CREATE TABLE IF NOT EXISTS assessments(student_id VARCHAR(64),assessment_type ENUM('aptitude','interests','technical','employability'),feature_name VARCHAR(64),score DECIMAL(5,2),PRIMARY KEY(student_id,assessment_type,feature_name),FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE)")
        conn.execute("CREATE TABLE IF NOT EXISTS student_skill_details(student_id VARCHAR(64) NOT NULL,skill_key VARCHAR(128) NOT NULL,normalized_name VARCHAR(128) NOT NULL,display_name VARCHAR(255) NOT NULL,category VARCHAR(32) NOT NULL,applicability VARCHAR(24) NOT NULL,proficiency DECIMAL(5,2) NULL,source_context VARCHAR(32) NULL,canonical_skill VARCHAR(64) NULL,is_custom BOOLEAN NOT NULL DEFAULT FALSE,PRIMARY KEY(student_id,skill_key),UNIQUE KEY uq_student_skill_name(student_id,normalized_name),CHECK(category IN ('technical','employability')),CHECK(applicability IN ('not_applicable','assessed')),CHECK(proficiency IS NULL OR proficiency BETWEEN 0 AND 100),CHECK(is_custom IN (0,1)),FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE)")
        conn.execute('CREATE TABLE IF NOT EXISTS recommendations(recommendation_id BIGINT PRIMARY KEY AUTO_INCREMENT,student_id VARCHAR(64) UNIQUE NOT NULL,results_json JSON NOT NULL,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(student_id) REFERENCES students(student_id))')
        conn.execute("CREATE TABLE IF NOT EXISTS aptitude_questions(question_id VARCHAR(16) PRIMARY KEY,domain VARCHAR(64) NOT NULL,difficulty VARCHAR(32) NOT NULL,question_text TEXT NOT NULL,options_json JSON NOT NULL,correct_option CHAR(1) NOT NULL,explanation TEXT NOT NULL,education_levels_json JSON NOT NULL,is_active BOOLEAN NOT NULL DEFAULT TRUE)")
        question_cols={r['COLUMN_NAME'] for r in conn.execute("SELECT COLUMN_NAME FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='aptitude_questions'").fetchall()}
        if 'is_active' not in question_cols: conn.execute('ALTER TABLE aptitude_questions ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE')
        conn.execute("CREATE TABLE IF NOT EXISTS aptitude_attempts(attempt_id BIGINT PRIMARY KEY AUTO_INCREMENT,student_id VARCHAR(64) NOT NULL,status ENUM('in_progress','completed') NOT NULL DEFAULT 'in_progress',started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,completed_at TIMESTAMP NULL,overall_score DECIMAL(5,2) NULL,FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE)")
        conn.execute("CREATE TABLE IF NOT EXISTS aptitude_attempt_questions(attempt_id BIGINT NOT NULL,question_id VARCHAR(16) NOT NULL,question_order TINYINT UNSIGNED NOT NULL,PRIMARY KEY(attempt_id,question_id),UNIQUE KEY uq_attempt_order(attempt_id,question_order),FOREIGN KEY(attempt_id) REFERENCES aptitude_attempts(attempt_id) ON DELETE CASCADE,FOREIGN KEY(question_id) REFERENCES aptitude_questions(question_id))")
        conn.execute("CREATE TABLE IF NOT EXISTS aptitude_responses(attempt_id BIGINT NOT NULL,question_id VARCHAR(16) NOT NULL,selected_option CHAR(1) NOT NULL,is_correct BOOLEAN NOT NULL,PRIMARY KEY(attempt_id,question_id),FOREIGN KEY(attempt_id,question_id) REFERENCES aptitude_attempt_questions(attempt_id,question_id) ON DELETE CASCADE)")
        conn.execute("CREATE TABLE IF NOT EXISTS aptitude_domain_scores(attempt_id BIGINT NOT NULL,domain VARCHAR(64) NOT NULL,total_questions TINYINT UNSIGNED NOT NULL,correct_answers TINYINT UNSIGNED NOT NULL,score DECIMAL(5,2) NOT NULL,PRIMARY KEY(attempt_id,domain),FOREIGN KEY(attempt_id) REFERENCES aptitude_attempts(attempt_id) ON DELETE CASCADE)")
        conn.execute("CREATE TABLE IF NOT EXISTS education_programs(program_id BIGINT PRIMARY KEY AUTO_INCREMENT,education_level VARCHAR(32) NOT NULL,program_name VARCHAR(128) NOT NULL,program_type ENUM('stream','degree') NOT NULL,UNIQUE KEY uq_education_program(education_level,program_name))")
        conn.execute('CREATE TABLE IF NOT EXISTS education_specializations(specialization_id BIGINT PRIMARY KEY AUTO_INCREMENT,program_id BIGINT NOT NULL,specialization_name VARCHAR(128) NOT NULL,UNIQUE KEY uq_education_specialization(program_id,specialization_name),FOREIGN KEY(program_id) REFERENCES education_programs(program_id) ON DELETE CASCADE)')
        conn.execute('CREATE TABLE IF NOT EXISTS education_subjects(subject_id BIGINT PRIMARY KEY AUTO_INCREMENT,subject_key VARCHAR(64) NOT NULL UNIQUE,subject_name VARCHAR(128) NOT NULL)')
        conn.execute('CREATE TABLE IF NOT EXISTS education_program_subjects(program_id BIGINT NOT NULL,subject_id BIGINT NOT NULL,PRIMARY KEY(program_id,subject_id),FOREIGN KEY(program_id) REFERENCES education_programs(program_id) ON DELETE CASCADE,FOREIGN KEY(subject_id) REFERENCES education_subjects(subject_id) ON DELETE RESTRICT)')
        conn.execute('CREATE TABLE IF NOT EXISTS education_specialization_subjects(specialization_id BIGINT NOT NULL,subject_id BIGINT NOT NULL,PRIMARY KEY(specialization_id,subject_id),FOREIGN KEY(specialization_id) REFERENCES education_specializations(specialization_id) ON DELETE CASCADE,FOREIGN KEY(subject_id) REFERENCES education_subjects(subject_id) ON DELETE RESTRICT)')
        conn.execute('CREATE TABLE IF NOT EXISTS recommendation_events(event_id BIGINT PRIMARY KEY AUTO_INCREMENT,student_id VARCHAR(64) NULL,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE SET NULL)')
        conn.execute('CREATE TABLE IF NOT EXISTS application_errors(error_id BIGINT PRIMARY KEY AUTO_INCREMENT,method VARCHAR(12) NOT NULL,endpoint VARCHAR(255) NOT NULL,status_code SMALLINT NOT NULL,error_type VARCHAR(80) NOT NULL,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
        conn.execute('CREATE TABLE IF NOT EXISTS admin_audit_logs(audit_id BIGINT PRIMARY KEY AUTO_INCREMENT,admin_user_id BIGINT NULL,action VARCHAR(80) NOT NULL,resource_type VARCHAR(80) NOT NULL,resource_id VARCHAR(128) NULL,details_json JSON NULL,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(admin_user_id) REFERENCES users(user_id) ON DELETE SET NULL)')
        conn.execute('CREATE TABLE IF NOT EXISTS recommendation_events(event_id BIGINT PRIMARY KEY AUTO_INCREMENT,student_id VARCHAR(64) NULL,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE SET NULL)')
        conn.execute('CREATE TABLE IF NOT EXISTS application_errors(error_id BIGINT PRIMARY KEY AUTO_INCREMENT,method VARCHAR(12) NOT NULL,endpoint VARCHAR(255) NOT NULL,status_code SMALLINT NOT NULL,error_type VARCHAR(80) NOT NULL,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
        conn.commit(); conn.close(); return
    conn=sqlite3.connect(DB_PATH); conn.row_factory=sqlite3.Row
    assessment_table=conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='assessments'").fetchone()
    if assessment_table:
        assessment_cols={r[1] for r in conn.execute('PRAGMA table_info(assessments)').fetchall()}
        if assessment_cols and 'assessment_type' not in assessment_cols:
            conn.close(); raise RuntimeError('Legacy assessments schema detected; setup stopped before DDL. A reviewed data-preserving migration is required.')
    conn.executescript('''PRAGMA foreign_keys=ON;
    CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, token TEXT UNIQUE, role TEXT NOT NULL DEFAULT 'student' CHECK(role IN ('student','admin')), is_active INTEGER NOT NULL DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS students(student_id TEXT PRIMARY KEY, user_id INTEGER UNIQUE, education_level TEXT NOT NULL, age INTEGER, gender TEXT, stream TEXT, degree TEXT, specialization TEXT, study_period TEXT, academic_performance REAL, academic_scale TEXT NOT NULL DEFAULT 'percentage', research_interests TEXT, career_preferences TEXT, academic_history TEXT, profile_updated_at TEXT, FOREIGN KEY(user_id) REFERENCES users(user_id));
    CREATE TABLE IF NOT EXISTS academic_records(student_id TEXT NOT NULL, subject_name TEXT NOT NULL, score REAL, PRIMARY KEY(student_id,subject_name), FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS assessments(student_id TEXT NOT NULL, assessment_type TEXT NOT NULL, feature_name TEXT NOT NULL, score REAL, PRIMARY KEY(student_id,assessment_type,feature_name), FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS student_skill_details(student_id TEXT NOT NULL,skill_key TEXT NOT NULL,normalized_name TEXT NOT NULL,display_name TEXT NOT NULL,category TEXT NOT NULL CHECK(category IN ('technical','employability')),applicability TEXT NOT NULL CHECK(applicability IN ('not_applicable','assessed')),proficiency REAL NULL CHECK(proficiency IS NULL OR proficiency BETWEEN 0 AND 100),source_context TEXT NULL,canonical_skill TEXT NULL,is_custom INTEGER NOT NULL DEFAULT 0 CHECK(is_custom IN (0,1)),PRIMARY KEY(student_id,skill_key),UNIQUE(student_id,normalized_name),FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS recommendations(student_id TEXT PRIMARY KEY, results_json TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(student_id) REFERENCES students(student_id));''')
    # Upgrade databases created by earlier CareerPath versions.
    if 'role' not in [r[1] for r in conn.execute('PRAGMA table_info(users)').fetchall()]: conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'student'")
    if 'is_active' not in [r[1] for r in conn.execute('PRAGMA table_info(users)').fetchall()]: conn.execute("ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
    if 'created_at' not in [r[1] for r in conn.execute('PRAGMA table_info(users)').fetchall()]: conn.execute("ALTER TABLE users ADD COLUMN created_at TEXT")
    if 'created_at' not in [r[1] for r in conn.execute('PRAGMA table_info(recommendations)').fetchall()]: conn.execute("ALTER TABLE recommendations ADD COLUMN created_at TEXT")
    student_cols=[r[1] for r in conn.execute('PRAGMA table_info(students)').fetchall()]
    for name,kind in [('age','INTEGER'),('gender','TEXT'),('stream','TEXT'),('degree','TEXT'),('specialization','TEXT'),('study_period','TEXT'),('academic_performance','REAL'),('academic_scale',"TEXT NOT NULL DEFAULT 'percentage'"),('research_interests','TEXT'),('career_preferences','TEXT'),('academic_history','TEXT')]:
        if name not in student_cols: conn.execute(f'ALTER TABLE students ADD COLUMN {name} {kind}')
    if 'profile_updated_at' not in student_cols: conn.execute('ALTER TABLE students ADD COLUMN profile_updated_at TEXT')
    assessment_cols=[r[1] for r in conn.execute('PRAGMA table_info(assessments)').fetchall()]
    if assessment_cols and 'assessment_type' not in assessment_cols:
        conn.execute('ALTER TABLE assessments RENAME TO assessments_legacy_json')
        conn.execute('CREATE TABLE assessments(student_id TEXT NOT NULL, assessment_type TEXT NOT NULL, feature_name TEXT NOT NULL, score REAL, PRIMARY KEY(student_id,assessment_type,feature_name), FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE)')
    conn.executescript('''CREATE TABLE IF NOT EXISTS aptitude_questions(question_id TEXT PRIMARY KEY,domain TEXT NOT NULL,difficulty TEXT NOT NULL,question_text TEXT NOT NULL,options_json TEXT NOT NULL,correct_option TEXT NOT NULL,explanation TEXT NOT NULL,education_levels_json TEXT NOT NULL,is_active INTEGER NOT NULL DEFAULT 1);
    CREATE TABLE IF NOT EXISTS aptitude_attempts(attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,student_id TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'in_progress' CHECK(status IN ('in_progress','completed')),started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,completed_at TEXT,overall_score REAL,FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS aptitude_attempt_questions(attempt_id INTEGER NOT NULL,question_id TEXT NOT NULL,question_order INTEGER NOT NULL,PRIMARY KEY(attempt_id,question_id),UNIQUE(attempt_id,question_order),FOREIGN KEY(attempt_id) REFERENCES aptitude_attempts(attempt_id) ON DELETE CASCADE,FOREIGN KEY(question_id) REFERENCES aptitude_questions(question_id));
    CREATE TABLE IF NOT EXISTS aptitude_responses(attempt_id INTEGER NOT NULL,question_id TEXT NOT NULL,selected_option TEXT NOT NULL,is_correct INTEGER NOT NULL,PRIMARY KEY(attempt_id,question_id),FOREIGN KEY(attempt_id,question_id) REFERENCES aptitude_attempt_questions(attempt_id,question_id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS aptitude_domain_scores(attempt_id INTEGER NOT NULL,domain TEXT NOT NULL,total_questions INTEGER NOT NULL,correct_answers INTEGER NOT NULL,score REAL NOT NULL,PRIMARY KEY(attempt_id,domain),FOREIGN KEY(attempt_id) REFERENCES aptitude_attempts(attempt_id) ON DELETE CASCADE);''')
    conn.executescript('''CREATE TABLE IF NOT EXISTS education_programs(program_id INTEGER PRIMARY KEY AUTOINCREMENT,education_level TEXT NOT NULL,program_name TEXT NOT NULL,program_type TEXT NOT NULL CHECK(program_type IN ('stream','degree')),UNIQUE(education_level,program_name));
    CREATE TABLE IF NOT EXISTS education_specializations(specialization_id INTEGER PRIMARY KEY AUTOINCREMENT,program_id INTEGER NOT NULL,specialization_name TEXT NOT NULL,UNIQUE(program_id,specialization_name),FOREIGN KEY(program_id) REFERENCES education_programs(program_id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS education_subjects(subject_id INTEGER PRIMARY KEY AUTOINCREMENT,subject_key TEXT NOT NULL UNIQUE,subject_name TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS education_program_subjects(program_id INTEGER NOT NULL,subject_id INTEGER NOT NULL,PRIMARY KEY(program_id,subject_id),FOREIGN KEY(program_id) REFERENCES education_programs(program_id) ON DELETE CASCADE,FOREIGN KEY(subject_id) REFERENCES education_subjects(subject_id) ON DELETE RESTRICT);
    CREATE TABLE IF NOT EXISTS education_specialization_subjects(specialization_id INTEGER NOT NULL,subject_id INTEGER NOT NULL,PRIMARY KEY(specialization_id,subject_id),FOREIGN KEY(specialization_id) REFERENCES education_specializations(specialization_id) ON DELETE CASCADE,FOREIGN KEY(subject_id) REFERENCES education_subjects(subject_id) ON DELETE RESTRICT);''')
    if 'is_active' not in [r[1] for r in conn.execute('PRAGMA table_info(aptitude_questions)').fetchall()]: conn.execute('ALTER TABLE aptitude_questions ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1')
    conn.executescript('''CREATE TABLE IF NOT EXISTS recommendation_events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,student_id TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE SET NULL);
    CREATE TABLE IF NOT EXISTS application_errors(error_id INTEGER PRIMARY KEY AUTOINCREMENT,method TEXT NOT NULL,endpoint TEXT NOT NULL,status_code INTEGER NOT NULL,error_type TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS admin_audit_logs(audit_id INTEGER PRIMARY KEY AUTOINCREMENT,admin_user_id INTEGER,action TEXT NOT NULL,resource_type TEXT NOT NULL,resource_id TEXT,details_json TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(admin_user_id) REFERENCES users(user_id) ON DELETE SET NULL);''')
    conn.commit(); conn.close()
def bootstrap_admin():
    email=os.environ.get('ADMIN_EMAIL','').strip().lower(); password=os.environ.get('ADMIN_PASSWORD','')
    if not email or len(password)<12: return
    conn=connect_db(); existing=conn.execute('SELECT user_id FROM users WHERE email=?',(email,)).fetchone()
    if not existing:
        salt=secrets.token_hex(16); hashed=salt+'$'+hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),180000).hex()
        conn.execute('INSERT INTO users(email,password_hash,token,role) VALUES(?,?,?,?)',(email,hashed,secrets.token_urlsafe(32),'admin')); conn.commit()
    conn.close()
@app.after_request
def record_api_error(response):
    if request.path.startswith('/api/') and response.status_code >= 400:
        try:
            db().execute('INSERT INTO application_errors(method,endpoint,status_code,error_type) VALUES(?,?,?,?)',(request.method,request.endpoint or 'unknown',response.status_code,'ClientError' if response.status_code<500 else 'ServerError'))
            db().commit()
        except Exception:
            # Error reporting must never replace the original API response.
            pass
    return response

def record_admin_action(action,resource_type,resource_id=None,details=None):
    token=request.headers.get('Authorization','').removeprefix('Bearer ').strip()
    admin=db().execute("SELECT user_id FROM users WHERE token=? AND role='admin' AND is_active=1",(token,)).fetchone() if token else None
    db().execute('INSERT INTO admin_audit_logs(admin_user_id,action,resource_type,resource_id,details_json) VALUES(?,?,?,?,?)',(admin['user_id'] if admin else None,action,resource_type,str(resource_id) if resource_id is not None else None,json.dumps(details or {})))
    db().commit()

def err(msg,status=400,code=None):
    body={'error':msg}
    if code: body['code']=code
    return jsonify(body),status
def valid_scores(values):
    return isinstance(values,dict) and all(isinstance(k,str) and 0<len(k)<=64 and (v is None or (type(v) in (int,float) and 0<=v<=100)) for k,v in values.items())
def valid_profile(profile):
    if not isinstance(profile,dict) or profile.get('education_level') not in ('10th','12th',"Bachelor's","Master's"): return False
    from backend.education_catalog import EDUCATION_CATALOG
    level=profile['education_level']; catalog=EDUCATION_CATALOG[level]
    stream=profile.get('stream','') or ''
    if stream not in ('',*catalog.get('streams',[])): return False
    degree=profile.get('degree','') or ''; specialization=profile.get('specialization','') or ''
    if level in ('10th','12th'):
        if degree or specialization: return False
    else:
        degrees=catalog.get('degrees',[])
        known_degree=degree in degrees
        # The UI sends the custom degree text with the explicit "Other" stream.
        if degree and not known_degree and (stream!='Other' or 'Other' not in degrees): return False
        if specialization and not degree: return False
        specialization_options=catalog.get('specializations',{}).get(degree if known_degree else 'Other',[])
        if specialization and specialization not in specialization_options:
            all_known_specializations={item for values in catalog.get('specializations',{}).values() for item in values}
            # Unknown text is allowed only for a course that exposes the catalog's
            # "Other" option; known specializations from another course are rejected.
            if 'Other' not in specialization_options or specialization in all_known_specializations: return False
    if any(not valid_scores(profile.get(key,{})) for key in ('subjects','aptitude','interests','technical','employability')): return False
    for key in ('degree','specialization','study_period','research_interests','career_preferences'):
        if key in profile and profile[key] is not None and (not isinstance(profile[key],str) or len(profile[key])>1000): return False
    performance=profile.get('academic_performance')
    scale=profile.get('academic_scale','percentage')
    if scale not in ('percentage','cgpa10'): return False
    if performance is not None and (type(performance) not in (int,float) or not 0<=performance<=(10 if scale=='cgpa10' else 100)): return False
    return profile.get('age') is None or (type(profile.get('age')) is int and 13<=profile['age']<=80)
def authorized(sid):
    token=bearer_token()
    return bool(token and db().execute("SELECT 1 FROM users u JOIN students s ON s.user_id=u.user_id WHERE s.student_id=? AND u.token=? AND u.role='student' AND u.is_active=1",(sid,token)).fetchone())
def bearer_token():
    value=request.headers.get('Authorization','')
    scheme,separator,token=value.partition(' ')
    return token.strip() if separator and scheme.lower()=='bearer' and token.strip() else ''
def recommendation_owner_error(sid):
    token=bearer_token()
    if not token: return err('A valid student bearer token is required',401)
    owner=db().execute("SELECT s.student_id FROM users u JOIN students s ON s.user_id=u.user_id WHERE u.token=? AND u.role='student' AND u.is_active=1",(token,)).fetchone()
    if not owner: return err('A valid student bearer token is required',401)
    if owner['student_id']!=sid: return err('The authenticated student cannot access another student’s recommendations',403)
    return None
def admin_authorized():
    token=request.headers.get('Authorization','').removeprefix('Bearer ').strip()
    return bool(token and db().execute("SELECT 1 FROM users WHERE token=? AND role='admin' AND is_active=1",(token,)).fetchone())
def admin_required(): return None if admin_authorized() else err('Admin bearer token required',403)
def student_profile(sid):
    row=db().execute('SELECT education_level,age,gender,stream,degree,specialization,study_period,academic_performance,academic_scale,research_interests,career_preferences,academic_history FROM students WHERE student_id=?',(sid,)).fetchone()
    if not row: return None
    history=unpack(row['academic_history']) if row['academic_history'] else empty_academic_history(row['education_level'])
    p={'education_level':row['education_level'],'age':row['age'],'gender':row['gender'],'stream':row['stream'],'degree':row['degree'],'specialization':row['specialization'],'study_period':row['study_period'],'academic_performance':float(row['academic_performance']) if row['academic_performance'] is not None else None,'academic_scale':row['academic_scale'],'research_interests':row['research_interests'],'career_preferences':row['career_preferences'],'academic_history':history,'subjects':{}}
    for score in db().execute('SELECT subject_name,score FROM academic_records WHERE student_id=?',(sid,)).fetchall(): p['subjects'][score['subject_name']]=float(score['score']) if score['score'] is not None else None
    p.update({'aptitude':{},'interests':{},'technical':{},'employability':{},'skill_assessments':[]})
    groups={'interests':'interests','technical':'technical','employability':'employability'}
    for score in db().execute('SELECT assessment_type,feature_name,score FROM assessments WHERE student_id=?',(sid,)).fetchall():
        group=groups.get(score['assessment_type'])
        if group: p[group][score['feature_name']]=float(score['score']) if score['score'] is not None else None
    for skill in db().execute('SELECT skill_key,normalized_name,display_name,category,applicability,proficiency,source_context,canonical_skill,is_custom FROM student_skill_details WHERE student_id=?',(sid,)).fetchall():
        item=dict(skill)
        item['proficiency']=float(item['proficiency']) if item['proficiency'] is not None else None
        item['is_custom']=bool(item['is_custom'])
        p['skill_assessments'].append(item)
        if item['canonical_skill'] and not item['is_custom']:
            if item['applicability']=='not_applicable':
                p[item['category']].pop(item['canonical_skill'],None)
            elif item['applicability']=='assessed' and item['proficiency'] is not None:
                p[item['category']].setdefault(item['canonical_skill'],item['proficiency'])
    # Only backend-scored completed attempts are authoritative aptitude results.
    scored=db().execute('SELECT ds.domain,ds.score FROM aptitude_domain_scores ds JOIN aptitude_attempts a ON a.attempt_id=ds.attempt_id WHERE a.attempt_id=(SELECT MAX(a2.attempt_id) FROM aptitude_attempts a2 WHERE a2.student_id=? AND a2.status=?)',(sid,'completed')).fetchall()
    p['aptitude']={row['domain']:float(row['score']) for row in scored}
    return p
@app.post('/api/register')
def register():
    data=request.get_json(silent=True) or {}; email=str(data.get('email','')).strip().lower(); password=data.get('password','')
    if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',email): return err('A valid email is required')
    if not isinstance(password,str) or len(password)<8: return err('Password must contain at least 8 characters')
    salt=secrets.token_hex(16); hashed=salt+'$'+hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),180000).hex(); token=secrets.token_urlsafe(32)
    try:
        cur=db().execute('INSERT INTO users(email,password_hash,token) VALUES(?,?,?)',(email,hashed,token)); sid='STU'+str(cur.lastrowid).zfill(6)
        db().execute('INSERT INTO students(student_id,user_id,education_level,stream) VALUES(?,?,?,?)',(sid,cur.lastrowid,'10th','')); db().commit()
    except Exception as ex:
        if isinstance(ex,sqlite3.IntegrityError): return err('Email is already registered',409)
        if USE_MYSQL:
            import pymysql
            if isinstance(ex,pymysql.err.IntegrityError): return err('Email is already registered',409)
        raise
    return jsonify(student_id=sid,token=token,role='student',email=email),201
@app.get('/api/auth/me')
def authenticated_user():
    token=request.headers.get('Authorization','').removeprefix('Bearer ').strip()
    row=db().execute('SELECT user_id,email,role FROM users WHERE token=? AND is_active=1',(token,)).fetchone() if token else None
    if not row: return err('Valid bearer token required',401)
    student=db().execute('SELECT student_id FROM students WHERE user_id=?',(row['user_id'],)).fetchone()
    return jsonify(email=row['email'],role=row['role'],student_id=student['student_id'] if student else None)
@app.post('/api/auth/logout')
def authenticated_logout():
    token=request.headers.get('Authorization','').removeprefix('Bearer ').strip()
    if not token: return err('Valid bearer token required',401)
    current=db().execute('SELECT user_id FROM users WHERE token=? AND is_active=1',(token,)).fetchone()
    if not current: return err('Valid bearer token required',401)
    db().execute('UPDATE users SET token=NULL WHERE user_id=?',(current['user_id'],)); db().commit()
    return jsonify(logged_out=True)
@app.post('/api/login')
def login():
    data=request.get_json(silent=True) or {}; row=db().execute('SELECT * FROM users WHERE email=?',(str(data.get('email','')).strip().lower(),)).fetchone()
    if not row or not row['is_active'] or '$' not in row['password_hash']: return err('Invalid credentials',401)
    salt,expected=row['password_hash'].split('$',1); actual=hashlib.pbkdf2_hmac('sha256',str(data.get('password','')).encode(),salt.encode(),180000).hex()
    if not hmac.compare_digest(expected,actual): return err('Invalid credentials',401)
    token=row['token']
    if not token:
        token=secrets.token_urlsafe(32)
        db().execute('UPDATE users SET token=? WHERE user_id=?',(token,row['user_id'])); db().commit()
    sid_row=db().execute('SELECT student_id FROM students WHERE user_id=?',(row['user_id'],)).fetchone()
    return jsonify(student_id=sid_row['student_id'] if sid_row else None,token=token,role=row['role'],email=row['email'])
@app.post('/api/student/profile')
def save_profile():
    data=request.get_json(silent=True) or {}; sid=data.get('student_id'); level=data.get('education_level')
    if not sid or level not in ('10th','12th',"Bachelor's","Master's"): return err('student_id and a supported education_level are required')
    if not authorized(sid): return err('Valid bearer token for this student is required',401)
    academic_history,history_error=validate_academic_history(level,data.get('academic_history'),data.get('stream',''))
    if history_error: return err(history_error)
    profile={'education_level':level,'stream':data.get('stream',''),'age':data.get('age')}
    for key in ('degree','specialization','study_period','research_interests','career_preferences'):
        value=data.get(key,'')
        if value is not None and (not isinstance(value,str) or len(value)>1000): return err(f'{key} must be text no longer than 1000 characters')
        profile[key]=value
    performance=data.get('academic_performance')
    scale=data.get('academic_scale','percentage')
    if scale not in ('percentage','cgpa10'): return err('academic_scale must be percentage or cgpa10')
    max_performance=10 if scale=='cgpa10' else 100
    if performance is not None and (type(performance) not in (int,float) or not 0<=performance<=max_performance): return err(f'academic_performance must be between 0 and {max_performance} for this scale')
    profile['academic_performance']=performance
    profile['academic_scale']=scale
    subjects=data.get('subjects',{})
    if not valid_scores(subjects): return err('Subject scores must be 0-100 or null')
    profile['subjects']=subjects
    if not valid_profile(profile): return err('Profile scores must be 0-100 or null, and stream/age must be valid')
    cur=db().execute('UPDATE students SET education_level=?,stream=?,age=?,degree=?,specialization=?,study_period=?,academic_performance=?,academic_scale=?,research_interests=?,career_preferences=?,academic_history=?,profile_updated_at=CURRENT_TIMESTAMP WHERE student_id=?',(level,profile['stream'],profile.get('age'),profile['degree'],profile['specialization'],profile['study_period'],performance,scale,profile['research_interests'],profile['career_preferences'],json.dumps(academic_history,ensure_ascii=False),sid))
    if cur.rowcount==0: return err('Student not found',404)
    db().execute('DELETE FROM academic_records WHERE student_id=?',(sid,))
    for name,value in subjects.items(): db().execute('INSERT INTO academic_records(student_id,subject_name,score) VALUES(?,?,?)',(sid,name,value))
    db().commit(); return jsonify(saved=True)
@app.get('/api/student/profile')
def get_profile():
    sid=request.args.get('student_id','')
    if not sid or not authorized(sid): return err('Valid bearer token for this student is required',401)
    profile=student_profile(sid)
    return jsonify(profile=profile) if profile else err('Student not found',404)
def save_assessment(kind):
    data=request.get_json(silent=True) or {}; sid=data.get('student_id'); values=data.get('scores')
    if not sid or not valid_scores(values): return err('student_id and numeric scores from 0 to 100 are required')
    if not authorized(sid): return err('Valid bearer token for this student is required',401)
    if not db().execute('SELECT 1 FROM students WHERE student_id=?',(sid,)).fetchone(): return err('Student not found',404)
    for feature,value in values.items():
        sql='INSERT INTO assessments(student_id,assessment_type,feature_name,score) VALUES(?,?,?,?) ON DUPLICATE KEY UPDATE score=VALUES(score)' if USE_MYSQL else 'INSERT INTO assessments(student_id,assessment_type,feature_name,score) VALUES(?,?,?,?) ON CONFLICT(student_id,assessment_type,feature_name) DO UPDATE SET score=excluded.score'
        db().execute(sql,(sid,kind,feature,value))
    db().commit(); return jsonify(saved=True)
@app.post('/api/assessment/aptitude')
def aptitude():
    data=request.get_json(silent=True) or {}; sid=data.get('student_id'); values=data.get('scores')
    if not sid or not authorized(sid): return err('Valid bearer token for this student is required',401)
    if not valid_scores(values): return err('scores must be a valid score map')
    rows=db().execute('SELECT ds.domain,ds.score FROM aptitude_domain_scores ds JOIN aptitude_attempts a ON a.attempt_id=ds.attempt_id WHERE a.attempt_id=(SELECT MAX(a2.attempt_id) FROM aptitude_attempts a2 WHERE a2.student_id=? AND a2.status=?)',(sid,'completed')).fetchall()
    authoritative={r['domain']:float(r['score']) for r in rows}
    if not authoritative or {k:float(v) for k,v in values.items() if v is not None}!=authoritative: return err('Aptitude scores must match the latest completed server-scored attempt')
    return jsonify(saved=True,source='completed_assessment_attempt')

@app.get('/api/education/catalog')
def education_catalog():
    from copy import deepcopy
    from backend.education_catalog import EDUCATION_CATALOG
    # The catalog is small, curated configuration. Keep its API independent of
    # legacy seeded rows, which may contain stale or cross-degree subject links.
    return jsonify(levels=deepcopy(EDUCATION_CATALOG))

@app.get('/api/aptitude/questions')
def aptitude_questions():
    from backend.aptitude_bank import public_question
    level=request.args.get('education_level','')
    if level not in ('10th','12th',"Bachelor's","Master's"): return err('A supported education_level query parameter is required')
    rows=db().execute('SELECT question_id,domain,difficulty,question_text,options_json,education_levels_json FROM aptitude_questions WHERE is_active=1 ORDER BY question_id').fetchall()
    questions=[{'question_id':r['question_id'],'domain':r['domain'],'difficulty':r['difficulty'],'question_text':r['question_text'],'options':unpack(r['options_json']),'education_levels':unpack(r['education_levels_json'])} for r in rows]
    selected=[public_question(q) for q in questions if level in q['education_levels']]
    return jsonify(assessment_notice='Project-level aptitude exercise; not a professionally validated psychometric test.',question_count=len(selected),questions=selected)

def validate_question(data):
    from backend.aptitude_bank import DOMAINS
    levels=('10th','12th',"Bachelor's","Master's")
    if not isinstance(data.get('domain'),str) or data['domain'] not in DOMAINS: return 'A supported aptitude domain is required'
    if data.get('difficulty') not in ('Foundational','Standard'): return 'difficulty must be Foundational or Standard'
    if not isinstance(data.get('question_text'),str) or not data['question_text'].strip() or len(data['question_text'])>1200: return 'question_text must be 1-1200 characters'
    options=data.get('options')
    if not isinstance(options,list) or not 2<=len(options)<=6: return 'Provide 2-6 answer options'
    ids=[]
    for option in options:
        if not isinstance(option,dict) or not isinstance(option.get('id'),str) or not re.fullmatch(r'[A-F]',option['id']): return 'Each option needs a unique ID from A to F'
        if not isinstance(option.get('text'),str) or not option['text'].strip() or len(option['text'])>500: return 'Each option needs 1-500 characters of text'
        ids.append(option['id'])
    if len(ids)!=len(set(ids)): return 'Answer option IDs must be unique'
    if data.get('correct_option') not in ids: return 'correct_option must match one of the supplied option IDs'
    if not isinstance(data.get('explanation'),str) or not data['explanation'].strip() or len(data['explanation'])>2000: return 'explanation must be 1-2000 characters'
    education_levels=data.get('education_levels')
    if not isinstance(education_levels,list) or not education_levels or not set(education_levels).issubset(levels): return 'Select one or more supported education levels'
    return None

def admin_question_list():
    rows=db().execute('SELECT question_id,domain,difficulty,question_text,options_json,correct_option,explanation,education_levels_json,is_active FROM aptitude_questions ORDER BY question_id').fetchall()
    return [{'question_id':r['question_id'],'domain':r['domain'],'difficulty':r['difficulty'],'question_text':r['question_text'],'options':unpack(r['options_json']),'correct_option':r['correct_option'],'explanation':r['explanation'],'education_levels':unpack(r['education_levels_json']),'is_active':bool(r['is_active'])} for r in rows]

@app.get('/api/admin/aptitude-questions')
def admin_get_aptitude_questions():
    denied=admin_required()
    if denied: return denied
    return jsonify(questions=admin_question_list())

@app.post('/api/admin/aptitude-questions')
def admin_create_aptitude_question():
    denied=admin_required()
    if denied: return denied
    data=request.get_json(silent=True) or {}; validation=validate_question(data)
    if validation: return err(validation)
    question_id=data.get('question_id') or 'AUX'+secrets.token_hex(4).upper()
    if not isinstance(question_id,str) or not re.fullmatch(r'[A-Z0-9_-]{3,16}',question_id): return err('question_id must be 3-16 uppercase letters, digits, _ or -')
    if db().execute('SELECT 1 FROM aptitude_questions WHERE question_id=?',(question_id,)).fetchone(): return err('question_id already exists',409)
    db().execute('INSERT INTO aptitude_questions(question_id,domain,difficulty,question_text,options_json,correct_option,explanation,education_levels_json,is_active) VALUES(?,?,?,?,?,?,?,?,1)',(question_id,data['domain'],data['difficulty'],data['question_text'].strip(),json.dumps(data['options']),data['correct_option'],data['explanation'].strip(),json.dumps(data['education_levels'])))
    db().commit(); record_admin_action('create_aptitude_question','aptitude_question',question_id,{'domain':data['domain'],'difficulty':data['difficulty']})
    return jsonify(created=True,question=next(q for q in admin_question_list() if q['question_id']==question_id)),201

@app.patch('/api/admin/aptitude-questions/<question_id>')
def admin_update_aptitude_question(question_id):
    denied=admin_required()
    if denied: return denied
    allowed={'domain','difficulty','question_text','options','correct_option','explanation','education_levels','is_active'}
    data=request.get_json(silent=True) or {}
    if set(data)-allowed: return err('Unsupported aptitude-question fields')
    current=next((q for q in admin_question_list() if q['question_id']==question_id),None)
    if current is None: return err('Question not found',404)
    merged={**current,**data}; validation=validate_question(merged)
    if validation: return err(validation)
    if 'is_active' in data and type(data['is_active']) is not bool: return err('is_active must be true or false')
    db().execute('UPDATE aptitude_questions SET domain=?,difficulty=?,question_text=?,options_json=?,correct_option=?,explanation=?,education_levels_json=?,is_active=? WHERE question_id=?',(merged['domain'],merged['difficulty'],merged['question_text'].strip(),json.dumps(merged['options']),merged['correct_option'],merged['explanation'].strip(),json.dumps(merged['education_levels']),int(merged['is_active']),question_id))
    db().commit(); record_admin_action('update_aptitude_question','aptitude_question',question_id,{'domain':merged['domain'],'is_active':merged['is_active']})
    return jsonify(updated=True,question=next(q for q in admin_question_list() if q['question_id']==question_id))

@app.delete('/api/admin/aptitude-questions/<question_id>')
def admin_deactivate_aptitude_question(question_id):
    denied=admin_required()
    if denied: return denied
    cur=db().execute('UPDATE aptitude_questions SET is_active=0 WHERE question_id=?',(question_id,))
    if not cur.rowcount: return err('Question not found',404)
    db().commit(); record_admin_action('deactivate_aptitude_question','aptitude_question',question_id)
    return jsonify(deactivated=True)

@app.post('/api/aptitude/attempts')
def create_aptitude_attempt():
    from backend.aptitude_bank import public_question
    data=request.get_json(silent=True) or {}; sid=data.get('student_id'); level=data.get('education_level')
    if level not in ('10th','12th',"Bachelor's","Master's"): return err('A supported education_level is required')
    if not sid or not authorized(sid): return err('A valid student bearer token is required to start an assessment',401)
    profile=db().execute('SELECT education_level FROM students WHERE student_id=?',(sid,)).fetchone()
    if not profile: return err('Student not found',404)
    if profile['education_level']!=level: return err('Save the current education level before starting the aptitude assessment')
    import random
    rows=db().execute('SELECT question_id,domain,difficulty,question_text,options_json,education_levels_json,correct_option,explanation FROM aptitude_questions WHERE is_active=1 ORDER BY question_id').fetchall()
    selected=[{'question_id':r['question_id'],'domain':r['domain'],'difficulty':r['difficulty'],'question_text':r['question_text'],'options':unpack(r['options_json']),'education_levels':unpack(r['education_levels_json']),'correct_option':r['correct_option'],'explanation':r['explanation']} for r in rows if level in unpack(r['education_levels_json'])]
    if not selected: return err('No active aptitude questions are configured for this education level. No attempt was created.',409,'APTITUDE_QUESTION_BANK_EMPTY')
    random.SystemRandom().shuffle(selected)
    cur=db().execute('INSERT INTO aptitude_attempts(student_id,status) VALUES(?,?)',(sid,'in_progress')); attempt_id=cur.lastrowid
    for order,q in enumerate(selected,1): db().execute('INSERT INTO aptitude_attempt_questions(attempt_id,question_id,question_order) VALUES(?,?,?)',(attempt_id,q['question_id'],order))
    db().commit()
    return jsonify(attempt_id=attempt_id,student_id=sid,started_at=db().execute('SELECT started_at FROM aptitude_attempts WHERE attempt_id=?',(attempt_id,)).fetchone()['started_at'],assessment_notice='Project-level aptitude exercise; not a professionally validated psychometric test.',questions=[public_question(q) for q in selected]),201

def aptitude_attempt_result(attempt_id, sid):
    attempt=db().execute('SELECT attempt_id,status,started_at,completed_at,overall_score FROM aptitude_attempts WHERE attempt_id=? AND student_id=?',(attempt_id,sid)).fetchone()
    if not attempt: return None
    domains=db().execute('SELECT domain,total_questions,correct_answers,score FROM aptitude_domain_scores WHERE attempt_id=? ORDER BY domain',(attempt_id,)).fetchall()
    responses=db().execute('SELECT q.question_id,q.domain,q.question_text,q.options_json,q.correct_option,q.explanation,r.selected_option,r.is_correct FROM aptitude_responses r JOIN aptitude_questions q ON q.question_id=r.question_id WHERE r.attempt_id=? ORDER BY q.question_id',(attempt_id,)).fetchall()
    return {'attempt_id':attempt_id,'status':attempt['status'],'started_at':attempt['started_at'],'completed_at':attempt['completed_at'],'overall_score':float(attempt['overall_score']) if attempt['overall_score'] is not None else None,'domains':[{'domain':d['domain'],'total_questions':d['total_questions'],'correct_answers':d['correct_answers'],'score':float(d['score'])} for d in domains],'responses':[{'question_id':r['question_id'],'domain':r['domain'],'question_text':r['question_text'],'options':unpack(r['options_json']),'selected_option':r['selected_option'],'correct_option':r['correct_option'],'is_correct':bool(r['is_correct']),'explanation':r['explanation']} for r in responses]}

@app.get('/api/aptitude/attempts/<int:attempt_id>')
def get_aptitude_attempt(attempt_id):
    sid=request.args.get('student_id','')
    if not sid or not authorized(sid): return err('Valid student bearer token is required',401)
    result=aptitude_attempt_result(attempt_id,sid)
    if not result: return err('Assessment attempt not found',404)
    if result['status']!='completed': return jsonify(attempt={k:v for k,v in result.items() if k not in ('domains','responses','overall_score')})
    return jsonify(attempt=result)

@app.get('/api/aptitude/history')
def aptitude_history():
    sid=request.args.get('student_id','')
    if not sid or not authorized(sid): return err('Valid student bearer token is required',401)
    rows=db().execute('SELECT attempt_id,status,started_at,completed_at,overall_score FROM aptitude_attempts WHERE student_id=? ORDER BY attempt_id DESC',(sid,)).fetchall()
    return jsonify(attempts=[{'attempt_id':r['attempt_id'],'status':r['status'],'started_at':r['started_at'],'completed_at':r['completed_at'],'overall_score':float(r['overall_score']) if r['overall_score'] is not None else None} for r in rows])

@app.post('/api/aptitude/attempts/<int:attempt_id>/submit')
def submit_aptitude_attempt(attempt_id):
    from backend.aptitude_bank import DOMAINS
    data=request.get_json(silent=True) or {}; sid=data.get('student_id'); answers=data.get('answers')
    if not sid or not authorized(sid): return err('Valid student bearer token is required',401)
    if not isinstance(answers,dict): return err('answers must map question IDs to option IDs')
    attempt=db().execute('SELECT status FROM aptitude_attempts WHERE attempt_id=? AND student_id=?',(attempt_id,sid)).fetchone()
    if not attempt: return err('Assessment attempt not found',404)
    if attempt['status']!='in_progress': return err('This assessment attempt has already been submitted',409)
    rows=db().execute('SELECT q.question_id,q.domain,q.correct_option FROM aptitude_attempt_questions aq JOIN aptitude_questions q ON q.question_id=aq.question_id WHERE aq.attempt_id=?',(attempt_id,)).fetchall()
    expected={r['question_id']:r for r in rows}
    if set(answers)!=set(expected): return err('Answer every question in this attempt exactly once before submitting')
    for question_id,answer in answers.items():
        valid_options={o['id'] for o in unpack(db().execute('SELECT options_json FROM aptitude_questions WHERE question_id=?',(question_id,)).fetchone()['options_json'])}
        if answer not in valid_options: return err(f'Invalid option for {question_id}')
    total=len(rows); correct=0; counts={domain:{'total':0,'correct':0} for domain in DOMAINS}
    for question_id,r in expected.items():
        is_correct=answers[question_id]==r['correct_option']; correct+=int(is_correct); counts[r['domain']]['total']+=1; counts[r['domain']]['correct']+=int(is_correct)
        db().execute('INSERT INTO aptitude_responses(attempt_id,question_id,selected_option,is_correct) VALUES(?,?,?,?)',(attempt_id,question_id,answers[question_id],int(is_correct)))
    for domain,count in counts.items():
        if count['total']:
            score=round(100*count['correct']/count['total'],2)
            db().execute('INSERT INTO aptitude_domain_scores(attempt_id,domain,total_questions,correct_answers,score) VALUES(?,?,?,?,?)',(attempt_id,domain,count['total'],count['correct'],score))
            sql='INSERT INTO assessments(student_id,assessment_type,feature_name,score) VALUES(?,?,?,?) ON DUPLICATE KEY UPDATE score=VALUES(score)' if USE_MYSQL else 'INSERT INTO assessments(student_id,assessment_type,feature_name,score) VALUES(?,?,?,?) ON CONFLICT(student_id,assessment_type,feature_name) DO UPDATE SET score=excluded.score'
            db().execute(sql,(sid,'aptitude',domain,score))
    overall=round(100*correct/total,2) if total else None
    db().execute('UPDATE aptitude_attempts SET status=?,completed_at=CURRENT_TIMESTAMP,overall_score=? WHERE attempt_id=? AND student_id=?',('completed',overall,attempt_id,sid)); db().commit()
    return jsonify(attempt=aptitude_attempt_result(attempt_id,sid))

@app.post('/api/assessment/interests')
def interests(): return save_assessment('interests')
@app.post('/api/assessment/skills')
def skills():
    data=request.get_json(silent=True) or {}; sid=data.get('student_id'); tech=data.get('technical',{}); emp=data.get('employability',{})
    if not sid or not valid_scores(tech) or not valid_scores(emp): return err('student_id and numeric technical/employability scores from 0 to 100 are required')
    if not authorized(sid): return err('Valid bearer token for this student is required',401)
    if not db().execute('SELECT 1 FROM students WHERE student_id=?',(sid,)).fetchone(): return err('Student not found',404)
    details=data.get('skill_assessments',None)
    if details is not None:
        from backend.skill_catalog import canonical_skill, normalize_skill_name, SKILLS
        if not isinstance(details,list) or len(details)>100: return err('skill_assessments must be a list with at most 100 entries')
        seen_keys=set(); seen_names=set(); seen_canonical=set(); cleaned=[]
        allowed_contexts={'course','self_learning','certification','internship','work_experience','other'}
        for item in details:
            if not isinstance(item,dict): return err('Each skill assessment must be an object')
            display=str(item.get('display_name') or '').strip()
            category=item.get('category'); applicability=item.get('applicability'); is_custom=item.get('is_custom') is True
            if not display or len(display)>255 or category not in ('technical','employability'):
                return err('Skill name or category is invalid')
            normalized=normalize_skill_name(display)
            if not normalized or len(normalized)>128 or normalized in seen_names: return err('Duplicate or invalid skill name')
            seen_names.add(normalized)
            canonical=canonical_skill(display)
            submitted_canonical=item.get('canonical_skill')
            if submitted_canonical is not None and submitted_canonical!=canonical:
                return err('Skill canonical mapping does not match the standardized catalogue')
            if is_custom:
                skill_key='custom:'+re.sub(r'[^a-z0-9]+','_',normalized).strip('_')
                context=item.get('source_context') or None
                score=item.get('proficiency')
                if applicability!='assessed' or type(score) not in (int,float) or not 0<=score<=100:
                    return err('Custom skills require an assessed proficiency from 0 to 100')
                if context is not None and (not isinstance(context,str) or context not in allowed_contexts): return err('Custom skill source/context is invalid')
                if canonical:
                    if category != SKILLS[canonical][1]: return err('A recognized custom skill must use its catalogue category')
                    if canonical in tech or canonical in emp: return err('This skill is already assessed in the predefined catalogue')
                    if canonical in seen_canonical: return err('Duplicate standardized skill mapping')
                    seen_canonical.add(canonical)
                cleaned.append((skill_key,normalized,display,category,'assessed',score,context,canonical,1))
            else:
                skill_key=str(item.get('skill_key') or '')
                if applicability!='not_applicable' or not skill_key or len(skill_key)>128:
                    return err('Predefined skill state must be Not applicable or omitted as unassessed')
                if not canonical or skill_key!=canonical: return err('Not-applicable state must reference a standardized catalogue skill')
                if category!=SKILLS[canonical][1]: return err('Predefined skill category does not match the catalogue')
                if canonical and (canonical in tech or canonical in emp): return err('A not-applicable skill cannot also have a proficiency score')
                if canonical and canonical in seen_canonical: return err('Duplicate standardized skill mapping')
                if canonical: seen_canonical.add(canonical)
                cleaned.append((skill_key,normalized,display,category,'not_applicable',None,None,canonical,0))
            if skill_key in seen_keys: return err('Duplicate skill entry')
            seen_keys.add(skill_key)
    for kind,values in [('technical',tech),('employability',emp)]:
        db().execute('DELETE FROM assessments WHERE student_id=? AND assessment_type=?',(sid,kind))
        for feature,value in values.items():
            db().execute('INSERT INTO assessments(student_id,assessment_type,feature_name,score) VALUES(?,?,?,?)',(sid,kind,feature,value))
    if details is not None:
        db().execute('DELETE FROM student_skill_details WHERE student_id=?',(sid,))
        for item in cleaned:
            db().execute('INSERT INTO student_skill_details(student_id,skill_key,normalized_name,display_name,category,applicability,proficiency,source_context,canonical_skill,is_custom) VALUES(?,?,?,?,?,?,?,?,?,?)',(sid,*item))
    db().commit(); return jsonify(saved=True)

@app.get('/api/education/skills')
def education_skills():
    from backend.skill_catalog import education_skill_catalog
    profile={key:request.args.get(key,'') for key in ('education_level','stream','degree','specialization')}
    if profile['education_level'] not in ('10th','12th',"Bachelor's","Master's"):
        return err('A supported education_level is required')
    return jsonify(catalog=education_skill_catalog(profile))
@app.post('/api/recommend')
def create_recommendations():
    data=request.get_json(silent=True) or {}; sid=data.get('student_id')
    if not sid: return err('A valid student bearer token and student_id are required',401)
    ownership_error=recommendation_owner_error(sid)
    if ownership_error: return ownership_error
    p=student_profile(sid)
    if not isinstance(p,dict): return err('Student profile was not found',404)
    if not valid_profile(p): return err('Profile has invalid education level, stream, age, or scores')
    top_n=data.get('top_n',5)
    if type(top_n) is not int or not 1<=top_n<=5: return err('top_n must be an integer from 1 to 5')
    results,catalog_fingerprint=recommend_with_catalog_fingerprint(p,top_n)
    input_fingerprint=recommendation_input_fingerprint(p)
    from backend.ml.predict import model_artifact_identity
    model_identity=getattr(results,'model_identity',None)
    model_status=getattr(results,'model_status','unavailable')
    model_failure_reason=getattr(results,'model_failure_reason',None)
    model_validation_status=getattr(results,'model_validation_status',None)
    model_missing_metadata=list(getattr(results,'model_missing_metadata',()))
    conn=db()
    try:
        # Serialize snapshot appends across processes. SQLite's write lock and
        # MySQL's student-row lock protect the read/append/write sequence.
        if USE_MYSQL:
            conn.execute('SELECT student_id FROM students WHERE student_id=? FOR UPDATE',(sid,)).fetchone()
        else:
            conn.execute('BEGIN IMMEDIATE')
        row=conn.execute('SELECT results_json FROM recommendations WHERE student_id=?',(sid,)).fetchone()
        history={"format":FORMAT,"format_version":FORMAT_VERSION,"snapshots":[],"legacy_records":[]}
        if row:
            try:
                history,was_legacy=decode_history(row['results_json'])
                if was_legacy:
                    pass
            except (ValueError,TypeError,json.JSONDecodeError):
                # Preserve malformed legacy bytes as opaque history; never
                # overwrite user data merely because it predates this format.
                raw=row['results_json']
                history['legacy_records'].append(raw.decode('utf-8','replace') if isinstance(raw,bytes) else str(raw))
        snapshot=new_snapshot(input_fingerprint,catalog_fingerprint,results,model_identity)
        history['snapshots'].append(snapshot)
        db().execute('INSERT INTO recommendation_events(student_id) VALUES(?)',(sid,))
        sql='INSERT INTO recommendations(student_id,results_json) VALUES(?,?) ON DUPLICATE KEY UPDATE results_json=VALUES(results_json)' if USE_MYSQL else 'INSERT INTO recommendations(student_id,results_json) VALUES(?,?) ON CONFLICT(student_id) DO UPDATE SET results_json=excluded.results_json'
        db().execute(sql,(sid,encode_history(history)))
        current_profile=student_profile(sid)
        current_input=recommendation_input_fingerprint(current_profile) if current_profile else None
        current_catalog=_active_catalog_fingerprint()
        current_model=model_artifact_identity(p.get('education_level','10th'))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    freshness='current' if (model_identity and model_identity==current_model and current_input==input_fingerprint and current_catalog==catalog_fingerprint) else 'unverified' if not model_identity or not current_model else 'stale'
    return jsonify(student_id=sid,recommendations=results,freshness=freshness,
                   model_status=model_status,model_failure_reason=model_failure_reason,
                   model_validation_status=model_validation_status,
                   model_metadata_unverified=model_missing_metadata,
                   snapshot={k:snapshot[k] for k in ('snapshot_id','created_at','input_version','input_fingerprint','catalog_fingerprint','model_identity')})
@app.get('/api/recommendations')
def get_recommendations():
    sid=request.args.get('student_id')
    if not sid: return err('A valid student bearer token and student_id are required',401)
    ownership_error=recommendation_owner_error(sid)
    if ownership_error: return ownership_error
    row=db().execute('SELECT results_json FROM recommendations WHERE student_id=?',(sid,)).fetchone()
    if not row: return jsonify(freshness='none',recommendations=[])
    try:
        history,legacy_only=decode_history(row['results_json'])
    except (ValueError,TypeError,json.JSONDecodeError):
        return jsonify(freshness='unverified',recommendations=[],message='Saved recommendations could not be verified.')
    profile=student_profile(sid)
    current_input=recommendation_input_fingerprint(profile) if profile else None
    current_catalog=_active_catalog_fingerprint()
    from backend.ml.predict import model_artifact_identity
    current_model=model_artifact_identity(profile.get('education_level','10th')) if profile else None
    snapshot=select_current_snapshot(history,current_input,current_catalog,current_model) if current_input else None
    if snapshot:
        metadata={k:snapshot[k] for k in ('snapshot_id','created_at','input_version','input_fingerprint','catalog_fingerprint','model_identity')}
        return jsonify(freshness='current',snapshot=metadata,recommendations=snapshot['recommendations'])
    if history['snapshots'] and (not current_model or any(not isinstance(item.get('model_identity'),str) or not item.get('model_identity') for item in history['snapshots'])):
        return jsonify(freshness='unverified',recommendations=[],message='Saved recommendations do not have verifiable model lineage.')
    if not history['snapshots'] and history['legacy_records']:
        return jsonify(freshness='unverified',recommendations=[],message='Saved recommendations predate freshness verification.')
    if history['snapshots']:
        return jsonify(freshness='stale',recommendations=[],message='Saved recommendations do not match the current profile or catalog.')
    return jsonify(freshness='unverified',recommendations=[],message='Saved recommendations could not be verified.')

def _active_catalog_fingerprint():
    from backend.services.recommendation_engine import KB,METADATA
    from backend.services.catalog_releases import load_active_catalog
    return load_active_catalog(KB,METADATA).fingerprint
@app.get('/api/career/<career_id>')
def get_career(career_id):
    row=career_detail(career_id)
    return jsonify(career=row) if row else err('Career not found',404)
def latest(sid):
    row=db().execute('SELECT results_json FROM recommendations WHERE student_id=?',(sid,)).fetchone()
    if not row: return None
    try: history,_=decode_history(row['results_json'])
    except (ValueError,TypeError,json.JSONDecodeError): return None
    profile=student_profile(sid)
    if not profile: return None
    from backend.ml.predict import model_artifact_identity
    snapshot=select_current_snapshot(history,recommendation_input_fingerprint(profile),_active_catalog_fingerprint(),model_artifact_identity(profile.get('education_level','10th')))
    return snapshot['recommendations'] if snapshot else None
@app.get('/api/skill-gap')
def get_gaps():
    sid=request.args.get('student_id','')
    if not authorized(sid): return err('Valid bearer token for this student is required',401)
    results=latest(sid)
    return jsonify(skill_gaps={r['career_name']:r['skill_gaps'] for r in results},skill_gap_status={r['career_name']:r.get('skill_gap_status','insufficient_data') for r in results},skill_gap_messages={r['career_name']:r.get('skill_gap_message','Gap assessment status unavailable.') for r in results}) if results is not None else err('No recommendation run found',404)
@app.get('/api/improvement-plan')
def get_plan():
    sid=request.args.get('student_id','')
    if not authorized(sid): return err('Valid bearer token for this student is required',401)
    results=latest(sid)
    return jsonify(improvement_plans={r['career_name']:r['improvement_suggestions'] for r in results}) if results is not None else err('No recommendation run found',404)

@app.get('/api/admin/dashboard')
def admin_dashboard():
    denied=admin_required()
    if denied: return denied
    users=db().execute('SELECT COUNT(*) AS n FROM users').fetchone()['n']; students=db().execute('SELECT COUNT(*) AS n FROM students').fetchone()['n']
    recs=db().execute('SELECT COUNT(*) AS n FROM recommendations').fetchone()['n']
    recommendation_requests=db().execute('SELECT COUNT(*) AS n FROM recommendation_events').fetchone()['n']
    attempts=db().execute('SELECT COUNT(*) AS n FROM aptitude_attempts').fetchone()['n']; completed_attempts=db().execute("SELECT COUNT(*) AS n FROM aptitude_attempts WHERE status='completed'").fetchone()['n']
    completed_profiles=db().execute('SELECT COUNT(*) AS n FROM students WHERE profile_updated_at IS NOT NULL').fetchone()['n']
    metrics=ROOT/'data/processed/career_model_metrics.json'
    model_data=json.loads(metrics.read_text(encoding='utf-8')) if metrics.exists() else {'status':'models_not_trained'}
    recent_errors=[dict(r) for r in db().execute('SELECT method,endpoint,status_code,error_type,created_at FROM application_errors ORDER BY error_id DESC LIMIT 10').fetchall()]
    return jsonify(statistics={'users':users,'students':students,'active_students':db().execute("SELECT COUNT(*) AS n FROM users WHERE role='student' AND is_active=1").fetchone()['n'],'completed_profiles':completed_profiles,'recommendation_runs':recs,'recommendation_requests':recommendation_requests,'aptitude_attempts':attempts,'completed_aptitude_attempts':completed_attempts,'careers':len(__import__('backend.services.recommendation_engine',fromlist=['careers']).careers())},model_performance=model_data,recent_errors=recent_errors)

@app.get('/api/admin/users')
def admin_users():
    denied=admin_required()
    if denied: return denied
    query=request.args.get('q','').strip().lower()
    if query:
        like='%'+query+'%'; rows=db().execute('SELECT u.user_id,u.email,u.role,u.is_active,u.created_at,s.student_id,s.education_level,s.degree,s.specialization,s.profile_updated_at FROM users u LEFT JOIN students s ON s.user_id=u.user_id WHERE lower(u.email) LIKE ? OR lower(COALESCE(s.student_id,\'\')) LIKE ? ORDER BY u.user_id DESC',(like,like)).fetchall()
    else: rows=db().execute('SELECT u.user_id,u.email,u.role,u.is_active,u.created_at,s.student_id,s.education_level,s.degree,s.specialization,s.profile_updated_at FROM users u LEFT JOIN students s ON s.user_id=u.user_id ORDER BY u.user_id DESC').fetchall()
    return jsonify(users=[dict(r) for r in rows])

@app.get('/api/admin/users/<int:user_id>')
def admin_user_detail(user_id):
    denied=admin_required()
    if denied: return denied
    row=db().execute('SELECT u.user_id,u.email,u.role,u.is_active,u.created_at,s.student_id FROM users u LEFT JOIN students s ON s.user_id=u.user_id WHERE u.user_id=?',(user_id,)).fetchone()
    if not row: return err('User not found',404)
    user=dict(row); user['profile']=student_profile(row['student_id']) if row['student_id'] else None
    return jsonify(user=user)

@app.patch('/api/admin/users/<int:user_id>/role')
def admin_set_role(user_id):
    denied=admin_required()
    if denied: return denied
    role=(request.get_json(silent=True) or {}).get('role')
    if role not in ('student','admin'): return err('role must be student or admin')
    current=db().execute('SELECT role FROM users WHERE user_id=?',(user_id,)).fetchone()
    if not current: return err('User not found',404)
    token=request.headers.get('Authorization','').removeprefix('Bearer ').strip()
    actor=db().execute('SELECT user_id FROM users WHERE token=?',(token,)).fetchone()
    if actor and actor['user_id']==user_id and role!='admin': return err('An administrator cannot remove their own admin role',409)
    if current['role']=='admin' and role=='student' and db().execute("SELECT COUNT(*) AS n FROM users WHERE role='admin' AND is_active=1").fetchone()['n']<=1: return err('Cannot remove the last active administrator',409)
    cur=db().execute('UPDATE users SET role=? WHERE user_id=?',(role,user_id)); db().commit()
    record_admin_action('change_user_role','user',user_id,{'role':role})
    return jsonify(updated=bool(cur.rowcount)) if cur.rowcount else err('User not found',404)

@app.patch('/api/admin/users/<int:user_id>/status')
def admin_set_user_status(user_id):
    denied=admin_required()
    if denied: return denied
    active=(request.get_json(silent=True) or {}).get('is_active')
    if type(active) is not bool: return err('is_active must be true or false')
    row=db().execute('SELECT role,is_active FROM users WHERE user_id=?',(user_id,)).fetchone()
    if not row: return err('User not found',404)
    token=request.headers.get('Authorization','').removeprefix('Bearer ').strip()
    actor=db().execute('SELECT user_id FROM users WHERE token=?',(token,)).fetchone()
    if actor and actor['user_id']==user_id and not active: return err('An administrator cannot disable their own account',409)
    if row['role']=='admin' and not active and db().execute("SELECT COUNT(*) AS n FROM users WHERE role='admin' AND is_active=1").fetchone()['n']<=1: return err('Cannot deactivate the last active administrator',409)
    db().execute('UPDATE users SET is_active=? WHERE user_id=?',(int(active),user_id)); db().commit()
    record_admin_action('set_user_status','user',user_id,{'is_active':active})
    return jsonify(updated=True,is_active=active)

@app.get('/api/admin/careers')
def admin_careers():
    denied=admin_required()
    if denied: return denied
    from backend.services.recommendation_engine import careers
    return jsonify(careers=careers(include_inactive=True))

CAREER_DRAFT_DIR=ROOT/'instance'/'career_drafts'
def _career_draft_lock_path(): return CAREER_DRAFT_DIR/'catalog.lock'

def _career_catalog_fingerprint():
    from backend.services.recommendation_engine import KB,METADATA
    from backend.services.catalog_releases import load_active_catalog
    return load_active_catalog(KB,METADATA).fingerprint

def _career_catalog_snapshot():
    """Read the canonical pair consistently for staging; never rewrite either file."""
    from backend.services.recommendation_engine import KB,METADATA
    try:
        from backend.services.catalog_releases import load_active_catalog
        snapshot=load_active_catalog(KB,METADATA)
    except Exception as exc:
        return None,None,f'Could not read a valid career catalog snapshot: {exc}'
    return snapshot.rows,snapshot.fingerprint,None

def _career_draft_path(draft_id):
    if not isinstance(draft_id,str) or not re.fullmatch(r'[a-f0-9]{24}',draft_id): return None
    return CAREER_DRAFT_DIR/(draft_id+'.json')

def _remove_career_draft(draft_id):
    path=_career_draft_path(draft_id)
    if path is None: return
    with interprocess_file_lock(_career_draft_lock_path()): path.unlink(missing_ok=True)

def _read_career_drafts():
    CAREER_DRAFT_DIR.mkdir(parents=True,exist_ok=True)
    with interprocess_file_lock(_career_draft_lock_path()):
        drafts=[]
        for path in sorted(CAREER_DRAFT_DIR.glob('*.json')):
            try: draft=json.loads(path.read_text(encoding='utf-8'))
            except (OSError,ValueError):
                drafts.append({'draft_id':path.stem,'valid':False,'errors':['Draft file is unreadable']}); continue
            from backend.catalog_validation import validate_career_records
            errors=validate_career_records(draft.get('rows'))
            preview=next((row for row in draft.get('rows',[]) if row.get('career_id')==draft.get('career_id')),None)
            drafts.append({'draft_id':draft.get('draft_id',path.stem),'action':draft.get('action'),'career_id':draft.get('career_id'),'career_name':draft.get('career_name'),'created_at':draft.get('created_at'),'valid':not errors,'errors':errors,'preview':preview})
        return drafts

def _stage_career_catalog(action,career_id,rows,career_name,expected_fingerprint):
    CAREER_DRAFT_DIR.mkdir(parents=True,exist_ok=True)
    with interprocess_file_lock(_career_draft_lock_path()):
        if list(CAREER_DRAFT_DIR.glob('*.json')): return None,'A career catalog draft is already awaiting review; publish or discard it first'
        if expected_fingerprint!=_career_catalog_fingerprint(): return None,'Active catalog changed while this draft was being prepared; reload and prepare a fresh draft'
        from backend.catalog_validation import validate_career_records
        errors=validate_career_records(rows)
        if errors: return None,'Catalog validation failed: '+'; '.join(errors)
        draft_id=secrets.token_hex(12)
        draft={'draft_id':draft_id,'action':action,'career_id':career_id,'career_name':career_name,'created_at':datetime.now(timezone.utc).isoformat(),'base_fingerprint':expected_fingerprint,'rows':rows}
        path=_career_draft_path(draft_id)
        try:
            descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(descriptor,'w',encoding='utf-8') as output: json.dump(draft,output,ensure_ascii=False,indent=2)
        except OSError as exc: return None,f'Could not safely save draft: {exc}'
        preview=next((row for row in rows if row.get('career_id')==career_id),None)
        return {'draft_id':draft_id,'action':action,'career_id':career_id,'career_name':career_name,'created_at':draft['created_at'],'valid':True,'errors':[],'preview':preview},None

@app.get('/api/admin/career-drafts')
def admin_career_drafts():
    denied=admin_required()
    if denied: return denied
    return jsonify(drafts=_read_career_drafts())

@app.post('/api/admin/career-drafts/<draft_id>/publish')
def admin_publish_career_draft(draft_id):
    denied=admin_required()
    if denied: return denied
    path=_career_draft_path(draft_id)
    if path is None: return err('Career draft not found',404)
    from backend.services.recommendation_engine import KB,METADATA
    from backend.services.catalog_releases import CatalogActivationError,CatalogReleaseError,publish_catalog
    with interprocess_file_lock(_career_draft_lock_path()):
        if not path.is_file(): return err('Career draft not found',404)
        try: draft=json.loads(path.read_text(encoding='utf-8'))
        except (OSError,ValueError): return err('Career draft is unreadable',400)
        if draft.get('draft_id')!=draft_id: return err('Career draft identifier does not match',400)
        from backend.catalog_validation import validate_career_records
        errors=validate_career_records(draft.get('rows'))
        if errors: return err('Draft failed validation: '+'; '.join(errors),400)
        activation_warning=None
        try:
            published=publish_catalog(draft['rows'],draft.get('base_fingerprint'),KB,METADATA)
        except CatalogActivationError as exc:
            if exc.outcome == 'committed':
                published=exc.snapshot
                if exc.durability_uncertain:
                    activation_warning='The release is active, but the active-pointer directory could not be synced; crash durability is uncertain.'
            elif exc.outcome == 'not_committed':
                return jsonify(error='Catalog activation did not commit. '+exc.diagnostic,activation_status='not_committed',activation_committed=False),500
            else:
                return jsonify(error='Catalog activation outcome is indeterminate. Do not retry until an administrator verifies the active release. '+exc.diagnostic,activation_status='indeterminate'),500
        except CatalogReleaseError as exc:
            status=409 if 'changed since' in str(exc) else 400
            return err(str(exc),status)
        except OSError:
            return jsonify(error='Catalog activation outcome is indeterminate; the active release could not be verified. Do not retry until an administrator checks the active release.',activation_status='indeterminate'),500
        audit_warning=None
        try: record_admin_action('publish_career_catalog_draft','career_catalog',draft_id,{'action':draft.get('action'),'career_id':draft.get('career_id'),'release_id':published.release_id})
        except Exception as exc: audit_warning=f'Catalog activated, but its audit event could not be recorded: {exc}'
        path.unlink(missing_ok=True)
    return jsonify(published=True,activation_status='committed',draft_id=draft_id,career_id=draft.get('career_id'),release_id=published.release_id,fingerprint=published.fingerprint,activation_warning=activation_warning,audit_warning=audit_warning)

@app.get('/api/admin/career-releases')
def admin_career_releases():
    denied=admin_required()
    if denied: return denied
    from backend.services.catalog_releases import CatalogReleaseError,list_releases
    try: return jsonify(releases=list_releases())
    except CatalogReleaseError as exc: return err(str(exc),503)

@app.post('/api/admin/career-releases/<release_id>/restore')
def admin_restore_career_release(release_id):
    denied=admin_required()
    if denied: return denied
    data=request.get_json(silent=True) or {}
    expected=data.get('expected_fingerprint')
    if not isinstance(expected,str): return err('expected_fingerprint is required to prevent restoring over a newer catalog',400)
    from backend.services.recommendation_engine import KB,METADATA
    from backend.services.catalog_releases import CatalogActivationError,CatalogReleaseError,restore_release
    activation_warning=None
    try: restored=restore_release(release_id,expected,KB,METADATA)
    except CatalogActivationError as exc:
        if exc.outcome == 'committed':
            restored=exc.snapshot
            if exc.durability_uncertain:
                activation_warning='The restored release is active, but the active-pointer directory could not be synced; crash durability is uncertain.'
        elif exc.outcome == 'not_committed':
            return jsonify(error='Restore did not commit. '+exc.diagnostic,activation_status='not_committed',restored=False),500
        else:
            return jsonify(error='Restore outcome is indeterminate. Verify the active release before retrying. '+exc.diagnostic,activation_status='indeterminate'),500
    except CatalogReleaseError as exc: return err(str(exc),409)
    except OSError: return jsonify(error='Restore outcome is indeterminate; verify the active release before retrying.',activation_status='indeterminate'),500
    audit_warning=None
    try: record_admin_action('restore_career_catalog_release','career_catalog',release_id,{'fingerprint':restored.fingerprint})
    except Exception as exc: audit_warning=f'Release {restored.release_id} is active, but its audit event could not be recorded ({type(exc).__name__}).'
    return jsonify(restored=True,activation_status='committed',release_id=restored.release_id,fingerprint=restored.fingerprint,activation_warning=activation_warning,audit_warning=audit_warning)

@app.delete('/api/admin/career-drafts/<draft_id>')
def admin_discard_career_draft(draft_id):
    denied=admin_required()
    if denied: return denied
    path=_career_draft_path(draft_id)
    if path is None: return err('Career draft not found',404)
    with interprocess_file_lock(_career_draft_lock_path()):
        if not path.is_file(): return err('Career draft not found',404)
        path.unlink()
    record_admin_action('discard_career_catalog_draft','career_catalog',draft_id)
    return jsonify(discarded=True,draft_id=draft_id)

def _unpack_json_file(path,default):
    try: return json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError): return default

def _audit_safe_details(data):
    # Keep audit logs to the non-secret fields needed to understand a change.
    return {k:v for k,v in data.items() if k not in {'token','password','password_hash','options_json','correct_option'}}

def _valid_encoded_score_map(value):
    if not isinstance(value,str): return False
    if not value.strip(): return True
    try:
        entries=[part.split(':',1) for part in value.split(';') if part]
        return bool(entries) and all(len(pair)==2 and re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_ -]{0,63}',pair[0]) and 0<=float(pair[1])<=100 for pair in entries)
    except (ValueError,TypeError): return False

def _normalize_score_map(value):
    if isinstance(value,dict):
        if not all(isinstance(k,str) and re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_ -]{0,63}',k) and type(v) in (int,float) and 0<=v<=100 for k,v in value.items()): return None
        return ';'.join(f'{k}:{v:g}' for k,v in value.items())
    if _valid_encoded_score_map(value): return value
    return None

def _validate_career_record(data,creating=False):
    base={'career_name','description','minimum_education_level','suitable_streams','required_subjects','aptitude_requirements','technical_skills','employability_skills','interest_requirements','recommended_degrees','optional_certifications'}
    if creating and not base.issubset(data): return 'Missing required career fields: '+', '.join(sorted(base-set(data)))
    if not isinstance(data.get('career_name','Career'),str) or not data.get('career_name','Career').strip() or len(data.get('career_name','Career'))>160: return 'career_name must be non-empty text up to 160 characters'
    if data.get('minimum_education_level',"Bachelor's") not in ('10th','12th',"Bachelor's","Master's"): return 'Unsupported minimum education level'
    for field in ('career_name','description','suitable_streams','required_subjects','recommended_degrees','optional_certifications'):
        value=data.get(field,'')
        if not isinstance(value,str) or len(value)>4000: return f'{field} must be text no longer than 4000 characters'
    for field in ('aptitude_requirements','technical_skills','employability_skills','interest_requirements'):
        if _normalize_score_map(data.get(field,'')) is None: return f'{field} must contain valid 0-100 skill scores'
    return None

@app.patch('/api/admin/careers/<career_id>')
def admin_update_career(career_id):
    denied=admin_required()
    if denied: return denied
    rows,fingerprint,snapshot_error=_career_catalog_snapshot()
    if snapshot_error: return err(snapshot_error,503)
    row=next((x for x in rows if x['career_id']==career_id),None)
    if row is None: return err('Career not found',404)
    data=request.get_json(silent=True) or {}; allowed={'career_name','description','minimum_education_level','suitable_streams','required_subjects','aptitude_requirements','technical_skills','employability_skills','interest_requirements','recommended_degrees','optional_certifications','family','keywords','qualification_notes','sources','active'}
    if set(data)-allowed: return err('Only career knowledge-base fields can be updated')
    validation=_validate_career_record({**row,**data})
    if validation: return err(validation)
    if 'minimum_education_level' in data and data['minimum_education_level'] not in ('10th','12th',"Bachelor's","Master's"): return err('Unsupported minimum education level')
    for field,value in data.items():
        if field=='family':
            if value not in ('technology_engineering','health_life_sciences','business_finance','creative_communication','public_social_research'): return err('Unsupported career family')
        elif field=='active':
            if type(value) is not bool: return err('active must be true or false')
        elif field in ('keywords','sources'):
            if not isinstance(value,list) or not all(isinstance(x,str) and len(x)<=160 for x in value): return err(f'{field} must be a list of short text values')
        if field.endswith('_skills') or field.endswith('_requirements'):
            if isinstance(value,dict):
                if not all(isinstance(k,str) and type(v) in (int,float) and 0<=v<=100 for k,v in value.items()): return err(f'Invalid score map for {field}')
                value=';'.join(f'{k}:{v:g}' for k,v in value.items())
            elif not isinstance(value,str) or not _valid_encoded_score_map(value): return err(f'{field} must be a valid skill-score map')
        elif field not in ('family','keywords','sources','active') and (not isinstance(value,str) or len(value)>4000): return err(f'{field} must be text no longer than 4000 characters')
        row[field]=value
    draft,message=_stage_career_catalog('update',career_id,rows,row['career_name'],fingerprint)
    if message: return err(message,409 if 'already awaiting review' in message else 400)
    try: record_admin_action('stage_career_update','career',career_id,{'draft_id':draft['draft_id'],**_audit_safe_details(data)})
    except Exception as exc: _remove_career_draft(draft['draft_id']); return err(f'Could not record staged change: {exc}',500)
    return jsonify(updated=True,staged=True,draft=draft,career=row)

@app.post('/api/admin/careers')
def admin_create_career():
    denied=admin_required()
    if denied: return denied
    rows,fingerprint,snapshot_error=_career_catalog_snapshot()
    if snapshot_error: return err(snapshot_error,503)
    data=request.get_json(silent=True) or {}
    allowed={'career_name','description','minimum_education_level','suitable_streams','required_subjects','aptitude_requirements','technical_skills','employability_skills','interest_requirements','recommended_degrees','optional_certifications','family','keywords','qualification_notes','sources'}
    if set(data)-allowed: return err('Unsupported career fields were provided')
    validation=_validate_career_record(data,creating=True)
    if validation: return err(validation)
    if data.get('family') not in ('technology_engineering','health_life_sciences','business_finance','creative_communication','public_social_research'): return err('A supported career family is required')
    for field in ('keywords','sources'):
        if field in data and (not isinstance(data[field],list) or not all(isinstance(x,str) and len(x)<=160 for x in data[field])): return err(f'{field} must be a list of short text values')
    if any(r['career_name'].strip().casefold()==data['career_name'].strip().casefold() for r in rows): return err('A career with this title already exists',409)
    ids=[int(m.group(1)) for r in rows if (m:=re.fullmatch(r'C(\d+)',r['career_id']))]
    career_id=f'C{max(ids,default=0)+1:02d}'
    record={'career_id':career_id}
    csv_fields=('career_name','description','minimum_education_level','suitable_streams','required_subjects','aptitude_requirements','technical_skills','employability_skills','interest_requirements','recommended_degrees','optional_certifications')
    for field in csv_fields:
        value=data.get(field,'')
        if field.endswith('_requirements') or field.endswith('_skills'):
            normalized=_normalize_score_map(value)
            if normalized is None: return err(f'{field} must contain valid 0-100 scores')
            value=normalized
        record[field]=value
    record.update({'family':data['family'],'keywords':data.get('keywords',[]),'qualification_notes':data.get('qualification_notes',''),'sources':data.get('sources',[]),'active':True})
    if len(record['qualification_notes'])>4000: return err('qualification_notes is too long')
    proposed=[*rows,record]
    draft,message=_stage_career_catalog('create',career_id,proposed,record['career_name'],fingerprint)
    if message: return err(message,409 if 'already awaiting review' in message else 400)
    try: record_admin_action('stage_career_create','career',career_id,{'draft_id':draft['draft_id'],**_audit_safe_details(data)})
    except Exception as exc: _remove_career_draft(draft['draft_id']); return err(f'Could not record staged change: {exc}',500)
    return jsonify(created=True,staged=True,draft=draft,career=record),201

@app.delete('/api/admin/careers/<career_id>')
def admin_delete_career(career_id):
    denied=admin_required()
    if denied: return denied
    rows,fingerprint,snapshot_error=_career_catalog_snapshot()
    if snapshot_error: return err(snapshot_error,503)
    row=next((x for x in rows if x['career_id']==career_id),None)
    if row is None: return err('Career not found',404)
    row['active']=False
    draft,message=_stage_career_catalog('deactivate',career_id,rows,row['career_name'],fingerprint)
    if message: return err(message,409 if 'already awaiting review' in message else 400)
    try: record_admin_action('stage_career_deactivation','career',career_id,{'draft_id':draft['draft_id']})
    except Exception as exc: _remove_career_draft(draft['draft_id']); return err(f'Could not record staged change: {exc}',500)
    return jsonify(deactivated=True,staged=True,draft=draft)

@app.get('/api/admin/skills')
def admin_skills():
    denied=admin_required()
    if denied: return denied
    from backend.services.recommendation_engine import careers
    catalog=[]
    for career in careers():
        for field in ('technical_skills','employability_skills'):
            for part in (career.get(field,'') or '').split(';'):
                if ':' not in part: continue
                skill,required=part.split(':',1)
                catalog.append({'skill':skill,'required_level':float(required),'category':'technical' if field=='technical_skills' else 'employability','career_id':career['career_id'],'career_name':career['career_name']})
    return jsonify(skills=catalog,skill_names=sorted({row['skill'] for row in catalog}))

@app.get('/api/admin/recommendations')
def admin_recommendations():
    denied=admin_required()
    if denied: return denied
    return jsonify(recommendation_runs=[dict(r) for r in db().execute('SELECT student_id,created_at FROM recommendations ORDER BY created_at DESC').fetchall()])

@app.get('/api/admin/datasets')
def admin_datasets():
    denied=admin_required()
    if denied: return denied
    from backend.data_registry import inspect_datasets
    return jsonify(inspect_datasets())

@app.get('/api/admin/models')
def admin_models():
    denied=admin_required()
    if denied: return denied
    metrics_path=ROOT/'data/processed/career_model_metrics.json'
    metrics=_unpack_json_file(metrics_path,{'status':'metrics_unavailable'})
    diagnostic=_unpack_json_file(ROOT/'data/processed/career_model_diagnostic.json',{'status':'baseline_not_run'})
    stages=[]
    for level,info in metrics.get('stages',{}).items():
        artifact=ROOT/'backend/models/career'/info.get('saved_model','')
        valid=artifact.is_file()
        digest=hashlib.sha256(artifact.read_bytes()).hexdigest()[:16] if valid else None
        stages.append({'education_level':level,'selected_model':info.get('selected_model'),'model_version':digest,'artifact_exists':valid,'artifact_bytes':artifact.stat().st_size if valid else None,'training_data':metrics.get('provenance','not recorded'),'trained_at':metrics.get('trained_at'),'dataset':metrics.get('dataset'),'metrics':info.get('results',{}),'final_held_out_test':info.get('final_held_out_test'),'features':info.get('features',[]),'classes':info.get('classes',[])})
    return jsonify(stages=stages,baseline=diagnostic.get('stages',{}),diagnostic=diagnostic,model_source=metrics.get('provenance'),empirically_validated=False,retraining_available=False,activation_history_available=False)

@app.get('/api/admin/errors')
def admin_errors():
    denied=admin_required()
    if denied: return denied
    return jsonify(errors=[dict(r) for r in db().execute('SELECT method,endpoint,status_code,error_type,created_at FROM application_errors ORDER BY error_id DESC LIMIT 100').fetchall()])

@app.get('/api/admin/audit')
def admin_audit():
    denied=admin_required()
    if denied: return denied
    rows=db().execute('SELECT a.audit_id,u.email AS admin_email,a.action,a.resource_type,a.resource_id,a.details_json,a.created_at FROM admin_audit_logs a LEFT JOIN users u ON u.user_id=a.admin_user_id ORDER BY a.audit_id DESC LIMIT 100').fetchall()
    return jsonify(events=[{**dict(r),'details':unpack(r['details_json']) if r['details_json'] else {}} for r in rows])

def _parse_skill_field(value):
    return [part.split(':',1)[0] for part in (value or '').split(';') if ':' in part]

if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)),debug=False)
