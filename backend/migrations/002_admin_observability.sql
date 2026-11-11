-- Additive MySQL migration for the CareerPath admin/observability features.
-- No student, account, assessment, recommendation, or source-dataset rows are removed.
-- MySQL 8.0.29+ supports ADD COLUMN IF NOT EXISTS; the Flask startup migrator
-- also checks columns before adding them for compatible MySQL installations.
USE careerpath;

ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE students ADD COLUMN IF NOT EXISTS profile_updated_at TIMESTAMP NULL;
ALTER TABLE aptitude_questions ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

CREATE TABLE IF NOT EXISTS recommendation_events (
  event_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  student_id VARCHAR(64) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_recommendation_event_student FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS application_errors (
  error_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  method VARCHAR(12) NOT NULL,
  endpoint VARCHAR(255) NOT NULL,
  status_code SMALLINT NOT NULL,
  error_type VARCHAR(80) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_application_errors_recent(created_at)
);
CREATE TABLE IF NOT EXISTS admin_audit_logs (
  audit_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  admin_user_id BIGINT NULL,
  action VARCHAR(80) NOT NULL,
  resource_type VARCHAR(80) NOT NULL,
  resource_id VARCHAR(128) NULL,
  details_json JSON NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_admin_audit_recent(created_at),
  CONSTRAINT fk_admin_audit_user FOREIGN KEY(admin_user_id) REFERENCES users(user_id) ON DELETE SET NULL
);
