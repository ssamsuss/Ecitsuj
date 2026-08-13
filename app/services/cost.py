"""Rough LLM cost estimation from character counts.

No real token counts are available from the stubbed LLM client, so cost is
approximated from characters (~4 chars/token) using published per-1K-token
rates. Update the pricing table when wiring a real provider/model.
"""

# (input $/1K chars, output $/1K chars)
_PRICING_PER_1K_CHARS_USD: dict[str, tuple[float, float]] = {
    "gpt-4.1": (0.0005, 0.002),
    "gpt-4o": (0.00025, 0.001),
    "gpt-4o-mini": (0.00004, 0.00015),
}
_DEFAULT_RATE_PER_1K_CHARS_USD = (0.0005, 0.0015)


def estimate_cost_usd(model: str, prompt_chars: int, completion_chars: int) -> float:
    input_rate, output_rate = _PRICING_PER_1K_CHARS_USD.get(model, _DEFAULT_RATE_PER_1K_CHARS_USD)
    return (prompt_chars / 1000) * input_rate + (completion_chars / 1000) * output_rate
