"""Class 10 progression guidance built from the maintained education/career catalogs.

This module only organizes existing catalog records; it does not assert local
eligibility or invent institutions, prerequisites, or admission requirements.
"""

from backend.education_catalog import EDUCATION_CATALOG


PATHWAY_ROUTES = {
    "Science": {"class12": ("Science PCM", "Science PCB"), "career_streams": ("Science",)},
    "Commerce": {"class12": ("Commerce",), "career_streams": ("Commerce",)},
    "Arts/Humanities": {"class12": ("Arts/Humanities",), "career_streams": ("Arts/Humanities",)},
    "Diploma/Vocational": {"class12": ("Vocational/Diploma",), "career_streams": ("Diploma/Vocational", "Vocational/Diploma")},
}

_BACHELOR_PREFIXES = ("ba ", "b.a", "bsc", "b.sc", "bcom", "b.com", "bba", "bca", "btech", "b.tech", "be/", "b.e", "b.pharm", "bdes", "b.des", "bachelor")

def _is_undergraduate_program(program):
    normalized = program.strip().lower()
    return normalized.startswith(_BACHELOR_PREFIXES)

def _career_options(pathway):
    from backend.services.recommendation_engine import careers
    from backend.services.recommendation_engine import _list

    route = PATHWAY_ROUTES[pathway]
    records = []
    for row in careers():
        streams = _list(row.get("suitable_streams"))
        degrees = [part.strip() for part in (row.get("recommended_degrees") or "").split(";") if part.strip()]
        listed_stream_match = any(stream in streams for stream in route["career_streams"])
        diploma_route_match = pathway == "Diploma/Vocational" and any("diploma" in degree.lower() or "vocational" in degree.lower() for degree in degrees)
        if not listed_stream_match:
            # Vocational routes may be listed as a recommended qualification.
            if not diploma_route_match:
                continue
        records.append({
            "career_id": row["career_id"],
            "career_name": row["career_name"],
            "description": row["description"],
            "minimum_education_level": row["minimum_education_level"],
            "degree_options_from_career_record": degrees,
            "route_rationale": (f"The maintained career record lists {pathway} as a suitable stream. This is a longer-term career option, not a direct post-Class 10 outcome. Confirm the course route, prerequisites, and any additional qualifications with the institution." if listed_stream_match else "The maintained career record lists a diploma/vocational qualification as one possible route toward this longer-term career. This does not establish direct entry or progression; verify recognition and prerequisites."),
            "qualification_notes": row.get("qualification_notes", ""),
            "qualification_sources": row.get("sources", []),
            "source": "CareerPath maintained career knowledge base and metadata",
            "verify_locally": True,
        })
    return records

