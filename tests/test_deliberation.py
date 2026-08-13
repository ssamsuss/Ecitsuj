import unittest
from types import SimpleNamespace
from uuid import uuid4

from app.services.deliberation import turn_order_for_round
from app.services.simulation import run_deliberation_rounds


class _FakeDB:
    def __init__(self):
        self.added = []
        self.commits = 0

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commits += 1


class _FakeLLM:
    def complete_json(self, system_prompt, user_prompt, temperature=0.4, output_type="vote"):
        return {"message": "A turn.", "cited_evidence_codes": [], "stance": "clarify"}


class TurnOrderTests(unittest.TestCase):
    def test_deterministic_for_same_seed_and_round(self):
        jurors = list(range(1, 13))
        self.assertEqual(
            turn_order_for_round(jurors, seed=42, round_no=1),
            turn_order_for_round(jurors, seed=42, round_no=1),
        )

    def test_rotates_across_rounds(self):
        jurors = list(range(1, 13))
        orders = {tuple(turn_order_for_round(jurors, seed=42, round_no=r)) for r in range(1, 13)}
        self.assertGreater(len(orders), 1)

    def test_every_juror_still_included(self):
        jurors = list(range(1, 13))
        order = turn_order_for_round(jurors, seed=1, round_no=5)
        self.assertEqual(sorted(order), jurors)

    def test_empty_jurors_returns_empty(self):
        self.assertEqual(turn_order_for_round([], seed=1, round_no=1), [])


class DeliberationRoundsTests(unittest.TestCase):
    def _jurors(self, count):
        return [SimpleNamespace(id=uuid4(), juror_number=i, persona_json={}) for i in range(1, count + 1)]

    def test_round_loop_persists_all_turns_and_commits_per_round(self):
        jurors = self._jurors(4)
        run = SimpleNamespace(id=uuid4())
        case = SimpleNamespace(standard_of_proof="beyond a reasonable doubt")
        db = _FakeDB()

        run_deliberation_rounds(db, run, case, jurors, _FakeLLM(), set(), 0.4, max_rounds=3, seed=42)

        self.assertEqual(len(db.added), 12)
        self.assertEqual(db.commits, 3)
        self.assertEqual([m.turn_no for m in db.added], list(range(1, 13)))

    def test_speaking_order_matches_turn_order_for_round(self):
        jurors = self._jurors(4)
        run = SimpleNamespace(id=uuid4())
        case = SimpleNamespace(standard_of_proof="beyond a reasonable doubt")
        db = _FakeDB()

        run_deliberation_rounds(db, run, case, jurors, _FakeLLM(), set(), 0.4, max_rounds=2, seed=42)

        expected_round_1 = [j.id for j in turn_order_for_round(jurors, seed=42, round_no=1)]
        expected_round_2 = [j.id for j in turn_order_for_round(jurors, seed=42, round_no=2)]
        self.assertEqual([m.juror_id for m in db.added[:4]], expected_round_1)
        self.assertEqual([m.juror_id for m in db.added[4:8]], expected_round_2)

    def test_unknown_citation_raises(self):
        class _BadCitationLLM:
            def complete_json(self, system_prompt, user_prompt, temperature=0.4, output_type="vote"):
                return {"message": "cites unknown evidence", "cited_evidence_codes": ["E9"], "stance": "challenge"}

        run = SimpleNamespace(id=uuid4())
        case = SimpleNamespace(standard_of_proof="beyond a reasonable doubt")
        with self.assertRaises(ValueError):
            run_deliberation_rounds(_FakeDB(), run, case, self._jurors(1), _BadCitationLLM(), {"E1"}, 0.4, 1, seed=1)

    def test_expired_deadline_raises_before_any_turn(self):
        import time

        db = _FakeDB()
        run = SimpleNamespace(id=uuid4())
        case = SimpleNamespace(standard_of_proof="beyond a reasonable doubt")
        expired_deadline = time.monotonic() - 1

        with self.assertRaises(TimeoutError):
            run_deliberation_rounds(
                db, run, case, self._jurors(2), _FakeLLM(), set(), 0.4, 1, seed=1, deadline=expired_deadline
            )
        self.assertEqual(db.added, [])


if __name__ == "__main__":
    unittest.main()
