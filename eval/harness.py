"""Evaluation harness for golden mock case packets.

Runs each golden case through packet validation and, when a database is
configured, through a full simulation + report validation cycle.
"""
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator
from pydantic import ValidationError

REPO_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_CASES_DIR = REPO_ROOT / "case_packet" / "golden"
CASE_PACKET_SCHEMA_PATH = REPO_ROOT / "Schema" / "jsonschemas" / "case_packet.schema.json"
RUN_REPORT_SCHEMA_PATH = REPO_ROOT / "Schema" / "jsonschemas" / "run_report.schema.json"
DEFAULT_SEEDS: tuple[int, ...] = (42, 1337, 2024)


def load_golden_cases() -> list[tuple[str, dict]]:
    paths = sorted(GOLDEN_CASES_DIR.glob("*.json"))
    return [(path.stem, json.loads(path.read_text())) for path in paths]


def validate_against_pydantic(data: dict) -> list[str]:
    from app.schemas import CasePacketIn

    try:
        CasePacketIn.model_validate(data)
        return []
    except ValidationError as e:
        return [str(err) for err in e.errors()]


def validate_against_json_schema(data: dict, schema_path: Path) -> list[str]:
    schema = json.loads(schema_path.read_text())
    validator = Draft202012Validator(schema)
    return [error.message for error in validator.iter_errors(data)]


def evaluate_packet(name: str, data: dict) -> dict:
    pydantic_errors = validate_against_pydantic(data)
    schema_errors = validate_against_json_schema(data, CASE_PACKET_SCHEMA_PATH)
    return {
        "name": name,
        "passed": not pydantic_errors and not schema_errors,
        "pydantic_errors": pydantic_errors,
        "schema_errors": schema_errors,
    }


def evaluate_simulation(db, name: str, data: dict, seed: int = 42, juror_count: int = 3, max_rounds: int = 1) -> dict:
    """Ingest a golden case, run a simulation, and validate the resulting report."""
    from app.schemas import CasePacketIn, RunCreateIn
    from app.services.cases import ingest_case_packet
    from app.services.simulation import run_simulation
    from app.services.report import build_report

    errors: list[str] = []
    initial_split = None
    try:
        case = ingest_case_packet(db, CasePacketIn.model_validate(data))
        run = run_simulation(db, RunCreateIn(
            case_id=case.id, seed=seed, juror_count=juror_count, max_rounds=max_rounds,
        ))
        if run.status != "done":
            errors.append(f"run finished with status {run.status!r}, expected 'done'")

        report = build_report(db, run.id)
        report_errors = validate_against_json_schema(report, RUN_REPORT_SCHEMA_PATH)
        errors.extend(f"report schema: {msg}" for msg in report_errors)

        initial_split = report["initial_split"]
        split_total = sum(initial_split.values())
        if split_total != juror_count:
            errors.append(f"initial_split total {split_total} != juror_count {juror_count}")
    except Exception as e:
        errors.append(f"{type(e).__name__}: {e}")

    return {"name": name, "seed": seed, "passed": not errors, "errors": errors, "initial_split": initial_split}


def evaluate_simulation_stability(
    db, name: str, data: dict, seeds: tuple[int, ...] = DEFAULT_SEEDS,
    juror_count: int = 3, max_rounds: int = 1,
) -> dict:
    """Run a case across multiple seeds, and re-run the first seed to confirm determinism."""
    seed_results = [
        evaluate_simulation(db, name, data, seed=seed, juror_count=juror_count, max_rounds=max_rounds)
        for seed in seeds
    ]

    repeat_errors: list[str] = []
    first_seed, first_run = seeds[0], seed_results[0]
    repeat_run = evaluate_simulation(db, name, data, seed=first_seed, juror_count=juror_count, max_rounds=max_rounds)
    if first_run["initial_split"] != repeat_run["initial_split"]:
        repeat_errors.append(
            f"seed {first_seed} not stable across re-run: "
            f"{first_run['initial_split']} != {repeat_run['initial_split']}"
        )

    return {
        "name": name,
        "passed": all(r["passed"] for r in seed_results) and not repeat_errors,
        "seed_results": seed_results,
        "repeat_errors": repeat_errors,
    }


def run_harness(database_url: str | None = None) -> list[dict]:
    """Validate every golden case; also run full simulations if a database is available."""
    cases = load_golden_cases()
    results = [evaluate_packet(name, data) for name, data in cases]

    if database_url:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        engine = create_engine(database_url)
        with Session(engine) as db:
            sim_results = {r["name"]: r for r in (
                evaluate_simulation_stability(db, name, data) for name, data in cases
            )}
        for result in results:
            sim = sim_results.get(result["name"])
            if sim:
                result["simulation_passed"] = sim["passed"]
                result["seed_results"] = sim["seed_results"]
                result["repeat_errors"] = sim["repeat_errors"]

    return results


def main() -> int:
    import os

    database_url = os.getenv("DATABASE_URL")
    results = run_harness(database_url)

    failures = 0
    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"[{status}] {result['name']} (packet validation)")
        for err in result["pydantic_errors"] + result["schema_errors"]:
            print(f"    - {err}")
        if not result["passed"]:
            failures += 1

        if "simulation_passed" in result:
            sim_status = "PASS" if result["simulation_passed"] else "FAIL"
            print(f"[{sim_status}] {result['name']} (simulation + report, {len(result['seed_results'])} seeds)")
            for seed_result in result["seed_results"]:
                seed_status = "PASS" if seed_result["passed"] else "FAIL"
                print(f"    [{seed_status}] seed={seed_result['seed']}")
                for err in seed_result["errors"]:
                    print(f"        - {err}")
            for err in result["repeat_errors"]:
                print(f"    - {err}")
            if not result["simulation_passed"]:
                failures += 1

    print(f"\n{len(results)} golden cases evaluated, {failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
