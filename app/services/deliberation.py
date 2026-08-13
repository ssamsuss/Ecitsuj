import hashlib


def _round_offset(seed: int, round_no: int, juror_count: int) -> int:
    digest = hashlib.sha256(f"{seed}:{round_no}".encode()).digest()
    return int.from_bytes(digest[:8], "big") % juror_count


def turn_order_for_round(jurors: list, seed: int, round_no: int) -> list:
    """Rotate the speaking order each round so no juror always leads; deterministic per seed."""
    if not jurors:
        return []
    offset = _round_offset(seed, round_no, len(jurors))
    return jurors[offset:] + jurors[:offset]
