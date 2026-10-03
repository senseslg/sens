from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parents[1]))
import export_report
import app
from reporting import REPORT_COLUMNS, REPORT_NAMES


class ExportReportTests(unittest.TestCase):
    def test_month_bounds_including_year_rollover(self):
        self.assertEqual(tuple(str(d) for d in export_report.month_window("2026-12")),
                         ("2026-12-01", "2027-01-01"))
        self.assertEqual(tuple(str(d) for d in export_report.month_window("2024-02")),
                         ("2024-02-01", "2024-03-01"))
        for value in ("2026-9", "2026-13", "2026-09-01"):
            with self.assertRaises(ValueError):
                export_report.month_window(value)

    def test_validated_save_does_not_overwrite(self):
        data = app.render_csv([], REPORT_COLUMNS, REPORT_NAMES)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "report.csv"
            with self.assertRaises(ValueError):
                export_report.save_csv(data, 1, target)
            self.assertFalse(target.exists())
            self.assertEqual(export_report.save_csv(data, 0, target), 0)
            with self.assertRaises(FileExistsError):
                export_report.save_csv(data, 0, target)
            self.assertEqual(target.read_bytes(), data)


if __name__ == "__main__":
    unittest.main()
