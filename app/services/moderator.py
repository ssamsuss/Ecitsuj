import re
from typing import Any

_NUMBER_PATTERN = re.compile(r"\d[\d:,.]*")


def _numeric_tokens(text: str) -> set[str]:
    return set(_NUMBER_PATTERN.findall(text))


def has_new_facts(message: str, grounded_text: str) -> bool:
    """Flag numeric claims (times, counts, dates) absent from the case packet."""
    message_numbers = _numeric_tokens(message)
    if not message_numbers:
        return False
    return not message_numbers.issubset(_numeric_tokens(grounded_text))


class ContradictionTracker:
    """Flags a juror citing the same evidence code with an opposing stance across turns."""

    _OPPOSING = {"support": "challenge", "challenge": "support"}

    def __init__(self):
        self._history: dict[tuple[int, str], str] = {}

    def check_and_record(self, juror_number: int, cited_codes: list[str], stance: str) -> bool:
        contradicted = False
        for code in cited_codes:
            key = (juror_number, code)
            prior_stance = self._history.get(key)
            if prior_stance and self._OPPOSING.get(prior_stance) == stance:
                contradicted = True
            self._history[key] = stance
        return contradicted


def validate_turn(
    message: str,
    cited_codes: list[str],
    allowed_codes: set[str],
    grounded_text: str = "",
    contradiction_flag: bool = False,
) -> dict[str, Any]:
    flags = {
        "missing_citation": len(cited_codes) == 0,
        "invalid_citation": any(c not in allowed_codes for c in cited_codes),
        "new_fact_flag": has_new_facts(message, grounded_text),
        "contradiction_flag": contradiction_flag,
    }
    return flags