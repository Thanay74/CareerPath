-- CareerPath assessment enhancement; additive migration for an existing database.
-- Back up your database before applying migrations in general. This migration does not
-- drop, rename, or rewrite existing application tables or records.
USE careerpath;

SET @careerpath_migration_sql = IF((SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='students' AND column_name='degree')=0,'ALTER TABLE students ADD COLUMN degree VARCHAR(255) NULL','SELECT 1');
PREPARE careerpath_migration_stmt FROM @careerpath_migration_sql; EXECUTE careerpath_migration_stmt; DEALLOCATE PREPARE careerpath_migration_stmt;
SET @careerpath_migration_sql = IF((SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='students' AND column_name='specialization')=0,'ALTER TABLE students ADD COLUMN specialization VARCHAR(255) NULL','SELECT 1');
PREPARE careerpath_migration_stmt FROM @careerpath_migration_sql; EXECUTE careerpath_migration_stmt; DEALLOCATE PREPARE careerpath_migration_stmt;
SET @careerpath_migration_sql = IF((SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='students' AND column_name='study_period')=0,'ALTER TABLE students ADD COLUMN study_period VARCHAR(64) NULL','SELECT 1');
PREPARE careerpath_migration_stmt FROM @careerpath_migration_sql; EXECUTE careerpath_migration_stmt; DEALLOCATE PREPARE careerpath_migration_stmt;
SET @careerpath_migration_sql = IF((SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='students' AND column_name='academic_performance')=0,'ALTER TABLE students ADD COLUMN academic_performance DECIMAL(5,2) NULL','SELECT 1');
PREPARE careerpath_migration_stmt FROM @careerpath_migration_sql; EXECUTE careerpath_migration_stmt; DEALLOCATE PREPARE careerpath_migration_stmt;
SET @careerpath_migration_sql = IF((SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='students' AND column_name='academic_scale')=0,'ALTER TABLE students ADD COLUMN academic_scale VARCHAR(16) NOT NULL DEFAULT ''percentage''','SELECT 1');
PREPARE careerpath_migration_stmt FROM @careerpath_migration_sql; EXECUTE careerpath_migration_stmt; DEALLOCATE PREPARE careerpath_migration_stmt;
SET @careerpath_migration_sql = IF((SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='students' AND column_name='research_interests')=0,'ALTER TABLE students ADD COLUMN research_interests TEXT NULL','SELECT 1');
PREPARE careerpath_migration_stmt FROM @careerpath_migration_sql; EXECUTE careerpath_migration_stmt; DEALLOCATE PREPARE careerpath_migration_stmt;
SET @careerpath_migration_sql = IF((SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='students' AND column_name='career_preferences')=0,'ALTER TABLE students ADD COLUMN career_preferences TEXT NULL','SELECT 1');
PREPARE careerpath_migration_stmt FROM @careerpath_migration_sql; EXECUTE careerpath_migration_stmt; DEALLOCATE PREPARE careerpath_migration_stmt;

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
