-- Additive, data-preserving MySQL migration. It uses the schema selected by
-- the already-verified MySQL connection and deliberately contains no USE or
-- hard-coded database name. Do not run without the normal target confirmation.
SET @careerpath_migration_sql = IF(
  DATABASE() IS NOT NULL AND
  (SELECT COUNT(*) FROM information_schema.columns
   WHERE table_schema=DATABASE() AND table_name='students' AND column_name='academic_history')=0,
  'ALTER TABLE students ADD COLUMN academic_history JSON NULL',
  'SELECT 1'
);
PREPARE careerpath_migration_stmt FROM @careerpath_migration_sql;
EXECUTE careerpath_migration_stmt;
DEALLOCATE PREPARE careerpath_migration_stmt;
