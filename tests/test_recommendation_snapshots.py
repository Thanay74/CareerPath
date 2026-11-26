import unittest

from backend.recommendation_snapshots import (
    decode_history, new_snapshot, recommendation_input_fingerprint,
    select_current_snapshot,
)


class RecommendationSnapshotContractTests(unittest.TestCase):
    def test_equivalent_numeric_values_have_same_fingerprint(self):
        a = {"education_level": "10th", "subjects": {"math": 72}}
        b = {"subjects": {"math": 72.0}, "education_level": "10th"}
        self.assertEqual(recommendation_input_fingerprint(a), recommendation_input_fingerprint(b))

    def test_missing_null_and_explicit_zero_remain_distinct(self):
        missing = {"education_level": "10th", "subjects": {}}
        null = {"education_level": "10th", "subjects": {"math": None}}
        zero = {"education_level": "10th", "subjects": {"math": 0}}
        hashes = {recommendation_input_fingerprint(item) for item in (missing, null, zero)}
        self.assertEqual(len(hashes), 3)

    def test_relevant_dimensions_invalidate_but_unrelated_fields_do_not(self):
        original = {"education_level": "10th", "stream": "Science", "subjects": {"math": None}, "age": 15}
        self.assertEqual(recommendation_input_fingerprint(original), recommendation_input_fingerprint({**original, "age": 16}))
        for field, value in (("education_level", "12th"), ("stream", "Commerce"),
                             ("subjects", {"math": 0}), ("interests", {"technology": 25}),
                             ("technical", {"python": 20}), ("degree", "BCA"),
                             ("academic_history", {"mathematics": "no", "subjects": ["Accountancy"]})):
            changed = dict(original, **{field: value})
            self.assertNotEqual(recommendation_input_fingerprint(original), recommendation_input_fingerprint(changed), field)

    def test_legacy_snapshots_are_preserved_but_not_selectable(self):
        old = [{"career_name": "Old result"}]
        history, legacy = decode_history(old)
        self.assertTrue(legacy)
        self.assertEqual(history["legacy_records"], [old])
        self.assertIsNone(select_current_snapshot(history, "profile", "catalog", "model-a"))

    def test_pre_academic_history_snapshot_is_preserved_but_not_current(self):
        old = new_snapshot("old-profile", "catalog", [{"career_name": "Old snapshot"}], "model-a")
        old["input_version"] = 1
        history, legacy = decode_history({"format": "careerpath.recommendation-history", "format_version": 1,
            "snapshots": [old], "legacy_records": []})
        self.assertFalse(legacy)
        self.assertEqual(len(history["snapshots"]), 1)
        self.assertIsNone(select_current_snapshot(history, "old-profile", "catalog", "model-a"))

    def test_pre_evidence_scoring_snapshots_are_preserved_but_not_current(self):
        old = new_snapshot("profile", "catalog", [{"career_name": "Old score"}], "model-a")
        old["input_version"] = 2
        history, legacy = decode_history({"format": "careerpath.recommendation-history", "format_version": 1,
            "snapshots": [old], "legacy_records": []})
        self.assertFalse(legacy)
        self.assertEqual(history["snapshots"], [old])
        self.assertIsNone(select_current_snapshot(history, "profile", "catalog", "model-a"))

    def test_current_selection_uses_matching_snapshot_and_stable_order(self):
        history, _ = decode_history({"format": "careerpath.recommendation-history", "format_version": 1, "snapshots": [], "legacy_records": []})
        first = new_snapshot("profile", "catalog", [{"career_name": "First"}], "model-a")
        second = new_snapshot("other", "catalog", [{"career_name": "Stale"}], "model-a")
        history["snapshots"].extend([first, second])
        self.assertEqual(select_current_snapshot(history, "profile", "catalog", "model-a"), first)
        self.assertIsNone(select_current_snapshot(history, "profile", "catalog", "model-b"))
        self.assertIsNone(select_current_snapshot(history, "profile", "new-catalog", "model-a"))

    def test_legacy_snapshot_without_model_identity_is_not_current(self):
        history, _ = decode_history({"format": "careerpath.recommendation-history", "format_version": 1,
            "snapshots": [new_snapshot("profile", "catalog", [{"career_name": "Old"}])], "legacy_records": []})
        self.assertIsNone(select_current_snapshot(history, "profile", "catalog", "model-a"))


if __name__ == "__main__":
    unittest.main()
