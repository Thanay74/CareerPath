"""Opt-in API persistence test; run only through tests.mysql_integration.harness."""
import unittest
import uuid
import os
from urllib.parse import unquote, urlparse

from backend import app as application
from backend.database_config import resolve_database_target


EXPECTED_IDENTITY = "mysql+pymysql://localhost:3306/careerpath_test_phase22e"
EXPECTED_USER = "careerpath_test_phase22e"
EXPECTED_SERVER = "LAPTOP-LJE9JD9B"


class IsolatedMySQLWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.environ.get("CAREERPATH_ENABLE_MYSQL_INTEGRATION") != "1":
            raise unittest.SkipTest("Use the fail-closed tests/mysql_integration/harness.py runner")
        # These checks run before the first request and prevent this test module
        # from ever silently exercising SQLite or a different MySQL schema.
        target = resolve_database_target(application.DATABASE_URL, None, allow_default=False)
        if not application.USE_MYSQL or target.identity != EXPECTED_IDENTITY:
            raise RuntimeError("Refusing integration tests: Flask target is not the approved MySQL test schema")
        if application.DATABASE_TARGET is None or application.DATABASE_TARGET.identity != EXPECTED_IDENTITY:
            raise RuntimeError("Refusing integration tests: resolved application target mismatch")
        cls._original_connect_db = application.connect_db

        def verified_connect_db():
            # Revalidate both Flask's resolved target and the server identity on
            # every connection used by requests or cleanup SQL.
            target_now = resolve_database_target(application.DATABASE_URL, None, allow_default=False)
            parsed = urlparse(application.DATABASE_URL)
            if (
                not application.USE_MYSQL
                or application._DATABASE_CONFIG_ERROR is not None
                or target_now.identity != EXPECTED_IDENTITY
                or application.DATABASE_TARGET is None
                or application.DATABASE_TARGET.identity != EXPECTED_IDENTITY
                or not application.DATABASE_TARGET.mysql
                or (parsed.hostname or "").casefold() != "localhost"
                or (parsed.port or 3306) != 3306
                or parsed.path.lstrip("/") != "careerpath_test_phase22e"
                or unquote(parsed.username or "") != EXPECTED_USER
                or unquote(parsed.password or "") != os.environ.get("CAREERPATH_MYSQL_TEST_PASSWORD")
            ):
                raise RuntimeError("Refusing DB connection: Flask target is not the approved MySQL test schema")
            conn = cls._original_connect_db()
            try:
                row = conn.execute(
                    "SELECT VERSION() AS version, DATABASE() AS schema_name, "
                    "CURRENT_USER() AS account, @@hostname AS server, @@port AS port"
                ).fetchone()
                if (
                    row["version"] != "8.0.46"
                    or row["schema_name"] != "careerpath_test_phase22e"
                    or row["account"] != f"{EXPECTED_USER}@localhost"
                    or str(row["server"]).casefold() != EXPECTED_SERVER.casefold()
                    or int(row["port"]) != 3306
                ):
                    raise RuntimeError("Refusing DB connection: connected server identity does not match approval")
                return conn
            except Exception:
                conn.close()
                raise

        application.connect_db = verified_connect_db
        cls.client = application.app.test_client()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "_original_connect_db"):
            application.connect_db = cls._original_connect_db

    def setUp(self):
        self.email = f"phase22e-{uuid.uuid4().hex}@example.test"
        self.student_id = None
        self.user_id = None
        self.token = None
        self.error_baseline = None
        self.addCleanup(self._cleanup_test_records)
        self.error_baseline = self._max_error_id()
        response = self.client.post("/api/register", json={"email": self.email, "password": "Disposable-test-123!"})
        self.assertEqual(response.status_code, 201, response.get_json())
        self.student_id = response.get_json()["student_id"]
        self.token = response.get_json()["token"]
        row = self._db().execute("SELECT user_id FROM users WHERE email=?", (self.email,)).fetchone()
        self.assertIsNotNone(row)
        self.user_id = row["user_id"]

    def _cleanup_test_records(self):
        conn = self._db()
        try:
            if not self.user_id:
                user = conn.execute("SELECT user_id FROM users WHERE email=?", (self.email,)).fetchone()
                self.user_id = user["user_id"] if user else None
            if not self.user_id:
                if self.error_baseline is not None:
                    conn.execute("DELETE FROM application_errors WHERE error_id>?", (self.error_baseline,))
                    conn.commit()
                else:
                    conn.rollback()
                return
            if not self.student_id:
                student = conn.execute("SELECT student_id FROM students WHERE user_id=?", (self.user_id,)).fetchone()
                self.student_id = student["student_id"] if student else None
            if not self.student_id:
                conn.execute("DELETE FROM users WHERE user_id=? AND email=?", (self.user_id, self.email))
                if self.error_baseline is not None:
                    conn.execute("DELETE FROM application_errors WHERE error_id>?", (self.error_baseline,))
                conn.commit()
                return
            attempt_rows = conn.execute("SELECT attempt_id FROM aptitude_attempts WHERE student_id=?", (self.student_id,)).fetchall()
            for attempt in attempt_rows:
                aid = attempt["attempt_id"]
                conn.execute("DELETE FROM aptitude_responses WHERE attempt_id=?", (aid,))
                conn.execute("DELETE FROM aptitude_attempt_questions WHERE attempt_id=?", (aid,))
                conn.execute("DELETE FROM aptitude_domain_scores WHERE attempt_id=?", (aid,))
            conn.execute("DELETE FROM aptitude_attempts WHERE student_id=?", (self.student_id,))
            conn.execute("DELETE FROM recommendation_events WHERE student_id=?", (self.student_id,))
            conn.execute("DELETE FROM academic_records WHERE student_id=?", (self.student_id,))
            conn.execute("DELETE FROM assessments WHERE student_id=?", (self.student_id,))
            conn.execute("DELETE FROM recommendations WHERE student_id=?", (self.student_id,))
            conn.execute("DELETE FROM students WHERE student_id=? AND user_id=?", (self.student_id, self.user_id))
            conn.execute("DELETE FROM users WHERE user_id=? AND email=?", (self.user_id, self.email))
            # application_errors has no owning-user FK. Since the harness refuses
            # to run unless the disposable schema is otherwise empty, rows created
            # after this test's baseline are limited to this serial test run.
            if self.error_baseline is not None:
                conn.execute("DELETE FROM application_errors WHERE error_id>?", (self.error_baseline,))
            conn.commit()
            remaining = conn.execute("SELECT COUNT(*) AS n FROM users WHERE user_id=?", (self.user_id,)).fetchone()["n"]
            if remaining:
                raise AssertionError("Test account cleanup did not remove the created account")
        finally:
            conn.close()

    @classmethod
    def _db(cls):
        # Guard every direct connection as well as the Flask request path.
        target = resolve_database_target(application.DATABASE_URL, None, allow_default=False)
        if not application.USE_MYSQL or target.identity != EXPECTED_IDENTITY:
            raise RuntimeError("Refusing direct DB access outside the approved MySQL test schema")
        return application.connect_db()

    def _max_error_id(self):
        conn = self._db()
        try:
            return conn.execute("SELECT COALESCE(MAX(error_id),0) AS n FROM application_errors").fetchone()["n"]
        finally:
            conn.close()

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    def test_mysql_adapter_converts_placeholders_and_preserves_named_rows(self):
        class FakeCursor:
            rowcount = 1
            lastrowid = 19

            def execute(self, sql, params):
                self.sql, self.params = sql, params

            def fetchone(self):
                return {"student_id": "STU000019"}

        class FakeRawConnection:
            def cursor(self):
                self.last_cursor = FakeCursor()
                return self.last_cursor

        raw = FakeRawConnection()
        result = application.MySQLConnection(raw).execute(
            "SELECT student_id FROM students WHERE user_id=?", (19,)
        )
        self.assertEqual(raw.last_cursor.sql, "SELECT student_id FROM students WHERE user_id=%s")
        self.assertEqual(raw.last_cursor.params, (19,))
        row = result.fetchone()
        self.assertEqual(row["student_id"], "STU000019")
        self.assertEqual(row[0], "STU000019")

    def test_profile_assessments_recommendations_and_auth_persist(self):
        identity = self.client.get("/api/auth/me", headers=self._headers())
        self.assertEqual(identity.status_code, 200)
        self.assertEqual(identity.get_json()["student_id"], self.student_id)

        profile = {
            "student_id": self.student_id,
            "education_level": "10th",
            "stream": "Science",
            "subjects": {"mathematics": 82, "science": 76},
            "career_preferences": "engineering",
        }
        self.assertEqual(self.client.post("/api/student/profile", json=profile, headers=self._headers()).status_code, 200)
        self.assertEqual(self.client.post("/api/assessment/interests", json={"student_id": self.student_id, "scores": {"technology": 75}}, headers=self._headers()).status_code, 200)
        self.assertEqual(self.client.post("/api/assessment/skills", json={"student_id": self.student_id, "technical": {"programming": 65}, "employability": {"communication": 70}}, headers=self._headers()).status_code, 200)

        # A separate API request and connection must read back committed state.
        loaded = self.client.get(f"/api/student/profile?student_id={self.student_id}", headers=self._headers())
        self.assertEqual(loaded.status_code, 200)
        self.assertEqual(loaded.get_json()["profile"]["subjects"], profile["subjects"])
        self.assertEqual(loaded.get_json()["profile"]["interests"]["technology"], 75)

        recommended = self.client.post("/api/recommend", json={"student_id": self.student_id, "top_n": 3}, headers=self._headers())
        self.assertEqual(recommended.status_code, 200, recommended.get_json())
        self.assertTrue(recommended.get_json().get("recommendations"))
        persisted = self.client.get(f"/api/recommendations?student_id={self.student_id}", headers=self._headers())
        self.assertEqual(persisted.status_code, 200)
        self.assertTrue(persisted.get_json().get("recommendations"))

        logout = self.client.post("/api/auth/logout", headers=self._headers())
        self.assertEqual(logout.status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me", headers=self._headers()).status_code, 401)
        login = self.client.post("/api/login", json={"email": self.email, "password": "Disposable-test-123!"})
        self.assertEqual(login.status_code, 200)
        self.token = login.get_json()["token"]
        self.assertEqual(self.client.get(f"/api/student/profile?student_id={self.student_id}", headers=self._headers()).status_code, 200)

    def test_validation_error_is_reported_and_does_not_save_invalid_profile(self):
        response = self.client.post(
            "/api/student/profile",
            json={"student_id": self.student_id, "education_level": "Doctorate", "subjects": {"math": 200}},
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 400)
        loaded = self.client.get(f"/api/student/profile?student_id={self.student_id}", headers=self._headers())
        self.assertEqual(loaded.status_code, 200)
        self.assertEqual(loaded.get_json()["profile"]["education_level"], "10th")
        errors = self._db()
        try:
            row = errors.execute("SELECT COUNT(*) AS n FROM application_errors WHERE error_id>?", (self.error_baseline,)).fetchone()
            self.assertGreaterEqual(row["n"], 1)
        finally:
            errors.close()

    def test_duplicate_registration_does_not_create_an_extra_student(self):
        response = self.client.post(
            "/api/register",
            json={"email": self.email, "password": "Disposable-test-123!"},
        )
        self.assertEqual(response.status_code, 409)
        conn = self._db()
        try:
            users = conn.execute("SELECT COUNT(*) AS n FROM users WHERE email=?", (self.email,)).fetchone()["n"]
            students = conn.execute("SELECT COUNT(*) AS n FROM students WHERE user_id=?", (self.user_id,)).fetchone()["n"]
            self.assertEqual(users, 1)
            self.assertEqual(students, 1)
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
