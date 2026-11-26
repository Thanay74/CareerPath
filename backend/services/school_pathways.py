"""Transparent, exploratory compatibility rules for choices after 10th standard.

The 60/100 requirement thresholds below are project guidance markers, not board,
admission, or psychometric standards. Only values actually supplied by a student
participate in scores or gap analysis.
"""
import re


PATHWAY_RULES = {
    "Science": {
        "subjects": ("mathematics", "science", "physics", "chemistry", "biology", "computer_science"),
        "interests": ("technology", "research", "healthcare", "innovation"),
        "aptitude": ("numerical_reasoning", "analytical_reasoning", "spatial_reasoning"),
        "families": {"technology_engineering": 0.55, "health_life_sciences": 0.45},
        "keywords": ("science", "engineering", "technology", "computer", "research", "medical", "health", "biology", "physics", "chemistry"),
        "description": "Consider science-focused study routes, then choose a subject combination suited to your interests and local offerings.",
    },
    "Commerce": {
        "subjects": ("accountancy", "business_studies", "economics", "mathematics", "english"),
        "interests": ("business", "entrepreneurship", "leadership"),
        "aptitude": ("numerical_reasoning", "attention_to_detail", "decision_making"),
        "families": {"business_finance": 1.0},
        "keywords": ("commerce", "business", "finance", "accounting", "accountancy", "economics", "entrepreneurship", "marketing"),
        "description": "Consider commerce, accounting, economics, and business study routes available through your board and schools.",
    },
    "Arts/Humanities": {
        "subjects": ("english", "language", "social_science", "history", "geography", "political_science", "sociology"),
        "interests": ("creativity", "social_service", "communication", "design", "research"),
        "aptitude": ("verbal_reasoning", "communication", "analytical_reasoning"),
        "families": {"creative_communication": 0.5, "public_social_research": 0.5},
        "keywords": ("arts", "humanities", "language", "writing", "communication", "history", "geography", "law", "social", "public service", "design", "media"),
        "description": "Consider humanities, language, social-science, communication, and creative study routes.",
    },
    "Diploma/Vocational": {
        "subjects": ("mathematics", "science", "computer_science", "physics", "business_studies"),
        "interests": ("technology", "design", "entrepreneurship", "innovation"),
        "aptitude": ("problem_solving", "spatial_reasoning", "attention_to_detail"),
        "families": {"technology_engineering": 0.5, "creative_communication": 0.25, "business_finance": 0.25},
        "keywords": ("diploma", "vocational", "technical", "trade", "hands-on", "practical", "design", "technology", "skill"),
        "description": "Explore recognized applied diploma and vocational programs, comparing their curriculum, progression routes, and local availability.",
    },
}

WEIGHTS = {"academic": 0.40, "aptitude": 0.25, "interests": 0.25, "preferences": 0.10}
GUIDANCE_THRESHOLD = 60.0
SUBJECT_ALIASES = {
    "science": ("science", "physics", "chemistry", "biology"),
    "language": ("language", "english", "regional_language"),
    "social_science": ("social_science", "history", "geography", "political_science", "sociology"),
}


def _numeric_map(values):
    result = {}
    for key, value in (values or {}).items():
        if type(value) in (int, float) and 0 <= value <= 100:
            result[str(key).strip().lower()] = float(value)
    return result


def _dimension(values, relevant_keys):
    values = _numeric_map(values)
    matched = [(key, score) for key, score in values.items() if key in relevant_keys]
    if not matched:
        return None, []
    return sum(score for _, score in matched) / len(matched), matched


def _subject_dimension(values, relevant_keys):
    values = _numeric_map(values)
    matched = []
    used = set()
    for key in relevant_keys:
        aliases = SUBJECT_ALIASES.get(key, (key,))
        for alias in aliases:
            if alias in values and alias not in used:
                matched.append((alias, values[alias]))
                used.add(alias)
                break
    if not matched:
        return None, []
    return sum(score for _, score in matched) / len(matched), matched


def _preference_signal(profile, pathway, rule):
    signals = []
    # Education stream is context, not evidence of personal compatibility.
    text = " ".join(str(profile.get(key) or "") for key in ("career_preferences", "research_interests")).lower()
    if text.strip():
        phrases = [word for word in rule["keywords"] if re.search(r"(?<![a-z0-9])" + re.escape(word) + r"(?![a-z0-9])", text)]
        signals.append((100.0 if phrases else 0.0, "career/research preference: " + (", ".join(phrases) if phrases else "no related pathway keywords")))
    return (sum(score for score, _ in signals) / len(signals), signals) if signals else (None, [])


def _family_probability(probabilities, rule):
    if not probabilities:
        return None
    return round(100 * sum(probabilities.get(family, 0.0) * weight for family, weight in rule["families"].items()), 1)


