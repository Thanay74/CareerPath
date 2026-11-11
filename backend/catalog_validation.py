"""Read-only structural validation for the maintained file-backed catalogs."""
from __future__ import annotations

import csv
import json
import math
import re
from pathlib import Path

from backend.education_catalog import EDUCATION_CATALOG

ROOT = Path(__file__).resolve().parents[1]
CAREER_CSV = ROOT / "data" / "career_knowledge_base.csv"
CAREER_METADATA = ROOT / "data" / "career_metadata.json"
LEVELS = ("10th", "12th", "Bachelor's", "Master's")
CAREER_FIELDS = {
    "career_id", "career_name", "description", "minimum_education_level",
    "suitable_streams", "required_subjects", "aptitude_requirements",
    "technical_skills", "employability_skills", "interest_requirements",
    "recommended_degrees", "optional_certifications",
}
SCORE_FIELDS = ("aptitude_requirements", "technical_skills", "employability_skills", "interest_requirements")
CAREER_FAMILIES = {"technology_engineering", "health_life_sciences", "business_finance", "creative_communication", "public_social_research"}


def validate_education_catalog(catalog=EDUCATION_CATALOG):
    errors = []
    if not isinstance(catalog, dict):
        return ["education catalog must be an object"]
    if set(catalog) != set(LEVELS):
        errors.append("education catalog must define exactly: " + ", ".join(LEVELS))
    for level, entry in catalog.items():
        if not isinstance(entry, dict):
            errors.append(f"{level}: catalog entry must be an object")
            continue
        streams, degrees = entry.get("streams"), entry.get("degrees")
        if not isinstance(streams, list) or not all(isinstance(x, str) and x.strip() for x in streams):
            errors.append(f"{level}: streams must be a list of non-empty strings")
            streams = []
        elif len({x.casefold() for x in streams}) != len(streams):
            errors.append(f"{level}: duplicate stream identifiers")
        if not isinstance(degrees, list) or not all(isinstance(x, str) and x.strip() for x in degrees):
            errors.append(f"{level}: degrees must be a list of non-empty strings")
            degrees = []
        elif len({x.casefold() for x in degrees}) != len(degrees):
            errors.append(f"{level}: duplicate degree identifiers")
        specializations = entry.get("specializations", {})
        if not isinstance(specializations, dict):
            errors.append(f"{level}: specializations must be an object")
            specializations = {}
        for degree, specs in specializations.items():
            if degree not in degrees:
                errors.append(f"{level}: specialization references unknown degree {degree!r}")
            if not isinstance(specs, list) or not all(isinstance(x, str) and x.strip() for x in specs):
                errors.append(f"{level}: specializations for {degree!r} must be non-empty strings")
            elif len({x.casefold() for x in specs}) != len(specs):
                errors.append(f"{level}: duplicate specialization identifier under {degree!r}")
        subjects = entry.get("subjects")
        if not isinstance(subjects, dict) or not subjects:
            errors.append(f"{level}: subjects must be a non-empty object")
            continue
        for key, values in subjects.items():
            if not isinstance(key, str) or not key.strip() or not isinstance(values, list) or not all(isinstance(x, str) and x.strip() for x in values):
                errors.append(f"{level}: malformed subject list for {key!r}")
                continue
            if len({x.casefold() for x in values}) != len(values):
                errors.append(f"{level}: duplicate subject identifier under {key!r}")
            if level in ("10th", "12th"):
                if level == "10th" and key != "default": errors.append(f"{level}: unknown subject group {key!r}")
                if level == "12th" and key not in streams: errors.append(f"{level}: subject group references unknown stream {key!r}")
            elif key not in degrees and "|" not in key:
                errors.append(f"{level}: subject group references unknown degree {key!r}")
            elif "|" in key:
                degree, specialization = key.split("|", 1)
                if degree not in degrees or specialization not in specializations.get(degree, []):
                    errors.append(f"{level}: subject group references unknown degree/specialization {key!r}")
    return errors


