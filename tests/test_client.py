"""Tests for DashboardClient and TyphoonDayOff."""

from datetime import date, datetime
import os
import unittest
from unittest.mock import MagicMock, patch

import requests

import tw_dayoff
from tw_dayoff import (
    ApiError,
    AuthenticationError,
    ClosureLevel,
    DashboardClient,
    RateLimitError,
    TyphoonDayOff,
    clear_token_cache,
    reset_default_client,
)


def _mock_response(
    status_code: int,
    json_body: dict = None,
    headers: dict = None,
    text: str = "",
) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.headers = headers or {}
    resp.reason = "Error"
    resp.text = text
    if json_body is not None:
        resp.json.return_value = json_body
    else:
        resp.json.side_effect = ValueError("No JSON")
    return resp


SAMPLE_ROW = {
    "county_code": "63000",
    "day": "2026-10-03",
    "announced_at": "2026-10-02T20:00:00+08:00",
    "status": "明天停止上班、停止上課。",
    "level": 2,
    "first_seen_at": "2026-10-02T20:05:00+08:00",
    "last_seen_at": "2026-10-03T23:55:00+08:00",
}

SAMPLE_META = {
    "dataset": "work_closure",
    "last_observed_at": "2026-10-03T23:55:00+08:00",
    "status": "ok",
    "source": {
        "agency": "行政院人事行政總處（資料來源：各縣市政府）",
        "license": "政府資料開放授權條款－第 1 版",
        "url": "https://www.dgpa.gov.tw/typh/daily/nds.html",
    },
}


class TestDashboardClient(unittest.TestCase):
    def setUp(self) -> None:
        clear_token_cache()
        reset_default_client()

    def tearDown(self) -> None:
        reset_default_client()
        clear_token_cache()

    def test_missing_credentials_raises(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            client = DashboardClient()
            with self.assertRaises(AuthenticationError):
                client.get_latest()

    def test_get_latest_with_oauth_and_etag_304(self) -> None:
        session = MagicMock(spec=requests.Session)
        session.post.return_value = _mock_response(
            200,
            {"access_token": "tok-1", "token_type": "Bearer", "expires_in": 86400},
        )
        session.get.side_effect = [
            _mock_response(
                200,
                {"data": [SAMPLE_ROW], "meta": SAMPLE_META},
                headers={
                    "ETag": '"etag-v1"',
                    "X-RateLimit-Limit": "600",
                    "X-RateLimit-Remaining": "599",
                    "X-Traffic-Limit": "314572800",
                    "X-Traffic-Used": "1024",
                },
            ),
            _mock_response(
                304,
                headers={"ETag": '"etag-v1"', "X-RateLimit-Remaining": "598"},
            ),
        ]

        client = DashboardClient("cid", "csec", session=session)
        records = client.get_latest("臺北市")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].county_code, "63000")
        self.assertEqual(records[0].county_name, "臺北市")
        self.assertTrue(records[0].is_day_off)
        self.assertEqual(records[0].closure_level, ClosureLevel.SUSPENDED)
        self.assertEqual(client.last_rate_limit.remaining, 599)
        self.assertEqual(client.last_source.agency, SAMPLE_META["source"]["agency"])

        # Second call sends If-None-Match and receives cached data on 304
        cached_records = client.get_latest("63000")
        self.assertEqual(cached_records, records)
        _, second_kwargs = session.get.call_args_list[1]
        self.assertEqual(second_kwargs["headers"]["If-None-Match"], '"etag-v1"')
        self.assertEqual(client.last_rate_limit.remaining, 598)

    def test_auto_refresh_on_401(self) -> None:
        session = MagicMock(spec=requests.Session)
        session.post.side_effect = [
            _mock_response(200, {"access_token": "expired-tok", "token_type": "Bearer", "expires_in": 86400}),
            _mock_response(200, {"access_token": "fresh-tok", "token_type": "Bearer", "expires_in": 86400}),
        ]
        session.get.side_effect = [
            _mock_response(401, {"error": {"code": "invalid_token", "message": "expired"}}),
            _mock_response(200, {"data": [SAMPLE_ROW], "meta": SAMPLE_META}),
        ]

        client = DashboardClient("cid", "csec", session=session)
        records = client.get_latest("63000")
        self.assertEqual(len(records), 1)
        self.assertEqual(session.post.call_count, 2)
        self.assertEqual(session.get.call_count, 2)
        self.assertEqual(
            session.get.call_args_list[1].kwargs["headers"]["Authorization"],
            "Bearer fresh-tok",
        )

    def test_get_history_pagination_and_time_formatting(self) -> None:
        session = MagicMock(spec=requests.Session)
        session.get.side_effect = [
            _mock_response(
                200,
                {
                    "data": [SAMPLE_ROW],
                    "meta": {**SAMPLE_META, "next_cursor": "cursor-2"},
                },
            ),
            _mock_response(
                200,
                {
                    "data": [{**SAMPLE_ROW, "day": "2026-10-04"}],
                    "meta": SAMPLE_META,
                },
            ),
        ]

        client = DashboardClient(access_token="static-tok", session=session)
        records = client.get_history(
            "高雄市",
            from_time=date(2026, 10, 1),
            to_time=datetime(2026, 10, 5, 12, 0),
            fetch_all=True,
        )
        self.assertEqual(len(records), 2)
        first_params = session.get.call_args_list[0].kwargs["params"]
        self.assertEqual(first_params["county"], "64000")
        self.assertEqual(first_params["from"], "2026-10-01")
        self.assertEqual(first_params["to"], "2026-10-05T12:00:00+08:00")
        second_params = session.get.call_args_list[1].kwargs["params"]
        self.assertEqual(second_params["cursor"], "cursor-2")

    def test_rate_limit_and_api_errors(self) -> None:
        session = MagicMock(spec=requests.Session)
        session.get.side_effect = [
            _mock_response(
                429,
                {"error": {"code": "quota_exceeded", "message": "Daily quota used up"}},
                headers={"Retry-After": "120"},
            ),
            _mock_response(
                400,
                {"error": {"code": "invalid_county", "message": "Bad county"}},
            ),
        ]
        client = DashboardClient(access_token="tok", session=session)
        with self.assertRaises(RateLimitError) as rl_ctx:
            client.get_latest()
        self.assertEqual(rl_ctx.exception.code, "quota_exceeded")
        self.assertEqual(rl_ctx.exception.retry_after, 120)

        with self.assertRaises(ApiError) as api_ctx:
            client.get_latest()
        self.assertEqual(api_ctx.exception.status_code, 400)
        self.assertEqual(api_ctx.exception.code, "invalid_county")


