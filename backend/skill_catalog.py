"""Student skill suggestions and career-skill guidance metadata.

Education mappings are suggestions, not course requirements. They are based on
the selected profile labels and never imply that a student has learned a skill.
"""
import re


EMPLOYABILITY = (
    "communication", "teamwork", "leadership", "adaptability", "time_management",
    "problem_solving", "critical_thinking", "presentation", "decision_making", "professionalism",
)

# Stable keys shared with the existing career catalogue where a compatible
# scoring signal exists. Other catalogue entries are display-only suggestions.
SKILLS = {
    "accounting": ("Accounting", "technical", "commerce management"),
    "finance": ("Finance", "technical", "commerce management economics"),
    "financial_analysis": ("Financial analysis", "technical", "commerce management economics"),
    "tally": ("Tally / accounting software", "technical", "commerce"),
    "gst": ("GST workflows", "technical", "commerce"),
    "excel": ("Spreadsheets (Excel or equivalent)", "technical", "commerce management mathematics physics chemistry economics journalism psychology"),
    "crm": ("CRM tools", "technical", "management journalism"),
    "power_bi": ("Power BI or equivalent", "technical", "management economics"),
    "business_analytics": ("Business analytics", "technical", "management commerce economics"),
    "digital_marketing": ("Digital marketing tools", "technical", "management journalism"),
    "programming": ("Programming", "technical", "computing mathematics physics"),
    "python": ("Python", "technical", "computing mathematics physics chemistry economics psychology"),
    "java": ("Java", "technical", "computing"),
    "javascript": ("JavaScript", "technical", "computing journalism"),
    "sql": ("SQL / relational databases", "technical", "computing management economics psychology"),
    "data_analysis": ("Data analysis", "technical", "computing mathematics physics chemistry economics psychology journalism"),
    "statistical_analysis": ("Statistical analysis", "technical", "mathematics physics chemistry economics psychology"),
    "r": ("R", "technical", "mathematics physics chemistry economics psychology"),
    "matlab": ("MATLAB or equivalent", "technical", "mathematics physics engineering"),
    "machine_learning": ("Machine learning", "technical", "computing mathematics"),
    "web_development": ("Web development", "technical", "computing journalism"),
    "software_testing": ("Software testing", "technical", "computing"),
    "cybersecurity": ("Cybersecurity", "technical", "computing"),
    "cloud_computing": ("Cloud computing", "technical", "computing"),
    "networking": ("Computer networking", "technical", "computing engineering"),
    "electronics": ("Electronics", "technical", "engineering physics"),
    "hardware": ("Hardware / instrumentation", "technical", "engineering physics chemistry"),
    "laboratory_instrumentation": ("Laboratory instrumentation", "technical", "physics chemistry"),
    "analytical_software": ("Analytical software", "technical", "chemistry"),
    "research_methods": ("Research methods", "technical", "mathematics physics chemistry economics journalism psychology"),
    "research_software": ("Research software", "technical", "journalism psychology mathematics economics"),
    "survey_tools": ("Survey tools", "technical", "journalism psychology economics"),
    "graphic_design": ("Graphic design", "technical", "journalism management"),
    "ui_ux": ("UI/UX design", "technical", "computing journalism management"),
    "video_editing": ("Video editing", "technical", "journalism"),
    "digital_publishing": ("Digital publishing", "technical", "journalism"),
    "seo": ("Search engine optimization", "technical", "journalism management"),
    "computer_literacy": ("General computer literacy", "technical", "all"),
    "html_css": ("HTML and CSS", "technical", "computing journalism"),
    **{key: (key.replace("_", " ").title(), "employability", "all") for key in EMPLOYABILITY},
}

# Explicit aliases only. Unmatched custom skills are retained but never scored.
ALIASES = {
    "python programming": "python", "javascript programming": "javascript",
    "relational database": "sql", "relational databases": "sql",
    "data analytics": "data_analysis", "financial accounting": "accounting",
    "ui ux": "ui_ux", "user experience design": "ui_ux",
}

