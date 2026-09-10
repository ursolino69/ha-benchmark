import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
UI = (ROOT / "smartdomo_benchmark" / "app" / "ui.js").read_text()
CSS = (ROOT / "smartdomo_benchmark" / "app" / "style.css").read_text()


class FrontendContractTests(unittest.TestCase):
    def test_ranking_has_requested_filters_and_dirty_state(self):
        for field in ('id="ram"', 'id="storage_size"', "filter-pending"):
            self.assertIn(field, UI + CSS)

    def test_comparison_checkbox_is_last_table_cell(self):
        row = next(line for line in UI.splitlines() if "async function ranking()" in line)
        self.assertIn('data-compare=', row)
        self.assertIn('</td></tr>`', row)
        self.assertLess(row.rfind('data-compare='), row.rfind('</td></tr>`'))
        self.assertNotIn('<tr><td><input type="checkbox"', row)

    def test_ram_is_presented_in_gigabytes(self):
        self.assertIn("function formatRam", UI)
        self.assertIn("return`${formatNumber(nominal||raw,nominal?0:1)} GB`", UI)

    def test_dialog_uses_spaced_field_and_consent_groups(self):
        for class_name in ("dialog-stack", "field-stack", "consent-line", "consent-box"):
            self.assertIn(class_name, UI)
            self.assertIn(f".{class_name}", CSS)

    def test_r3_and_r4_weights_are_separate(self):
        self.assertIn("weightsR3=", UI)
        self.assertIn("weightsR4=", UI)
        self.assertIn("resultWeights", UI)

    def test_calibrated_r4_is_the_default_ranking(self):
        self.assertIn('value="CORE-2026.9.1-R4"', UI)
        self.assertIn("Green = 100 · Kalibrierung D", UI)
        self.assertIn("0.8.0", UI)


if __name__ == "__main__":
    unittest.main()
