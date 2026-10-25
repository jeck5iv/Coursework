import unittest
from pathlib import Path

import numpy as np
from scripts.reserve_audit import audit, load_prospects, prior_moments, sample_prior

ROOT = Path(__file__).resolve().parents[1]


class ReservePriorTests(unittest.TestCase):
    def test_certain_failure(self):
        self.assertEqual(prior_moments(0, 2, 1), (0.0, 0.0))
        self.assertTrue((sample_prior(np.random.default_rng(1), 0, 2, 1, 100) == 0).all())

    def test_zero_log_variance_reduces_to_scaled_bernoulli(self):
        p, amount = 0.3, 7.0
        mean, variance = prior_moments(p, np.log(amount), 0)
        self.assertAlmostEqual(mean, p * amount)
        self.assertAlmostEqual(variance, p * (1 - p) * amount ** 2)

    def test_invalid_parameters_fail(self):
        for args in [(-0.1, 0, 1), (1.1, 0, 1), (0.5, 0, -1), (0.5, np.nan, 1)]:
            with self.assertRaises(ValueError):
                prior_moments(*args)

    def test_sampler_matches_mixture_moments(self):
        p, mu, sigma, n = 0.4, 2.0, 0.5, 200000
        mean, variance = prior_moments(p, mu, sigma)
        samples = sample_prior(np.random.default_rng(12345), p, mu, sigma, n)
        self.assertLess(abs(samples.mean() - mean), 5 * np.sqrt(variance / n))
        self.assertLess(abs((samples == 0).mean() - (1 - p)), 5 * np.sqrt(p * (1 - p) / n))

    def test_original_workbook_and_seeded_audit(self):
        frame = load_prospects(ROOT / "Датасет.xlsx")
        self.assertEqual(len(frame), 10)
        first = audit(frame, 2000, 12345)
        self.assertTrue(first.equals(audit(frame, 2000, 12345)))
        self.assertTrue(np.isfinite(first.select_dtypes(include="number").to_numpy()).all())


if __name__ == "__main__":
    unittest.main()
