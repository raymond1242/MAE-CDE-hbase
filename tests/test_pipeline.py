"""Unit tests for the cleaning, indicator, loader and shell-parser logic.

They need no HBase cluster. Run from the repository root:
    python3 -m unittest discover -s tests -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from hbase_readers import decode_shell_bytes, read_via_shell_export  # noqa: E402
from indicators import canonical_labels, compute_all, parse_salary  # noqa: E402
from load_hbase import cells_for, ruby_quote  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def record(row_key, city, designation, salary, name="Test"):
    return {"row_key": row_key, "name": name, "city": city, "designation": designation, "salary": salary}


class ParseSalaryTests(unittest.TestCase):
    def test_valid_and_fixed(self):
        self.assertEqual(parse_salary("45000"), (45000.0, "ok", ""))
        self.assertEqual(parse_salary("45000.50")[0:2], (45000.5, "ok"))
        self.assertEqual(parse_salary(" 48500 ")[0:2], (48500.0, "fixed"))

    def test_missing(self):
        for raw in (None, "", "   "):
            self.assertEqual(parse_salary(raw)[0:2], (None, "missing"), raw)

    def test_invalid(self):
        for raw in ("N/A", "pending", "-1500", "0", "4,250", "1e5", "nan", "inf"):
            self.assertEqual(parse_salary(raw)[0:2], (None, "invalid"), raw)


class CanonicalLabelTests(unittest.TestCase):
    def test_case_and_whitespace_variants_are_merged(self):
        labels = canonical_labels(["Lima", "Lima", "LIMA", " lima ", "Buenos  Aires", None, ""])
        self.assertEqual(labels["LIMA"], "Lima")
        self.assertEqual(labels[" lima "], "Lima")
        self.assertEqual(labels["Buenos  Aires"], "Buenos Aires")
        self.assertNotIn("", labels)


class IndicatorTests(unittest.TestCase):
    def setUp(self):
        records = [record(f"E{i:04d}", "Lima", "Data Analyst", str(1000 * i)) for i in range(1, 6)]
        records += [record(f"E{i:04d}", "Quito", "Accountant", "9000") for i in range(6, 9)]
        records += [
            record("E0009", "LIMA", "Data Analyst", "N/A"),
            record("E0010", None, None, None),
        ]
        self.results = compute_all(records)

    def test_employees_and_percentage_by_city(self):
        by_city = {r["city"]: r for r in self.results["by_city"]}
        self.assertEqual(by_city["Lima"]["employees"], 6)   # 'LIMA' is merged into 'Lima'
        self.assertEqual(by_city["Lima"]["percentage"], 60.0)
        self.assertEqual(by_city["UNKNOWN"]["employees"], 1)
        self.assertEqual(self.results["by_city"][-1]["city"], "UNKNOWN")
        self.assertAlmostEqual(sum(r["percentage"] for r in self.results["by_city"]), 100.0)

    def test_salary_summary_excludes_missing_and_invalid(self):
        s = self.results["salary_summary"]
        self.assertEqual(s["total_records"], 10)
        self.assertEqual(s["valid_salaries"], 8)
        self.assertEqual((s["missing_salaries"], s["invalid_salaries"]), (1, 1))
        self.assertEqual((s["min_salary"], s["max_salary"]), (1000.0, 9000.0))
        self.assertEqual(s["avg_salary"], round((15000 + 27000) / 8, 2))

    def test_top_city_requires_minimum_valid_salaries(self):
        # Quito has the higher average (9000) but only 3 valid salaries (< 5).
        self.assertEqual(self.results["top_city"]["city"], "Lima")
        quito = next(r for r in self.results["salary_by_city"] if r["city"] == "Quito")
        self.assertFalse(quito["meets_minimum"])
        self.assertIsNone(quito["rank"])

    def test_every_problem_is_logged(self):
        problems = {(i["row_key"], i["field"]) for i in self.results["issues"]}
        self.assertIn(("E0009", "salary"), problems)
        self.assertIn(("E0009", "city"), problems)
        self.assertIn(("E0010", "designation"), problems)


class LoaderTests(unittest.TestCase):
    def test_empty_fields_are_not_written(self):
        cells = cells_for({"row_key": "E1", "name": "Ana", "city": "", "designation": "Director", "salary": ""})
        self.assertEqual(cells, [("personal:name", "Ana"), ("professional:designation", "Director")])

    def test_ruby_quote_escapes(self):
        self.assertEqual(ruby_quote("O'Neil"), r"'O\'Neil'")
        self.assertEqual(ruby_quote("a\\b"), r"'a\\b'")


class ShellExportTests(unittest.TestCase):
    def test_decode_escaped_utf8(self):
        self.assertEqual(decode_shell_bytes(r"Bogot\xC3\xA1"), "Bogotá")

    def test_parse_real_scan_output(self):
        # Output of `scan 'emp'` captured from HBase 2.6.4 (see tests/fixtures/README.md).
        records, info = read_via_shell_export(FIXTURES / "scan_sample.txt")
        by_key = {r["row_key"]: r for r in records}
        self.assertEqual(info["rows_read"], info["rows_reported_by_shell"])
        self.assertEqual(by_key["T0001"], {"row_key": "T0001", "name": "Ana Torres", "city": "Lima",
                                           "designation": "Data Analyst", "salary": "41000"})
        self.assertEqual(by_key["T0002"]["city"], " lima ")       # whitespace is preserved
        self.assertIsNone(by_key["T0002"]["salary"])               # absent cell -> None
        self.assertEqual(by_key["T0003"]["city"], "Bogotá")        # \xNN escapes decoded
        self.assertEqual(by_key["T0003"]["name"], "Peter O'Neil, Jr.")
        self.assertEqual(by_key["T0004"]["salary"], "N/A")
        self.assertEqual(info["ignored_columns"], ["personal:nickname"])  # extra qualifier, not used


if __name__ == "__main__":
    unittest.main()