def build_pathway_roadmap(pathway, profile=None):
    """Build route stages from maintained education catalog and career rows."""
    if pathway not in PATHWAY_ROUTES:
        raise ValueError(f"Unsupported Class 10 pathway: {pathway}")
    profile = profile or {}
    streams = EDUCATION_CATALOG["12th"]["streams"]
    routes = [name for name in PATHWAY_ROUTES[pathway]["class12"] if name in streams]
    catalog_status = "available" if routes else "unavailable"
    stage_options = []
    for name in routes:
        subjects = EDUCATION_CATALOG["12th"]["subjects"].get(name, [])
        stage_options.append({"route": name, "subjects_from_catalog": subjects})
    if pathway == "Diploma/Vocational":
        after10 = "Explore recognized vocational or diploma programs available locally. Confirm recognition, entry criteria, and progression routes with the provider and school counselor."
        class12 = "If continuing through an equivalent or later Class 12 qualification, compare the subjects and prerequisites accepted by the next program. Do not assume every diploma offers the same progression."
    else:
        after10 = (f"Explore the {pathway} route shown in the Class 12 subject catalog. Compare subject combinations with your interests and the schools available to you." if routes else f"The maintained education catalog has no Class 11–12 subject route for {pathway} right now. Ask a school counselor to help identify recognized local options.")
        class12 = ("Complete the selected Class 11–12 route and verify any subject prerequisites required by each future course with the relevant institution." if routes else "No matching route is currently available in the maintained Class 12 catalog. Confirm recognized progression routes with your school or counselor.")
    careers = _career_options(pathway)
    career_directions = [{"career_id": item["career_id"], "career_name": item["career_name"], "description": item["description"], "minimum_education_level": item["minimum_education_level"], "degree_options_from_career_record": item["degree_options_from_career_record"], "route_rationale": item["route_rationale"], "qualification_notes": item["qualification_notes"], "qualification_sources": item["qualification_sources"], "source": item["source"], "verify_locally": True} for item in careers]
    programs = {}
    for item in careers:
        for degree in item["degree_options_from_career_record"]:
            if _is_undergraduate_program(degree):
                programs.setdefault(degree, set()).add(item["career_name"])
    post_12_program_options = [{"program_text_from_career_record": degree, "career_directions_in_record": sorted(names), "source": "CareerPath maintained career knowledge base", "verify_locally": True} for degree, names in sorted(programs.items())]
    relevant = [key.replace("_", " ") for key, value in (profile.get("interests") or {}).items() if type(value) in (int, float) and value >= 60]
    if not relevant:
        exploration = "Try a small school project, club activity, or introductory task related to this pathway and note what you enjoy."
    else:
        exploration = "Use your reported interests (" + ", ".join(relevant[:3]) + ") to choose a small project, club activity, or introductory task linked to this route."
    subjects = sorted({subject for option in stage_options for subject in option["subjects_from_catalog"]})
    actions = ["Ask a subject teacher or school counselor which combinations are offered and what prerequisites apply.", "Compare the official syllabus and progression requirements for options available in your area.", exploration]
    if pathway == "Diploma/Vocational":
        actions.insert(1, "Ask the program provider to confirm current recognition, entry criteria, and whether further study pathways are available.")
    else:
        actions.insert(1, "Check whether any desired future course requires a particular Class 11–12 subject combination.")
    return {
        "pathway": pathway,
        "source_note": "Education options come from the maintained CareerPath education catalog. Career and degree directions come from maintained career records. These records are guidance, not a complete or current admission authority.",
        "stages": [
            {"id": "after_10", "title": "Next steps after Class 10", "summary": after10, "route_choices": [{"route": option["route"], "route_type": "Diploma/vocational route" if option["route"] == "Vocational/Diploma" else "Class 11–12 stream"} for option in stage_options], "prerequisite_checks": ["Confirm the relevant board's eligibility rules and subject availability with your school.", "Compare the exact syllabus and any entry conditions before selecting a program."], "skills_to_explore": list(PATHWAY_RULES_FOR_ROADMAP[pathway]), "activities": [exploration], "conversations": ["Discuss your subject strengths, interests, and questions with a teacher, guardian, or counselor."]},
            {"id": "class_11_12_or_equivalent", "title": "Class 11–12 or a recognized equivalent route", "summary": class12, "catalog_status": catalog_status, "catalog_subjects": subjects, "route_options": stage_options, "prerequisite_checks": ["Verify subject prerequisites and progression with the specific school or recognized program; CareerPath does not determine eligibility."], "skills_to_explore": list(PATHWAY_RULES_FOR_ROADMAP[pathway]), "activities": [exploration], "conversations": ["Review progress and subject choices with a teacher or counselor before changing routes."]},
            {"id": "after_12", "title": "Options after Class 12 or equivalent", "summary": "Undergraduate program names below are copied from pathway-linked CareerPath records. The catalog does not establish eligibility or prerequisites; confirm current entry requirements with each institution.", "program_options": post_12_program_options, "prerequisite_checks": ["For each course, check the current official admission notice, subject prerequisites, entrance tests, and recognition."], "activities": ["Compare course syllabi and speak with a counselor or course provider before applying."], "conversations": ["Ask a counselor to help compare the prerequisites for two or three options that interest you."]},
            {"id": "further_study_and_careers", "title": "Longer-term degrees, further study, and career progression", "summary": "Career directions and minimum study stages below are copied from maintained CareerPath career records. Where a record lists additional qualifications or references, use them to plan further study; verify all current rules with official institutions.", "career_directions": career_directions, "prerequisite_checks": ["Where a career record includes qualification notes or official references, read them and verify the latest rules with the responsible regulator or institution."], "activities": ["Explore a beginner-friendly project or age-appropriate career conversation where available."], "conversations": ["Discuss longer-term study and career options with a qualified counselor; keep more than one route open."]},
        ],
        "unavailable_assessment": profile.get("skill_gap_message") if profile.get("skill_gap_status") in ("insufficient_data", "insufficient_requirements") else None,
        "verify_locally": True,
    }

PATHWAY_RULES_FOR_ROADMAP = {
    "Science": ("mathematics", "science", "research", "problem solving"),
    "Commerce": ("numeracy", "communication", "organization", "decision making"),
    "Arts/Humanities": ("communication", "research", "critical reading", "creative expression"),
    "Diploma/Vocational": ("practical problem solving", "safe tool use", "communication", "project planning"),
}
