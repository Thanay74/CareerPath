"""Feature contract for the Kaggle university career-field benchmark.

The Kaggle source is synthetically generated and is benchmark-only. Fields
created after a career/placement decision, direct identifiers, demographics,
and the target itself are intentionally excluded.
"""

TARGET = "Career_Field"
EXCLUDED_LABEL = "Not Placed"

FEATURES = [
    "University_Year",
    "Major",
    "Attendance_Percentage",
    "Study_Hours_Per_Week",
    "CGPA",
    "Programming_Skill",
    "Projects_Completed",
    "Certifications",
    "Hackathons",
    "Internships",
    "Leadership_Experience",
    "Communication_Skills",
    "Teamwork",
    "Problem_Solving",
    "English_Proficiency",
]

CATEGORICAL_FEATURES = [
    "University_Year",
    "Major",
    "Leadership_Experience",
    "English_Proficiency",
]


def validate_and_filter(frame):
    """Check schema and keep only records with a placed career-field label."""
    missing = sorted(set(FEATURES + [TARGET]) - set(frame.columns))
    if missing:
        raise ValueError(f"Kaggle dataset is missing required columns: {missing}")
    result = frame[FEATURES + [TARGET]].copy()
    result[TARGET] = result[TARGET].astype(str).str.strip()
    result = result[result[TARGET].ne(EXCLUDED_LABEL)].dropna(subset=[TARGET])
    if result.empty:
        raise ValueError("No labeled placed records remain after filtering.")
    return result
