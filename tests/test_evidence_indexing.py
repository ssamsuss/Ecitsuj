import unittest
from types import SimpleNamespace

from app.services.cases import build_evidence_index, tag_evidence_item


class EvidenceIndexingTests(unittest.TestCase):
    def test_tags_derive_from_kind_and_keywords(self):
        tags = tag_evidence_item("forensic", "The lab matched the fingerprint to the suspect.")
        self.assertIn("scientific", tags)
        self.assertIn("physical", tags)
        self.assertIn("forensic:fingerprint", tags)

    def test_tags_are_case_insensitive_and_deduplicated(self):
        tags = tag_evidence_item("witness", "CCTV footage backs up the eyewitness account.")
        self.assertEqual(tags, sorted(set(tags)))
        self.assertIn("video", tags)
        self.assertIn("eyewitness", tags)
        self.assertIn("testimonial", tags)

    def test_index_is_keyed_by_evidence_code(self):
        case = SimpleNamespace(evidence_items=[
            SimpleNamespace(evidence_code="E1", kind="witness", content="Clerk testimony.",
                             metadata_json={"tags": ["testimonial"]}),
            SimpleNamespace(evidence_code="E2", kind="forensic", content="Fingerprint report.",
                             metadata_json={"tags": ["scientific", "physical", "forensic:fingerprint"]}),
        ])
        index = build_evidence_index(case)
        self.assertEqual(set(index), {"E1", "E2"})
        self.assertEqual(index["E2"].tags, ["forensic:fingerprint", "physical", "scientific"])


if __name__ == "__main__":
    unittest.main()
