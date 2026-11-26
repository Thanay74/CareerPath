-- Run as a MySQL administrator once. Create the scoped application account
-- separately with a unique password, then store that password in .env.
CREATE DATABASE IF NOT EXISTS careerpath CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE careerpath;

CREATE TABLE IF NOT EXISTS users (
  user_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  token VARCHAR(128) UNIQUE,
  role ENUM('student','admin') NOT NULL DEFAULT 'student',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS students (
  student_id VARCHAR(64) PRIMARY KEY,
  user_id BIGINT NOT NULL UNIQUE,
  education_level ENUM('10th','12th','Bachelor\'s','Master\'s') NOT NULL DEFAULT '10th',
  age TINYINT UNSIGNED NULL,
  gender VARCHAR(40) NULL,
  stream VARCHAR(64) NULL,
  degree VARCHAR(255) NULL,
  specialization VARCHAR(255) NULL,
  study_period VARCHAR(64) NULL,
  academic_performance DECIMAL(5,2) NULL,
  academic_scale ENUM('percentage','cgpa10') NOT NULL DEFAULT 'percentage',
  research_interests TEXT NULL,
  career_preferences TEXT NULL,
  CONSTRAINT fk_students_user FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS academic_records (
  student_id VARCHAR(64) NOT NULL,
  subject_name VARCHAR(64) NOT NULL,
  score DECIMAL(5,2) NULL,
  PRIMARY KEY(student_id, subject_name),
  CONSTRAINT ck_academic_score CHECK(score IS NULL OR score BETWEEN 0 AND 100),
  CONSTRAINT fk_academic_student FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS assessments (
  student_id VARCHAR(64) NOT NULL,
  assessment_type ENUM('aptitude','interests','technical','employability') NOT NULL,
  feature_name VARCHAR(64) NOT NULL,
  score DECIMAL(5,2) NULL,
  PRIMARY KEY(student_id, assessment_type, feature_name),
  CONSTRAINT ck_assessment_score CHECK(score IS NULL OR score BETWEEN 0 AND 100),
  CONSTRAINT fk_assessment_student FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS student_skill_details (
  student_id VARCHAR(64) NOT NULL,
  skill_key VARCHAR(128) NOT NULL,
  normalized_name VARCHAR(128) NOT NULL,
  display_name VARCHAR(255) NOT NULL,
  category VARCHAR(32) NOT NULL,
  applicability VARCHAR(24) NOT NULL,
  proficiency DECIMAL(5,2) NULL,
  source_context VARCHAR(32) NULL,
  canonical_skill VARCHAR(64) NULL,
  is_custom BOOLEAN NOT NULL DEFAULT FALSE,
  PRIMARY KEY(student_id, skill_key),
  UNIQUE KEY uq_student_skill_name(student_id, normalized_name),
  CONSTRAINT ck_student_skill_category CHECK(category IN ('technical','employability')),
  CONSTRAINT ck_student_skill_state CHECK(applicability IN ('not_applicable','assessed')),
  CONSTRAINT ck_student_skill_score CHECK(proficiency IS NULL OR proficiency BETWEEN 0 AND 100),
  CONSTRAINT ck_student_skill_custom CHECK (is_custom IN (0,1)),
  CONSTRAINT fk_student_skill_student FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS recommendations (
  recommendation_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  student_id VARCHAR(64) NOT NULL UNIQUE,
  results_json JSON NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_recommendation_student FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS careers (
  career_id VARCHAR(16) PRIMARY KEY,
  career_name VARCHAR(180) NOT NULL,
  description TEXT NOT NULL,
  minimum_education_level ENUM('10th','12th','Bachelor\'s','Master\'s') NOT NULL
);
CREATE TABLE IF NOT EXISTS career_streams (
  career_id VARCHAR(16) NOT NULL,
  stream_name VARCHAR(64) NOT NULL,
  PRIMARY KEY(career_id,stream_name),
  CONSTRAINT fk_career_stream FOREIGN KEY(career_id) REFERENCES careers(career_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS career_subjects (
  career_id VARCHAR(16) NOT NULL,
  subject_name VARCHAR(64) NOT NULL,
  PRIMARY KEY(career_id,subject_name),
  CONSTRAINT fk_career_subject FOREIGN KEY(career_id) REFERENCES careers(career_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS career_requirements (
  career_id VARCHAR(16) NOT NULL,
  dimension_type ENUM('aptitude','interest') NOT NULL,
  dimension_name VARCHAR(64) NOT NULL,
  minimum_score TINYINT UNSIGNED NOT NULL,
  PRIMARY KEY(career_id,dimension_type,dimension_name),
  CONSTRAINT ck_career_requirement CHECK(minimum_score <= 100),
  CONSTRAINT fk_career_requirement FOREIGN KEY(career_id) REFERENCES careers(career_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS career_pathways (
  career_id VARCHAR(16) NOT NULL,
  pathway_type ENUM('degree','certification') NOT NULL,
  pathway_name VARCHAR(250) NOT NULL,
  PRIMARY KEY(career_id,pathway_type,pathway_name),
  CONSTRAINT fk_career_pathway FOREIGN KEY(career_id) REFERENCES careers(career_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS skills (
  skill_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  skill_name VARCHAR(100) NOT NULL UNIQUE,
  skill_category ENUM('technical','employability') NOT NULL
);
CREATE TABLE IF NOT EXISTS career_skills (
  career_id VARCHAR(16) NOT NULL,
  skill_id BIGINT NOT NULL,
  required_score TINYINT UNSIGNED NOT NULL,
  PRIMARY KEY(career_id, skill_id),
  CONSTRAINT ck_required_skill_score CHECK(required_score <= 100),
  CONSTRAINT fk_career_skill_career FOREIGN KEY(career_id) REFERENCES careers(career_id) ON DELETE CASCADE,
  CONSTRAINT fk_career_skill_skill FOREIGN KEY(skill_id) REFERENCES skills(skill_id) ON DELETE RESTRICT
);
CREATE TABLE IF NOT EXISTS skill_gaps (
  recommendation_id BIGINT NOT NULL,
  skill_id BIGINT NOT NULL,
  current_score TINYINT UNSIGNED NOT NULL,
  required_score TINYINT UNSIGNED NOT NULL,
  gap_score TINYINT UNSIGNED NOT NULL,
  severity ENUM('Low','Moderate','High') NOT NULL,
  PRIMARY KEY(recommendation_id, skill_id),
  CONSTRAINT fk_gap_recommendation FOREIGN KEY(recommendation_id) REFERENCES recommendations(recommendation_id) ON DELETE CASCADE,
  CONSTRAINT fk_gap_skill FOREIGN KEY(skill_id) REFERENCES skills(skill_id) ON DELETE RESTRICT
);
CREATE TABLE IF NOT EXISTS improvement_plans (
  recommendation_id BIGINT NOT NULL,
  skill_id BIGINT NOT NULL,
  action_order TINYINT UNSIGNED NOT NULL,
  action_text VARCHAR(500) NOT NULL,
  PRIMARY KEY(recommendation_id, skill_id, action_order),
  CONSTRAINT fk_plan_recommendation FOREIGN KEY(recommendation_id) REFERENCES recommendations(recommendation_id) ON DELETE CASCADE,
  CONSTRAINT fk_plan_skill FOREIGN KEY(skill_id) REFERENCES skills(skill_id) ON DELETE RESTRICT
);

-- Aptitude attempt history is additive and preserves the legacy aggregate assessment rows.
CREATE TABLE IF NOT EXISTS aptitude_questions (
  question_id VARCHAR(16) PRIMARY KEY,
  domain VARCHAR(64) NOT NULL,
  difficulty VARCHAR(32) NOT NULL,
  question_text TEXT NOT NULL,
  options_json JSON NOT NULL,
  correct_option CHAR(1) NOT NULL,
  explanation TEXT NOT NULL,
  education_levels_json JSON NOT NULL
);
CREATE TABLE IF NOT EXISTS aptitude_attempts (
  attempt_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  student_id VARCHAR(64) NOT NULL,
  status ENUM('in_progress','completed') NOT NULL DEFAULT 'in_progress',
  started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at TIMESTAMP NULL,
  overall_score DECIMAL(5,2) NULL,
  CONSTRAINT fk_aptitude_attempt_student FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS aptitude_attempt_questions (
  attempt_id BIGINT NOT NULL,
  question_id VARCHAR(16) NOT NULL,
  question_order TINYINT UNSIGNED NOT NULL,
  PRIMARY KEY(attempt_id,question_id),
  UNIQUE KEY uq_aptitude_attempt_order(attempt_id,question_order),
  CONSTRAINT fk_aptitude_attempt_question_attempt FOREIGN KEY(attempt_id) REFERENCES aptitude_attempts(attempt_id) ON DELETE CASCADE,
  CONSTRAINT fk_aptitude_attempt_question_question FOREIGN KEY(question_id) REFERENCES aptitude_questions(question_id)
);
CREATE TABLE IF NOT EXISTS aptitude_responses (
  attempt_id BIGINT NOT NULL,
  question_id VARCHAR(16) NOT NULL,
  selected_option CHAR(1) NOT NULL,
  is_correct BOOLEAN NOT NULL,
  PRIMARY KEY(attempt_id,question_id),
  CONSTRAINT fk_aptitude_response_attempt_question FOREIGN KEY(attempt_id,question_id) REFERENCES aptitude_attempt_questions(attempt_id,question_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS aptitude_domain_scores (
  attempt_id BIGINT NOT NULL,
  domain VARCHAR(64) NOT NULL,
  total_questions TINYINT UNSIGNED NOT NULL,
  correct_answers TINYINT UNSIGNED NOT NULL,
  score DECIMAL(5,2) NOT NULL,
  PRIMARY KEY(attempt_id,domain),
  CONSTRAINT fk_aptitude_domain_attempt FOREIGN KEY(attempt_id) REFERENCES aptitude_attempts(attempt_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS education_programs (
  program_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  education_level VARCHAR(32) NOT NULL,
  program_name VARCHAR(128) NOT NULL,
  program_type ENUM('stream','degree') NOT NULL,
  UNIQUE KEY uq_education_program(education_level,program_name)
);
CREATE TABLE IF NOT EXISTS education_specializations (
  specialization_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  program_id BIGINT NOT NULL,
  specialization_name VARCHAR(128) NOT NULL,
  UNIQUE KEY uq_education_specialization(program_id,specialization_name),
  CONSTRAINT fk_education_specialization_program FOREIGN KEY(program_id) REFERENCES education_programs(program_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS education_subjects (
  subject_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  subject_key VARCHAR(64) NOT NULL UNIQUE,
  subject_name VARCHAR(128) NOT NULL
);
CREATE TABLE IF NOT EXISTS education_program_subjects (
  program_id BIGINT NOT NULL,
  subject_id BIGINT NOT NULL,
  PRIMARY KEY(program_id,subject_id),
  CONSTRAINT fk_program_subject_program FOREIGN KEY(program_id) REFERENCES education_programs(program_id) ON DELETE CASCADE,
  CONSTRAINT fk_program_subject_subject FOREIGN KEY(subject_id) REFERENCES education_subjects(subject_id) ON DELETE RESTRICT
);
CREATE TABLE IF NOT EXISTS education_specialization_subjects (
  specialization_id BIGINT NOT NULL,
  subject_id BIGINT NOT NULL,
  PRIMARY KEY(specialization_id,subject_id),
  CONSTRAINT fk_specialization_subject_specialization FOREIGN KEY(specialization_id) REFERENCES education_specializations(specialization_id) ON DELETE CASCADE,
  CONSTRAINT fk_specialization_subject_subject FOREIGN KEY(subject_id) REFERENCES education_subjects(subject_id) ON DELETE RESTRICT
);