def validate_career_records(records, metadata=None):
    errors = []
    known_streams={stream.casefold() for entry in EDUCATION_CATALOG.values() for stream in entry.get("streams", [])}
    if not isinstance(records, list):
        return ["career catalog must be a list"]
    ids, names = set(), set()
    for index, row in enumerate(records, 1):
        prefix = f"career record {index}"
        if not isinstance(row, dict):
            errors.append(f"{prefix}: must be an object")
            continue
        missing = CAREER_FIELDS - set(row)
        if missing: errors.append(f"{prefix}: missing required fields {', '.join(sorted(missing))}")
        career_id, name = row.get("career_id"), row.get("career_name")
        if not isinstance(career_id, str) or not re.fullmatch(r"C\d+", career_id):
            errors.append(f"{prefix}: career_id must use stable C<number> format")
        elif career_id in ids: errors.append(f"{prefix}: duplicate career_id {career_id}")
        else: ids.add(career_id)
        if not isinstance(name, str) or not name.strip(): errors.append(f"{prefix}: career_name must be non-empty")
        elif name.strip().casefold() in names: errors.append(f"{prefix}: duplicate career_name {name.strip()!r}")
        else: names.add(name.strip().casefold())
        if row.get("minimum_education_level") not in LEVELS: errors.append(f"{prefix}: unsupported minimum_education_level")
        for field in CAREER_FIELDS - {"career_id", "career_name", "minimum_education_level"}:
            value = row.get(field)
            if not isinstance(value, str): errors.append(f"{prefix}: {field} must be text")
        streams=row.get("suitable_streams", "")
        if isinstance(streams,str):
            for stream in (item.strip() for item in streams.split(";") if item.strip()):
                if stream.casefold() not in known_streams: errors.append(f"{prefix}: suitable_streams references unknown stream {stream!r}")
        for field in SCORE_FIELDS:
            value = row.get(field, "")
            if not isinstance(value, str): continue
            seen = set()
            for item in filter(None, (part.strip() for part in value.split(";"))):
                if ":" not in item:
                    errors.append(f"{prefix}: malformed score entry in {field}: {item!r}"); continue
                key, raw_score = (part.strip() for part in item.split(":", 1))
                try: score = float(raw_score)
                except ValueError: score = math.nan
                if not key or key in seen: errors.append(f"{prefix}: empty or duplicate score key in {field}: {key!r}")
                if not math.isfinite(score) or not 0 <= score <= 100: errors.append(f"{prefix}: score in {field} must be between 0 and 100")
                seen.add(key)
    if metadata is not None:
        if not isinstance(metadata, dict): return errors + ["career metadata must be an object keyed by career_id"]
        for career_id, item in metadata.items():
            if career_id not in ids: errors.append(f"career metadata references unknown career_id {career_id!r}")
            if not isinstance(item, dict): errors.append(f"career metadata for {career_id!r} must be an object"); continue
            if "family" in item and item["family"] not in CAREER_FAMILIES: errors.append(f"career metadata family for {career_id!r} is unsupported")
            if "active" in item and type(item["active"]) is not bool: errors.append(f"career metadata active flag for {career_id!r} must be boolean")
            if "qualification_notes" in item and not isinstance(item["qualification_notes"],str): errors.append(f"career metadata qualification_notes for {career_id!r} must be text")
            for field in ("keywords", "sources"):
                if field in item and (not isinstance(item[field], list) or not all(isinstance(x, str) and x.strip() for x in item[field])):
                    errors.append(f"career metadata {field} for {career_id!r} must be a list of non-empty strings")
    return errors


def validate_project_catalogs(career_csv=CAREER_CSV, metadata_json=CAREER_METADATA):
    errors = validate_education_catalog()
    try:
        with Path(career_csv).open(encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            headers = set(reader.fieldnames or [])
            missing = CAREER_FIELDS - headers
            if missing: errors.append("career CSV missing required columns: " + ", ".join(sorted(missing)))
            rows = list(reader)
        metadata = json.loads(Path(metadata_json).read_text(encoding="utf-8"))
        errors.extend(validate_career_records(rows, metadata))
    except (OSError, csv.Error, json.JSONDecodeError) as exc:
        errors.append(f"could not read career catalogs: {exc}")
    return errors
