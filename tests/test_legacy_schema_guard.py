import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend import app as application


class LegacySchemaGuardTests(unittest.TestCase):
    def test_legacy_assessments_are_detected_before_any_schema_mutation(self):
        with tempfile.TemporaryDirectory() as scratch:
            path = Path(scratch)/'legacy_test.sqlite3'
            conn = sqlite3.connect(path)
            conn.execute('CREATE TABLE assessments(student_id TEXT PRIMARY KEY, assessment_json TEXT)')
            conn.commit(); conn.close()
            with patch.object(application, 'DB_PATH', path), patch.object(application, 'USE_MYSQL', False), patch.object(application, '_DATABASE_CONFIG_ERROR', None):
                with self.assertRaisesRegex(RuntimeError, 'Legacy assessments schema detected'):
                    application.init_db()
            conn = sqlite3.connect(path)
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            columns = {row[1] for row in conn.execute('PRAGMA table_info(assessments)')}
            conn.close()
            self.assertEqual(tables, {'assessments'})
            self.assertEqual(columns, {'student_id', 'assessment_json'})


if __name__ == '__main__':
    unittest.main()
