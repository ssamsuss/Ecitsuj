from collections import Counter
from math import log2
from typing import Iterable

def split_counts(verdicts: Iterable[str]) -> dict[str, int]:
    c = Counter(verdicts)
    return {
        "guilty": c.get("guilty", 0),
        "not_guilty": c.get("not_guilty", 0),
        "undecided": c.get("undecided", 0),
    }

def entropy_from_split(split: dict[str, int]) -> float:
    total = sum(split.values()) or 1
    ps = [v / total for v in split.values() if v > 0]
    return -sum(p * log2(p) for p in ps)

def average_confidence(confidences: Iterable[float]) -> float:
    values = list(confidences)
    return sum(values) / len(values) if values else 0.0

def citation_coverage(turn_flags: Iterable[dict]) -> float:
    """Fraction of deliberation turns that cited at least one evidence code."""
    values = list(turn_flags)
    if not values:
        return 0.0
    return sum(1 for f in values if not f.get("missing_citation")) / len(values)

def contradiction_rate(turn_flags: Iterable[dict]) -> float:
    """Fraction of deliberation turns flagged as contradicting the same juror's prior stance."""
    values = list(turn_flags)
    if not values:
        return 0.0
    return sum(1 for f in values if f.get("contradiction_flag")) / len(values)

def dominance_index(turn_counts: Iterable[int]) -> float:
    """Herfindahl-Hirschman concentration of turns across jurors (1/n=even, 1=one juror dominates)."""
    counts = list(turn_counts)
    total = sum(counts)
    if total == 0:
        return 0.0
    return sum((c / total) ** 2 for c in counts)

CONFIDENCE_SWING_THRESHOLD = 0.4
VERDICT_SWING_RATIO = 0.5

def build_swing_warnings(
    vote_shifts: Iterable[dict],
    confidence_threshold: float = CONFIDENCE_SWING_THRESHOLD,
    verdict_swing_ratio: float = VERDICT_SWING_RATIO,
) -> list[str]:
    """Flag jurors whose confidence swung sharply, or a jury that swung verdicts en masse."""
    shifts = list(vote_shifts)
    warnings = []

    if shifts:
        changed = [s for s in shifts if s["changed"]]
        if len(changed) / len(shifts) > verdict_swing_ratio:
            warnings.append(
                f"{len(changed)}/{len(shifts)} jurors changed verdict between initial and final votes "
                f"(exceeds {verdict_swing_ratio:.0%} threshold)"
            )

    for shift in shifts:
        swing = abs(shift["confidence_to"] - shift["confidence_from"])
        if swing > confidence_threshold:
            warnings.append(
                f"Juror #{shift['juror_number']} confidence swung by {swing:.2f} "
                f"({shift['confidence_from']:.2f} -> {shift['confidence_to']:.2f}), "
                f"exceeding {confidence_threshold:.2f} threshold"
            )

    return warnings