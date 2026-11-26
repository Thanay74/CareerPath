import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from api_test_safety import (
    PROCESS_TEMP_ROOT,
    application,
    assert_isolated_sqlite,
    capture_database_configuration,
    configure_isolated_database,
    initialize_and_seed_isolated_database,
    restore_database_configuration,
)
from backend.database_config import resolve_database_target


class ApiDatabaseIsolationTests(unittest.TestCase):
    def setUp(self):
        self.configuration = capture_database_configuration(application)
        self.addCleanup(restore_database_configuration, application, self.configuration)
        self.init_db = application.init_db
        self.connect_db = application.connect_db
        self.addCleanup(setattr, application, "connect_db", self.connect_db)
        self.addCleanup(setattr, application, "init_db", self.init_db)

    def test_process_and_application_explicitly_select_sqlite(self):
        resolved = assert_isolated_sqlite(application, PROCESS_TEMP_ROOT)
        self.assertTrue(resolved.is_relative_to(PROCESS_TEMP_ROOT))
        self.assertEqual(application.DATABASE_TARGET.driver, "SQLite")
        self.assertFalse(application.USE_MYSQL)

    def test_mysql_selection_fails_before_init_connect_or_seed(self):
        mysql_url = "mysql+pymysql://test_user@127.0.0.1/careerpath_test"
        application.DATABASE_URL = mysql_url
        application.DATABASE_TARGET = resolve_database_target(mysql_url, allow_default=False)
        application.USE_MYSQL = True
        application._DATABASE_CONFIG_ERROR = None
        application.init_db = Mock(name="init_db")
        application.connect_db = Mock(name="connect_db")
        seed = Mock(name="seed")

        with self.assertRaisesRegex(RuntimeError, "driver is not SQLite"):
            initialize_and_seed_isolated_database(application, PROCESS_TEMP_ROOT, (seed,))

        application.init_db.assert_not_called()
        application.connect_db.assert_not_called()
        seed.assert_not_called()

    def test_mysql_process_environment_mismatch_fails_before_database_operations(self):
        # Keep the already-imported app globals on their verified SQLite
        # target while the current process environment resolves to MySQL.
        assert_isolated_sqlite(application, PROCESS_TEMP_ROOT)
        application.init_db = Mock(name="init_db")
        application.connect_db = Mock(name="connect_db")
        seed = Mock(name="seed")
        mysql_url = "mysql+pymysql://test_user@127.0.0.1/careerpath_test"
        with patch.dict(
            os.environ,
            {
                "DATABASE_URL": mysql_url,
                "CAREERPATH_DB": str(PROCESS_TEMP_ROOT / "would-not-be-used.sqlite3"),
            },
        ):
            with self.assertRaisesRegex(RuntimeError, "process environment selected a non-SQLite driver"):
                initialize_and_seed_isolated_database(application, PROCESS_TEMP_ROOT, (seed,))

        application.init_db.assert_not_called()
        application.connect_db.assert_not_called()
        seed.assert_not_called()

    def test_database_path_outside_approved_root_fails_before_init(self):
        original_init = application.init_db
        application.init_db = Mock(name="init_db")
        try:
            with self.assertRaisesRegex(RuntimeError, "outside the approved temporary root"):
                configure_isolated_database(application, Path(PROCESS_TEMP_ROOT).parent / "outside.sqlite3", PROCESS_TEMP_ROOT)
            application.init_db.assert_not_called()
        finally:
            application.init_db = original_init

    def test_changing_db_path_alone_does_not_make_mysql_safe(self):
        mysql_url = "mysql+pymysql://test_user@127.0.0.1/careerpath_test"
        application.DATABASE_URL = mysql_url
        application.DATABASE_TARGET = resolve_database_target(mysql_url, allow_default=False)
        application.USE_MYSQL = True
        application._DATABASE_CONFIG_ERROR = None
        application.DB_PATH = PROCESS_TEMP_ROOT / "looks-isolated.sqlite3"
        with self.assertRaisesRegex(RuntimeError, "driver is not SQLite"):
            assert_isolated_sqlite(application, PROCESS_TEMP_ROOT)

    def test_no_initialization_or_seed_callback_runs_before_all_guards_pass(self):
        with tempfile.TemporaryDirectory(dir=PROCESS_TEMP_ROOT) as temp_root:
            configure_isolated_database(application, Path(temp_root) / "safe.sqlite3", temp_root)
            original_init, original_connect = application.init_db, application.connect_db
            application.init_db = Mock(name="init_db", side_effect=RuntimeError("reached init"))
            application.connect_db = Mock(name="connect_db")
            seed = Mock(name="seed")
            try:
                # Break the target after configuration; the pre-init guard must
                # reject it without invoking initialization, connection, or seed.
                application.USE_MYSQL = True
                with self.assertRaises(RuntimeError):
                    initialize_and_seed_isolated_database(application, temp_root, (seed,))
                application.init_db.assert_not_called()
                application.connect_db.assert_not_called()
                seed.assert_not_called()
            finally:
                application.init_db, application.connect_db = original_init, original_connect


if __name__ == "__main__":
    unittest.main()
