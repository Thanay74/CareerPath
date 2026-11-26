import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend import app as application
from scripts import phase2_2f_student_runtime as runtime


class StudentRuntimeResumeTests(unittest.TestCase):
    def setUp(self):
        # The sandbox's OS temp directory may be read-only. Keep each disposable
        # SQLite fixture under this writable test directory and remove only it.
        self.scratch = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name) / "careerpath_phase22f_student_test"
        self.database = self.root / "db" / "student_test.sqlite3"
        self.database.parent.mkdir(parents=True)
        with patch.object(application, "DB_PATH", self.database), patch.object(application, "USE_MYSQL", False):
            application.init_db()

    def _add_student(self, role="student"):
        connection = sqlite3.connect(self.database)
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute(
                "INSERT INTO users(user_id,email,password_hash,token,role,is_active) VALUES(1,?,?,?,?,1)",
                ("resume@example.test", "test-hash", "test-token", role),
            )
            connection.execute(
                "INSERT INTO students(student_id,user_id,education_level,stream) VALUES(?,?,?,?)",
                ("TEST-STUDENT-1", 1, "10th", ""),
            )
            connection.commit()
        finally:
            connection.close()

    def _digest(self):
        return hashlib.sha256(self.database.read_bytes()).hexdigest()

    def test_fresh_serve_still_accepts_an_empty_initialized_database(self):
        runtime._validate_readonly_sqlite(self.database, self.root, self._digest())

    def test_default_serve_still_refuses_existing_student_data(self):
        self._add_student()
        before = self._digest()
        with self.assertRaisesRegex(runtime.IsolationError, "pre-existing account/student/event data"):
            runtime._validate_readonly_sqlite(self.database, self.root, before)
        self.assertEqual(self._digest(), before)

    def test_resume_accepts_student_only_data_without_writing(self):
        self._add_student()
        before = self._digest()
        runtime._validate_readonly_sqlite(
            self.database, self.root, before, allow_existing_test_data=True
        )
        self.assertEqual(self._digest(), before)

    def test_resume_refuses_empty_database(self):
        with self.assertRaisesRegex(runtime.IsolationError, "requires existing student accounts"):
            runtime._validate_readonly_sqlite(
                self.database, self.root, self._digest(), allow_existing_test_data=True
            )

    def test_resume_refuses_administrator_accounts(self):
        self._add_student(role="admin")
        with self.assertRaisesRegex(runtime.IsolationError, "administrator records are not permitted"):
            runtime._validate_readonly_sqlite(
                self.database, self.root, self._digest(), allow_existing_test_data=True
            )

    def test_resume_refuses_admin_audit_records(self):
        self._add_student()
        connection = sqlite3.connect(self.database)
        try:
            connection.execute(
                "INSERT INTO admin_audit_logs(action,resource_type,resource_id,details_json) VALUES(?,?,?,?)",
                ("test", "test", "test", "{}"),
            )
            connection.commit()
        finally:
            connection.close()
        with self.assertRaisesRegex(runtime.IsolationError, "administrator records are not permitted"):
            runtime._validate_readonly_sqlite(
                self.database, self.root, self._digest(), allow_existing_test_data=True
            )

    def test_resume_cli_requires_explicit_existing_data_confirmation(self):
        with patch.object(runtime, "_command_resume") as command:
            with self.assertRaises(SystemExit) as raised:
                runtime.main([
                    "resume", "--runtime-root", str(self.root), "--runtime-id", "runtime-test",
                    "--expected-database-sha256", "a" * 64,
                ])
            self.assertEqual(raised.exception.code, 2)
            command.assert_not_called()

    def test_resume_command_refuses_without_confirmation_before_validation(self):
        with patch.object(runtime, "_command_start") as start:
            result = runtime._command_resume(str(self.root), "runtime-test", "a" * 64, 5000)
        self.assertEqual(result, 2)
        start.assert_not_called()

    def test_confirmed_resume_cli_dispatches_without_initializing(self):
        with patch.object(runtime, "_command_resume", return_value=0) as command:
            result = runtime.main([
                "resume", "--runtime-root", str(self.root), "--runtime-id", "runtime-test",
                "--expected-database-sha256", "a" * 64,
                "--confirm-existing-student-data", "--port", "5000",
            ])
        self.assertEqual(result, 0)
        command.assert_called_once_with(
            str(self.root), "runtime-test", "a" * 64, 5000,
            confirm_existing_student_data=True,
        )


if __name__ == "__main__":
    unittest.main()
