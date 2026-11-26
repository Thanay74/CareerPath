"""Versioned, privacy-preserving recommendation snapshot metadata."""
from __future__ import annotations

import hashlib
import json
import math
import uuid
from datetime import datetime, timezone


FORMAT = "careerpath.recommendation-history"
FORMAT_VERSION = 1
# Scoring semantics changed: stage, stream, degree, and missing-evidence
# renormalization are no longer treated as personalized compatibility evidence.
# Versioning the input fingerprint prevents older saved scores from being
# presented as current under the new policy.
INPUT_VERSION = 3
INPUT_FIELDS = (
    "education_level", "stream", "degree", "specialization", "subjects",
    "academic_history",
    "aptitude", "interests", "technical", "employability",
    "career_preferences", "research_interests", "academic_performance",
    "academic_scale",
)
MISSING = {"$missing": True}


def _canonical_value(value):
    if value is None or isinstance(value, (str, bool)):
        return value
    if type(value) in (int, float):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("Recommendation inputs must be finite")
        return number
    if isinstance(value, dict):
        return {str(key): _canonical_value(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    raise ValueError("Recommendation inputs contain an unsupported value")


def recommendation_input_fingerprint(profile):
    """Hash only recommendation-affecting profile fields; never expose inputs."""
    normalized = {
        field: _canonical_value(profile[field]) if field in profile else MISSING
        for field in INPUT_FIELDS
    }
    payload = json.dumps(
        {"input_version": INPUT_VERSION, "inputs": normalized},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def new_snapshot(profile_fingerprint, catalog_fingerprint, recommendations, model_identity=None):
    return {
        "snapshot_id": uuid.uuid4().hex,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input_version": INPUT_VERSION,
        "input_fingerprint": profile_fingerprint,
        "catalog_fingerprint": catalog_fingerprint,
        "model_identity": model_identity,
        "recommendations": recommendations,
    }


def decode_history(value):
    """Return valid history and whether an old/unknown value was encountered."""
    parsed = json.loads(value) if isinstance(value, (str, bytes, bytearray)) else value
    if isinstance(parsed, dict) and parsed.get("format") == FORMAT and parsed.get("format_version") == FORMAT_VERSION:
        snapshots = parsed.get("snapshots")
        legacy = parsed.get("legacy_records")
        if not isinstance(snapshots, list) or not isinstance(legacy, list):
            raise ValueError("Recommendation history is malformed")
        for item in snapshots:
            if (not isinstance(item, dict) or type(item.get("input_version")) is not int
                    or item.get("input_version") < 1
                    or not isinstance(item.get("input_fingerprint"), str)
                    or not isinstance(item.get("catalog_fingerprint"), str)
                    or not isinstance(item.get("recommendations"), list)
                    or not isinstance(item.get("created_at"), str)
                    or not isinstance(item.get("snapshot_id"), str)):
                raise ValueError("Recommendation history contains a malformed snapshot")
            if "model_identity" in item and item["model_identity"] is not None and not isinstance(item["model_identity"], str):
                raise ValueError("Recommendation history contains malformed model lineage")
        return {"format": FORMAT, "format_version": FORMAT_VERSION,
                "snapshots": snapshots, "legacy_records": legacy}, False
    return {"format": FORMAT, "format_version": FORMAT_VERSION,
            "snapshots": [], "legacy_records": [parsed]}, True


def encode_history(history):
    return json.dumps(history, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def select_current_snapshot(history, profile_fingerprint, catalog_fingerprint, model_identity=None):
    # A missing current identity or lineage on an old snapshot is unverified,
    # never an implicit model-version match.
    if not isinstance(model_identity, str) or not model_identity:
        return None
    matches = [item for item in history["snapshots"]
               if item["input_version"] == INPUT_VERSION
               and item["input_fingerprint"] == profile_fingerprint
               and item["catalog_fingerprint"] == catalog_fingerprint
               and item.get("model_identity") == model_identity]
    if not matches:
        return None
    # The stable secondary key makes equal timestamps deterministic.
    return max(matches, key=lambda item: (item["created_at"], item["snapshot_id"]))
