import unittest

from eval.harness import evaluate_packet, load_golden_cases


class GoldenCasesTests(unittest.TestCase):
    def test_case_count_is_between_five_and_ten(self):
        cases = load_golden_cases()
        self.assertGreaterEqual(len(cases), 5)
        self.assertLessEqual(len(cases), 10)

    def test_case_names_are_unique(self):
        names = [name for name, _ in load_golden_cases()]
        self.assertEqual(len(names), len(set(names)))

    def test_every_golden_case_passes_validation(self):
        for name, data in load_golden_cases():
            with self.subTest(case=name):
                result = evaluate_packet(name, data)
                self.assertTrue(
                    result["passed"],
                    f"{name} failed validation: {result['pydantic_errors'] + result['schema_errors']}",
                )

    def test_rejects_a_deliberately_broken_packet(self):
        broken = {
            "title": "",
            "facts": [],
            "jury_instructions": "x",
            "evidence_items": [],
        }
        result = evaluate_packet("broken", broken)
        self.assertFalse(result["passed"])
        self.assertTrue(result["pydantic_errors"] or result["schema_errors"])


if __name__ == "__main__":
    unittest.main()
