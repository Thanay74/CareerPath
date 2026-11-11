"""Explicit database setup actions. Never run against a database without review."""
import argparse
import sys

from backend import app as application
from backend.database_config import resolve_database_target, validate_setup_target, DatabaseTargetError


def _with_connection(action):
    conn = application.connect_db()
    try:
        action(conn)
        conn.commit()
    finally:
        conn.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--schema", action="store_true", help="create/upgrade application tables (review migrations first)")
    group.add_argument("--seed-education", action="store_true", help="insert missing education catalog lookup rows")
    group.add_argument("--seed-aptitude-fixture", action="store_true", help="insert missing fixture questions; existing question IDs are not updated")
    group.add_argument("--bootstrap-admin", action="store_true", help="create the configured first admin if absent")
    group.add_argument("--validate-catalogs", action="store_true", help="read-only validation of education and career catalog files")
    parser.add_argument("--confirm-target", help="exact credential-free resolved target identity; required for mutations")
    parser.add_argument("--allow-non-test-target", action="store_true", help="allow a reviewed non-test target after exact confirmation")
    args = parser.parse_args(argv)
    if not args.validate_catalogs:
        try:
            configured_url = application.DATABASE_URL
            sqlite_path = None if configured_url else __import__('os').environ.get('CAREERPATH_DB')
            target = resolve_database_target(configured_url, sqlite_path, allow_default=False, project_root=application.ROOT)
            validate_setup_target(target, args.confirm_target, args.allow_non_test_target)
        except DatabaseTargetError as exc:
            print(f"Setup refused: {exc}", file=sys.stderr)
            return 2
        print(f"Setup target: driver={target.driver}, host={target.host}, database={target.database}")
    if args.schema:
        application.init_db()
    elif args.seed_education:
        _with_connection(application.seed_education_catalog)
    elif args.seed_aptitude_fixture:
        _with_connection(application.seed_aptitude_questions)
    elif args.bootstrap_admin:
        application.bootstrap_admin()
    elif args.validate_catalogs:
        from backend.catalog_validation import validate_project_catalogs
        errors=validate_project_catalogs()
        if errors:
            print("Catalog validation failed:")
            for error in errors: print(f" - {error}")
            return 1
        print("Education and career catalogs are structurally valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
