import unittest

from backend.services.recommendation_engine import (
    _observed,
    _requirements_score,
    _subject_score,
    skill_gap_analysis,
)
from backend.services.school_pathways import evaluate_pathway, summarize_pathways
from backend.services.school_roadmap import build_pathway_roadmap


def _ranked_pathways(margin, evidence_count=2):
    return [
        {
            "career_id": "PATH-1",
            "career_name": "Science stream/pathway",
            "pathway_name": "Science",
            "combined_score": 80.0,
            "evidence_count": evidence_count,
            "evidence_domains": 2 if evidence_count >= 2 else evidence_count,
        },
        {
            "career_id": "PATH-2",
            "career_name": "Commerce stream/pathway",
            "pathway_name": "Commerce",
            "combined_score": 80.0 - margin,
            "evidence_count": evidence_count,
            "evidence_domains": 2 if evidence_count >= 2 else evidence_count,
        },
    ]


class MissingValueAndPathwayGuidanceTests(unittest.TestCase):
    def test_unassessed_values_are_omitted_but_numeric_zero_is_observed(self):
        self.assertEqual(_observed({"python": None, "sql": 0}), {"sql": 0.0})
        requirements = {"python": 70, "sql": 50}
        self.assertIsNone(_requirements_score({"python": None}, requirements))
        self.assertEqual(_requirements_score({"sql": 0}, requirements), 0.0)

    def test_missing_subject_is_unknown_and_zero_subject_is_real_evidence(self):
        required = ["mathematics"]
        self.assertIsNone(_subject_score({"subjects": {"mathematics": None}}, required))
        self.assertEqual(_subject_score({"subjects": {"mathematics": 0}}, required), 0.0)

    def test_inapplicable_subject_does_not_lower_a_career_subject_score(self):
        career = {
            "required_subjects": "mathematics;computer_science",
        }
        relevant_only = {"subjects": {"mathematics": 80, "computer_science": 70}}
        with_unrelated = {"subjects": {**relevant_only["subjects"], "chemistry": 0, "history": 0}}
        self.assertEqual(
            _subject_score(relevant_only, career["required_subjects"].split(";")),
            _subject_score(with_unrelated, career["required_subjects"].split(";")),
        )

    def test_skill_gaps_require_both_a_requirement_and_an_observed_value(self):
        career = {"technical_skills": "python:70;sql:50", "employability_skills": "communication:60"}
        missing = skill_gap_analysis(
            {"technical": {"python": None}, "employability": {"communication": None}}, career
        )
        self.assertEqual(missing["status"], "insufficient_data")
        self.assertEqual(missing["gaps"], [])

        zero = skill_gap_analysis({"technical": {"python": 0}}, career)
        self.assertEqual(zero["status"], "some_gaps_identified")
        python_gap = next(gap for gap in zero["gaps"] if gap["skill"] == "Python")
        self.assertEqual((python_gap["current"], python_gap["required"], python_gap["gap"]), (0, 70, 70))

        partial = skill_gap_analysis({"technical": {"python": 65, "sql": None}}, career)
        self.assertEqual(partial["status"], "some_gaps_identified")
        self.assertEqual([gap["skill"] for gap in partial["gaps"]], ["Python"])
        self.assertIn("only for assessed skills", partial["message"])

    def test_missing_requirements_are_not_claimed_as_student_deficits(self):
        result = skill_gap_analysis(
            {"technical": {"python": 0}},
            {"technical_skills": "", "employability_skills": ""},
        )
        self.assertEqual(result["status"], "insufficient_requirements")
        self.assertEqual(result["gaps"], [])

    def test_class10_unassessed_inputs_produce_insufficient_gap_status_and_roadmap_note(self):
        assessed = evaluate_pathway(
            {"subjects": {"mathematics": None}, "aptitude": {"logical_reasoning": None}},
            "Science",
        )
        self.assertEqual(assessed["skill_gap_status"], "insufficient_data")
        self.assertEqual(assessed["skill_gaps"], [])
        roadmap = build_pathway_roadmap(
            "Science",
            {
                "skill_gap_status": assessed["skill_gap_status"],
                "skill_gap_message": assessed["skill_gap_message"],
            },
        )
        self.assertIn("unavailable_assessment", roadmap)
        self.assertIsNotNone(roadmap["unavailable_assessment"])
        self.assertTrue(roadmap["stages"][0]["skills_to_explore"])
        self.assertFalse(any("deficit" in str(stage).lower() for stage in roadmap["stages"]))

    def test_class10_inapplicable_subject_does_not_add_negative_evidence_or_gap(self):
        relevant = evaluate_pathway(
            {"subjects": {"mathematics": 80}, "aptitude": {}, "interests": {}}, "Science"
        )
        extra_inapplicable = evaluate_pathway(
            {"subjects": {"mathematics": 80, "accountancy": 0}, "aptitude": {}, "interests": {}},
            "Science",
        )
        self.assertEqual(relevant["components"]["academic"], extra_inapplicable["components"]["academic"])
        self.assertEqual(relevant["skill_gaps"], extra_inapplicable["skill_gaps"])
        self.assertFalse(any("accountancy" in item.lower() for item in extra_inapplicable["factors_to_consider"]))

    def test_class10_uncertainty_message_covers_margin_below_eight(self):
        result = summarize_pathways(_ranked_pathways(7.9))[0]
        guidance = result["recommendation_guidance"]
        self.assertFalse(guidance["is_leader_clear"])
        self.assertIn("12-point", guidance["small_difference_note"])
        self.assertIn("compare pathways", guidance["small_difference_note"])

    def test_class10_uncertainty_message_covers_margin_from_eight_to_under_twelve(self):
        for margin in (8.0, 11.9):
            with self.subTest(margin=margin):
                result = summarize_pathways(_ranked_pathways(margin))[0]
                self.assertFalse(result["recommendation_guidance"]["is_leader_clear"])
                self.assertIn("No single pathway stands out", result["recommendation_guidance"]["summary"])

    def test_class10_twelve_point_margin_can_show_only_a_provisional_leader(self):
        result = summarize_pathways(_ranked_pathways(12.0))[0]
        self.assertTrue(result["recommendation_guidance"]["is_leader_clear"])
        self.assertIn("provisional leading option", result["recommendation_guidance"]["summary"])
        self.assertIn("not a prediction of success or admission", result["recommendation_guidance"]["summary"])

    def test_class10_large_margin_is_not_a_leader_when_evidence_is_insufficient(self):
        result = summarize_pathways(_ranked_pathways(20.0, evidence_count=1))[0]
        self.assertFalse(result["recommendation_guidance"]["is_leader_clear"])
        self.assertIn("not enough assessed information", result["recommendation_guidance"]["summary"])


if __name__ == "__main__":
    unittest.main()
