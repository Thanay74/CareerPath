"""Fail-closed runner for the dedicated CareerPath MySQL integration schema.

This module is deliberately opt-in. Importing it does not import Flask or connect
to a database. See docs/phase2_2e_mysql_harness.md before using a write command.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

if __package__ in (None, ""):
    # Support the documented direct-script invocation without requiring a
    # tests/ package or making unittest recursively discover this suite.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


EXPECTED_HOST = "localhost"
EXPECTED_PORT = 3306
EXPECTED_SERVER = "LAPTOP-LJE9JD9B"
EXPECTED_SCHEMA = "careerpath_test_phase22e"
EXPECTED_USER = "careerpath_test_phase22e"
EXPECTED_VERSION = "8.0.46"
CONFIRM_IDENTITY = f"mysql+pymysql://{EXPECTED_HOST}:{EXPECTED_PORT}/{EXPECTED_SCHEMA}"
REQUIRED_TABLES = {
    "users", "students", "academic_records", "assessments", "recommendations",
    "aptitude_questions", "aptitude_attempts", "aptitude_attempt_questions",
    "aptitude_responses", "aptitude_domain_scores", "education_programs",
    "education_specializations", "education_subjects", "education_program_subjects",
    "education_specialization_subjects", "student_skill_details", "recommendation_events", "application_errors",
    "admin_audit_logs",
}


class HarnessRefused(RuntimeError):
    """Raised when target identity or isolation cannot be proven."""


def _configuration():
    host = os.environ.get("CAREERPATH_MYSQL_TEST_HOST", "")
    port_text = os.environ.get("CAREERPATH_MYSQL_TEST_PORT", "")
    schema = os.environ.get("CAREERPATH_MYSQL_TEST_SCHEMA", "")
    username = os.environ.get("CAREERPATH_MYSQL_TEST_USER", "")
    password = os.environ.get("CAREERPATH_MYSQL_TEST_PASSWORD", "")
    if (host.casefold(), port_text, schema, username) != (
        EXPECTED_HOST, str(EXPECTED_PORT), EXPECTED_SCHEMA, EXPECTED_USER
    ) or not password:
        raise HarnessRefused(
            "Set the five CAREERPATH_MYSQL_TEST_* variables to the approved target "
            "and restricted account; the password must be non-empty."
        )

    # Reject an inherited DATABASE_URL that points anywhere else instead of
    # silently hiding a potentially dangerous configuration.
    inherited = os.environ.get("DATABASE_URL", "").strip()
    if inherited:
        parsed = urlparse(inherited)
        try:
            inherited_port = parsed.port or 3306
        except ValueError as exc:
            raise HarnessRefused("Inherited DATABASE_URL is malformed.") from exc
        if (
            parsed.scheme not in ("mysql", "mysql+pymysql")
            or (parsed.hostname or "").casefold() != EXPECTED_HOST
            or inherited_port != EXPECTED_PORT
            or parsed.path.lstrip("/") != EXPECTED_SCHEMA
            or parsed.username != EXPECTED_USER
        ):
            raise HarnessRefused("Inherited DATABASE_URL does not match the approved test target.")

    url = (
        f"mysql+pymysql://{quote(username, safe='')}:{quote(password, safe='')}"
        f"@{EXPECTED_HOST}:{EXPECTED_PORT}/{EXPECTED_SCHEMA}"
    )
    return url, password


def _safe_environment(database_url):
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    env["CAREERPATH_ENABLE_MYSQL_INTEGRATION"] = "1"
    # MySQL selection is explicit; a SQLite path must never influence this run.
    env.pop("CAREERPATH_DB", None)
    return env


def _connect():
    database_url, password = _configuration()
    del password
    try:
        import pymysql
    except ImportError as exc:
        raise HarnessRefused("PyMySQL is unavailable; install backend/requirements.txt.") from exc
    url = urlparse(database_url)
    conn = pymysql.connect(
        host=EXPECTED_HOST, port=EXPECTED_PORT,
        user=EXPECTED_USER, password=unquote(url.password),
        database=EXPECTED_SCHEMA, charset="utf8mb4", autocommit=False,
        cursorclass=pymysql.cursors.DictCursor, connect_timeout=5,
    )
    return conn, database_url


def preflight(mode):
    """Connect read-only in intent and prove identity, grants, and schema state."""
    conn, _ = _connect()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT VERSION() AS version, DATABASE() AS schema_name, CURRENT_USER() AS account, @@hostname AS server, @@port AS port")
            identity = cursor.fetchone()
            expected_account = f"{EXPECTED_USER}@localhost"
            if identity["version"] != EXPECTED_VERSION:
                raise HarnessRefused("Connected MySQL version did not match the approved version.")
            if identity["schema_name"] != EXPECTED_SCHEMA or identity["account"] != expected_account:
                raise HarnessRefused("Connected schema or authenticated account did not match the approved target.")
            if int(identity["port"]) != EXPECTED_PORT:
                raise HarnessRefused("Connected MySQL port did not match the approved target.")
            if str(identity["server"]).casefold() != EXPECTED_SERVER.casefold():
                raise HarnessRefused("Connected MySQL server hostname did not match the approved server.")

            cursor.execute("SHOW GRANTS FOR CURRENT_USER()")
            grants = [next(iter(row.values())) for row in cursor.fetchall()]
            for grant in grants:
                normalized = grant.casefold().replace("`", "")
                if " on " not in normalized:
                    # Fail closed on roles or grant syntax whose effective
                    # database scope this harness does not independently prove.
                    raise HarnessRefused("An unrecognized grant or role assignment prevents scope verification.")
                if " on *.* " in normalized and "grant usage" not in normalized:
                    raise HarnessRefused("The test account has a global privilege; refusing to proceed.")
                if " on careerpath." in normalized or " on careerpath_db." in normalized or " on student." in normalized:
                    raise HarnessRefused("The test account has a grant on a protected database; refusing to proceed.")
                if " on " in normalized and " on *.* " not in normalized:
                    scope = normalized.split(" on ", 1)[1].split(" to ", 1)[0]
                    if scope not in (f"{EXPECTED_SCHEMA}.*", "*.*"):
                        raise HarnessRefused("The test account has a grant outside the approved schema.")
            cursor.execute(
                "SELECT TABLE_NAME AS table_name "
                "FROM information_schema.tables WHERE table_schema=%s",
                (EXPECTED_SCHEMA,),
            )
            tables = {row["table_name"] for row in cursor.fetchall()}
            if mode == "empty" and tables:
                raise HarnessRefused("The approved test schema is not empty; no setup was attempted.")
            if mode == "initialized" and not REQUIRED_TABLES.issubset(tables):
                missing = sorted(REQUIRED_TABLES - tables)
                raise HarnessRefused("Initialized schema is missing required tables: " + ", ".join(missing))
            if mode == "initialized" and tables - REQUIRED_TABLES:
                raise HarnessRefused("Unexpected tables exist in the test schema; refusing to run tests.")
            if mode == "initialized":
                # The integration account/schema is disposable and must be clean
                # before each run. This prevents cleanup from touching prior data.
                populated = []
                for table in sorted(REQUIRED_TABLES):
                    cursor.execute(f"SELECT COUNT(*) AS n FROM `{table}`")
                    if cursor.fetchone()["n"]:
                        populated.append(table)
                if populated:
                    raise HarnessRefused(
                        "Initialized test schema contains rows before this run: "
                        + ", ".join(populated)
                    )
        conn.rollback()
        print(
            f"Preflight PASS: MySQL {EXPECTED_VERSION}; server={identity['server']}; "
            f"port={EXPECTED_PORT}; schema={EXPECTED_SCHEMA}; account={EXPECTED_USER}@localhost; "
            f"tables={len(tables)} ({mode}). Secrets were not displayed."
        )
    finally:
        conn.close()


def _load_setup_and_initialize(database_url):
    # Import only after installing the approved URL, so .env or SQLite fallback
    # cannot select a different target. setup.main revalidates its target before
    # opening a connection and prints only credential-free target identity.
    os.environ["DATABASE_URL"] = database_url
    os.environ.pop("CAREERPATH_DB", None)
    from backend import setup
    from backend.database_config import resolve_database_target

    target = resolve_database_target(setup.application.DATABASE_URL, None, allow_default=False)
    app = setup.application
    parsed = urlparse(app.DATABASE_URL)
    if (
        not app.USE_MYSQL
        or app._DATABASE_CONFIG_ERROR is not None
        or target.identity != CONFIRM_IDENTITY
        or app.DATABASE_TARGET is None
        or app.DATABASE_TARGET.identity != CONFIRM_IDENTITY
        or not app.DATABASE_TARGET.mysql
        or (parsed.hostname or "").casefold() != EXPECTED_HOST
        or (parsed.port or 3306) != EXPECTED_PORT
        or parsed.path.lstrip("/") != EXPECTED_SCHEMA
        or unquote(parsed.username or "") != EXPECTED_USER
        or unquote(parsed.password or "") != os.environ["CAREERPATH_MYSQL_TEST_PASSWORD"]
    ):
        raise HarnessRefused("Flask setup target does not match the approved MySQL target.")

    # setup.main(--schema) calls application.init_db(), which calls
    # application.connect_db(). Guard that exact boundary and validate the
    # server-reported connection identity before init_db can issue DDL.
    original_connect = app.connect_db

    def verified_connect():
        current = resolve_database_target(app.DATABASE_URL, None, allow_default=False)
        current_url = urlparse(app.DATABASE_URL)
        if (
            not app.USE_MYSQL
            or app._DATABASE_CONFIG_ERROR is not None
            or current.identity != CONFIRM_IDENTITY
            or app.DATABASE_TARGET is None
            or app.DATABASE_TARGET.identity != CONFIRM_IDENTITY
            or not app.DATABASE_TARGET.mysql
            or (current_url.hostname or "").casefold() != EXPECTED_HOST
            or (current_url.port or 3306) != EXPECTED_PORT
            or current_url.path.lstrip("/") != EXPECTED_SCHEMA
            or unquote(current_url.username or "") != EXPECTED_USER
            or unquote(current_url.password or "") != os.environ["CAREERPATH_MYSQL_TEST_PASSWORD"]
        ):
            raise HarnessRefused("Flask connection configuration changed before connect; refusing DDL.")
        conn = original_connect()
        try:
            row = conn.execute(
                "SELECT VERSION() AS version, DATABASE() AS schema_name, "
                "CURRENT_USER() AS account, @@hostname AS server, @@port AS port"
            ).fetchone()
            if (
                row["version"] != EXPECTED_VERSION
                or row["schema_name"] != EXPECTED_SCHEMA
                or row["account"] != f"{EXPECTED_USER}@localhost"
                or str(row["server"]).casefold() != EXPECTED_SERVER.casefold()
                or int(row["port"]) != EXPECTED_PORT
            ):
                raise HarnessRefused("Connected identity changed at the schema initialization boundary.")
            return conn
        except Exception:
            conn.close()
            raise

    app.connect_db = verified_connect
    try:
        return setup.main([
            "--schema", "--confirm-target", CONFIRM_IDENTITY,
            # This schema name is not recognized by the generic *_test suffix rule;
            # the exact target and restricted account are independently gated here.
            "--allow-non-test-target",
        ])
    finally:
        app.connect_db = original_connect


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("preflight-empty", help="read-only identity/grant check before approved initialization")
    init_parser = commands.add_parser("initialize", help="schema-changing; requires explicit approval flag")
    init_parser.add_argument("--approve-schema-init", required=True, choices=[EXPECTED_SCHEMA])
    init_parser.add_argument("--confirm-target", required=True, choices=[CONFIRM_IDENTITY])
    commands.add_parser("preflight-initialized", help="read-only check before running integration tests")
    commands.add_parser("test", help="run dedicated MySQL tests; writes disposable rows and cleans them")
    args = parser.parse_args(argv)
    try:
        if args.command == "preflight-empty":
            preflight("empty")
            return 0
        if args.command == "initialize":
            if args.approve_schema_init != EXPECTED_SCHEMA or args.confirm_target != CONFIRM_IDENTITY:
                raise HarnessRefused("Explicit schema approval or target confirmation did not match.")
            preflight("empty")
            database_url, _ = _configuration()
            return _load_setup_and_initialize(database_url)
        if args.command == "preflight-initialized":
            preflight("initialized")
            return 0
        if args.command == "test":
            preflight("initialized")
            database_url, _ = _configuration()
            env = _safe_environment(database_url)
            completed = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", "tests/mysql_integration", "-p", "test_mysql_workflow.py", "-v"],
                env=env, check=False,
            )
            return completed.returncode
    except HarnessRefused as exc:
        print(f"Harness refused: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
