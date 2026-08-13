import json
import unittest

from app.services.legal import (
    CORE_STANDARD_TYPES,
    JURISDICTIONS_DIR,
    list_charges,
    list_defenses,
    list_jurisdictions,
    list_jury_instructions,
    list_legal_standards,
    load_charge_elements,
    load_jury_instruction,
    load_legal_standard,
    parse_frontmatter,
    validate_legal_library,
)

# Jurisdictions that use the charges/ + standards/ content convention;
# us-federal uses a different convention (statutes/manuals + jury_or_panel_instructions).
STANDARDS_CONVENTION_JURISDICTIONS = ("us-ca", "us-ny")


class FrontmatterParsingTests(unittest.TestCase):
    def test_parses_metadata_and_body(self):
        doc = parse_frontmatter('---\n{"id": "x", "jurisdiction": "us-ca"}\n---\nBody text.')
        self.assertEqual(doc.metadata, {"id": "x", "jurisdiction": "us-ca"})
        self.assertEqual(doc.body, "Body text.")

    def test_missing_frontmatter_raises(self):
        with self.assertRaises(ValueError):
            parse_frontmatter("no frontmatter here")


class LegalLibraryTests(unittest.TestCase):
    def test_at_least_two_jurisdictions_exist(self):
        self.assertGreaterEqual(len(list_jurisdictions()), 2)

    def test_every_jurisdiction_has_all_core_standards(self):
        for jurisdiction in STANDARDS_CONVENTION_JURISDICTIONS:
            standard_types = {
                load_legal_standard(jurisdiction, slug).metadata["standard_type"]
                for slug in list_legal_standards(jurisdiction)
            }
            with self.subTest(jurisdiction=jurisdiction):
                self.assertEqual(standard_types, set(CORE_STANDARD_TYPES))

    def test_every_jurisdiction_has_charges_and_instructions(self):
        for jurisdiction in STANDARDS_CONVENTION_JURISDICTIONS:
            with self.subTest(jurisdiction=jurisdiction):
                self.assertGreater(len(list_charges(jurisdiction)), 0)
                self.assertGreater(len(list_jury_instructions(jurisdiction)), 0)

    def test_every_charge_file_validates_against_schema(self):
        for jurisdiction in list_jurisdictions():
            for slug in list_charges(jurisdiction):
                with self.subTest(jurisdiction=jurisdiction, charge=slug):
                    data = load_charge_elements(jurisdiction, slug)
                    self.assertEqual(data["jurisdiction"], jurisdiction)
                    self.assertGreater(len(data["elements"]), 0)

    def test_every_jury_instruction_validates_against_schema(self):
        for jurisdiction in list_jurisdictions():
            for slug in list_jury_instructions(jurisdiction):
                with self.subTest(jurisdiction=jurisdiction, instruction=slug):
                    doc = load_jury_instruction(jurisdiction, slug)
                    self.assertEqual(doc.metadata["jurisdiction"], jurisdiction)
                    self.assertTrue(doc.body)

    def test_charge_elements_are_keyed_by_matching_jurisdiction_directory(self):
        for jurisdiction in STANDARDS_CONVENTION_JURISDICTIONS:
            for slug in list_charges(jurisdiction):
                data = load_charge_elements(jurisdiction, slug)
                self.assertEqual(data["jurisdiction"], jurisdiction)

    def test_full_library_has_no_validation_errors(self):
        errors = validate_legal_library()
        self.assertEqual(errors, [])

    def test_unknown_jurisdiction_reports_empty_lists(self):
        self.assertEqual(list_charges("xx-yy"), [])
        self.assertEqual(list_jury_instructions("xx-yy"), [])
        self.assertEqual(list_legal_standards("xx-yy"), [])


class UsFederalLayoutTests(unittest.TestCase):
    """us-federal uses statutes/manuals + jury_or_panel_instructions instead of charges/standards."""

    def test_ucmj_articles_exist_and_validate(self):
        articles_dir = JURISDICTIONS_DIR / "us-federal" / "statutes" / "ucmj" / "articles"
        articles = sorted(articles_dir.glob("*.json"))
        self.assertGreater(len(articles), 0)
        for path in articles:
            with self.subTest(article=path.stem):
                data = json.loads(path.read_text())
                self.assertEqual(data["jurisdiction"], "us-federal")
                self.assertGreater(len(data["elements"]), 0)

    def test_mcm_manual_files_exist(self):
        manual_dir = JURISDICTIONS_DIR / "us-federal" / "manuals" / "mcm" / "2019"
        self.assertTrue((manual_dir / "metadata.json").exists())
        self.assertTrue((manual_dir / "pt-ii-rcm.md").exists())
        self.assertTrue((manual_dir / "pt-iv-punitive-articles.md").exists())

    def test_panel_instructions_cover_standard_and_credibility_categories(self):
        panel_dir = JURISDICTIONS_DIR / "us-federal" / "jury_or_panel_instructions"
        categories = {
            parse_frontmatter(path.read_text()).metadata["category"]
            for path in panel_dir.glob("*.md")
        }
        self.assertTrue({"standard", "credibility"}.issubset(categories))


class ListDefensesTests(unittest.TestCase):
    def test_us_federal_defenses_exclude_procedure_heading(self):
        defenses = list_defenses("us-federal")
        self.assertGreater(len(defenses), 10)
        self.assertIn("Self-Defense", defenses)
        self.assertIn("Duress", defenses)
        self.assertNotIn("PROCEDURE", defenses)

    def test_jurisdictions_without_defenses_content_fall_back_to_shared_list(self):
        self.assertEqual(list_defenses("us-ca"), list_defenses("us-federal"))
        self.assertEqual(list_defenses("us-ny"), list_defenses("us-federal"))


if __name__ == "__main__":
    unittest.main()
