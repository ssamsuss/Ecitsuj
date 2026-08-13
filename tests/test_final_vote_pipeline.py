import threading
import unittest
from types import SimpleNamespace

from app.services.simulation import run_final_votes


def _juror_number_from_system_prompt(system_prompt: str) -> int:
    return int(system_prompt.split("#", 1)[1].split(" ", 1)[0])


class _ConcurrentFakeLLM:
    """Fake LLM that blocks on a barrier to prove calls overlap in time."""

    def __init__(self, juror_count: int):
        self._barrier = threading.Barrier(juror_count)
        self._lock = threading.Lock()
        self._in_flight = 0
        self.max_in_flight = 0

    def complete_json(self, system_prompt, user_prompt, temperature=0.4, output_type="final_vote"):
        with self._lock:
            self._in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self._in_flight)
        self._barrier.wait(timeout=2)
        with self._lock:
            self._in_flight -= 1
        juror_number = _juror_number_from_system_prompt(system_prompt)
        return {
            "verdict": "guilty" if juror_number % 2 == 0 else "not_guilty",
            "confidence": 0.6,
            "rationale": f"Juror {juror_number} final rationale.",
            "what_changed": f"Juror {juror_number} updated after deliberation.",
            "cited_evidence_codes": ["E1"],
        }


class _BadCitationLLM:
    def complete_json(self, system_prompt, user_prompt, temperature=0.4, output_type="final_vote"):
        return {
            "verdict": "guilty",
            "confidence": 0.5,
            "rationale": "cites unknown evidence",
            "what_changed": "n/a",
            "cited_evidence_codes": ["E9"],
        }


class FinalVotePipelineTests(unittest.TestCase):
    def _jurors(self, count):
        return [
            SimpleNamespace(juror_number=i, persona_json={"style": "calm"})
            for i in range(1, count + 1)
        ]

    def _case(self):
        return SimpleNamespace(standard_of_proof="beyond a reasonable doubt")

    def test_final_votes_are_dispatched_concurrently(self):
        jurors = self._jurors(12)
        llm = _ConcurrentFakeLLM(len(jurors))

        votes = run_final_votes(llm, self._case(), {"E1"}, 0.4, jurors)

        self.assertEqual(len(votes), 12)
        self.assertGreater(llm.max_in_flight, 1)

    def test_what_changed_is_preserved_per_juror(self):
        jurors = self._jurors(3)
        llm = _ConcurrentFakeLLM(len(jurors))

        votes = run_final_votes(llm, self._case(), {"E1"}, 0.4, jurors)

        self.assertEqual(
            [v.what_changed for v in votes],
            ["Juror 1 updated after deliberation.", "Juror 2 updated after deliberation.", "Juror 3 updated after deliberation."],
        )

    def test_empty_juror_list_returns_empty(self):
        self.assertEqual(run_final_votes(object(), self._case(), set(), 0.4, []), [])

    def test_unknown_citation_raises(self):
        with self.assertRaises(ValueError):
            run_final_votes(_BadCitationLLM(), self._case(), {"E1"}, 0.4, self._jurors(1))


if __name__ == "__main__":
    unittest.main()
