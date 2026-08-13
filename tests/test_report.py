import unittest
from types import SimpleNamespace
from uuid import uuid4

from app.services.report import build_report


class _FakeDB:
    def __init__(self, run):
        self._run = run

    def get(self, model, run_id):
        return self._run if run_id == self._run.id else None


def _vote(juror_id, phase, verdict, confidence):
    return SimpleNamespace(juror_id=juror_id, phase=phase, verdict=verdict, confidence=confidence)


def _message(juror_id, flags):
    return SimpleNamespace(juror_id=juror_id, flags_json=flags)


class BuildReportTests(unittest.TestCase):
    def test_returns_none_for_missing_run(self):
        db = _FakeDB(SimpleNamespace(id=uuid4()))
        self.assertIsNone(build_report(db, uuid4()))

    def test_splits_shifts_and_confidence_without_stored_metrics(self):
        run_id = uuid4()
        j1, j2 = uuid4(), uuid4()
        run = SimpleNamespace(
            id=run_id,
            status="done",
            jurors=[SimpleNamespace(id=j1, juror_number=1), SimpleNamespace(id=j2, juror_number=2)],
            votes=[
                _vote(j1, "initial", "guilty", 0.6),
                _vote(j2, "initial", "not_guilty", 0.4),
                _vote(j1, "final", "guilty", 0.9),
                _vote(j2, "final", "guilty", 0.7),
            ],
            messages=[
                _message(j1, {"missing_citation": False, "contradiction_flag": False}),
                _message(j1, {"missing_citation": True, "contradiction_flag": True}),
                _message(j2, {"missing_citation": False, "contradiction_flag": False}),
            ],
            metrics=None,
            estimated_cost_usd=None,
        )
        db = _FakeDB(run)

        report = build_report(db, run_id)

        self.assertEqual(report["initial_split"], {"guilty": 1, "not_guilty": 1, "undecided": 0})
        self.assertEqual(report["final_split"], {"guilty": 2, "not_guilty": 0, "undecided": 0})
        self.assertEqual(len(report["vote_shifts"]), 2)
        shift_j2 = next(s for s in report["vote_shifts"] if s["juror_number"] == 2)
        self.assertEqual(shift_j2["from"], "not_guilty")
        self.assertEqual(shift_j2["to"], "guilty")
        self.assertTrue(shift_j2["changed"])
        self.assertAlmostEqual(report["metrics"]["avg_confidence_initial"], 0.5)
        self.assertAlmostEqual(report["metrics"]["avg_confidence_final"], 0.8)
        self.assertGreaterEqual(report["metrics"]["vote_entropy_initial"], 0)
        self.assertAlmostEqual(report["metrics"]["citation_coverage"], 2 / 3)
        self.assertAlmostEqual(report["metrics"]["contradiction_rate"], 1 / 3)
        self.assertAlmostEqual(report["metrics"]["dominance_index"], (2 / 3) ** 2 + (1 / 3) ** 2)
        self.assertEqual(report["warnings"], [])

    def test_uses_stored_metrics_when_available(self):
        run_id = uuid4()
        j1 = uuid4()
        run = SimpleNamespace(
            id=run_id,
            status="done",
            jurors=[SimpleNamespace(id=j1, juror_number=1)],
            votes=[_vote(j1, "initial", "guilty", 0.6), _vote(j1, "final", "guilty", 0.6)],
            messages=[],
            metrics=SimpleNamespace(
                vote_entropy_initial=0.0, vote_entropy_final=0.0,
                persuasion_index=0.25, citation_coverage=0.75,
                contradiction_rate=0.1, dominance_index=0.2,
            ),
            estimated_cost_usd=0.0123,
        )
        db = _FakeDB(run)

        report = build_report(db, run_id)

        self.assertEqual(report["metrics"]["persuasion_index"], 0.25)
        self.assertEqual(report["metrics"]["citation_coverage"], 0.75)

    def test_incomplete_run_has_zeroed_confidence_and_splits(self):
        run_id = uuid4()
        run = SimpleNamespace(id=run_id, status="failed", jurors=[], votes=[], messages=[], metrics=None, estimated_cost_usd=None)
        db = _FakeDB(run)

        report = build_report(db, run_id)

        self.assertEqual(report["initial_split"], {"guilty": 0, "not_guilty": 0, "undecided": 0})
        self.assertEqual(report["vote_shifts"], [])
        self.assertEqual(report["metrics"]["avg_confidence_initial"], 0.0)
        self.assertEqual(report["metrics"]["avg_confidence_final"], 0.0)

    def test_warns_on_large_confidence_swing(self):
        run_id = uuid4()
        j1 = uuid4()
        run = SimpleNamespace(
            id=run_id,
            status="done",
            jurors=[SimpleNamespace(id=j1, juror_number=1)],
            votes=[
                _vote(j1, "initial", "not_guilty", 0.2),
                _vote(j1, "final", "not_guilty", 0.9),
            ],
            messages=[],
            metrics=None,
            estimated_cost_usd=None,
        )
        db = _FakeDB(run)

        report = build_report(db, run_id)

        self.assertEqual(len(report["warnings"]), 1)
        self.assertIn("Juror #1", report["warnings"][0])

    def test_warns_when_majority_of_jurors_swing_verdict(self):
        run_id = uuid4()
        j1, j2, j3 = uuid4(), uuid4(), uuid4()
        run = SimpleNamespace(
            id=run_id,
            status="done",
            jurors=[SimpleNamespace(id=j, juror_number=i) for i, j in enumerate([j1, j2, j3], start=1)],
            votes=[
                _vote(j1, "initial", "guilty", 0.5), _vote(j1, "final", "not_guilty", 0.6),
                _vote(j2, "initial", "not_guilty", 0.5), _vote(j2, "final", "guilty", 0.6),
                _vote(j3, "initial", "guilty", 0.5), _vote(j3, "final", "guilty", 0.6),
            ],
            messages=[],
            metrics=None,
            estimated_cost_usd=None,
        )
        db = _FakeDB(run)

        report = build_report(db, run_id)

        self.assertTrue(any("jurors changed verdict" in w for w in report["warnings"]))


if __name__ == "__main__":
    unittest.main()
