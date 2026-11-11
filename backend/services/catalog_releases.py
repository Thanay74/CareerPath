"""Crash-safe, file-backed career catalog releases selected by one pointer."""
from dataclasses import dataclass
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
import csv
import hashlib
import io
import json
import os
import re
import secrets

from backend.catalog_validation import validate_career_records
from backend.interprocess_lock import interprocess_file_lock

ROOT = Path(__file__).resolve().parents[2]
RELEASES_DIR = ROOT / "data" / "career_releases"
ACTIVE_MANIFEST = ROOT / "data" / "career_active.json"
MANAGED_MARKER = ROOT / "data" / "career_catalog_managed.json"
ACTIVATION_LOCK = ROOT / "data" / "career_catalog_activation.lock"
METADATA_FIELDS = ("family", "keywords", "active", "qualification_notes", "sources")
RELEASE_VERSION = 1
RELEASE_ID_RE = re.compile(r"^[a-f0-9]{64}$")
_CURRENT_SNAPSHOT = ContextVar("career_catalog_snapshot", default=None)


class CatalogReleaseError(RuntimeError):
    pass


class ManifestActivationFailure(CatalogReleaseError):
    """An exception during pointer activation, including post-replace fsync."""
    def __init__(self, release_id, pointer_replaced, cause):
        self.release_id = release_id
        self.pointer_replaced = pointer_replaced
        self.cause = cause
        super().__init__(f"Manifest activation failed ({type(cause).__name__})")


class CatalogActivationError(CatalogReleaseError):
    """Activation outcome established, or explicitly indeterminate, after failure."""
    def __init__(self, outcome, release_id, diagnostic, snapshot=None, durability_uncertain=False):
        self.outcome = outcome
        self.release_id = release_id
        self.diagnostic = diagnostic
        self.snapshot = snapshot
        self.durability_uncertain = durability_uncertain
        super().__init__(diagnostic)


@dataclass(frozen=True)
class CatalogSnapshot:
    rows: list
    metadata: dict
    csv_bytes: bytes
    metadata_bytes: bytes
    fingerprint: str
    release_id: str | None


def _fingerprint(csv_bytes, metadata_bytes):
    digest = hashlib.sha256()
    for label, content in ((b"csv", csv_bytes), (b"metadata", metadata_bytes)):
        digest.update(label); digest.update(len(content).to_bytes(8, "big")); digest.update(content)
    return digest.hexdigest()


def _sha256(content):
    return hashlib.sha256(content).hexdigest()


def _strict_json(content, label):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise CatalogReleaseError(f"{label} contains duplicate JSON keys")
            result[key] = value
        return result
    try:
        return json.loads(content.decode("utf-8"), object_pairs_hook=pairs)
    except CatalogReleaseError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CatalogReleaseError(f"{label} is malformed JSON") from exc


def _validated_snapshot(csv_bytes, metadata_bytes, release_id=None):
    metadata = _strict_json(metadata_bytes, "Career metadata")
    if not isinstance(metadata, dict):
        raise CatalogReleaseError("Career metadata must be an object keyed by career_id")
    try:
        rows = list(csv.DictReader(io.StringIO(csv_bytes.decode("utf-8-sig"), newline="")))
    except (UnicodeError, csv.Error) as exc:
        raise CatalogReleaseError("Career CSV is malformed") from exc
    if not rows:
        raise CatalogReleaseError("Career release contains no records")
    errors = validate_career_records(rows, metadata)
    if errors:
        raise CatalogReleaseError("Career release validation failed: " + "; ".join(errors))
    for row in rows:
        row.update(metadata.get(row.get("career_id", ""), {}))
    return CatalogSnapshot(rows, metadata, csv_bytes, metadata_bytes, _fingerprint(csv_bytes, metadata_bytes), release_id)


def _read_release(release_id, releases_dir=None):
    root = Path(releases_dir or RELEASES_DIR).resolve()
    if not isinstance(release_id, str) or not RELEASE_ID_RE.fullmatch(release_id):
        raise CatalogReleaseError("Active catalog manifest has an invalid release_id")
    directory = (root / release_id).resolve()
    if directory.parent != root:
        raise CatalogReleaseError("Active catalog release path is invalid")
    try:
        release_manifest_bytes = (directory / "release.json").read_bytes()
        csv_bytes = (directory / "career_knowledge_base.csv").read_bytes()
        metadata_bytes = (directory / "career_metadata.json").read_bytes()
    except OSError as exc:
        raise CatalogReleaseError(f"Active catalog release {release_id} is incomplete or missing") from exc
    release = _strict_json(release_manifest_bytes, "Release manifest")
    if release != {
        "schema_version": RELEASE_VERSION,
        "release_id": release_id,
        "career_knowledge_base.csv": _sha256(csv_bytes),
        "career_metadata.json": _sha256(metadata_bytes),
    }:
        raise CatalogReleaseError("Career release manifest does not match its catalog files")
    if _fingerprint(csv_bytes, metadata_bytes) != release_id:
        raise CatalogReleaseError("Career release content does not match its release_id")
    return _validated_snapshot(csv_bytes, metadata_bytes, release_id)


