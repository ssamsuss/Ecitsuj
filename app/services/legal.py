"""Loads jurisdiction-scoped legal content: charge elements (JSON), pattern
jury instructions (markdown + JSON frontmatter metadata), and core legal
standards (reasonable doubt, presumption of innocence, credibility factors).

Layout (see app/legal/legal_knowledge_tree.txt for the original plan):
    app/legal/jurisdictions/{jurisdiction}/charges/{slug}.json
    app/legal/jurisdictions/{jurisdiction}/jury_instructions/{slug}.md
    app/legal/jurisdictions/{jurisdiction}/standards/{slug}.md
    app/legal/schemas/*.schema.json
"""
import json
import re
from dataclasses import dataclass
from pathlib import Path

from jsonschema import Draft202012Validator

LEGAL_ROOT = Path(__file__).resolve().parent.parent / "legal"
JURISDICTIONS_DIR = LEGAL_ROOT / "jurisdictions"
SCHEMAS_DIR = LEGAL_ROOT / "schemas"

CORE_STANDARD_TYPES = ("burden_of_proof", "presumption_of_innocence", "credibility_factors")

_FRONTMATTER_PATTERN = re.compile(r"\A---\n(?P<metadata>.*?)\n---\n(?P<body>.*)\Z", re.DOTALL)


def _load_schema(name: str) -> dict:
    return json.loads((SCHEMAS_DIR / name).read_text())


CHARGE_ELEMENTS_SCHEMA = _load_schema("charge_elements.schema.json")
JURY_INSTRUCTION_SCHEMA = _load_schema("jury_instruction.schema.json")
LEGAL_STANDARD_SCHEMA = _load_schema("legal_standard.schema.json")
PANEL_INSTRUCTION_SCHEMA = _load_schema("instruction.schema.json")


@dataclass(frozen=True)
class LegalDocument:
    metadata: dict
    body: str


def parse_frontmatter(text: str) -> LegalDocument:
    match = _FRONTMATTER_PATTERN.match(text)
    if not match:
        raise ValueError("expected JSON frontmatter delimited by '---' lines, followed by a markdown body")
    metadata = json.loads(match.group("metadata"))
    return LegalDocument(metadata=metadata, body=match.group("body").strip())


def _validate(schema: dict, data: dict, source: Path) -> None:
    errors = [e.message for e in Draft202012Validator(schema).iter_errors(data)]
    if errors:
        raise ValueError(f"{source}: {'; '.join(errors)}")


def list_jurisdictions() -> list[str]:
    if not JURISDICTIONS_DIR.exists():
        return []
    return sorted(p.name for p in JURISDICTIONS_DIR.iterdir() if p.is_dir())


def list_charges(jurisdiction: str) -> list[str]:
    charges_dir = JURISDICTIONS_DIR / jurisdiction / "charges"
    return sorted(p.stem for p in charges_dir.glob("*.json")) if charges_dir.exists() else []


def load_charge_elements(jurisdiction: str, charge_slug: str) -> dict:
    path = JURISDICTIONS_DIR / jurisdiction / "charges" / f"{charge_slug}.json"
    data = json.loads(path.read_text())
    _validate(CHARGE_ELEMENTS_SCHEMA, data, path)
    return data


def list_jury_instructions(jurisdiction: str) -> list[str]:
    dir_ = JURISDICTIONS_DIR / jurisdiction / "jury_instructions"
    return sorted(p.stem for p in dir_.glob("*.md")) if dir_.exists() else []


def load_jury_instruction(jurisdiction: str, instruction_slug: str) -> LegalDocument:
    path = JURISDICTIONS_DIR / jurisdiction / "jury_instructions" / f"{instruction_slug}.md"
    doc = parse_frontmatter(path.read_text())
    _validate(JURY_INSTRUCTION_SCHEMA, doc.metadata, path)
    return doc


def list_legal_standards(jurisdiction: str) -> list[str]:
    dir_ = JURISDICTIONS_DIR / jurisdiction / "standards"
    return sorted(p.stem for p in dir_.glob("*.md")) if dir_.exists() else []


def load_legal_standard(jurisdiction: str, standard_slug: str) -> LegalDocument:
    path = JURISDICTIONS_DIR / jurisdiction / "standards" / f"{standard_slug}.md"
    doc = parse_frontmatter(path.read_text())
    _validate(LEGAL_STANDARD_SCHEMA, doc.metadata, path)
    return doc


