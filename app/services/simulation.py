import logging
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import partial
from sqlalchemy.orm import Session
from app import models, schemas
from app.config import settings
from app.llm import LLMClient
from app.prompts import JUROR_SYSTEM, INITIAL_VOTE_PROMPT, TURN_PROMPT, FINAL_VOTE_PROMPT
from app.services.personas import build_personas
from app.services.moderator import validate_turn, ContradictionTracker
from app.services.metrics import (
    split_counts,
    entropy_from_split,
    citation_coverage,
    contradiction_rate,
    dominance_index,
)
from app.services.cases import build_evidence_index
from app.services.cost import estimate_cost_usd
from app.services.deliberation import turn_order_for_round

logger = logging.getLogger(__name__)

INITIAL_VOTE_MAX_WORKERS = 12


def _check_time_budget(deadline: float | None) -> None:
    if deadline is not None and time.monotonic() > deadline:
        raise TimeoutError("run exceeded its time budget")

def _case_packet_dict(case: models.Case) -> dict:
    index = build_evidence_index(case)
    return {
        "title": case.title,
        "jurisdiction": case.jurisdiction,
        "charge": case.charge,
        "standard_of_proof": case.standard_of_proof,
        "facts": case.facts_json.get("facts", []),
        "jury_instructions": case.instructions_text,
        "evidence_items": [
            {"code": e.code, "kind": e.kind, "content": e.content, "tags": e.tags}
            for e in index.values()
        ],
    }

def _ensure_allowed_citations(codes: list[str], allowed_codes: set[str]) -> None:
    invalid = sorted(set(codes) - allowed_codes)
    if invalid:
        raise ValueError(f"LLM returned unknown evidence codes: {', '.join(invalid)}")

def _collect_initial_vote(llm, case, packet, allowed_codes, temperature, juror) -> schemas.InitialVoteResult:
    system = JUROR_SYSTEM.format(
        juror_number=juror.juror_number,
        standard_of_proof=case.standard_of_proof,
        persona_json=juror.persona_json,
    )
    user = INITIAL_VOTE_PROMPT.format(case_packet=packet)
    out = schemas.InitialVoteResult.model_validate(
        llm.complete_json(system, user, temperature=temperature)
    )
    _ensure_allowed_citations(out.cited_evidence_codes, allowed_codes)
    return out

def run_initial_votes(llm, case, packet, allowed_codes, temperature, jurors) -> list[schemas.InitialVoteResult]:
    """Dispatch initial vote calls concurrently (up to 12 in flight), preserving juror order."""
    if not jurors:
        return []
    worker = partial(_collect_initial_vote, llm, case, packet, allowed_codes, temperature)
    with ThreadPoolExecutor(max_workers=min(len(jurors), INITIAL_VOTE_MAX_WORKERS)) as pool:
        return list(pool.map(worker, jurors))

def _grounded_text(packet: dict) -> str:
    return " ".join(packet["facts"]) + " " + " ".join(e["content"] for e in packet["evidence_items"])

def _collect_final_vote(llm, case, allowed_codes, temperature, juror) -> schemas.FinalVoteResult:
    system = JUROR_SYSTEM.format(
        juror_number=juror.juror_number,
        standard_of_proof=case.standard_of_proof,
        persona_json=juror.persona_json,
    )
    out = schemas.FinalVoteResult.model_validate(
        llm.complete_json(system, FINAL_VOTE_PROMPT, temperature=temperature, output_type="final_vote")
    )
    _ensure_allowed_citations(out.cited_evidence_codes, allowed_codes)
    return out

def run_final_votes(llm, case, allowed_codes, temperature, jurors) -> list[schemas.FinalVoteResult]:
    """Dispatch final vote calls concurrently (up to 12 in flight), preserving juror order."""
    if not jurors:
        return []
    worker = partial(_collect_final_vote, llm, case, allowed_codes, temperature)
    with ThreadPoolExecutor(max_workers=min(len(jurors), INITIAL_VOTE_MAX_WORKERS)) as pool:
        return list(pool.map(worker, jurors))

def run_deliberation_rounds(db, run, case, jurors, llm, allowed_codes, temperature, max_rounds, seed, grounded_text="", deadline=None) -> None:
    """Run each deliberation round with a rotated turn order, committing progress per round."""
    turn_no = 0
    round_summaries = []
    contradictions = ContradictionTracker()
    for round_no in range(1, max_rounds + 1):
        _check_time_budget(deadline)
        for j in turn_order_for_round(jurors, seed, round_no):
            turn_no += 1
            system = JUROR_SYSTEM.format(
                juror_number=j.juror_number,
                standard_of_proof=case.standard_of_proof,
                persona_json=j.persona_json
            )
            context = "\n".join(round_summaries[-8:]) or "No prior discussion."
            user = TURN_PROMPT.format(round_no=round_no, turn_no=turn_no, round_context=context)
            out = schemas.DeliberationTurnResult.model_validate(
                llm.complete_json(
                    system,
                    user,
                    temperature=temperature,
                    output_type="deliberation",
                )
            )
            msg = out.message
            cited = out.cited_evidence_codes
            _ensure_allowed_citations(cited, allowed_codes)
            flags = validate_turn(msg, cited, allowed_codes, grounded_text)
            flags["contradiction_flag"] = contradictions.check_and_record(j.juror_number, cited, out.stance)

            db.add(models.DeliberationMessage(
                run_id=run.id,
                round_no=round_no,
                turn_no=turn_no,
                juror_id=j.id,
                message_text=msg,
                cited_evidence_codes=cited,
                stance=out.stance,
                flags_json=flags
            ))
            round_summaries.append(f"J{j.juror_number}: {msg}")
        db.commit()
        logger.info("run %s completed deliberation round %d/%d", run.id, round_no, max_rounds)

