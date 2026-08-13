import hashlib
import random
from dataclasses import asdict, dataclass

EVIDENCE_RIGOR = ("low", "medium", "high")
GROUP_DEFERENCE = ("low", "high")
RISK_AVERSION = ("avoid_false_conviction", "avoid_false_acquittal")
STYLE = ("assertive", "calm", "analytical")
TRUST_LEVELS = ("low", "medium", "high")


@dataclass(frozen=True)
class JurorPersona:
    juror_number: int
    evidence_rigor: str
    group_deference: str
    risk_aversion: str
    style: str
    trust_forensics: str
    trust_eyewitness: str


def _juror_seed(seed: int, juror_number: int) -> int:
    """Derive a per-juror seed so a persona stays fixed regardless of juror_count."""
    digest = hashlib.sha256(f"{seed}:{juror_number}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def _build_persona(seed: int, juror_number: int) -> JurorPersona:
    rnd = random.Random(_juror_seed(seed, juror_number))
    return JurorPersona(
        juror_number=juror_number,
        evidence_rigor=rnd.choice(EVIDENCE_RIGOR),
        group_deference=rnd.choice(GROUP_DEFERENCE),
        risk_aversion=rnd.choice(RISK_AVERSION),
        style=rnd.choice(STYLE),
        trust_forensics=rnd.choice(TRUST_LEVELS),
        trust_eyewitness=rnd.choice(TRUST_LEVELS),
    )


def build_personas(juror_count: int, seed: int) -> list[dict]:
    if juror_count < 1:
        raise ValueError("juror_count must be at least 1")
    return [asdict(_build_persona(seed, i)) for i in range(1, juror_count + 1)]
