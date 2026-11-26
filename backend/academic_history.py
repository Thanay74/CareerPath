"""Validation and normalization for student-reported academic history.

This data records what a student reports studying; it is not transcript or
institution-verified eligibility evidence.
"""
from __future__ import annotations

import re


LEVEL_FIELDS = {
    "10th": {"board", "qualification", "study_status", "subjects_status", "subjects"},
    "12th": {"board", "qualification", "study_status", "subjects_status", "subjects", "mathematics"},
    "Bachelor's": {"qualification", "study_status", "major", "minor", "specialization", "subjects_status", "subjects", "institution"},
    "Master's": {"qualification", "study_status", "major", "specialization", "subjects_status", "subjects", "institution", "previous_degree_status", "previous_degree"},
}
STUDY_STATUS = {"unknown", "current", "completed", "not_applicable"}
SUBJECT_STATUS = {"unknown", "selected", "not_applicable"}
MATH_STATUS = {"unknown", "yes", "no", "not_applicable"}
PREVIOUS_STATUS = {"unknown", "provided", "not_applicable"}
TEXT_FIELDS = {"board", "qualification", "major", "minor", "specialization", "institution", "previous_degree"}


def subject_key(value):
    key = re.sub(r"[^a-z0-9]", "", value.casefold())
    return {"math": "mathematics", "maths": "mathematics", "phy": "physics", "chem": "chemistry", "bio": "biology"}.get(key, key)


def empty_academic_history(level: str) -> dict:
    fields = LEVEL_FIELDS.get(level, set())
    result = {"study_status": "unknown", "subjects_status": "unknown", "subjects": []}
    if "mathematics" in fields:
        result["mathematics"] = "unknown"
    if "previous_degree_status" in fields:
        result.update(previous_degree_status="unknown", previous_degree="")
    return {key: value for key, value in result.items() if key in fields}


def validate_academic_history(level, value, stream=None):
    """Return (normalized, error); absent history stays explicitly unknown."""
    if level not in LEVEL_FIELDS:
        return None, "Unsupported education level for academic history"
    if value is None:
        return empty_academic_history(level), None
    if not isinstance(value, dict):
        return None, "academic_history must be an object"
    allowed = LEVEL_FIELDS[level]
    if set(value) - allowed:
        return None, "academic_history contains fields that do not apply to this education level"
    result = empty_academic_history(level)
    result.update(value)
    if result.get("study_status") not in STUDY_STATUS:
        return None, "study_status must be unknown, current, completed, or not_applicable"
    if result.get("subjects_status") not in SUBJECT_STATUS:
        return None, "subjects_status must be unknown, selected, or not_applicable"
    subjects = result.get("subjects")
    if not isinstance(subjects, list) or len(subjects) > 80:
        return None, "subjects must be a list of at most 80 subject names"
    normalized_subjects = []
    seen = set()
    for subject in subjects:
        if not isinstance(subject, str) or not subject.strip() or len(subject.strip()) > 100:
            return None, "Each academic subject must be non-empty text of at most 100 characters"
        clean = subject.strip()
        key = clean.casefold()
        if key in seen:
            return None, "academic_history subjects must not contain duplicates"
        seen.add(key)
        normalized_subjects.append(clean)
    result["subjects"] = normalized_subjects
    if result["subjects_status"] == "selected" and not normalized_subjects:
        return None, "Select at least one subject or mark subject information unknown"
    if result["subjects_status"] == "not_applicable" and normalized_subjects:
        return None, "Subjects must be empty when subjects_status is not_applicable"
    for key in TEXT_FIELDS & allowed:
        text = result.get(key, "")
        if text is None:
            text = ""
        if not isinstance(text, str) or len(text) > 200:
            return None, f"{key} must be text of at most 200 characters"
        result[key] = text.strip()
    if "mathematics" in allowed:
        if result.get("mathematics") not in MATH_STATUS:
            return None, "mathematics must be unknown, yes, no, or not_applicable"
        subject_math = any(subject_key(name) == "mathematics" for name in normalized_subjects)
        if result["mathematics"] == "no" and subject_math:
            return None, "Mathematics cannot be marked no when it is listed among studied subjects"
        if result["mathematics"] == "yes" and result["subjects_status"] == "selected" and not subject_math:
            return None, "Add Mathematics to studied subjects or change the mathematics answer"
        if result["mathematics"] == "not_applicable" and result["subjects_status"] == "selected":
            return None, "Mathematics cannot be not_applicable when subjects are selected"
        if stream in ("Science PCM", "Science PCMB") and result["mathematics"] == "no":
            return None, f"{stream} cannot be selected when Mathematics is marked not studied"
        science_core = {
            "Science PCM": {"physics", "chemistry", "mathematics"},
            "Science PCB": {"physics", "chemistry", "biology"},
            "Science PCMB": {"physics", "chemistry", "mathematics", "biology"},
        }.get(stream)
        if science_core and result["subjects_status"] == "selected":
            actual = {subject_key(name) for name in normalized_subjects}
            if not science_core.issubset(actual):
                return None, f"Selected {stream} requires its listed core subjects in academic_history"
    if "previous_degree_status" in allowed:
        if result.get("previous_degree_status") not in PREVIOUS_STATUS:
            return None, "previous_degree_status must be unknown, provided, or not_applicable"
        degree = result.get("previous_degree", "")
        if not isinstance(degree, str) or len(degree) > 200:
            return None, "previous_degree must be text of at most 200 characters"
        result["previous_degree"] = degree.strip()
        if result["previous_degree_status"] == "provided" and not result["previous_degree"]:
            return None, "Provide the previous Bachelor's qualification or mark it unknown"
        if result["previous_degree_status"] != "provided" and result["previous_degree"]:
            return None, "previous_degree must be empty unless its status is provided"
    return result, None