def run_simulation(db: Session, payload: schemas.RunCreateIn) -> models.SimulationRun:
    case = db.get(models.Case, payload.case_id)
    if not case:
        raise ValueError("case_id not found")

    run = models.SimulationRun(
        case_id=case.id,
        model_name=payload.model_name,
        temperature=payload.temperature,
        status="running",
        config_json={
            "max_rounds": payload.max_rounds,
            "juror_count": payload.juror_count,
            "seed": payload.seed,
        },
    )
    db.add(run)
    db.flush()

    personas = build_personas(payload.juror_count, payload.seed)
    jurors = []
    for p in personas:
        j = models.Juror(run_id=run.id, juror_number=p["juror_number"], persona_json=p)
        db.add(j)
        jurors.append(j)
    db.commit()
    logger.info("run %s started with %d jurors", run.id, len(jurors))

    llm = LLMClient(model=payload.model_name, max_retries=settings.llm_max_retries, timeout=settings.llm_timeout_seconds)
    packet = _case_packet_dict(case)
    allowed_codes = set(build_evidence_index(case))
    timeout_seconds = payload.timeout_seconds or settings.run_timeout_seconds
    deadline = time.monotonic() + timeout_seconds

    try:
        _check_time_budget(deadline)
        # 1) initial private votes, dispatched concurrently (up to 12 in flight)
        initial_votes = run_initial_votes(
            llm, case, packet, allowed_codes, float(payload.temperature), jurors
        )
        for j, out in zip(jurors, initial_votes):
            db.add(models.Vote(
                run_id=run.id,
                juror_id=j.id,
                phase="initial",
                verdict=out.verdict,
                confidence=out.confidence,
                rationale=out.rationale,
                cited_evidence_codes=out.cited_evidence_codes,
            ))
        db.commit()
        logger.info("run %s persisted %d initial votes", run.id, len(initial_votes))

        # 2) deliberation rounds, rotating turn order each round
        run_deliberation_rounds(
            db, run, case, jurors, llm, allowed_codes,
            float(payload.temperature), payload.max_rounds, payload.seed,
            _grounded_text(packet), deadline,
        )

        # 3) final private votes, dispatched concurrently (up to 12 in flight)
        _check_time_budget(deadline)
        final_votes = run_final_votes(
            llm, case, allowed_codes, float(payload.temperature), jurors
        )
        for j, out in zip(jurors, final_votes):
            db.add(models.Vote(
                run_id=run.id,
                juror_id=j.id,
                phase="final",
                verdict=out.verdict,
                confidence=out.confidence,
                rationale=out.rationale,
                cited_evidence_codes=out.cited_evidence_codes,
                what_changed=out.what_changed,
            ))
        db.commit()
        logger.info("run %s persisted %d final votes", run.id, len(final_votes))

        # 4) metrics
        initial = [v.verdict for v in run.votes if v.phase == "initial"]
        final = [v.verdict for v in run.votes if v.phase == "final"]
        initial_split = split_counts(initial)
        final_split = split_counts(final)

        messages = run.messages
        turn_flags = [m.flags_json for m in messages]
        turn_counts_per_juror = Counter(m.juror_id for m in messages).values()

        metric = models.RunMetric(
            run_id=run.id,
            initial_split_json=initial_split,
            final_split_json=final_split,
            vote_entropy_initial=entropy_from_split(initial_split),
            vote_entropy_final=entropy_from_split(final_split),
            persuasion_index=0.0,      # TODO
            citation_coverage=citation_coverage(turn_flags),
            contradiction_rate=contradiction_rate(turn_flags),
            dominance_index=dominance_index(turn_counts_per_juror),
        )
        db.add(metric)

        run.status = "done"
        run.completed_at = datetime.utcnow()
        run.estimated_cost_usd = estimate_cost_usd(payload.model_name, llm.total_prompt_chars, llm.total_completion_chars)
        db.commit()
        db.refresh(run)
        logger.info("run %s done", run.id)
        return run
    except Exception:
        db.rollback()
        logger.exception("run %s failed", run.id)
        run.status = "failed"
        run.completed_at = datetime.utcnow()
        run.estimated_cost_usd = estimate_cost_usd(payload.model_name, llm.total_prompt_chars, llm.total_completion_chars)
        db.commit()
        raise