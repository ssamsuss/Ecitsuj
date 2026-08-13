import csv
import io
import unittest
from types import SimpleNamespace
from uuid import uuid4

from app.services.export import build_export_bundle, votes_to_csv


class _FakeDB:
    def __init__(self, run):
        self._run = run

    def get(self, model, run_id):
        return self._run if run_id == self._run.id else None


class VotesToCsvTests(unittest.TestCase):
    def test_produces_header_and_rows(self):
        csv_text = votes_to_csv([{
            "juror_number": 1,
            "phase": "initial",
            "verdict": "guilty",
            "confidence": 0.7,
            "rationale": "Clear evidence.",
            "cited_evidence_codes": ["E1", "E2"],
            "what_changed": None,
        }])
        rows = list(csv.DictReader(io.StringIO(csv_text)))
        self.assertEqual(rows[0]["juror_number"], "1")
        self.assertEqual(rows[0]["cited_evidence_codes"], "E1;E2")
        self.assertEqual(rows[0]["what_changed"], "")

    def test_neutralizes_formula_injection(self):
        csv_text = votes_to_csv([{
            "juror_number": 1,
            "phase": "initial",
            "verdict": "guilty",
            "confidence": 0.5,
            "rationale": "=cmd|'/c calc'!A1",
            "cited_evidence_codes": [],
            "what_changed": "+SUM(A1:A9)",
        }])
        rows = list(csv.DictReader(io.StringIO(csv_text)))
        self.assertTrue(rows[0]["rationale"].startswith("'="))
        self.assertTrue(rows[0]["what_changed"].startswith("'+"))


class BuildExportBundleTests(unittest.TestCase):
    def test_returns_none_for_missing_run(self):
        db = _FakeDB(SimpleNamespace(id=uuid4()))
        self.assertIsNone(build_export_bundle(db, uuid4()))

    def test_bundle_includes_report_votes_and_transcript(self):
        run_id = uuid4()
        j1 = uuid4()
        run = SimpleNamespace(
            id=run_id,
            case_id=uuid4(),
            status="done",
            model_name="gpt-4.1",
            created_at=None,
            completed_at=None,
            estimated_cost_usd=None,
            jurors=[SimpleNamespace(id=j1, juror_number=1)],
            votes=[
                SimpleNamespace(
                    juror_id=j1, phase="initial", verdict="guilty", confidence=0.6,
                    rationale="r1", cited_evidence_codes=["E1"], what_changed=None,
                ),
            ],
            messages=[
                SimpleNamespace(
                    round_no=1, turn_no=1, juror_id=j1, message_text="m1",
                    cited_evidence_codes=["E1"], stance="support", flags_json={},
                ),
            ],
            metrics=None,
        )
        db = _FakeDB(run)

        bundle = build_export_bundle(db, run_id)

        self.assertEqual(bundle["run_id"], str(run_id))
        self.assertEqual(len(bundle["votes"]), 1)
        self.assertEqual(bundle["votes"][0]["juror_number"], 1)
        self.assertEqual(len(bundle["transcript"]), 1)
        self.assertEqual(bundle["transcript"][0]["stance"], "support")
        self.assertIn("initial_split", bundle["report"])
        self.assertEqual(bundle["estimated_cost_usd"], 0.0)


if __name__ == "__main__":
    unittest.main()
