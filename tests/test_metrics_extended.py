import unittest

from app.services.metrics import build_swing_warnings, citation_coverage, contradiction_rate, dominance_index
from app.services.moderator import ContradictionTracker


class CitationCoverageTests(unittest.TestCase):
    def test_fraction_of_turns_with_citations(self):
        flags = [{"missing_citation": False}, {"missing_citation": True}, {"missing_citation": False}]
        self.assertAlmostEqual(citation_coverage(flags), 2 / 3)

    def test_empty_turns_is_zero(self):
        self.assertEqual(citation_coverage([]), 0.0)


class ContradictionRateTests(unittest.TestCase):
    def test_fraction_of_turns_flagged(self):
        flags = [{"contradiction_flag": True}, {"contradiction_flag": False}]
        self.assertEqual(contradiction_rate(flags), 0.5)

    def test_empty_turns_is_zero(self):
        self.assertEqual(contradiction_rate([]), 0.0)


class DominanceIndexTests(unittest.TestCase):
    def test_even_split_is_one_over_n(self):
        self.assertAlmostEqual(dominance_index([3, 3, 3]), 1 / 3)

    def test_single_juror_dominates(self):
        self.assertEqual(dominance_index([10]), 1.0)

    def test_no_turns_is_zero(self):
        self.assertEqual(dominance_index([]), 0.0)


class BuildSwingWarningsTests(unittest.TestCase):
    def _shift(self, juror_number, from_verdict, to_verdict, confidence_from, confidence_to):
        return {
            "juror_number": juror_number,
            "from": from_verdict,
            "to": to_verdict,
            "confidence_from": confidence_from,
            "confidence_to": confidence_to,
            "changed": from_verdict != to_verdict,
        }

    def test_no_warnings_for_stable_shifts(self):
        shifts = [self._shift(1, "guilty", "guilty", 0.6, 0.65)]
        self.assertEqual(build_swing_warnings(shifts), [])

    def test_warns_on_confidence_swing_above_threshold(self):
        shifts = [self._shift(1, "guilty", "guilty", 0.2, 0.9)]
        warnings = build_swing_warnings(shifts)
        self.assertEqual(len(warnings), 1)
        self.assertIn("Juror #1", warnings[0])

    def test_warns_when_majority_change_verdict(self):
        shifts = [
            self._shift(1, "guilty", "not_guilty", 0.5, 0.5),
            self._shift(2, "not_guilty", "guilty", 0.5, 0.5),
            self._shift(3, "guilty", "guilty", 0.5, 0.5),
        ]
        warnings = build_swing_warnings(shifts)
        self.assertTrue(any("jurors changed verdict" in w for w in warnings))

    def test_empty_shifts_produce_no_warnings(self):
        self.assertEqual(build_swing_warnings([]), [])

    def test_custom_thresholds_are_respected(self):
        shifts = [self._shift(1, "guilty", "guilty", 0.5, 0.6)]
        self.assertEqual(build_swing_warnings(shifts, confidence_threshold=0.05), [
            "Juror #1 confidence swung by 0.10 (0.50 -> 0.60), exceeding 0.05 threshold"
        ])


class ContradictionTrackerTests(unittest.TestCase):
    def test_opposing_stance_on_same_code_is_flagged(self):
        tracker = ContradictionTracker()
        self.assertFalse(tracker.check_and_record(1, ["E1"], "support"))
        self.assertTrue(tracker.check_and_record(1, ["E1"], "challenge"))

    def test_same_stance_is_not_flagged(self):
        tracker = ContradictionTracker()
        tracker.check_and_record(1, ["E1"], "support")
        self.assertFalse(tracker.check_and_record(1, ["E1"], "support"))

    def test_different_jurors_do_not_interfere(self):
        tracker = ContradictionTracker()
        tracker.check_and_record(1, ["E1"], "support")
        self.assertFalse(tracker.check_and_record(2, ["E1"], "challenge"))

    def test_clarify_stance_never_flags(self):
        tracker = ContradictionTracker()
        tracker.check_and_record(1, ["E1"], "support")
        self.assertFalse(tracker.check_and_record(1, ["E1"], "clarify"))


if __name__ == "__main__":
    unittest.main()
