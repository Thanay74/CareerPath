import unittest
from datetime import date
from unittest.mock import patch

from backend.academic_history import empty_academic_history, validate_academic_history
from backend.services.eligibility import assess_eligibility


class AcademicHistoryValidationTests(unittest.TestCase):
    def test_absent_history_remains_unknown_for_each_education_level(self):
        for level in ("10th", "12th", "Bachelor's", "Master's"):
            with self.subTest(level=level):
                normalized, error = validate_academic_history(level, None)
                self.assertIsNone(error)
                self.assertEqual(normalized, empty_academic_history(level))
                self.assertEqual(normalized["subjects_status"], "unknown")

    def test_commerce_with_and_without_mathematics_are_distinct_student_facts(self):
        with_math = {"subjects_status": "selected", "subjects": ["Mathematics", "Accountancy"], "mathematics": "yes"}
        without_math = {"subjects_status": "selected", "subjects": ["Accountancy", "Economics"], "mathematics": "no"}
        yes, yes_error = validate_academic_history("12th", with_math, "Commerce")
        no, no_error = validate_academic_history("12th", without_math, "Commerce")
        self.assertIsNone(yes_error)
        self.assertIsNone(no_error)
        self.assertEqual(yes["mathematics"], "yes")
        self.assertEqual(no["mathematics"], "no")

    def test_science_combinations_require_consistent_recorded_core_subjects(self):
        combinations = {
            "Science PCM": ["Physics", "Chemistry", "Mathematics"],
            "Science PCB": ["Physics", "Chemistry", "Biology"],
            "Science PCMB": ["Physics", "Chemistry", "Mathematics", "Biology"],
        }
        for stream, subjects in combinations.items():
            history = {"subjects_status": "selected", "subjects": subjects,
                       "mathematics": "yes" if "Mathematics" in subjects else "no"}
            normalized, error = validate_academic_history("12th", history, stream)
            with self.subTest(stream=stream):
                self.assertIsNone(error)
                self.assertEqual(set(normalized["subjects"]), set(subjects))
        invalid, error = validate_academic_history("12th", {
            "subjects_status": "selected", "subjects": ["Physics", "Chemistry"], "mathematics": "no"
        }, "Science PCM")
        self.assertIsNone(invalid)
        self.assertIn("Mathematics", error)

    def test_arts_humanities_and_unknown_subjects_are_not_assumed(self):
        history, error = validate_academic_history("12th", {
            "subjects_status": "selected", "subjects": ["History", "Political Science"], "mathematics": "unknown"
        }, "Arts/Humanities")
        self.assertIsNone(error)
        self.assertEqual(history["mathematics"], "unknown")
        unknown, error = validate_academic_history("12th", None, "Commerce")
        self.assertIsNone(error)
        self.assertEqual(unknown["subjects"], [])
        self.assertEqual(unknown["mathematics"], "unknown")

    def test_degree_and_previous_degree_fields_are_level_scoped(self):
        bachelor, error = validate_academic_history("Bachelor's", {
            "study_status": "completed", "major": "Computer Science", "minor": "Mathematics",
            "subjects_status": "selected", "subjects": ["Algorithms"], "institution": "Example University"
        })
        self.assertIsNone(error)
        self.assertEqual(bachelor["major"], "Computer Science")
        master, error = validate_academic_history("Master's", {
            "previous_degree_status": "provided", "previous_degree": "BCA", "study_status": "current"
        })
        self.assertIsNone(error)
        self.assertEqual(master["previous_degree"], "BCA")
        _, error = validate_academic_history("Bachelor's", {"mathematics": "yes"})
        self.assertIn("do not apply", error)

    def test_inconsistent_or_malformed_history_is_rejected(self):
        cases = [
            {"subjects_status": "selected", "subjects": []},
            {"subjects_status": "selected", "subjects": ["Math", " math "], "mathematics": "yes"},
            {"subjects_status": "not_applicable", "subjects": ["English"]},
            {"subjects_status": "selected", "subjects": [3]},
            {"mathematics": "perhaps"},
        ]
        for value in cases:
            with self.subTest(value=value):
                normalized, error = validate_academic_history("12th", value)
                self.assertIsNone(normalized)
                self.assertTrue(error)

    def test_eligibility_requires_current_evidence_and_actual_subjects(self):
        career = {"career_id": "TEST"}
        rule = {"source_url": "https://official.example/program", "last_verified_at": date.today().isoformat(),
                "required_subjects_all": ["Mathematics"]}
        unknown = assess_eligibility({"education_level": "12th", "academic_history": empty_academic_history("12th")}, career, {"TEST": rule})
        self.assertEqual(unknown["status"], "eligibility_not_verified")
        absent = assess_eligibility({"education_level": "12th", "academic_history": {"subjects_status": "selected", "subjects": []}}, career, {"TEST": rule})
        self.assertEqual(absent["status"], "not_currently_eligible")
        present = assess_eligibility({"education_level": "12th", "academic_history": {"subjects_status": "selected", "subjects": ["Mathematics"]}}, career, {"TEST": rule})
        self.assertEqual(present["status"], "eligible_now")
        stale = assess_eligibility({"education_level": "12th", "academic_history": {"subjects_status": "selected", "subjects": ["Mathematics"]}}, career, {"TEST": {**rule, "last_verified_at": "not-a-date"}})
        self.assertEqual(stale["status"], "eligibility_not_verified")

    def test_additional_and_alternative_routes_are_reported_separately(self):
        career = {"career_id": "TEST"}
        profile = {"education_level": "12th", "academic_history": {"subjects_status": "selected", "subjects": ["Mathematics"]}}
        rule = {"source_url": "https://official.example/program", "last_verified_at": date.today().isoformat(),
                "required_subjects_all": ["Mathematics"], "additional_qualifications": ["Named foundation course"]}
        additional = assess_eligibility(profile, career, {"TEST": rule})
        self.assertEqual(additional["status"], "eligible_after_additional_qualification")
        alternative_rule = {**rule, "additional_qualifications": [], "required_degrees": ["BCA"],
                            "alternative_routes": [{"label": "Recognized subject route", "required_subjects_all": ["Mathematics"]}]}
        alternative = assess_eligibility(profile, career, {"TEST": alternative_rule})
        self.assertEqual(alternative["status"], "potentially_eligible_alternative_route")

    def test_verified_subject_exclusion_happens_before_personalized_ranking(self):
        from backend.services import eligibility, recommendation_engine
        from backend.ml import predict
        career = {"career_id": "TEST", "career_name": "Test program", "minimum_education_level": "Bachelor's"}
        rule = {"source_url": "https://official.example/program", "last_verified_at": date.today().isoformat(),
                "required_subjects_all": ["Mathematics"]}
        profile = {"education_level": "Bachelor's", "academic_history": {
            "subjects_status": "selected", "subjects": ["Biology"]}}
        with patch.object(eligibility, "VERIFIED_PROGRAM_RULES", {"TEST": rule}), \
             patch.object(recommendation_engine, "careers", return_value=[career]), \
             patch.object(predict, "predict_career_families", return_value={}), \
             patch.object(recommendation_engine, "_profile_score", side_effect=AssertionError("ranked despite unmet verified prerequisite")):
            self.assertEqual(recommendation_engine._recommend_with_catalog(profile), [])


if __name__ == "__main__":
    unittest.main()
