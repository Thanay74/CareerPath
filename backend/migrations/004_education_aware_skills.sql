-- Additive custom skill/applicability storage. Run only after confirming the
-- exact intended MySQL target with the existing setup workflow.
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
