import unittest

from app.services.cost import estimate_cost_usd


class EstimateCostUsdTests(unittest.TestCase):
    def test_zero_chars_is_zero_cost(self):
        self.assertEqual(estimate_cost_usd("gpt-4.1", 0, 0), 0.0)

    def test_known_model_uses_its_rate(self):
        cost = estimate_cost_usd("gpt-4.1", prompt_chars=1000, completion_chars=1000)
        self.assertAlmostEqual(cost, 0.0005 + 0.002)

    def test_unknown_model_falls_back_to_default_rate(self):
        cost = estimate_cost_usd("some-future-model", prompt_chars=1000, completion_chars=1000)
        self.assertAlmostEqual(cost, 0.0005 + 0.0015)

    def test_cost_scales_with_character_count(self):
        small = estimate_cost_usd("gpt-4o", prompt_chars=500, completion_chars=0)
        large = estimate_cost_usd("gpt-4o", prompt_chars=1000, completion_chars=0)
        self.assertAlmostEqual(large, small * 2)


if __name__ == "__main__":
    unittest.main()
