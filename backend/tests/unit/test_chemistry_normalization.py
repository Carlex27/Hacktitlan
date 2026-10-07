from decimal import Decimal
import unittest

from backend.app.normalization.chemistry import (
    ChemistryNormalizationError,
    normalize_scaled_percentage,
    parse_power_of_ten,
)


class ChemistryNormalizationTests(unittest.TestCase):
    def test_user_example(self):
        self.assertEqual(normalize_scaled_percentage("13", "10^-4"), Decimal("0.0013"))

    def test_superscript_notation(self):
        self.assertEqual(parse_power_of_ten("10⁻³"), -3)

    def test_column_examples(self):
        self.assertEqual(normalize_scaled_percentage(12, "10^-2"), Decimal("0.12"))
        self.assertEqual(normalize_scaled_percentage(31, "10^-3"), Decimal("0.031"))

    def test_missing_is_not_zero(self):
        self.assertIsNone(normalize_scaled_percentage(None, -4))
        self.assertEqual(normalize_scaled_percentage(0, -4), Decimal("0.0000"))

    def test_out_of_range_is_rejected(self):
        with self.assertRaises(ChemistryNormalizationError):
            normalize_scaled_percentage(101, 0)


if __name__ == "__main__":
    unittest.main()
