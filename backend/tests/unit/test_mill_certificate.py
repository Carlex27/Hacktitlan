import json
from pathlib import Path
import unittest

from backend.app.certificate_parser.mill_certificate import CertificateParseError, normalize_certificate


FIXTURE = Path(__file__).parents[3] / "data" / "samples" / "molino-1.raw.json"
FIXTURE_2 = Path(__file__).parents[3] / "data" / "samples" / "molino-2.raw.json"
FIXTURE_3 = Path(__file__).parents[3] / "data" / "samples" / "molino-3.raw.json"
FIXTURE_4 = Path(__file__).parents[3] / "data" / "samples" / "molino-4.raw.json"


class MillCertificateTests(unittest.TestCase):
    def setUp(self):
        self.raw = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_six_rolls_and_totals(self):
        result = normalize_certificate(self.raw)
        self.assertEqual(len(result["products"]), 6)
        self.assertTrue(all(result["validation"].values()))

    def test_chemistry_uses_header_scale(self):
        composition = normalize_certificate(self.raw)["products"][0]["composition_pct"]
        self.assertEqual(composition["C"], 0.0013)
        self.assertEqual(composition["Mn"], 0.12)
        self.assertEqual(composition["P"], 0.011)
        self.assertEqual(composition["Al_soluble"], 0.031)

    def test_c_in_length_column_means_coiled(self):
        product = normalize_certificate(self.raw)["products"][0]
        self.assertTrue(product["coiled"])
        self.assertIsNone(product["length_m"])

    def test_inconsistent_total_is_rejected(self):
        self.raw["total_net_weight_kg"] = 1
        with self.assertRaises(CertificateParseError):
            normalize_certificate(self.raw)

    def test_variable_product_count_and_total_aluminium(self):
        raw = json.loads(FIXTURE_2.read_text(encoding="utf-8"))
        result = normalize_certificate(raw)
        self.assertEqual(len(result["products"]), 1)
        product = result["products"][0]
        self.assertEqual(product["composition_pct"]["C"], 0.08)
        self.assertEqual(product["composition_pct"]["Al_total"], 0.029)
        self.assertNotIn("Al_soluble", product["composition_pct"])
        self.assertNotIn("Si", product["composition_pct"])
        self.assertEqual(product["mechanical_properties"]["yield_strength_mpa"], 230.0)
        self.assertTrue(all(result["validation"].values()))

    def test_ditto_marks_generic_mass_and_chemistry_by_heat(self):
        raw = json.loads(FIXTURE_3.read_text(encoding="utf-8"))
        result = normalize_certificate(raw)
        self.assertEqual(len(result["products"]), 11)
        self.assertEqual(result["products"][0]["product_id"], "14159481")
        self.assertEqual(result["products"][1]["thickness_mm"], 1.8)
        thickness = result["products"][1]["observations"]["thickness_mm"]
        self.assertEqual(thickness["raw_value"], '"')
        self.assertEqual(thickness["normalized_value"], 1.8)
        self.assertTrue(thickness["inherited"])
        self.assertEqual(thickness["inherited_from"], "14159481")
        self.assertEqual(result["products"][1]["composition_pct"]["C"], 0.35)
        carbon = result["products"][1]["observations"]["composition_pct"]["C"]
        self.assertEqual(carbon["raw_value"], '"')
        self.assertEqual(carbon["normalized_value"], 0.35)
        self.assertTrue(carbon["inherited"])
        self.assertEqual(carbon["inherited_from"], "14159481")
        self.assertEqual(result["products"][2]["composition_pct"]["C"], 0.33)
        self.assertEqual(result["products"][10]["composition_pct"]["Al_total"], 0.025)
        self.assertEqual(result["products"][0]["composition_pct"]["B"], 0.0003)
        self.assertEqual(result["products"][0]["weight_kg"], 7280.0)
        self.assertIsNone(result["products"][0]["net_weight_kg"])
        self.assertTrue(all(result["validation"].values()))

    def test_ditto_without_previous_value_is_rejected(self):
        raw = json.loads(FIXTURE_3.read_text(encoding="utf-8"))
        raw["rows"][0]["width_mm"] = '"'
        with self.assertRaises(CertificateParseError):
            normalize_certificate(raw)

    def test_normalization_does_not_mutate_raw_evidence(self):
        raw = json.loads(FIXTURE_3.read_text(encoding="utf-8"))
        normalize_certificate(raw)
        self.assertEqual(raw["rows"][1]["thickness_mm"], '"')
        self.assertEqual(raw["rows"][1]["chemistry"]["C"], '"')

    def test_direct_percentages_coating_and_subtotals(self):
        raw = json.loads(FIXTURE_4.read_text(encoding="utf-8"))
        result = normalize_certificate(raw)
        self.assertEqual(len(result["products"]), 6)
        first = result["products"][0]
        self.assertEqual(first["product_id"], "CBG2629A")
        self.assertEqual(first["thickness_mm"], 1.21)
        self.assertEqual(first["composition_pct"]["C"], 0.0136)
        self.assertEqual(first["coating"]["metal"], "Zn")
        self.assertEqual(first["coating"]["superior_g_m2"], 19.1)
        self.assertEqual(first["coating"]["inferior_g_m2"], 19.1)
        self.assertEqual(result["products"][3]["coating"]["superior_g_m2"], 19.5)
        self.assertTrue(all(result["validation"].values()))

    def test_inconsistent_group_subtotal_is_rejected(self):
        raw = json.loads(FIXTURE_4.read_text(encoding="utf-8"))
        raw["subtotals"][0]["total_weight_kg"] = 1
        with self.assertRaises(CertificateParseError):
            normalize_certificate(raw)


if __name__ == "__main__":
    unittest.main()
