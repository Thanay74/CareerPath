"""Database target parsing and safe, credential-free target identity helpers."""
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse


class DatabaseTargetError(ValueError):
    pass


@dataclass(frozen=True)
class DatabaseTarget:
    driver: str
    host: str
    database: str
    identity: str
    sqlite_path: Path | None = None
    mysql: bool = False


def resolve_database_target(database_url, sqlite_path=None, *, allow_default=False, project_root=None):
    url = (database_url or "").strip()
    if not url:
        if sqlite_path:
            path = Path(sqlite_path).expanduser().resolve()
        elif allow_default:
            root = Path(project_root) if project_root else Path.cwd()
            path = (root / "careerpath.sqlite3").resolve()
        else:
            raise DatabaseTargetError("No explicit database target is configured")
        return DatabaseTarget("SQLite", "local", str(path), f"sqlite:///{path.as_posix()}", path, False)

    try:
        parsed = urlparse(url)
        parsed_port = parsed.port
        parsed_host = parsed.hostname
    except ValueError as exc:
        raise DatabaseTargetError("Database URL is malformed") from exc
    if parsed.scheme in ("mysql", "mysql+pymysql"):
        if not parsed_host or not parsed.path or parsed.path == "/" or parsed.query or parsed.fragment:
            raise DatabaseTargetError("MySQL URL must specify an unambiguous host and database, without query or fragment")
        if parsed.username is None:
            raise DatabaseTargetError("MySQL URL must specify a database user")
        database = unquote(parsed.path.lstrip("/"))
        if not database or "/" in database:
            raise DatabaseTargetError("MySQL URL must specify exactly one database name")
        host = parsed_host.lower()
        port = parsed_port or 3306
        identity = f"mysql+pymysql://{host}:{port}/{database}"
        return DatabaseTarget("MySQL (PyMySQL)", host, database, identity, None, True)

    if parsed.scheme == "sqlite":
        if parsed.netloc not in ("", "localhost") or parsed.query or parsed.fragment:
            raise DatabaseTargetError("SQLite URL must identify a local file without query or fragment")
        raw_path = unquote(url[len("sqlite:///"):]) if url.startswith("sqlite:///") else ""
        if not raw_path:
            raise DatabaseTargetError("SQLite URL must include a file path")
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            root = Path(project_root) if project_root else Path.cwd()
            path = root / path
        path = path.resolve()
        return DatabaseTarget("SQLite", "local", str(path), f"sqlite:///{path.as_posix()}", path, False)

    raise DatabaseTargetError(f"Unsupported database URL scheme: {parsed.scheme or '(missing)'}")


def is_test_target(target):
    if target.mysql:
        name = target.database.casefold()
        return name in {"test", "testing"} or name.endswith(("_test", "-test")) or name.startswith(("test_", "test-"))
    path = target.sqlite_path
    if path is None:
        return False
    components = [part.casefold() for part in path.parts]
    filename = path.stem.casefold()
    return any(part in {".test-tmp", "test", "tests", "tmp", "temp"} for part in components) or filename in {"test", "testing"} or filename.endswith(("_test", "-test")) or filename.startswith(("test_", "test-"))


def validate_setup_target(target, confirmation, allow_non_test=False):
    if target.database.strip().casefold() == "careerpath" or (target.sqlite_path and target.sqlite_path.stem.strip().casefold() == "careerpath"):
        raise DatabaseTargetError("The production CareerPath database name is blocked for setup commands")
    if not confirmation or confirmation != target.identity:
        raise DatabaseTargetError("--confirm-target must exactly match the resolved credential-free target identity")
    if not is_test_target(target) and not allow_non_test:
        raise DatabaseTargetError("Non-test database targets require --allow-non-test-target")
    return target
