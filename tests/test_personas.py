import unittest

from app.services.personas import build_personas


class PersonaGeneratorTests(unittest.TestCase):
    def test_same_seed_and_count_are_reproducible(self):
        self.assertEqual(build_personas(12, seed=42), build_personas(12, seed=42))

    def test_different_seeds_diverge(self):
        self.assertNotEqual(build_personas(12, seed=1), build_personas(12, seed=2))

    def test_persona_is_stable_regardless_of_juror_count(self):
        small = build_personas(3, seed=42)
        large = build_personas(12, seed=42)
        self.assertEqual(small, large[:3])

    def test_juror_numbers_are_sequential(self):
        personas = build_personas(5, seed=7)
        self.assertEqual([p["juror_number"] for p in personas], [1, 2, 3, 4, 5])

    def test_juror_count_must_be_positive(self):
        with self.assertRaises(ValueError):
            build_personas(0, seed=1)


if __name__ == "__main__":
    unittest.main()
