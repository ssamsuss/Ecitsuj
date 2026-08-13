import unittest

from app.llm import LLMClient, LLMTimeoutError, LLMTransientError


class LLMClientRetryTests(unittest.TestCase):
    def test_succeeds_without_retry(self):
        client = LLMClient(model="gpt-4.1", max_retries=3)
        calls = []

        def fn():
            calls.append(1)
            return "ok"

        self.assertEqual(client._with_retries(fn), "ok")
        self.assertEqual(len(calls), 1)

    def test_retries_transient_errors_then_succeeds(self):
        client = LLMClient(model="gpt-4.1", max_retries=3, backoff_base=0.0)
        attempts = {"count": 0}

        def fn():
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise LLMTransientError("rate limited")
            return "ok"

        self.assertEqual(client._with_retries(fn), "ok")
        self.assertEqual(attempts["count"], 3)

    def test_raises_after_exhausting_retries(self):
        client = LLMClient(model="gpt-4.1", max_retries=2, backoff_base=0.0)

        def fn():
            raise LLMTransientError("still failing")

        with self.assertRaises(LLMTransientError):
            client._with_retries(fn)

    def test_non_transient_errors_are_not_retried(self):
        client = LLMClient(model="gpt-4.1", max_retries=3, backoff_base=0.0)
        attempts = {"count": 0}

        def fn():
            attempts["count"] += 1
            raise ValueError("not retryable")

        with self.assertRaises(ValueError):
            client._with_retries(fn)
        self.assertEqual(attempts["count"], 1)

    def test_slow_call_raises_timeout(self):
        import time

        client = LLMClient(model="gpt-4.1", max_retries=1, timeout=0.0)

        def fn():
            time.sleep(0.01)
            return "ok"

        with self.assertRaises(LLMTimeoutError):
            client._with_retries(fn)


class LLMClientCostTrackingTests(unittest.TestCase):
    def test_tracks_call_count_and_char_totals(self):
        client = LLMClient(model="gpt-4.1")
        client.complete_json("system prompt", "user prompt", output_type="vote")
        client.complete_json("another system", "another user", output_type="deliberation")

        self.assertEqual(client.call_count, 2)
        self.assertGreater(client.total_prompt_chars, 0)
        self.assertGreater(client.total_completion_chars, 0)


if __name__ == "__main__":
    unittest.main()
