"""Demo: ingest a golden case, run a simulation with retries/timeout/cost
tracking, print a human-readable summary, and optionally write a JSON export.

Usage:
    export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/mockjury
    python scripts/demo.py --case burglary_basic --juror-count 5 --max-rounds 2
"""
import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

GOLDEN_CASES_DIR = REPO_ROOT / "case_packet" / "golden"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", default="burglary_basic", help="golden case name (see case_packet/golden/)")
    parser.add_argument("--juror-count", type=int, default=5)
    parser.add_argument("--max-rounds", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", help="optional path to write the JSON export bundle")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is required to run the demo")
        return 1

    case_path = GOLDEN_CASES_DIR / f"{args.case}.json"
    if not case_path.exists():
        available = sorted(p.stem for p in GOLDEN_CASES_DIR.glob("*.json"))
        print(f"Unknown golden case {args.case!r}. Available: {', '.join(available)}")
        return 1

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app import schemas
    from app.services.cases import ingest_case_packet
    from app.services.simulation import run_simulation
    from app.services.report import build_report
    from app.services.export import build_export_bundle

    engine = create_engine(database_url)
    with Session(engine) as db:
        packet = json.loads(case_path.read_text())
        case = ingest_case_packet(db, schemas.CasePacketIn.model_validate(packet))
        print(f"Ingested case {case.id} ({packet['title']!r})")

        run = run_simulation(db, schemas.RunCreateIn(
            case_id=case.id, juror_count=args.juror_count,
            max_rounds=args.max_rounds, seed=args.seed,
        ))
        print(f"Run {run.id} finished with status={run.status!r}")

        report = build_report(db, run.id)
        print(f"Initial split: {report['initial_split']}")
        print(f"Final split:   {report['final_split']}")
        for label, value in report["metrics"].items():
            print(f"  {label}: {value:.4f}" if isinstance(value, float) else f"  {label}: {value}")
        if report["warnings"]:
            print("Warnings:")
            for warning in report["warnings"]:
                print(f"  - {warning}")
        print(f"Estimated cost: ${report['metrics']['estimated_cost_usd']:.4f}")

        if args.output:
            bundle = build_export_bundle(db, run.id)
            Path(args.output).write_text(json.dumps(bundle, default=str, indent=2))
            print(f"Wrote export bundle to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
