"""Fail-closed SQLite configuration for API tests.

Import this module before ``backend.app``. It pins the process to an explicit
SQLite target before application configuration is resolved, then exposes
guards used before every test-fixture database operation.
"""

import importlib
import os
import tempfile
from pathlib import Path

from backend.database_config import resolve_database_target


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_SCRATCH_ROOT = PROJECT_ROOT / ".test-tmp"
if not TEST_SCRATCH_ROOT.is_dir():
    raise RuntimeError("API tests require the existing .test-tmp directory")

PROCESS_RUNTIME = tempfile.TemporaryDirectory(
    prefix="api-test-isolation-", dir=TEST_SCRATCH_ROOT
)
PROCESS_TEMP_ROOT = Path(PROCESS_RUNTIME.name).resolve()
PROCESS_DB_PATH = PROCESS_TEMP_ROOT / "db" / "api_test.sqlite3"


def _sqlite_url(path):
    return "sqlite:///" + Path(path).resolve().as_posix()


def _pin_process_to(path):
    os.environ["DATABASE_URL"] = _sqlite_url(path)
    os.environ["CAREERPATH_DB"] = str(Path(path).resolve())


_pin_process_to(PROCESS_DB_PATH)

# Import only after the explicit process environment is established. If
# another test imported the app first, the assertion below rejects its config.
application = importlib.import_module("backend.app")


def _is_within(path, root):
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
        return True
    except (ValueError, OSError):
        return False


def assert_isolated_sqlite(app_module, approved_root):
    """Validate the resolved and effective app target without opening it."""
    root = Path(approved_root).resolve()
    target = getattr(app_module, "DATABASE_TARGET", None)
    db_path = Path(getattr(app_module, "DB_PATH", "")).resolve()
    target_path = getattr(target, "sqlite_path", None)
    if target is None or target.driver != "SQLite" or target.mysql:
        raise RuntimeError("API test isolation refused: resolved driver is not SQLite")
    if getattr(app_module, "USE_MYSQL", None) is not False:
        raise RuntimeError("API test isolation refused: MySQL is enabled")
    if getattr(app_module, "_DATABASE_CONFIG_ERROR", None):
        raise RuntimeError("API test isolation refused: application database configuration is invalid")
    if target_path is None or Path(target_path).resolve() != db_path:
        raise RuntimeError("API test isolation refused: effective DB_PATH differs from resolved SQLite target")
    if not _is_within(target_path, root) or not _is_within(db_path, root):
        raise RuntimeError("API test isolation refused: database path is outside the approved temporary root")
    if db_path == (PROJECT_ROOT / "careerpath.sqlite3").resolve():
        raise RuntimeError("API test isolation refused: project database path selected")
    expected_url = _sqlite_url(db_path)
    if getattr(app_module, "DATABASE_URL", None) != expected_url:
        raise RuntimeError("API test isolation refused: application URL does not match the SQLite target")
    configured_target = resolve_database_target(
        os.environ.get("DATABASE_URL"),
        os.environ.get("CAREERPATH_DB"),
        allow_default=False,
        project_root=PROJECT_ROOT,
    )
    if configured_target.driver != "SQLite" or configured_target.mysql:
        raise RuntimeError("API test isolation refused: process environment selected a non-SQLite driver")
    if configured_target.sqlite_path != db_path or configured_target.identity != target.identity:
        raise RuntimeError("API test isolation refused: process and application targets do not match")
    return db_path


def capture_database_configuration(app_module):
    return {
        name: getattr(app_module, name)
        for name in ("DATABASE_URL", "DATABASE_TARGET", "DB_PATH", "USE_MYSQL", "_DATABASE_CONFIG_ERROR")
    }


def restore_database_configuration(app_module, snapshot):
    for name, value in snapshot.items():
        setattr(app_module, name, value)
    target = snapshot["DATABASE_TARGET"]
    if target is None or target.sqlite_path is None or target.mysql:
        raise RuntimeError("Refusing to restore a non-SQLite API test configuration")
    _pin_process_to(target.sqlite_path)
    assert_isolated_sqlite(app_module, target.sqlite_path.parent.parent)


def configure_isolated_database(app_module, database_path, approved_root):
    """Select a per-test SQLite file and prove containment before any I/O."""
    root = Path(approved_root).resolve()
    path = Path(database_path).resolve()
    if not _is_within(path, root):
        raise RuntimeError("API test isolation refused: requested database is outside the approved temporary root")
    url = _sqlite_url(path)
    target = resolve_database_target(url, str(path), allow_default=False, project_root=PROJECT_ROOT)
    if target.driver != "SQLite" or target.mysql or target.sqlite_path != path:
        raise RuntimeError("API test isolation refused: requested target did not resolve to the exact SQLite file")
    app_module.DATABASE_URL = url
    app_module.DATABASE_TARGET = target
    app_module.DB_PATH = target.sqlite_path
    app_module.USE_MYSQL = False
    app_module._DATABASE_CONFIG_ERROR = None
    _pin_process_to(path)
    assert_isolated_sqlite(app_module, root)
    return path


def initialize_and_seed_isolated_database(app_module, approved_root, seeders=()):
    """Run test fixture writes only after repeated target checks."""
    assert_isolated_sqlite(app_module, approved_root)
    app_module.init_db()
    assert_isolated_sqlite(app_module, approved_root)
    connection = app_module.connect_db()
    try:
        assert_isolated_sqlite(app_module, approved_root)
        for seed in seeders:
            seed(connection)
        connection.commit()
    finally:
        connection.close()


# Establish the import-time target without creating/opening the SQLite file.
assert_isolated_sqlite(application, PROCESS_TEMP_ROOT)