def _gap_actions(kind, name):
    readable = name.replace("_", " ").title()
    if kind == "subject":
        return [f"Review your current {readable} lessons and identify one topic to practise.", f"Work through a few age-appropriate exercises and ask a teacher to check your approach.", "Compare the next-stage subject syllabus with your interests before choosing a pathway."]
    return [f"Practise {readable} with short age-appropriate puzzles or classroom activities.", "Review which question types felt difficult; this is practice guidance, not a diagnosis.", "Ask a teacher or counselor for ideas suited to your learning goals."]


def evaluate_pathway(profile, pathway, model_probabilities=None):
    rule = PATHWAY_RULES[pathway]
    subject_score, subjects = _subject_dimension(profile.get("subjects"), rule["subjects"])
    aptitude_score, aptitude = _dimension(profile.get("aptitude"), rule["aptitude"])
    interest_score, interests = _dimension(profile.get("interests"), rule["interests"])
    preference_score, preferences = _preference_signal(profile, pathway, rule)
    dimensions = {"academic": subject_score, "aptitude": aptitude_score, "interests": interest_score, "preferences": preference_score}
    assessed = [("subject", key, score) for key, score in subjects] + [("aptitude", key, score) for key, score in aptitude]
    assessed += [("interest", key, score) for key, score in interests]
    assessed += [("preference", text, score) for score, text in preferences]
    assessed_domains = sum(value is not None for value in dimensions.values())
    evidence_items = len(assessed)
    evidence_sufficient = assessed_domains >= 2 and evidence_items >= 2
    active_weight = sum(WEIGHTS[key] for key, value in dimensions.items() if value is not None)
    knowledge_value = round(sum(value * WEIGHTS[key] for key, value in dimensions.items() if value is not None) / active_weight, 1) if active_weight else None
    knowledge = knowledge_value if evidence_sufficient else None
    ml = _family_probability(model_probabilities, rule) if evidence_sufficient else None
    combined = round(0.90 * knowledge + 0.10 * ml, 1) if knowledge is not None and ml is not None else knowledge
    def evidence_dimension(key, label, required, used, score):
        required=list(required); used=[name for name, _ in used]
        status="assessed" if score is not None else "not_applicable" if not required else "missing"
        missing=[name for name in required if not any(alias in used for alias in (SUBJECT_ALIASES.get(name,(name,)) if key=="academic" else (name,)))]
        return {"key": key, "label": label, "status": status, "score": score,
            "inputs_used": used, "missing_inputs": missing,
            "not_applicable_inputs": []}

    evidence_coverage = {
        "status": "sufficient" if evidence_sufficient else "insufficient",
        "sufficient": evidence_sufficient,
        "assessed_dimensions": assessed_domains,
        "total_dimensions": len(dimensions),
        "coverage_percent": round(100 * assessed_domains / len(dimensions)),
        "input_count": evidence_items,
        "minimum_dimensions_required": 2,
        "minimum_inputs_required": 2,
        "dimensions": [
            evidence_dimension("academic", "Self-reported subject ratings", rule["subjects"], subjects, subject_score),
            evidence_dimension("aptitude", "Aptitude assessment", rule["aptitude"], aptitude, aptitude_score),
            evidence_dimension("interests", "Interests", rule["interests"], interests, interest_score),
            evidence_dimension("preferences", "Career and research preferences", ["career/research preference"] if preferences else [], [("career/research preference", score) for score, _ in preferences], preference_score),
        ],
        "summary": (f"{assessed_domains} of {len(dimensions)} assessment areas contributed using {evidence_items} provided inputs." if evidence_sufficient else
            f"Only {assessed_domains} of {len(dimensions)} assessment areas contributed using {evidence_items} provided inputs. A personalized score needs at least 2 areas and 2 inputs; this is a provisional pathway suggestion."),
    }
    gaps = []
    for kind, key, score in assessed:
        if score < GUIDANCE_THRESHOLD:
            gap = round(GUIDANCE_THRESHOLD - score)
            gaps.append({"skill": key.replace("_", " ").title(), "source_dimension": kind, "current": round(score), "required": int(GUIDANCE_THRESHOLD), "gap": gap, "severity": "High" if gap >= 30 else "Moderate" if gap >= 15 else "Low", "missing": False, "requirement_basis": "CareerPath project guidance marker; not a formal academic, admission, or aptitude standard", "actions": _gap_actions(kind, key)})
    requirement_count = len(rule["subjects"]) + len(rule["aptitude"])
    if not assessed:
        gap_status = "insufficient_data"
        gap_message = "No relevant subject or scored aptitude inputs are available for this pathway. Assess those areas before interpreting gaps."
    elif gaps:
        gap_status = "some_gaps_identified"
        gap_message = "Practice markers below 60 were found among the relevant inputs you provided. They are guidance prompts, not proof of inability."
    else:
        gap_status = "no_gaps_identified"
        gap_message = "No gaps were identified against the available, project-defined subject and aptitude markers. Unassessed areas remain unknown."

    supporting = []
    reducing = []
    for label, values in (("Self-reported subject rating", subjects), ("Aptitude", aptitude), ("Interest", interests)):
        for key, score in values:
            text = f"{label}: {key.replace('_', ' ')} rated {score:.0f}/100"
            (supporting if score >= GUIDANCE_THRESHOLD else reducing).append(text)
    for score, text in preferences:
        if score >= GUIDANCE_THRESHOLD:
            supporting.append(f"Preference: {text}")
        else:
            reducing.append(f"Preference to compare: {text}")
    if not subjects:
        reducing.append("No relevant academic subject ratings were supplied.")
    if not aptitude:
        reducing.append("No relevant scored aptitude domains were supplied.")
    if not interests:
        reducing.append("No relevant interest ratings were supplied.")
    if profile.get("stream"):
        reducing.append("Your selected study stream is shown as context and is not counted as a personal-strength assessment.")

    return {
        "knowledge_score": knowledge,
        "combined_score": combined,
        "ml_score": ml,
        "components": dimensions,
        "evidence_count": evidence_items,
        "evidence_domains": assessed_domains,
        "evidence_coverage": evidence_coverage,
        "recommendation_type": "personalized" if evidence_sufficient else "provisional",
        "context": {"selected_stream": profile.get("stream") or None, "suggested_pathway": pathway, "stream_is_scoring_evidence": False},
        "evidence_labels": ["academic subjects", "scored aptitude", "interests", "stated preferences"],
        "why_matches": supporting[:6],
        "factors_to_consider": reducing[:6],
        "skill_gaps": gaps,
        "skill_gap_status": gap_status,
        "skill_gap_message": gap_message,
        "improvement_suggestions": ([{"skill": gap["skill"], "severity": gap["severity"], "actions": gap["actions"]} for gap in gaps[:4]] if gaps else []),
        "available_requirements": {"subjects": list(rule["subjects"]), "aptitude_domains": list(rule["aptitude"]), "project_threshold": GUIDANCE_THRESHOLD, "defined_requirement_count": requirement_count},
        "rules_version": "school-pathways-1.0",
    }


