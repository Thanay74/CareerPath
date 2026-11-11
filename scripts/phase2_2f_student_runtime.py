"""Prepare or serve CareerPath from an isolated student-test runtime.

``prepare`` is a non-server preflight that copies catalogs into a fresh temp
directory. ``serve`` requires an owner-supplied database hash and runtime ID,
validates SQLite read-only, then starts Flask on loopback. Neither command
initializes a database or creates accounts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import uuid


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PREFIX = "careerpath_phase22f_student_"
MARKER_NAME = ".phase2_2f_student_runtime.json"
RUNTIME_VERSION = 1

# Derived from the SQLite CREATE TABLE statements and upgrades in
# backend/app.py::init_db. The application does not set PRAGMA user_version;
# the current code therefore leaves SQLite's default value (0) in place.
EXPECTED_SQLITE_COLUMNS = {
    "users": {"user_id": "INTEGER", "email": "TEXT", "password_hash": "TEXT", "token": "TEXT", "role": "TEXT", "is_active": "INTEGER", "created_at": "TEXT"},
    "students": {"student_id": "TEXT", "user_id": "INTEGER", "education_level": "TEXT", "age": "INTEGER", "gender": "TEXT", "stream": "TEXT", "degree": "TEXT", "specialization": "TEXT", "study_period": "TEXT", "academic_performance": "REAL", "academic_scale": "TEXT", "research_interests": "TEXT", "career_preferences": "TEXT", "profile_updated_at": "TEXT"},
    "academic_records": {"student_id": "TEXT", "subject_name": "TEXT", "score": "REAL"},
    "assessments": {"student_id": "TEXT", "assessment_type": "TEXT", "feature_name": "TEXT", "score": "REAL"},
    "recommendations": {"student_id": "TEXT", "results_json": "TEXT", "created_at": "TEXT"},
    "aptitude_questions": {"question_id": "TEXT", "domain": "TEXT", "difficulty": "TEXT", "question_text": "TEXT", "options_json": "TEXT", "correct_option": "TEXT", "explanation": "TEXT", "education_levels_json": "TEXT", "is_active": "INTEGER"},
    "aptitude_attempts": {"attempt_id": "INTEGER", "student_id": "TEXT", "status": "TEXT", "started_at": "TEXT", "completed_at": "TEXT", "overall_score": "REAL"},
    "aptitude_attempt_questions": {"attempt_id": "INTEGER", "question_id": "TEXT", "question_order": "INTEGER"},
    "aptitude_responses": {"attempt_id": "INTEGER", "question_id": "TEXT", "selected_option": "TEXT", "is_correct": "INTEGER"},
    "aptitude_domain_scores": {"attempt_id": "INTEGER", "domain": "TEXT", "total_questions": "INTEGER", "correct_answers": "INTEGER", "score": "REAL"},
    "education_programs": {"program_id": "INTEGER", "education_level": "TEXT", "program_name": "TEXT", "program_type": "TEXT"},
    "education_specializations": {"specialization_id": "INTEGER", "program_id": "INTEGER", "specialization_name": "TEXT"},
    "education_subjects": {"subject_id": "INTEGER", "subject_key": "TEXT", "subject_name": "TEXT"},
    "education_program_subjects": {"program_id": "INTEGER", "subject_id": "INTEGER"},
    "education_specialization_subjects": {"specialization_id": "INTEGER", "subject_id": "INTEGER"},
    "recommendation_events": {"event_id": "INTEGER", "student_id": "TEXT", "created_at": "TEXT"},
    "application_errors": {"error_id": "INTEGER", "method": "TEXT", "endpoint": "TEXT", "status_code": "INTEGER", "error_type": "TEXT", "created_at": "TEXT"},
    "admin_audit_logs": {"audit_id": "INTEGER", "admin_user_id": "INTEGER", "action": "TEXT", "resource_type": "TEXT", "resource_id": "TEXT", "details_json": "TEXT", "created_at": "TEXT"},
}
EXPECTED_TABLES = set(EXPECTED_SQLITE_COLUMNS)
EXPECTED_INTERNAL_TABLES = {"sqlite_sequence"}
EXPECTED_PRIMARY_KEYS = {
    "users": ("user_id",),
    "students": ("student_id",),
    "academic_records": ("student_id", "subject_name"),
    "assessments": ("student_id", "assessment_type", "feature_name"),
    "recommendations": ("student_id",),
    "aptitude_questions": ("question_id",),
    "aptitude_attempts": ("attempt_id",),
    "aptitude_attempt_questions": ("attempt_id", "question_id"),
    "aptitude_responses": ("attempt_id", "question_id"),
    "aptitude_domain_scores": ("attempt_id", "domain"),
    "education_programs": ("program_id",),
    "education_specializations": ("specialization_id",),
    "education_subjects": ("subject_id",),
    "education_program_subjects": ("program_id", "subject_id"),
    "education_specialization_subjects": ("specialization_id", "subject_id"),
    "recommendation_events": ("event_id",),
    "application_errors": ("error_id",),
    "admin_audit_logs": ("audit_id",),
}
EXPECTED_FOREIGN_KEYS = {
    ("students", (("user_id", "user_id"),), "users", "NO ACTION"),
    ("academic_records", (("student_id", "student_id"),), "students", "CASCADE"),
    ("assessments", (("student_id", "student_id"),), "students", "CASCADE"),
    ("recommendations", (("student_id", "student_id"),), "students", "NO ACTION"),
    ("aptitude_attempts", (("student_id", "student_id"),), "students", "CASCADE"),
    ("aptitude_attempt_questions", (("attempt_id", "attempt_id"),), "aptitude_attempts", "CASCADE"),
    ("aptitude_attempt_questions", (("question_id", "question_id"),), "aptitude_questions", "NO ACTION"),
    ("aptitude_responses", (("attempt_id", "attempt_id"), ("question_id", "question_id")), "aptitude_attempt_questions", "CASCADE"),
    ("aptitude_domain_scores", (("attempt_id", "attempt_id"),), "aptitude_attempts", "CASCADE"),
    ("education_specializations", (("program_id", "program_id"),), "education_programs", "CASCADE"),
    ("education_program_subjects", (("program_id", "program_id"),), "education_programs", "CASCADE"),
    ("education_program_subjects", (("subject_id", "subject_id"),), "education_subjects", "RESTRICT"),
    ("education_specialization_subjects", (("specialization_id", "specialization_id"),), "education_specializations", "CASCADE"),
    ("education_specialization_subjects", (("subject_id", "subject_id"),), "education_subjects", "RESTRICT"),
    ("recommendation_events", (("student_id", "student_id"),), "students", "SET NULL"),
    ("admin_audit_logs", (("admin_user_id", "user_id"),), "users", "SET NULL"),
}
EXPECTED_UNIQUE_CONSTRAINTS = {
    ("users", ("email",)),
    ("users", ("token",)),
    ("students", ("user_id",)),
    ("aptitude_attempt_questions", ("attempt_id", "question_order")),
    ("education_programs", ("education_level", "program_name")),
    ("education_specializations", ("program_id", "specialization_name")),
    ("education_subjects", ("subject_key",)),
}
EXPECTED_CHECKS = {
    "users": ("check(role in ('student','admin'))",),
    "aptitude_attempts": ("check(status in ('in_progress','completed'))",),
    "education_programs": ("check(program_type in ('stream','degree'))",),
}
EMPTY_USER_DATA_TABLES = {
    "users", "students", "academic_records", "assessments", "recommendations",
    "aptitude_attempts", "aptitude_attempt_questions", "aptitude_responses",
    "aptitude_domain_scores", "recommendation_events", "application_errors",
    "admin_audit_logs",
}
EMPTY_USER_DATA_SEQUENCE_TABLES = {
    "aptitude_attempts", "recommendation_events", "application_errors", "admin_audit_logs",
}


class IsolationError(RuntimeError):
    """Raised when the runtime cannot be proven sufficiently isolated."""


class PreparationFailure(IsolationError):
    def __init__(self, runtime_root: Path, cause: Exception):
        self.runtime_root = runtime_root
        self.cause = cause
        super().__init__(f"{type(cause).__name__}: {cause}")


def _is_within(path: Path, root: Path) -> bool:
    resolved_path = path.resolve()
    resolved_root = root.resolve()
    return resolved_path == resolved_root or resolved_root in resolved_path.parents


def _has_reparse_or_symlink(path: Path) -> bool:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    if path.is_symlink():
        return True
    # Windows junctions and other reparse points may not report as symlinks.
    reparse_flag = getattr(__import__("stat"), "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(getattr(info, "st_file_attributes", 0) & reparse_flag)


def _assert_no_reparse_components(path: Path, root: Path) -> None:
    root = root.resolve()
    if not _is_within(path, root):
        raise IsolationError(f"Path escapes the isolated runtime: {path.name}")
    relative = path.absolute().relative_to(root)
    current = root
    for component in relative.parts:
        current = current / component
        if _has_reparse_or_symlink(current):
            raise IsolationError(f"Symlink/reparse path is not permitted: {current.name}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_catalog_sources() -> tuple[Path, Path]:
    data_dir = PROJECT_ROOT / "data"
    csv_source = data_dir / "career_knowledge_base.csv"
    metadata_source = data_dir / "career_metadata.json"
    for source in (csv_source, metadata_source):
        if _has_reparse_or_symlink(source) or not source.is_file():
            raise IsolationError(f"Required canonical catalog is missing or is a link: {source.name}")
        if source.resolve().parent != data_dir.resolve():
            raise IsolationError(f"Canonical catalog resolves outside the expected data directory: {source.name}")
    return csv_source, metadata_source


def _expected_paths(runtime_root: Path) -> dict[str, Path]:
    data_dir = runtime_root / "data"
    draft_dir = runtime_root / "instance" / "career_drafts"
    return {
        "database": runtime_root / "db" / "student_test.sqlite3",
        "career_csv": data_dir / "career_knowledge_base.csv",
        "career_metadata": data_dir / "career_metadata.json",
        "active_manifest": data_dir / "career_active.json",
        "managed_marker": data_dir / "career_catalog_managed.json",
        "release_dir": data_dir / "career_releases",
        "activation_lock": data_dir / "career_catalog_activation.lock",
        "draft_dir": draft_dir,
        "draft_lock": draft_dir / "catalog.lock",
    }


def _assert_root_is_safe(runtime_root: Path) -> Path:
    if _has_reparse_or_symlink(runtime_root):
        raise IsolationError("Runtime root may not be a symlink or reparse point")
    root = runtime_root.resolve(strict=True)
    temp_root = Path(tempfile.gettempdir()).resolve(strict=True)
    if root.parent != temp_root:
        raise IsolationError("Runtime root must be a direct child of the system temporary directory")
    if not root.name.startswith(RUNTIME_PREFIX):
        raise IsolationError("Runtime directory does not have the expected unique test prefix")
    if root == PROJECT_ROOT or _is_within(PROJECT_ROOT, root):
        raise IsolationError("Runtime root overlaps the project checkout")
    return root


def _load_runtime_marker(runtime_root: Path, expected_runtime_id: str | None = None) -> dict:
    marker_path = runtime_root / MARKER_NAME
    if _has_reparse_or_symlink(marker_path) or not marker_path.is_file():
        raise IsolationError("Runtime marker is missing or is a link")
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise IsolationError("Runtime marker is unreadable or malformed") from exc
    if not isinstance(marker, dict) or marker.get("runtime_version") != RUNTIME_VERSION:
        raise IsolationError("Runtime marker has an unsupported structure or version")
    if marker.get("runtime_root") != str(runtime_root) or marker.get("project_root") != str(PROJECT_ROOT.resolve()):
        raise IsolationError("Runtime marker does not identify this exact project and directory")
    runtime_id = marker.get("runtime_id")
    if not isinstance(runtime_id, str) or len(runtime_id) != 32:
        raise IsolationError("Runtime marker has no valid run identity")
    try:
        uuid.UUID(hex=runtime_id)
    except ValueError as exc:
        raise IsolationError("Runtime marker run identity is malformed") from exc
    if expected_runtime_id is not None and runtime_id != expected_runtime_id:
        raise IsolationError("Runtime ID does not match the value recorded after preparation")
    return marker


def _prepare_runtime() -> tuple[Path, str]:
    csv_source, metadata_source = _canonical_catalog_sources()
    created_root = Path(tempfile.mkdtemp(prefix=RUNTIME_PREFIX)).absolute()
    try:
        runtime_root = created_root.resolve(strict=True)
        runtime_id = uuid.uuid4().hex
        paths = _expected_paths(runtime_root)
        paths["database"].parent.mkdir(parents=True, exist_ok=True)
        paths["release_dir"].mkdir(parents=True, exist_ok=False)
        paths["draft_dir"].mkdir(parents=True, exist_ok=False)
        shutil.copyfile(csv_source, paths["career_csv"])
        shutil.copyfile(metadata_source, paths["career_metadata"])
        marker = {
            "runtime_version": RUNTIME_VERSION,
            "runtime_id": runtime_id,
            "runtime_root": str(runtime_root),
            "project_root": str(PROJECT_ROOT.resolve()),
            "catalog_sha256": {
                "career_knowledge_base.csv": _sha256(paths["career_csv"]),
                "career_metadata.json": _sha256(paths["career_metadata"]),
            },
        }
        (runtime_root / MARKER_NAME).write_text(json.dumps(marker, indent=2) + "\n", encoding="utf-8")
    except Exception as exc:
        # Preserve evidence for precise manual cleanup; never delete an unknown
        # or partially prepared directory automatically.
        raise PreparationFailure(created_root, exc) from exc
    return runtime_root, runtime_id


def _check_catalog_paths(runtime_root: Path, paths: dict[str, Path], marker: dict, *, fresh: bool, catalog_releases, recommendation_engine) -> object:
    for name, path in paths.items():
        _assert_no_reparse_components(path, runtime_root)
    if recommendation_engine.KB.resolve() != paths["career_csv"].resolve():
        raise IsolationError("Recommendation engine did not retain the isolated career CSV")
    if recommendation_engine.METADATA.resolve() != paths["career_metadata"].resolve():
        raise IsolationError("Recommendation engine did not retain isolated metadata")
    if paths["career_csv"].resolve() in {path.resolve() for path in _canonical_catalog_sources()}:
        raise IsolationError("A canonical shared career catalog remains selected")
    expected_hashes = marker.get("catalog_sha256")
    if not isinstance(expected_hashes, dict):
        raise IsolationError("Runtime marker has no catalog copy fingerprints")
    for filename, key in (("career_knowledge_base.csv", "career_csv"), ("career_metadata.json", "career_metadata")):
        expected_hash = expected_hashes.get(filename)
        if not isinstance(expected_hash, str) or _sha256(paths[key]) != expected_hash:
            raise IsolationError(f"Copied catalog fingerprint mismatch: {filename}")

    snapshot = catalog_releases.load_active_catalog(
        paths["career_csv"], paths["career_metadata"],
        active_manifest=paths["active_manifest"],
        releases_dir=paths["release_dir"],
        managed_marker=paths["managed_marker"],
    )
    if not snapshot.rows:
        raise IsolationError("Isolated catalog reader returned no career records")

    if fresh:
        if paths["active_manifest"].exists() or paths["managed_marker"].exists() or any(paths["release_dir"].iterdir()):
            raise IsolationError("Fresh preflight runtime unexpectedly contains managed catalog state")
        if snapshot.release_id is not None:
            raise IsolationError("Fresh runtime did not use canonical-bootstrap mode")
        if snapshot.csv_bytes != paths["career_csv"].read_bytes() or snapshot.metadata_bytes != paths["career_metadata"].read_bytes():
            raise IsolationError("Canonical-bootstrap reader did not use the copied catalog bytes")
    elif paths["active_manifest"].exists():
        # load_active_catalog/_read_release validates pointer structure, release
        # hashes, release ID, and career records. Do not compare release content
        # to the original canonical copies after a valid managed publish.
        if snapshot.release_id is None:
            raise IsolationError("Active manifest did not resolve to a versioned release")
    elif paths["managed_marker"].exists():
        raise IsolationError("Managed marker exists without a valid active pointer")
    elif any(paths["release_dir"].iterdir()):
        raise IsolationError("Orphan release directories make canonical fallback ambiguous")
    elif snapshot.release_id is not None or snapshot.csv_bytes != paths["career_csv"].read_bytes() or snapshot.metadata_bytes != paths["career_metadata"].read_bytes():
        raise IsolationError("Canonical-bootstrap catalog state is inconsistent")
    return snapshot


def _validate_readonly_sqlite(database_path: Path, runtime_root: Path, expected_sha256: str) -> None:
    if not re_full_sha256(expected_sha256):
        raise IsolationError("An externally recorded 64-character database SHA-256 is required")
    _assert_no_reparse_components(database_path, runtime_root)
    if _has_reparse_or_symlink(database_path) or not database_path.is_file():
        raise IsolationError("Isolated SQLite database must be a regular, non-link file")
    for suffix in ("-wal", "-shm", "-journal"):
        if Path(str(database_path) + suffix).exists():
            raise IsolationError("SQLite sidecar exists; stop all processes and establish a clean database snapshot")
    with database_path.open("rb") as source:
        if source.read(16) != b"SQLite format 3\x00":
            raise IsolationError("Database file is not a SQLite database")
    if _sha256(database_path) != expected_sha256.lower():
        raise IsolationError("SQLite file hash does not match the owner-supplied external attestation")

    uri = database_path.resolve().as_uri() + "?mode=ro&immutable=1"
    connection = None
    try:
        connection = sqlite3.connect(uri, uri=True)
        connection.row_factory = sqlite3.Row
        user_version = connection.execute("PRAGMA user_version").fetchone()[0]
        if user_version != 0:
            raise IsolationError("Unsupported SQLite user_version; current init_db does not assign a schema version")
        check = connection.execute("PRAGMA quick_check").fetchone()
        if check is None or check[0] != "ok":
            raise IsolationError("SQLite quick_check did not return ok")

        objects = connection.execute("SELECT type, name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchall()
        tables = {name for kind, name in objects if kind == "table"}
        expected = EXPECTED_TABLES
        if tables != expected:
            missing = sorted(expected - tables)
            unexpected = sorted(tables - expected)
            raise IsolationError(f"SQLite tables differ from backend/app.py::init_db; missing={missing}; unexpected={unexpected}")
        unexpected_objects = sorted((kind, name) for kind, name in objects if kind in {"view", "trigger"})
        if unexpected_objects:
            raise IsolationError(f"Unexpected SQLite views/triggers: {unexpected_objects}")

        internal_tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'sqlite_%'")}
        if internal_tables != EXPECTED_INTERNAL_TABLES:
            raise IsolationError(f"Unexpected SQLite internal tables: {sorted(internal_tables)}")
        explicit_indexes = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_autoindex_%'")]
        if explicit_indexes:
            raise IsolationError(f"Unexpected explicit SQLite indexes: {sorted(explicit_indexes)}")

        for table, expected_columns in EXPECTED_SQLITE_COLUMNS.items():
            table_info = connection.execute(f'PRAGMA table_info("{table}")').fetchall()
            actual = {row["name"]: str(row["type"]).upper() for row in table_info}
            if actual != expected_columns:
                raise IsolationError(f"SQLite columns/types differ from backend/app.py::init_db for table {table}")
            actual_primary_key = tuple(row["name"] for row in sorted((r for r in table_info if r["pk"]), key=lambda r: r["pk"]))
            if actual_primary_key != EXPECTED_PRIMARY_KEYS[table]:
                raise IsolationError(f"SQLite primary key differs from backend/app.py::init_db for table {table}")

        actual_foreign_keys = set()
        for table in EXPECTED_TABLES:
            grouped = {}
            for row in connection.execute(f'PRAGMA foreign_key_list("{table}")').fetchall():
                grouped.setdefault(row["id"], []).append(row)
            for rows in grouped.values():
                rows.sort(key=lambda row: row["seq"])
                actual_foreign_keys.add((
                    table,
                    tuple((row["from"], row["to"]) for row in rows),
                    rows[0]["table"],
                    rows[0]["on_delete"].upper(),
                ))
        if actual_foreign_keys != EXPECTED_FOREIGN_KEYS:
            raise IsolationError("SQLite foreign keys differ from backend/app.py::init_db")

        actual_unique_constraints = set()
        for table in EXPECTED_TABLES:
            indexes = connection.execute(f'PRAGMA index_list("{table}")').fetchall()
            for index in indexes:
                if index["unique"] and index["origin"] == "u":
                    quoted_index = str(index["name"]).replace('"', '""')
                    columns = connection.execute(f'PRAGMA index_info("{quoted_index}")').fetchall()
                    actual_unique_constraints.add((table, tuple(row["name"] for row in columns)))
        if actual_unique_constraints != EXPECTED_UNIQUE_CONSTRAINTS:
            raise IsolationError("SQLite unique constraints differ from backend/app.py::init_db")

        for table, expected_checks in EXPECTED_CHECKS.items():
            sql = connection.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()[0]
            normalized = "".join(str(sql).lower().split())
            if any("".join(check.lower().split()) not in normalized for check in expected_checks):
                raise IsolationError(f"SQLite CHECK constraints differ from backend/app.py::init_db for table {table}")

        nonempty = {}
        for table in sorted(EMPTY_USER_DATA_TABLES):
            count = connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            if count:
                nonempty[table] = count
        if nonempty:
            raise IsolationError(f"Refusing pre-existing account/student/event data: {nonempty}")
        sequence_rows = connection.execute("SELECT name, seq FROM sqlite_sequence").fetchall()
        prior_user_sequences = {
            row["name"]: row["seq"] for row in sequence_rows
            if row["name"] in EMPTY_USER_DATA_SEQUENCE_TABLES
        }
        if prior_user_sequences:
            raise IsolationError(f"Refusing prior account/student/event sequence history: {prior_user_sequences}")
        if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise IsolationError("SQLite foreign_key_check found an integrity violation")
    except sqlite3.DatabaseError as exc:
        raise IsolationError(f"Read-only SQLite validation failed: {type(exc).__name__}") from exc
    finally:
        if connection is not None:
            connection.close()

    if _sha256(database_path) != expected_sha256.lower():
        raise IsolationError("SQLite file changed during read-only validation")
    for suffix in ("-wal", "-shm", "-journal"):
        if Path(str(database_path) + suffix).exists():
            raise IsolationError("SQLite sidecar appeared during read-only validation")


def re_full_sha256(value: str) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdefABCDEF" for char in value)


def _file_identity(path: Path) -> tuple[int, int]:
    stat_result = path.stat()
    if not stat_result.st_ino:
        raise IsolationError("Filesystem does not expose a stable file identity for the isolated SQLite target")
    return stat_result.st_dev, stat_result.st_ino


def _install_sqlite_connection_guard(application, database_path: Path, runtime_root: Path) -> None:
    expected_path = database_path.resolve(strict=True)
    expected_identity = _file_identity(expected_path)

    def guarded_connect_db():
        target = application.DATABASE_TARGET
        if (
            application.DATABASE_URL != ""
            or application.USE_MYSQL is not False
            or target is None
            or target.driver != "SQLite"
            or target.mysql is not False
            or application.DB_PATH.resolve() != expected_path
        ):
            raise IsolationError("Database configuration changed after the isolated SQLite preflight")
        _assert_no_reparse_components(expected_path, runtime_root)
        if expected_path.resolve(strict=True) != expected_path or _file_identity(expected_path) != expected_identity:
            raise IsolationError("Isolated SQLite file identity changed after preflight")
        # mode=rw refuses to create a replacement file if the prepared DB is
        # removed between the checks and open.
        connection = sqlite3.connect(expected_path.as_uri() + "?mode=rw", uri=True)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            main_db = next((row for row in connection.execute("PRAGMA database_list").fetchall() if row[1] == "main"), None)
            if main_db is None or Path(main_db[2]).resolve(strict=True) != expected_path:
                raise IsolationError("SQLite connection opened a database outside the approved runtime target")
            if _file_identity(expected_path) != expected_identity:
                raise IsolationError("SQLite file identity changed while opening the application connection")
        except Exception:
            connection.close()
            raise
        return connection

    application.connect_db = guarded_connect_db


def _configure_and_assert(runtime_root: Path, *, mode: str, expected_runtime_id: str | None = None, expected_database_sha256: str | None = None):
    runtime_root = _assert_root_is_safe(runtime_root)
    marker = _load_runtime_marker(runtime_root, expected_runtime_id)
    paths = _expected_paths(runtime_root)

    # Set before importing backend.app. The inherited DATABASE_URL is replaced
    # in this process; load_dotenv() does not override it from the project .env.
    os.environ["DATABASE_URL"] = ""
    os.environ["CAREERPATH_DB"] = str(paths["database"])
    sys.dont_write_bytecode = True

    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    import backend.app as application  # noqa: PLC0415
    import backend.services.catalog_releases as catalog_releases  # noqa: PLC0415
    import backend.services.recommendation_engine as recommendation_engine  # noqa: PLC0415

    recommendation_engine.KB = paths["career_csv"]
    recommendation_engine.METADATA = paths["career_metadata"]
    catalog_releases.ACTIVE_MANIFEST = paths["active_manifest"]
    catalog_releases.MANAGED_MARKER = paths["managed_marker"]
    catalog_releases.RELEASES_DIR = paths["release_dir"]
    catalog_releases.ACTIVATION_LOCK = paths["activation_lock"]
    application.CAREER_DRAFT_DIR = paths["draft_dir"]

    target = application.DATABASE_TARGET
    if (
        application.DATABASE_URL != ""
        or application.USE_MYSQL is not False
        or application._DATABASE_CONFIG_ERROR is not None
        or target is None
        or target.driver != "SQLite"
        or target.mysql is not False
        or application.DB_PATH.resolve() != paths["database"].resolve()
        or target.sqlite_path is None
        or target.sqlite_path.resolve() != paths["database"].resolve()
    ):
        raise IsolationError("Resolved application database is not the exact isolated SQLite target")
    if mode == "prepare" and paths["database"].exists():
        raise IsolationError("Fresh preflight runtime unexpectedly contains a database file")
    if mode == "serve":
        if expected_database_sha256 is None:
            raise IsolationError("Serve requires an owner-recorded database SHA-256 from outside the runtime marker")
        _validate_readonly_sqlite(paths["database"], runtime_root, expected_database_sha256)
        _install_sqlite_connection_guard(application, paths["database"], runtime_root)
    else:
        if paths["database"].exists():
            raise IsolationError("Preparation must not create or open a database file")

    snapshot = _check_catalog_paths(
        runtime_root, paths, marker, fresh=(mode == "prepare"),
        catalog_releases=catalog_releases,
        recommendation_engine=recommendation_engine,
    )
    if application._career_draft_lock_path().resolve() != paths["draft_lock"].resolve():
        raise IsolationError("Admin draft lock is not derived from the isolated draft directory")
    return application, snapshot, paths, marker


def _command_prepare() -> int:
    runtime_root = None
    try:
        runtime_root, runtime_id = _prepare_runtime()
        _, snapshot, paths, _ = _configure_and_assert(runtime_root, mode="prepare", expected_runtime_id=runtime_id)
    except PreparationFailure as exc:
        print(f"ISOLATION PREFLIGHT FAILED; exact partial runtime root: {exc.runtime_root}", file=sys.stderr)
        print(f"Cause: {exc}", file=sys.stderr)
        print("No automatic cleanup was attempted; inspect and remove only this exact invocation-created directory after identity checks.", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ISOLATION PREFLIGHT FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        if runtime_root is not None:
            print(f"Exact invocation-created runtime root: {runtime_root}", file=sys.stderr)
            print("No automatic cleanup was attempted; inspect and remove only this exact directory after identity checks.", file=sys.stderr)
        else:
            print("No runtime root was created before this failure.", file=sys.stderr)
        return 2
    print("ISOLATION PREFLIGHT PASS (no server or database connection started)")
    print(f"runtime_root={runtime_root}")
    print(f"runtime_id={runtime_id}")
    print("database_driver=SQLite; mysql_enabled=False; database_file_not_created=True")
    print(f"catalog_records={len(snapshot.rows)}; release_id={snapshot.release_id or 'canonical-bootstrap-copy'}")
    for name, path in paths.items():
        print(f"{name}={path}")
    return 0


def _command_serve(runtime_arg: str, runtime_id: str, expected_database_sha256: str, port: int) -> int:
    runtime_root = Path(runtime_arg).expanduser()
    try:
        application, _, _, _ = _configure_and_assert(
            runtime_root, mode="serve", expected_runtime_id=runtime_id,
            expected_database_sha256=expected_database_sha256,
        )
    except Exception as exc:
        print(f"ISOLATION SERVER REFUSED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(f"Isolated student runtime serving on http://127.0.0.1:{port}")
    application.app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("prepare", help="create a fresh runtime and run preflight only")
    serve_parser = subparsers.add_parser("serve", help="validate an initialized runtime read-only and serve on loopback")
    serve_parser.add_argument("--runtime-root", required=True)
    serve_parser.add_argument("--runtime-id", required=True, help="value printed by prepare; accidental-substitution check, not a secret")
    serve_parser.add_argument("--expected-database-sha256", required=True, help="owner-recorded digest verified outside the mutable runtime marker")
    serve_parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args(argv)
    if args.command == "prepare":
        return _command_prepare()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    return _command_serve(args.runtime_root, args.runtime_id, args.expected_database_sha256, args.port)


if __name__ == "__main__":
    raise SystemExit(main())