_DEFENSES_SOURCE_JURISDICTION = "us-federal"
_DEFENSE_HEADING_PATTERN = re.compile(r"^##\s+[IVXLC]+\.\s+(.+)$", re.MULTILINE)
_NON_DEFENSE_HEADINGS = {"procedure"}


def list_defenses(jurisdiction: str) -> list[str]:
    """List common affirmative defenses, parsed from the Defenses reference document.

    Only us-federal has a dedicated defenses chapter; other jurisdictions fall
    back to this same general-purpose list as an MVP baseline until
    jurisdiction-specific defenses content is authored.
    """
    path = JURISDICTIONS_DIR / _DEFENSES_SOURCE_JURISDICTION / "jury_or_panel_instructions" / "Defenses.md"
    if not path.exists():
        return []
    body = parse_frontmatter(path.read_text()).body
    return [
        title.strip().title() for title in _DEFENSE_HEADING_PATTERN.findall(body)
        if title.strip().lower() not in _NON_DEFENSE_HEADINGS
    ]


def _load_panel_instructions(jurisdiction: str) -> list[tuple[Path, LegalDocument]]:
    """Some jurisdictions (e.g. military panels) use jury_or_panel_instructions/ instead of jury_instructions/."""
    dir_ = JURISDICTIONS_DIR / jurisdiction / "jury_or_panel_instructions"
    if not dir_.exists():
        return []
    docs = []
    for path in sorted(dir_.glob("*.md")):
        doc = parse_frontmatter(path.read_text())
        _validate(PANEL_INSTRUCTION_SCHEMA, doc.metadata, path)
        docs.append((path, doc))
    return docs


def _has_statute_sections(jurisdiction: str) -> bool:
    """Statute/article sections (statutes/, penal_code/) count as substantive law, like charges/."""
    jurisdiction_dir = JURISDICTIONS_DIR / jurisdiction
    return any(
        sub.is_dir() and sub.name in {"sections", "articles"} and any(sub.glob("*.json"))
        for sub in jurisdiction_dir.rglob("*")
    )


def validate_legal_library() -> list[str]:
    """Check every jurisdiction has substantive law, pattern instructions, and core legal standards."""
    errors: list[str] = []
    jurisdictions = list_jurisdictions()
    if not jurisdictions:
        return ["no jurisdictions found under app/legal/jurisdictions/"]

    for jurisdiction in jurisdictions:
        charges = list_charges(jurisdiction)
        for slug in charges:
            try:
                load_charge_elements(jurisdiction, slug)
            except (ValueError, json.JSONDecodeError) as e:
                errors.append(f"{jurisdiction}/charges/{slug}.json: {e}")
        if not charges and not _has_statute_sections(jurisdiction):
            errors.append(f"{jurisdiction}: no charge elements or statute sections found")

        instructions = list_jury_instructions(jurisdiction)
        for slug in instructions:
            try:
                load_jury_instruction(jurisdiction, slug)
            except (ValueError, json.JSONDecodeError) as e:
                errors.append(f"{jurisdiction}/jury_instructions/{slug}.md: {e}")
        try:
            panel_instructions = _load_panel_instructions(jurisdiction)
        except (ValueError, json.JSONDecodeError) as e:
            errors.append(f"{jurisdiction}/jury_or_panel_instructions: {e}")
            panel_instructions = []
        if not instructions and not panel_instructions:
            errors.append(f"{jurisdiction}: no pattern jury or panel instructions found")

        standards = list_legal_standards(jurisdiction)
        loaded_standard_types = set()
        for slug in standards:
            try:
                doc = load_legal_standard(jurisdiction, slug)
                loaded_standard_types.add(doc.metadata["standard_type"])
            except (ValueError, json.JSONDecodeError) as e:
                errors.append(f"{jurisdiction}/standards/{slug}.md: {e}")

        if loaded_standard_types:
            missing = set(CORE_STANDARD_TYPES) - loaded_standard_types
            if missing:
                errors.append(f"{jurisdiction}: missing core legal standards {sorted(missing)}")
        else:
            # No dedicated standards/ directory: accept a consolidated panel-instruction
            # model where burden of proof / presumption of innocence and credibility
            # are each covered by at least one "standard" and "credibility" instruction.
            categories = {doc.metadata.get("category") for _, doc in panel_instructions}
            missing_categories = {"standard", "credibility"} - categories
            if missing_categories:
                errors.append(f"{jurisdiction}: missing core legal standards {sorted(missing_categories)}")

    return errors