def load_active_catalog(canonical_csv, canonical_metadata, *, active_manifest=None, releases_dir=None, managed_marker=None, ignore_context=False):
    current = None if ignore_context else _CURRENT_SNAPSHOT.get()
    if current is not None and Path(canonical_csv).resolve()==current[0] and Path(canonical_metadata).resolve()==current[1]:
        return current[2]
    pointer = Path(active_manifest or ACTIVE_MANIFEST)
    marker = Path(managed_marker or MANAGED_MARKER)
    try:
        pointer_bytes = pointer.read_bytes()
    except FileNotFoundError:
        pointer_bytes = None
    except OSError as exc:
        raise CatalogReleaseError("Could not read the active career catalog pointer") from exc
    if pointer_bytes is not None:
        manifest = _strict_json(pointer_bytes, "Active catalog manifest")
        if not isinstance(manifest, dict) or set(manifest) != {"schema_version", "release_id"} or manifest.get("schema_version") != RELEASE_VERSION:
            raise CatalogReleaseError("Active catalog manifest has an unsupported or incomplete structure")
        return _read_release(manifest["release_id"], releases_dir)
    if marker.exists():
        try:
            managed = _strict_json(marker.read_bytes(), "Catalog managed marker")
        except OSError as exc:
            raise CatalogReleaseError("Could not read catalog managed marker; refusing canonical fallback") from exc
        if managed != {"schema_version": RELEASE_VERSION}:
            raise CatalogReleaseError("Catalog managed marker is invalid; refusing canonical fallback")
        raise CatalogReleaseError("Active catalog manifest is missing after versioned catalog activation")
    try:
        csv_bytes = Path(canonical_csv).read_bytes()
        metadata_bytes = Path(canonical_metadata).read_bytes()
        if (csv_bytes,metadata_bytes)!=(Path(canonical_csv).read_bytes(),Path(canonical_metadata).read_bytes()):
            raise CatalogReleaseError("Canonical career catalogs changed while being read; retry after the update is complete")
    except CatalogReleaseError:
        raise
    except OSError as exc:
        raise CatalogReleaseError("No active release pointer or complete canonical catalog pair is available") from exc
    return _validated_snapshot(csv_bytes, metadata_bytes)


@contextmanager
def catalog_read_context(canonical_csv, canonical_metadata, *, active_manifest=None, releases_dir=None, managed_marker=None):
    """Pin a single complete release for every reader within one recommendation run."""
    snapshot=load_active_catalog(canonical_csv,canonical_metadata,active_manifest=active_manifest,releases_dir=releases_dir,managed_marker=managed_marker)
    token=_CURRENT_SNAPSHOT.set((Path(canonical_csv).resolve(),Path(canonical_metadata).resolve(),snapshot))
    try: yield snapshot
    finally: _CURRENT_SNAPSHOT.reset(token)


