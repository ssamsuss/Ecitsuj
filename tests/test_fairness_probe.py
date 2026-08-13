import unittest

from eval.fairness import IDENTITY_VARIANTS, _confidence_disparity, _verdict_disparity, inject_identity
from eval.harness import evaluate_packet, load_golden_cases


class InjectIdentityTests(unittest.TestCase):
    def test_appends_one_fact_without_mutating_original(self):
        original = {"title": "T", "facts": ["fact one"], "jury_instructions": "x", "evidence_items": []}
        variant = inject_identity(original, "Jamal Washington")

        self.assertEqual(original["facts"], ["fact one"])
        self.assertEqual(variant["facts"], ["fact one", "The defendant, Jamal Washington, was identified as present at the scene."])
        self.assertEqual(variant["title"], original["title"])

    def test_variant_still_passes_packet_validation(self):
        for name, data in load_golden_cases():
            for _, identity_name in IDENTITY_VARIANTS:
                with self.subTest(case=name, identity=identity_name):
                    variant = inject_identity(data, identity_name)
                    result = evaluate_packet(f"{name}-{identity_name}", variant)
                    self.assertTrue(result["passed"], result["pydantic_errors"] + result["schema_errors"])

    def test_identity_variants_cover_multiple_groups(self):
        labels = {label for label, _ in IDENTITY_VARIANTS}
        self.assertGreaterEqual(len(labels), 3)


class DisparityHelperTests(unittest.TestCase):
    def test_verdict_disparity_is_zero_when_identical(self):
        splits = [{"guilty": 1, "not_guilty": 1, "undecided": 1}] * 3
        self.assertEqual(_verdict_disparity(splits), 0)

    def test_verdict_disparity_detects_spread(self):
        splits = [
            {"guilty": 2, "not_guilty": 1, "undecided": 0},
            {"guilty": 0, "not_guilty": 1, "undecided": 2},
        ]
        self.assertEqual(_verdict_disparity(splits), 2)

    def test_confidence_disparity_is_max_minus_min(self):
        self.assertAlmostEqual(_confidence_disparity([0.5, 0.7, 0.6]), 0.2)

    def test_confidence_disparity_empty_is_zero(self):
        self.assertEqual(_confidence_disparity([]), 0.0)


if __name__ == "__main__":
    unittest.main()
