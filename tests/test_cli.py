"""Tests for the tw_dayoff CLI entry point."""

import io
import json
import unittest
from unittest.mock import patch

from tw_dayoff.__main__ import main
from tw_dayoff.models import WorkClosureRecord


class TestCli(unittest.TestCase):
    def test_cli_json_output(self) -> None:
        sample = WorkClosureRecord(
            county_code="63000",
            county_name="臺北市",
            day="2026-10-03",
            announced_at="2026-10-02T20:00:00+08:00",
            status="明天停止上班、停止上課。",
            level=2,
            first_seen_at="2026-10-02T20:05:00+08:00",
            last_seen_at="2026-10-03T23:55:00+08:00",
        )
        stdout = io.StringIO()
        with patch("tw_dayoff.__main__.DashboardClient") as mock_cls:
            mock_cls.return_value.__enter__.return_value.get_latest.return_value = [sample]
            with patch("sys.stdout", stdout):
                code = main(["--county", "臺北市", "--json"])

        self.assertEqual(code, 0)
        parsed = json.loads(stdout.getvalue())
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["county_code"], "63000")
        self.assertEqual(parsed[0]["level"], 2)


if __name__ == "__main__":
    unittest.main()
