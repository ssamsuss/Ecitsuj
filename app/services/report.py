from collections import Counter
from sqlalchemy.orm import Session
from app import models
from app.services.metrics import (
    average_confidence,
    build_swing_warnings,
    citation_coverage,
    contradiction_rate,
    dominance_index,
    entropy_from_split,
    split_counts,
)

def build_report(db: Session, run_id):
    run = db.get(models.SimulationRun, run_id)
    if not run:
        return None

    juror_map = {j.id: j.juror_number for j in run.jurors}
    initial = {v.juror_id: v for v in run.votes if v.phase == "initial"}
    final = {v.juror_id: v for v in run.votes if v.phase == "final"}

    vote_shifts = []
    for juror_id, iv in initial.items():
        fv = final.get(juror_id)
        if not fv:
            continue
        vote_shifts.append({
            "juror_number": juror_map[juror_id],
            "from": iv.verdict,
            "to": fv.verdict,
            "confidence_from": float(iv.confidence),
            "confidence_to": float(fv.confidence),
            "changed": iv.verdict != fv.verdict
        })

    initial_split = split_counts(v.verdict for v in initial.values())
    final_split = split_counts(v.verdict for v in final.values())
    metrics = run.metrics
    messages = run.messages
    turn_flags = [m.flags_json for m in messages]
    turn_counts_per_juror = Counter(m.juror_id for m in messages).values()
    sorted_shifts = sorted(vote_shifts, key=lambda x: x["juror_number"])

    return {
        "run_id": str(run.id),
        "status": run.status,
        "initial_split": initial_split,
        "final_split": final_split,
        "vote_shifts": sorted_shifts,
        "warnings": build_swing_warnings(sorted_shifts),
        "metrics": {
            "vote_entropy_initial": float(metrics.vote_entropy_initial) if metrics and metrics.vote_entropy_initial is not None else entropy_from_split(initial_split),
            "vote_entropy_final": float(metrics.vote_entropy_final) if metrics and metrics.vote_entropy_final is not None else entropy_from_split(final_split),
            "avg_confidence_initial": average_confidence(float(v.confidence) for v in initial.values()),
            "avg_confidence_final": average_confidence(float(v.confidence) for v in final.values()),
            "persuasion_index": float(metrics.persuasion_index or 0) if metrics else 0.0,
            "citation_coverage": float(metrics.citation_coverage) if metrics and metrics.citation_coverage is not None else citation_coverage(turn_flags),
            "contradiction_rate": float(metrics.contradiction_rate) if metrics and metrics.contradiction_rate is not None else contradiction_rate(turn_flags),
            "dominance_index": float(metrics.dominance_index) if metrics and metrics.dominance_index is not None else dominance_index(turn_counts_per_juror),
            "estimated_cost_usd": float(run.estimated_cost_usd) if run.estimated_cost_usd is not None else 0.0,
        }
    }