def summarize_pathways(results):
    scored = [result for result in results if result.get("combined_score") is not None]
    scored.sort(key=lambda item: (-item["combined_score"], item["career_name"]))
    evidence_items = max((item.get("evidence_count", 0) for item in results), default=0)
    evidence_domains = max((item.get("evidence_domains", 0) for item in results), default=0)
    margin = scored[0]["combined_score"] - scored[1]["combined_score"] if len(scored) > 1 else 0
    clear_leader = bool(scored and evidence_items >= 2 and margin >= 12)
    sufficient = evidence_domains >= 2 and evidence_items >= 2
    if not sufficient:
        summary = "There is not enough assessed information yet to distinguish pathways. Rate relevant subjects and interests, complete the scored aptitude exercise, and discuss local options with a teacher or counselor."
    elif clear_leader:
        summary = f"{scored[0].get('pathway_name', scored[0]['career_name'])} is a provisional leading option to explore from the assessed information. This is not a prediction of success or admission; compare alternatives and local subject availability."
    else:
        summary = "No single pathway stands out clearly from the available evidence. The close compatibility estimates should not be treated as meaningful certainty; compare the listed alternatives and gather more information."
    for result in results:
        if not sufficient or not scored:
            label = "More information needed"
        elif clear_leader and result["career_id"] == scored[0]["career_id"]:
            label = "Provisional leading option to explore"
        elif result.get("combined_score") is not None and result["combined_score"] >= scored[0]["combined_score"] - 8:
            label = "Suitable alternative to explore"
        elif result.get("combined_score") is not None and result["combined_score"] >= 55:
            label = "Potential option; compare further"
        else:
            label = "Explore further if interested"
        result["pathway_fit_label"] = label
        result["recommendation_guidance"] = {"summary": summary, "is_leader_clear": clear_leader, "score_margin": round(margin, 1), "evidence_count": evidence_items, "evidence_domains": evidence_domains, "evidence_coverage": result.get("evidence_coverage"), "score_label": "Exploratory compatibility estimate — not a probability of success or admission", "small_difference_note": "A leading option is shown only with at least two evidence areas, two provided inputs, and a 12-point or larger lead. Otherwise, compare provisional pathway suggestions; these do not decide your future."}
        if not result.get("improvement_suggestions"):
            result["improvement_suggestions"] = [{"skill": "Pathway exploration", "severity": "Informational", "actions": ["Check subject combinations and entry requirements offered by local schools or recognized programs.", "Try a small classroom, club, or project activity linked to this pathway.", "Discuss your interests and questions with a teacher, guardian, or school counselor."]}]
    return sorted(results, key=lambda item: (-(item.get("combined_score") if item.get("combined_score") is not None else -1), item["career_name"]))