def _serialize_release(rows, current_csv_bytes):
    current_reader = csv.DictReader(io.StringIO(current_csv_bytes.decode("utf-8-sig"), newline=""))
    fields = current_reader.fieldnames
    if not fields:
        raise CatalogReleaseError("Cannot publish because the active catalog has no CSV header")
    metadata = {}
    csv_output = io.StringIO(newline="")
    writer = csv.DictWriter(csv_output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key, "") for key in fields})
        extra = {key: row[key] for key in METADATA_FIELDS if key in row}
        if extra:
            metadata[row["career_id"]] = extra
    metadata_bytes = (json.dumps(metadata, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    csv_bytes = csv_output.getvalue().encode("utf-8")
    errors = validate_career_records(rows, metadata)
    if errors:
        raise CatalogReleaseError("Staged career catalog validation failed: " + "; ".join(errors))
    _validated_snapshot(csv_bytes, metadata_bytes)
    return csv_bytes, metadata_bytes


def _fsync_directory(path):
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _prepare_release(csv_bytes, metadata_bytes, releases_dir=None):
    root = Path(releases_dir or RELEASES_DIR)
    root.mkdir(parents=True, exist_ok=True)
    release_id = _fingerprint(csv_bytes, metadata_bytes)
    destination = root / release_id
    if destination.exists():
        snapshot = _read_release(release_id, root)
        if snapshot.csv_bytes != csv_bytes or snapshot.metadata_bytes != metadata_bytes:
            raise CatalogReleaseError("An existing immutable release directory does not match its release_id")
        return release_id
    staging = root / (".staging-" + secrets.token_hex(12))
    staging.mkdir()
    try:
        files = {
            "career_knowledge_base.csv": csv_bytes,
            "career_metadata.json": metadata_bytes,
            "release.json": (json.dumps({
                "schema_version": RELEASE_VERSION,
                "release_id": release_id,
                "career_knowledge_base.csv": _sha256(csv_bytes),
                "career_metadata.json": _sha256(metadata_bytes),
            }, sort_keys=True, indent=2) + "\n").encode("utf-8"),
        }
        for name, content in files.items():
            with (staging / name).open("xb") as output:
                output.write(content); output.flush(); os.fsync(output.fileno())
        _validated_snapshot(csv_bytes, metadata_bytes, release_id)
        _fsync_directory(staging)
        os.rename(staging, destination)
        _fsync_directory(root)
    except Exception:
        if staging.exists():
            for child in staging.iterdir(): child.unlink(missing_ok=True)
            staging.rmdir()
        raise
    _read_release(release_id, root)
    return release_id


def _atomic_replace_manifest(active_manifest, release_id):
    pointer = Path(active_manifest or ACTIVE_MANIFEST)
    pointer.parent.mkdir(parents=True, exist_ok=True)
    staging = pointer.parent / ("." + pointer.name + "." + secrets.token_hex(12) + ".tmp")
    content = (json.dumps({"schema_version": RELEASE_VERSION, "release_id": release_id}, sort_keys=True) + "\n").encode("utf-8")
    replaced = False
    try:
        with staging.open("xb") as output:
            output.write(content); output.flush(); os.fsync(output.fileno())
        os.replace(staging, pointer)
        replaced = True
        _fsync_directory(pointer.parent)
    except Exception as exc:
        raise ManifestActivationFailure(release_id, replaced, exc) from exc
    finally:
        staging.unlink(missing_ok=True)


def _verified_activation_failure(exc, release_id, canonical_csv, canonical_metadata, *, active_manifest, releases_dir, managed_marker):
    """Re-read the actual selected release before describing a failed switch."""
    try:
        active = load_active_catalog(
            canonical_csv, canonical_metadata, active_manifest=active_manifest,
            releases_dir=releases_dir, managed_marker=managed_marker, ignore_context=True,
        )
    except Exception as verify_exc:
        return CatalogActivationError(
            "indeterminate", release_id,
            f"Activation outcome is indeterminate; pointer/release verification failed ({type(verify_exc).__name__}) after {type(exc).__name__}.",
        )
    if active.release_id == release_id:
        return CatalogActivationError(
            "committed", release_id,
            f"Release {release_id} is active; activation reported {type(exc).__name__}.",
            snapshot=active,
            durability_uncertain=isinstance(exc, ManifestActivationFailure) and exc.pointer_replaced,
        )
    return CatalogActivationError(
        "not_committed", release_id,
        f"Release {release_id} is not active; the current active release was verified after {type(exc).__name__}.",
        snapshot=active,
    )


def _ensure_managed_marker(managed_marker=None):
    marker = Path(managed_marker or MANAGED_MARKER)
    marker.parent.mkdir(parents=True, exist_ok=True)
    if marker.exists():
        try: data = _strict_json(marker.read_bytes(), "Catalog managed marker")
        except OSError as exc: raise CatalogReleaseError("Could not read catalog managed marker") from exc
        if data != {"schema_version": RELEASE_VERSION}:
            raise CatalogReleaseError("Catalog managed marker is invalid")
        return
    staging = marker.parent / ("." + marker.name + "." + secrets.token_hex(12) + ".tmp")
    try:
        with staging.open("xb") as output:
            output.write((json.dumps({"schema_version": RELEASE_VERSION}, sort_keys=True) + "\n").encode("utf-8"))
            output.flush(); os.fsync(output.fileno())
        os.replace(staging, marker)
        _fsync_directory(marker.parent)
    finally:
        staging.unlink(missing_ok=True)


def publish_catalog(rows, expected_fingerprint, canonical_csv, canonical_metadata, *, active_manifest=None, releases_dir=None, activation_lock=None, managed_marker=None):
    pointer = Path(active_manifest or ACTIVE_MANIFEST)
    root = Path(releases_dir or RELEASES_DIR)
    lock = Path(activation_lock or ACTIVATION_LOCK)
    with interprocess_file_lock(lock):
        current = load_active_catalog(canonical_csv, canonical_metadata, active_manifest=pointer, releases_dir=root, managed_marker=managed_marker,ignore_context=True)
        if current.fingerprint != expected_fingerprint:
            raise CatalogReleaseError("Active career catalog changed since this draft was prepared; reload and stage a new draft")
        csv_bytes, metadata_bytes = _serialize_release(rows, current.csv_bytes)
        release_id = _fingerprint(csv_bytes, metadata_bytes)
        try:
            if current.release_id is None:
                # Preserve the pre-release active pair as a rollback target before
                # switching the pointer away from the legacy canonical files.
                baseline_id = _prepare_release(current.csv_bytes, current.metadata_bytes, root)
                _atomic_replace_manifest(pointer, baseline_id)
                _ensure_managed_marker(managed_marker)
            prepared_id = _prepare_release(csv_bytes, metadata_bytes, root)
            _read_release(prepared_id, root)
            _atomic_replace_manifest(pointer, prepared_id)
        except Exception as exc:
            raise _verified_activation_failure(
                exc, release_id, canonical_csv, canonical_metadata,
                active_manifest=pointer, releases_dir=root, managed_marker=managed_marker,
            ) from exc
        try:
            return load_active_catalog(canonical_csv, canonical_metadata, active_manifest=pointer, releases_dir=root, managed_marker=managed_marker,ignore_context=True)
        except Exception as exc:
            raise _verified_activation_failure(
                exc, release_id, canonical_csv, canonical_metadata,
                active_manifest=pointer, releases_dir=root, managed_marker=managed_marker,
            ) from exc


def restore_release(release_id, expected_fingerprint, canonical_csv, canonical_metadata, *, active_manifest=None, releases_dir=None, activation_lock=None, managed_marker=None):
    pointer = Path(active_manifest or ACTIVE_MANIFEST)
    root = Path(releases_dir or RELEASES_DIR)
    lock = Path(activation_lock or ACTIVATION_LOCK)
    with interprocess_file_lock(lock):
        current = load_active_catalog(canonical_csv, canonical_metadata, active_manifest=pointer, releases_dir=root, managed_marker=managed_marker,ignore_context=True)
        if current.fingerprint != expected_fingerprint:
            raise CatalogReleaseError("Active career catalog changed; reload before restoring a release")
        target = _read_release(release_id, root)
        try:
            _atomic_replace_manifest(pointer, target.release_id)
        except Exception as exc:
            raise _verified_activation_failure(
                exc, target.release_id, canonical_csv, canonical_metadata,
                active_manifest=pointer, releases_dir=root, managed_marker=managed_marker,
            ) from exc
        try:
            return load_active_catalog(canonical_csv, canonical_metadata, active_manifest=pointer, releases_dir=root, managed_marker=managed_marker,ignore_context=True)
        except Exception as exc:
            raise _verified_activation_failure(
                exc, target.release_id, canonical_csv, canonical_metadata,
                active_manifest=pointer, releases_dir=root, managed_marker=managed_marker,
            ) from exc


def list_releases(*, active_manifest=None, releases_dir=None, managed_marker=None):
    pointer = Path(active_manifest or ACTIVE_MANIFEST)
    marker = Path(managed_marker or MANAGED_MARKER)
    root = Path(releases_dir or RELEASES_DIR)
    active_id = None
    if pointer.exists():
        manifest = _strict_json(pointer.read_bytes(), "Active catalog manifest")
        if not isinstance(manifest, dict) or set(manifest) != {"schema_version", "release_id"} or manifest.get("schema_version") != RELEASE_VERSION:
            raise CatalogReleaseError("Active catalog manifest has an unsupported or incomplete structure")
        active_id = manifest["release_id"]
        _read_release(active_id, root)
    elif marker.exists():
        raise CatalogReleaseError("Active catalog manifest is missing after versioned catalog activation")
    releases = []
    if root.exists():
        for path in root.iterdir():
            if path.is_dir() and RELEASE_ID_RE.fullmatch(path.name):
                snapshot = _read_release(path.name, root)
                releases.append({"release_id": path.name, "fingerprint": snapshot.fingerprint, "active": path.name == active_id})
    return sorted(releases, key=lambda release: release["release_id"], reverse=True)