# Project-level career guidance only; these are not admissions, licensing, or
# official occupational standards. Unlisted thresholds are optional guidance.
CORE_CAREER_SKILLS = {
    "C01": {"programming", "python"}, "C02": {"python", "data_analysis", "machine_learning"},
    "C03": {"python", "machine_learning", "programming"}, "C04": {"cybersecurity"},
    "C05": {"javascript", "web_development", "html_css"}, "C06": {"sql", "data_analysis"},
    "C07": {"ui_ux", "graphic_design"}, "C08": {"hardware"}, "C10": {"electronics", "hardware"},
    "C13": {"research_methods"}, "C14": {"accounting"}, "C15": {"finance", "accounting"},
    "C16": {"data_analysis"}, "C19": {"research_methods", "data_analysis"},
    "C20": {"research_methods"}, "C21": {"research_methods"}, "C23": {"graphic_design"},
}


def normalize_skill_name(value):
    return " ".join(re.findall(r"[a-z0-9]+", str(value or "").casefold()))


def canonical_skill(value):
    normalized = normalize_skill_name(value)
    by_key = {normalize_skill_name(key): key for key in SKILLS}
    by_label = {}
    for key, (label, _category, _contexts) in SKILLS.items():
        by_label.setdefault(normalize_skill_name(label), key)
    return by_key.get(normalized) or by_label.get(normalized) or ALIASES.get(normalized)


def _profile_tags(profile):
    text = normalize_skill_name(" ".join(str(profile.get(k) or "") for k in ("stream", "degree", "specialization")))
    tags = set()
    rules = {
        "commerce": r"commerce|b com|account|finance|tax|gst|tally",
        "management": r"bba|business|management|marketing|human resource|entrepreneur|operations|crm",
        "computing": r"bca|mca|computer|software|programming|cyber|data science|information technology",
        "mathematics": r"math|statistic|quantitative|pcm|pcmb",
        "physics": r"physics|mechanical|electrical|electronics|pcm|pcmb",
        "chemistry": r"chemistry|pharma|laboratory|pcb|pcmb",
        "economics": r"economics|econometric",
        "journalism": r"journal|media|communication|publishing|digital marketing",
        "psychology": r"psychology|counsel|behavioral",
        "engineering": r"engineering|b tech|btech|m tech|mtech",
        "vocational": r"vocational|b voc|bvoc|diploma",
    }
    for tag, pattern in rules.items():
        if re.search(pattern, text):
            tags.add(tag)
    if "other" in text and profile.get("education_level") in ("10th", "12th"):
        tags.add("vocational")
    return tags


def education_skill_catalog(profile):
    tags = _profile_tags(profile)
    domain = []
    optional = []
    employability = []
    for key, (label, category, contexts) in SKILLS.items():
        aliases = [alias for alias, target in ALIASES.items() if target == key]
        item = {"key": key, "name": label, "category": category, "aliases": aliases, "canonical_skill": key if key in _career_skill_keys() else None}
        if category == "employability":
            employability.append(item)
        elif "all" in contexts.split():
            optional.append(item)
        elif tags.intersection(contexts.split()):
            domain.append(item)
        else:
            optional.append(item)
    return {
        "domain_skills": domain,
        "general_digital_skills": [x for x in optional if x["key"] in {"computer_literacy", "excel", "crm", "power_bi", "digital_publishing", "seo"}],
        "advanced_self_acquired_skills": [x for x in optional if x["key"] not in {"computer_literacy", "excel", "crm", "power_bi", "digital_publishing", "seo"}],
        "employability_skills": employability,
        "notice": "Suggestions are not curriculum requirements. Unanswered skills remain unassessed; use Not applicable only when a standardized skill does not apply.",
    }


def _career_skill_keys():
    return set(SKILLS) | {"html_css", "finance"}


def career_skill_guidance(career_id, technical, employability, actual=None):
    core = CORE_CAREER_SKILLS.get(career_id, set())
    actual = actual or {}
    result = {}
    for key, level in {**(technical or {}), **(employability or {})}.items():
        result[key] = {
            "level": level,
            "current": actual.get(key),
            "classification": "core" if key in core else "optional",
            "trainable": True,
            "source": "project guidance; not an eligibility requirement",
        }
    return result
