import json
import logging
import time
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class LLMTimeoutError(Exception):
    """Raised when a single LLM call exceeds its configured timeout budget."""


class LLMTransientError(Exception):
    """Raised for retryable provider errors (rate limits, connection resets, 5xx, etc.)."""


# Replace this with your provider SDK (OpenAI, Azure OpenAI, etc.)
# Keep interface stable for easier testing.
class LLMClient:
    def __init__(self, model: str, max_retries: int = 3, timeout: float = 30.0, backoff_base: float = 0.5):
        self.model = model
        self.max_retries = max_retries
        self.timeout = timeout
        self.backoff_base = backoff_base
        self.call_count = 0
        self.total_prompt_chars = 0
        self.total_completion_chars = 0

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.4,
        output_type: str = "vote",
    ) -> dict[str, Any]:
        return self._with_retries(self._call_provider, system_prompt, user_prompt, temperature, output_type)

    def _with_retries(self, fn: Callable[..., T], *args, **kwargs) -> T:
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            start = time.monotonic()
            try:
                result = fn(*args, **kwargs)
                elapsed = time.monotonic() - start
                if elapsed > self.timeout:
                    raise LLMTimeoutError(f"LLM call exceeded {self.timeout}s timeout budget (took {elapsed:.2f}s)")
                return result
            except LLMTransientError as e:
                last_error = e
                if attempt == self.max_retries:
                    break
                delay = self.backoff_base * (2 ** (attempt - 1))
                logger.warning(
                    "LLM call attempt %d/%d failed: %s; retrying in %.2fs", attempt, self.max_retries, e, delay
                )
                time.sleep(delay)
        logger.error("LLM call failed after %d attempts: %s", self.max_retries, last_error)
        raise last_error

    def _call_provider(self, system_prompt: str, user_prompt: str, temperature: float, output_type: str) -> dict[str, Any]:
        """
        Stubbed deterministic fallback for local dev.
        Replace with real model call that enforces JSON output, passes
        `timeout=self.timeout` to the HTTP client, and raises LLMTransientError
        on retryable failures (timeouts, rate limits, 5xx).
        """
        # TODO: provider call with response_format=json_schema if supported
        self.call_count += 1
        self.total_prompt_chars += len(system_prompt) + len(user_prompt)

        if output_type == "deliberation":
            result = {
                "message": "The available evidence does not resolve the uncertainty.",
                "cited_evidence_codes": [],
                "stance": "clarify",
            }
        else:
            result = {
                "verdict": "undecided",
                "confidence": 0.5,
                "rationale": "Insufficient certainty from provided evidence.",
                "cited_evidence_codes": [],
            }
            if output_type == "final_vote":
                result["what_changed"] = "No additional certainty emerged during deliberation."

        self.total_completion_chars += len(json.dumps(result))
        return result