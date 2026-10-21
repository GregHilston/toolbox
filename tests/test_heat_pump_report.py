"""heat-pump-report.py turns Prometheus and Open-Meteo responses into report rows."""

from __future__ import annotations

import csv
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from _loader import load

report = load("heat-pump-report.py")


class StepTest(unittest.TestCase):
    def test_short_range_floors_at_one_minute(self):
        start = datetime(2026, 10, 21, tzinfo=timezone.utc)
        self.assertEqual(report.step_seconds(start, start + timedelta(hours=1)), 60)

    def test_long_range_stays_under_prometheus_point_limit(self):
        start = datetime(2026, 7, 21, tzinfo=timezone.utc)
        end = start + timedelta(days=90)
        points = (end - start).total_seconds() / report.step_seconds(start, end)
        self.assertLessEqual(points, 11_000)


class ParseMatrixTest(unittest.TestCase):
    def test_empty_result_is_no_points(self):
        self.assertEqual(report.parse_matrix({"data": {"result": []}}), [])

    def test_values_become_floats(self):
        body = {"data": {"result": [{"values": [[1792587662, "17.5"]]}]}}
        self.assertEqual(report.parse_matrix(body), [(1792587662.0, 17.5)])


class HeatingSpansTest(unittest.TestCase):
    def test_consecutive_ones_merge_and_a_gap_splits(self):
        points = [(0, 1), (60, 1), (120, 0), (180, 1), (240, 0)]
        self.assertEqual(report.heating_spans(points, 60), [(0, 120), (180, 240)])

    def test_missing_samples_end_a_run(self):
        self.assertEqual(report.heating_spans([(0, 1), (600, 1)], 60), [(0, 60), (600, 660)])


class CsvTest(unittest.TestCase):
    def test_rows_take_their_hours_outdoor_reading(self):
        hour = 1792587600  # on the hour, UTC
        data = {
            "temps": {"Basement": [(hour + 300, 68.04)], "Guest room": [(hour + 300, 66.0)]},
            "outdoor": [(hour, 34.1, 70)],
        }
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "out.csv"
            report.write_csv(path, data)
            rows = list(csv.reader(path.open()))
        self.assertEqual(rows[0][1:], ["Basement °F", "Guest room °F", "outdoor °F", "outdoor RH %"])
        self.assertEqual(rows[1][1:], ["68.0", "66.0", "34.1", "70"])


if __name__ == "__main__":
    unittest.main()
