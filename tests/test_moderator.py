import unittest

from app.services.moderator import has_new_facts, validate_turn


class NewFactGuardTests(unittest.TestCase):
    def test_flags_numbers_absent_from_case_packet(self):
        self.assertTrue(has_new_facts("The clerk saw him at 11:45 PM.", "The alarm sounded at 10:05 PM."))

    def test_allows_numbers_present_in_case_packet(self):
        self.assertFalse(has_new_facts("The alarm went off at 10:05 PM.", "The alarm sounded at 10:05 PM."))

    def test_messages_without_numbers_are_not_flagged(self):
        self.assertFalse(has_new_facts("The witness seemed uncertain.", "The alarm sounded at 10:05 PM."))


class ValidateTurnTests(unittest.TestCase):
    def test_missing_citation_is_flagged(self):
        flags = validate_turn("No citation here.", cited_codes=[], allowed_codes={"E1"})
        self.assertTrue(flags["missing_citation"])

    def test_invalid_citation_is_flagged(self):
        flags = validate_turn("See E9.", cited_codes=["E9"], allowed_codes={"E1"})
        self.assertTrue(flags["invalid_citation"])

    def test_valid_citation_is_not_flagged(self):
        flags = validate_turn("See E1.", cited_codes=["E1"], allowed_codes={"E1"})
        self.assertFalse(flags["missing_citation"])
        self.assertFalse(flags["invalid_citation"])

    def test_new_fact_flag_uses_grounded_text(self):
        flags = validate_turn(
            "The suspect was seen at 11:45 PM.",
            cited_codes=["E1"],
            allowed_codes={"E1"},
            grounded_text="The alarm sounded at 10:05 PM.",
        )
        self.assertTrue(flags["new_fact_flag"])


if __name__ == "__main__":
    unittest.main()