class TestTyphoonDayOff(unittest.TestCase):
    def setUp(self) -> None:
        clear_token_cache()
        reset_default_client()

    def tearDown(self) -> None:
        reset_default_client()
        clear_token_cache()

    def test_high_level_wrapper_and_empty_result(self) -> None:
        session = MagicMock(spec=requests.Session)
        session.get.side_effect = [
            _mock_response(200, {"data": [SAMPLE_ROW], "meta": SAMPLE_META}),
            _mock_response(200, {"data": [SAMPLE_ROW], "meta": SAMPLE_META}),
            _mock_response(200, {"data": [], "meta": SAMPLE_META}),
            _mock_response(200, {"data": [], "meta": SAMPLE_META}),
        ]
        shared = DashboardClient(access_token="tok", session=session)

        wrapper = TyphoonDayOff("台北市", client=shared)
        self.assertEqual(wrapper.county_code, "63000")
        self.assertEqual(wrapper.get_dayoff(use_etag=False), "明天停止上班、停止上課。")
        self.assertTrue(wrapper.is_dayoff(use_etag=False))
        # Subsequent calls return empty data (no active closure announcement)
        self.assertIsNone(wrapper.get_day_off(use_etag=False))
        self.assertFalse(wrapper.is_dayoff(use_etag=False))

    def test_configure_and_cross_function_token_reuse(self) -> None:
        session = MagicMock(spec=requests.Session)
        session.post.return_value = _mock_response(
            200,
            {"access_token": "global-tok", "token_type": "Bearer", "expires_in": 86400},
        )
        session.get.return_value = _mock_response(
            200,
            {"data": [SAMPLE_ROW], "meta": SAMPLE_META},
        )

        tw_dayoff.configure("cid", "csec", session=session)

        def other_function() -> str:
            return tw_dayoff.get_token()

        class OtherService:
            def check(self) -> bool:
                with TyphoonDayOff("臺北市") as wrapper:
                    return wrapper.is_dayoff()

        self.assertEqual(other_function(), "global-tok")
        self.assertTrue(OtherService().check())
        self.assertEqual(tw_dayoff.get_dayoff("臺北市"), "明天停止上班、停止上課。")
        self.assertEqual(session.post.call_count, 1)

        # Even a newly constructed DashboardClient with the same credentials reuses the token
        separate_session = MagicMock(spec=requests.Session)
        separate_client = DashboardClient("cid", "csec", session=separate_session)
        self.assertEqual(separate_client.access_token, "global-tok")
        self.assertEqual(separate_session.post.call_count, 0)


if __name__ == "__main__":
    unittest.main()
