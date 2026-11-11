# CareerPath Versioned Career Catalog Releases

## Status

Implemented for the file-based career catalog. Career publishing is enabled only through the validated release path described here. The education catalog, MySQL catalog tables, student records, and canonical career source files remain unchanged.

## Current data flow

```text
Admin edit/create/deactivate
        │
        ▼
Shared staged draft JSON ── validation + base fingerprint
        │                         │
        └── publish request ──────┘
                    │
                    ▼
      cross-process activation lock
                    │
       current fingerprint compare
                    │
       serialize and validate CSV+JSON
                    │
     new immutable content-addressed release
                    │
   atomic replace of data/career_active.json
                    │
                    ▼
Recommendation engine reads active pointer once
and loads both files from that release directory.
```

The canonical bootstrap files remain `data/career_knowledge_base.csv` and `data/career_metadata.json`. They are used only while the release pointer and managed marker have never been established. Their pair is validated and double-read for changes before use. Once versioned mode is established, a missing or malformed pointer does not fall back to these files.

## On-disk layout

```text
data/
  career_knowledge_base.csv             # canonical bootstrap, never overwritten
  career_metadata.json                  # canonical bootstrap, never overwritten
  career_catalog_activation.lock        # OS cross-process lock
  career_catalog_managed.json           # fail-closed marker after versioning begins
  career_active.json                     # the sole active-release pointer
  career_releases/
    <sha256-content-id>/
      career_knowledge_base.csv
      career_metadata.json
      release.json
```

The release ID is a SHA-256 fingerprint over both byte sequences with labels and lengths. `release.json` records the format version, ID, and individual file hashes. Existing release directories are never rewritten; their hashes and complete catalog validation are checked whenever read or reused.

## Publish and recovery behavior

1. Admin stage operations capture rows and the fingerprint from the same validated active snapshot. Staging rechecks the fingerprint under a shared OS-backed file lock.
2. Publication re-reads the draft under the draft lock, validates it, then acquires the catalog activation lock and compares the draft base fingerprint with the active pair.
3. Both files and the per-release manifest are written into a new temporary release directory. Each file is flushed and fsynced; the directory is validated before it is renamed into its content-addressed final path.
4. The active pointer is written to a temporary file in the same directory and switched with `os.replace`. No reader observes a CSV from one release and JSON from another.
5. On first activation, the current canonical pair is first copied into a content-addressed rollback release. The pointer is set to that baseline before the managed marker is created and the new release is activated. A crash before the final switch therefore leaves a complete baseline or complete new release active.
6. If validation, stale checking, release construction, or pointer replacement fails before the switch, the previous active pointer remains in place. Complete but unreferenced release directories are safe to retain.
7. After restart, the engine validates the pointer, release manifest, hashes, and career records before returning either file. Invalid or incomplete active data raises an error; it does not mix or silently fall back.
8. Previous releases remain on disk. `POST /api/admin/career-releases/<release_id>/restore` uses an expected current fingerprint and the same activation lock to switch the pointer to a validated prior release. `GET /api/admin/career-releases` lists validated releases.

Recommendation calls pin one catalog snapshot in a context-local read scope. Nested career and roadmap reads in that recommendation use that same CSV/JSON release even if another process activates a newer release mid-request.

## Coordination and boundaries

- Draft reservation/list/discard and publishing share a cross-process lock in `instance/career_drafts/catalog.lock`.
- Release activation and rollback share `data/career_catalog_activation.lock` (`msvcrt.locking` on Windows; `flock` on POSIX).
- Activation uses the same-filesystem pointer rename as the transaction boundary; the source does not rewrite canonical catalog files.
- The application never edits an existing content-addressed release. File hashes make out-of-band corruption detectable. OS-level protection against an administrator with filesystem write access is outside the application lock model.
- External tools editing canonical files do not honor the application lock. Before versioned mode, readers double-check the pair; an unstable read fails closed. After first activation, runtime reads ignore canonical files unless the pointer has never been established.
- Atomic namespace replacement and process-restart recovery were exercised on this Windows environment. Power-loss durability, filesystem/controller behavior under abrupt machine failure, and other operating systems were not independently tested.
- MySQL is not part of this release store. No MySQL integration was attempted.

## Verification criteria covered

Automated isolated tests cover incomplete and malformed pointers, malformed release manifests, corrupted release content, stale drafts, two-process concurrent activation, failures before release/pointer activation, failure at pointer replacement, interruption immediately after a successful atomic switch, reload after restart, pinned per-recommendation reads, and rollback to a previous release. Test catalogs and manifests live only in temporary directories.
