import unittest
from types import SimpleNamespace

from pydantic import ValidationError

from app.schemas import CasePacketIn, DeliberationTurnResult
from app.services.simulation import _case_packet_dict


class CasePacketValidationTests(unittest.TestCase):
    def setUp(self):
        self.packet = {
            "title": "State v. Doe",
            "facts": ["The alarm sounded."],
            "jury_instructions": "Presume innocence.",
            "evidence_items": [
                {
                    "code": "E1",
                    "kind": "witness",
                    "content": "Clerk testimony.",
                    "metadata": {"source": "transcript"},
                }
            ],
        }

    def test_duplicate_codes_are_rejected(self):
        self.packet["evidence_items"].append({
            "code": "E1",
            "kind": "exhibit",
            "content": "CCTV footage.",
        })
        with self.assertRaises(ValidationError):
            CasePacketIn.model_validate(self.packet)

    def test_malformed_codes_are_rejected(self):
        self.packet["evidence_items"][0]["code"] = "evidence-1"
        with self.assertRaises(ValidationError):
            CasePacketIn.model_validate(self.packet)

    def test_extra_fields_are_rejected(self):
        self.packet["unexpected"] = True
        with self.assertRaises(ValidationError):
            CasePacketIn.model_validate(self.packet)

    def test_missing_fields_are_rejected(self):
        del self.packet["jury_instructions"]
        with self.assertRaises(ValidationError):
            CasePacketIn.model_validate(self.packet)

    def test_deliberation_citations_use_evidence_code_format(self):
        with self.assertRaises(ValidationError):
            DeliberationTurnResult(
                message="The testimony is uncertain.",
                cited_evidence_codes=["witness-1"],
                stance="challenge",
            )

    def test_evidence_tags_are_preserved_for_simulation(self):
        case = SimpleNamespace(
            title="State v. Doe",
            jurisdiction=None,
            charge=None,
            standard_of_proof="beyond a reasonable doubt",
            facts_json={"facts": ["The alarm sounded."]},
            instructions_text="Presume innocence.",
            evidence_items=[SimpleNamespace(
                evidence_code="E1",
                kind="witness",
                content="Clerk testimony.",
                metadata_json={"tags": ["testimonial"]},
            )],
        )
        packet = _case_packet_dict(case)
        self.assertEqual(packet["evidence_items"][0]["tags"], ["testimonial"])


if __name__ == "__main__":
    unittest.main()
