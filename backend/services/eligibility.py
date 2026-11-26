"""Conservative, evidence-driven program eligibility assessment.

The career catalog does not currently contain verified program rules, so the
registry intentionally starts empty. Never infer admission requirements from
similarity, a model-family signal, self-ratings, or a career title.
"""
from __future__ import annotations

from datetime import date
from backend.academic_history import subject_key


# Add records only after review of an official, applicable source and date.
# Optional fields: required_degrees, required_subjects_all,
# required_examinations, additional_qualifications, bridge_courses,
# institution_restrictions, alternative_routes.
VERIFIED_PROGRAM_RULES = {}
ELIGIBILITY_ORDER = {
    "eligible_now": 0,
    "eligible_after_additional_qualification": 1,
    "potentially_eligible_alternative_route": 2,
    "eligibility_not_verified": 3,
    "not_currently_eligible": 4,
}


def _rule_is_current(rule):
    if not isinstance(rule, dict) or not isinstance(rule.get("source_url"), str) or not rule["source_url"].startswith("https://"):
        return False
    if not any(rule.get(field) for field in ("required_degrees", "required_subjects_all", "required_examinations")):
        return False
    for field in ("required_degrees", "required_subjects_all", "required_examinations"):
        value = rule.get(field, [])
        if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
            return False
    try:
        verified = date.fromisoformat(rule.get("last_verified_at", ""))
    except (TypeError, ValueError):
        return False
    return verified <= date.today()


def _check_route(profile, route):
    """Return whether the route is known, whether it is met, and explanations."""
    history = profile.get("academic_history") or {}
    unknown, unmet = [], []
    degrees = route.get("required_degrees", [])
    if degrees:
        actual_degree = profile.get("degree") if profile.get("education_level") in ("Bachelor's", "Master's") else None
        if profile.get("education_level") == "Master's":
            actual_degree = history.get("previous_degree") if history.get("previous_degree_status") == "provided" else None
        if actual_degree is None:
            unknown.append("previous qualification is not recorded")
        elif actual_degree.casefold() not in {item.casefold() for item in degrees}:
            unmet.append("accepted previous qualification")

    required_subjects = route.get("required_subjects_all", [])
    if required_subjects:
        if history.get("subjects_status", "unknown") != "selected":
            unknown.append("actual subjects studied are unknown")
        else:
            actual_subjects = {subject_key(item.strip()) for item in history.get("subjects", [])}
            absent = [item for item in required_subjects if subject_key(item) not in actual_subjects]
            unmet.extend(absent)

    examinations = route.get("required_examinations", [])
    if examinations:
        # Entrance-test history is not yet collected, so never claim it is met.
        unknown.append("required entrance-examination status is not recorded")
    return not unknown, not unmet, unknown, unmet


def assess_eligibility(profile, career, rules=None):
    """Assess only explicit, dated official rules; unknown facts stay unknown."""
    rules = VERIFIED_PROGRAM_RULES if rules is None else rules
    rule = rules.get(career.get("career_id"))
    if not _rule_is_current(rule):
        return {
            "status": "eligibility_not_verified", "label": "Eligibility not verified", "evidence": [],
            "missing_requirements": [],
            "explanation": "No current, reviewed official program rule is available for this career record.",
        }

    known, met, unknown, unmet = _check_route(profile, rule)
    evidence = [rule["source_url"]]
    common = {
        "evidence": evidence,
        "last_verified_at": rule["last_verified_at"],
        "required_examinations": rule.get("required_examinations", []),
        "additional_qualifications": rule.get("additional_qualifications", []),
        "bridge_courses": rule.get("bridge_courses", []),
        "institution_restrictions": rule.get("institution_restrictions", []),
    }

    if known and met:
        additional = common["additional_qualifications"]
        if additional:
            return {**common, "status": "eligible_after_additional_qualification",
                    "label": "Eligible after the listed additional qualification",
                    "missing_requirements": additional,
                    "explanation": "The documented academic route is met; the listed additional qualification remains."}
        return {**common, "status": "eligible_now",
                "label": "Eligible under the documented rule; final admission remains institution-controlled",
                "missing_requirements": [], "explanation": "Recorded academic history meets the documented rule."}

    for alternative in rule.get("alternative_routes", []):
        alt_known, alt_met, alt_unknown, alt_unmet = _check_route(profile, alternative)
        if alt_known and alt_met:
            return {**common, "status": "potentially_eligible_alternative_route",
                    "label": "Potential alternative route; confirm with the institution",
                    "missing_requirements": [],
                    "explanation": alternative.get("label", "A documented alternative route may apply.")}
        unknown.extend(alt_unknown)

    if unknown:
        return {**common, "status": "eligibility_not_verified", "label": "Eligibility not verified",
                "missing_requirements": list(dict.fromkeys(unknown)),
                "explanation": "Required academic or entrance-examination history is incomplete."}
    return {**common, "status": "not_currently_eligible", "label": "Not currently eligible under this verified rule",
            "missing_requirements": unmet,
            "explanation": "The recorded academic history does not meet this program's documented route."}
