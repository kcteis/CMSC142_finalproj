"""
Tests for utils.py — input validation, supply warnings, report export
=====================================================================
"""

import csv
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))

from models import Family, ReliefItem
from priority import assign_bags
from utils import (
    validate_item, validate_capacity, validate_family,
    check_supply_warnings, build_text_report, export_text, export_csv,
)


# ── Item validation ───────────────────────────────────────────────────────────
class TestValidateItem(unittest.TestCase):

    def test_valid_item(self):
        ok, _ = validate_item("Rice", "3.0", "9", "50")
        self.assertTrue(ok)

    def test_blank_name_rejected(self):
        ok, msg = validate_item("   ", "3.0", "9", "50")
        self.assertFalse(ok)
        self.assertIn("name", msg.lower())

    def test_non_numeric_weight_rejected(self):
        ok, _ = validate_item("Rice", "abc", "9", "50")
        self.assertFalse(ok)

    def test_weight_out_of_range_rejected(self):
        ok, _ = validate_item("Rice", "0", "9", "50")
        self.assertFalse(ok)
        ok, _ = validate_item("Rice", "21", "9", "50")
        self.assertFalse(ok)

    def test_benefit_out_of_range_rejected(self):
        ok, _ = validate_item("Rice", "3.0", "0", "50")
        self.assertFalse(ok)
        ok, _ = validate_item("Rice", "3.0", "11", "50")
        self.assertFalse(ok)

    def test_quantity_below_one_rejected(self):
        ok, _ = validate_item("Rice", "3.0", "9", "0")
        self.assertFalse(ok)


# ── Capacity validation ───────────────────────────────────────────────────────
class TestValidateCapacity(unittest.TestCase):

    def test_valid_capacity(self):
        ok, _ = validate_capacity("10")
        self.assertTrue(ok)

    def test_zero_rejected(self):
        ok, _ = validate_capacity("0")
        self.assertFalse(ok)

    def test_over_max_rejected(self):
        ok, _ = validate_capacity("51")
        self.assertFalse(ok)

    def test_non_numeric_rejected(self):
        ok, _ = validate_capacity("ten")
        self.assertFalse(ok)


# ── Family validation ─────────────────────────────────────────────────────────
class TestValidateFamily(unittest.TestCase):

    def test_valid_family(self):
        ok, _ = validate_family("F-001", "5", "2", "3")
        self.assertTrue(ok)

    def test_empty_id_rejected(self):
        ok, _ = validate_family("", "5", "2", "3")
        self.assertFalse(ok)

    def test_size_out_of_range_rejected(self):
        ok, _ = validate_family("F-1", "0", "0", "1")
        self.assertFalse(ok)
        ok, _ = validate_family("F-1", "21", "0", "1")
        self.assertFalse(ok)

    def test_vulnerable_exceeds_size_rejected(self):
        ok, msg = validate_family("F-1", "3", "5", "1")
        self.assertFalse(ok)

    def test_damage_level_must_be_1_2_or_3(self):
        for d in ("0", "4", "abc"):
            with self.subTest(d=d):
                ok, _ = validate_family("F-1", "3", "0", d)
                self.assertFalse(ok)


# ── Supply warnings ───────────────────────────────────────────────────────────
class TestSupplyWarnings(unittest.TestCase):

    def test_no_warning_when_supply_sufficient(self):
        fams = [Family("F1", 3, 0, 1, 1), Family("F2", 4, 1, 2, 2)]
        warns = check_supply_warnings(fams, supply=2)
        self.assertEqual(warns, [])

    def test_shortage_produces_warning(self):
        fams = [Family("F1", 3, 0, 1, 1), Family("F2", 4, 1, 2, 2)]
        warns = check_supply_warnings(fams, supply=1)
        self.assertTrue(any("shortage" in w.lower() for w in warns))

    def test_critical_warning_when_over_half_unserved(self):
        fams = [Family(f"F{i}", 3, 0, 1, i) for i in range(10)]
        warns = check_supply_warnings(fams, supply=2)  # 8/10 unserved
        self.assertTrue(any("critical" in w.lower() for w in warns))

    def test_high_vulnerability_flag(self):
        fams = [
            Family("HV1", 5, 3, 3, 1),  # 3+ vulnerable
            Family("HV2", 6, 4, 3, 2),
            Family("F3",  3, 0, 1, 3),
        ]
        warns = check_supply_warnings(fams, supply=1)  # shortage exists
        self.assertTrue(any("vulnerable" in w.lower() for w in warns))


# ── Report export ─────────────────────────────────────────────────────────────
class TestReportExport(unittest.TestCase):

    def _make_summary(self):
        fams = [Family("F1", 5, 2, 3, 1), Family("F2", 3, 0, 2, 2)]
        bag = [ReliefItem("Rice", 3.0, 9, 50), ReliefItem("Water", 2.0, 8, 60)]
        return assign_bags(fams, bag, 5.0, 17, supply=1)

    def test_text_report_contains_key_sections(self):
        summary = self._make_summary()
        report = build_text_report(summary, disaster="Typhoon X", barangay="Brgy Y")
        for section in ["BARANGAY RELIEF DISTRIBUTION REPORT",
                        "OPTIMIZED BAG CONTENTS",
                        "SUPPLY SUMMARY",
                        "PRIORITY ASSIGNMENT",
                        "Typhoon X",
                        "Brgy Y"]:
            self.assertIn(section, report)

    def test_export_text_writes_file(self):
        summary = self._make_summary()
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as tmp:
            path = tmp.name
        try:
            export_text(summary, path, "Typhoon X", "Brgy Y")
            with open(path, encoding="utf-8") as f:
                content = f.read()
            self.assertIn("BARANGAY RELIEF DISTRIBUTION REPORT", content)
        finally:
            os.unlink(path)

    def test_export_csv_has_expected_columns_and_rows(self):
        summary = self._make_summary()
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as tmp:
            path = tmp.name
        try:
            export_csv(summary, path)
            with open(path, encoding="utf-8") as f:
                rows = list(csv.reader(f))
            header = rows[0]
            self.assertIn("Family ID", header)
            self.assertIn("Final Score", header)
            self.assertIn("Status", header)
            # 1 header + 2 family rows
            self.assertEqual(len(rows), 3)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
