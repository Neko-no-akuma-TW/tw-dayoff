"""Command-line entry point for ``tw_dayoff``."""

import argparse
import json
import sys
from typing import List, Optional

from .client import DashboardClient
from .exceptions import TwDayOffError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tw-dayoff",
        description="Query Taiwan natural disaster work/school closure status via dashboard.tw.",
    )
    parser.add_argument(
        "-c",
        "--county",
        help="County code (e.g. 63000), Chinese name (e.g. 臺北市), or English name (e.g. Taipei). Omit for nationwide.",
    )
    parser.add_argument("--client-id", help="dashboard.tw OAuth Client ID (or set DASHBOARD_TW_CLIENT_ID).")
    parser.add_argument(
        "--client-secret",
        help="dashboard.tw OAuth Client Secret (or set DASHBOARD_TW_CLIENT_SECRET).",
    )
    parser.add_argument(
        "--access-token",
        help="dashboard.tw Bearer access token (or set DASHBOARD_TW_ACCESS_TOKEN).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Output raw JSON records.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Run the tw-dayoff CLI and return an exit status code."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        with DashboardClient(
            client_id=args.client_id,
            client_secret=args.client_secret,
            access_token=args.access_token,
        ) as client:
            records = client.get_latest(county=args.county)
    except TwDayOffError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.as_json:
        print(
            json.dumps(
                [
                    {
                        "county_code": r.county_code,
                        "county_name": r.county_name,
                        "day": r.day,
                        "level": r.level,
                        "status": r.status,
                        "announced_at": r.announced_at,
                    }
                    for r in records
                ],
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if not records:
        print("目前無停止上班及上課公告資料。")
        return 0

    for record in records:
        label = record.county_name or record.county_code or "未標註縣市"
        day_str = record.day or "-"
        status_str = record.status or "(無公告內容)"
        print(f"[{day_str}] {label} ({record.county_code or '-'}) [level={record.level}]: {status_str}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
