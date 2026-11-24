"""Tests for OAuth 2.0 Client Credentials token handling."""

import unittest
from unittest.mock import MagicMock

import requests

from tw_dayoff import AuthenticationError, OAuthTokenClient, RateLimitError


def _mock_response(status_code: int, json_body: dict, headers: dict = None) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.json.return_value = json_body
    resp.headers = headers or {}
    resp.reason = "Error"
    return resp


class TestOAuthTokenClient(unittest.TestCase):
    def test_requires_credentials(self) -> None:
        with self.assertRaises(AuthenticationError):
            OAuthTokenClient("", "secret")
        with self.assertRaises(AuthenticationError):
            OAuthTokenClient("cid", "")

    def test_fetches_and_caches_token(self) -> None:
        session = MagicMock(spec=requests.Session)
        session.post.return_value = _mock_response(
            200,
            {"access_token": "tok-1", "token_type": "Bearer", "expires_in": 86400},
        )
        client = OAuthTokenClient("cid", "csec", session=session)

        self.assertEqual(client.get_token(), "tok-1")
        self.assertEqual(client.get_token(), "tok-1")
        self.assertEqual(session.post.call_count, 1)

        _, kwargs = session.post.call_args
        self.assertEqual(
            kwargs["data"],
            {
                "grant_type": "client_credentials",
                "client_id": "cid",
                "client_secret": "csec",
            },
        )

    def test_force_refresh_and_invalidate(self) -> None:
        session = MagicMock(spec=requests.Session)
        session.post.side_effect = [
            _mock_response(200, {"access_token": "tok-1", "token_type": "Bearer", "expires_in": 86400}),
            _mock_response(200, {"access_token": "tok-2", "token_type": "Bearer", "expires_in": 86400}),
            _mock_response(200, {"access_token": "tok-3", "token_type": "Bearer", "expires_in": 86400}),
        ]
        client = OAuthTokenClient("cid", "csec", session=session)

        self.assertEqual(client.get_token(), "tok-1")
        self.assertEqual(client.get_token(force_refresh=True), "tok-2")
        client.invalidate()
        self.assertEqual(client.get_token(), "tok-3")
        self.assertEqual(session.post.call_count, 3)

    def test_invalid_client_raises_authentication_error(self) -> None:
        session = MagicMock(spec=requests.Session)
        session.post.return_value = _mock_response(
            401,
            {"error": "invalid_client", "error_description": "Invalid credentials"},
        )
        client = OAuthTokenClient("bad", "bad", session=session)
        with self.assertRaises(AuthenticationError):
            client.get_token()

    def test_rate_limited_raises_rate_limit_error(self) -> None:
        session = MagicMock(spec=requests.Session)
        session.post.return_value = _mock_response(429, {"error": {}}, headers={"Retry-After": "15"})
        client = OAuthTokenClient("cid", "csec", session=session)
        with self.assertRaises(RateLimitError) as ctx:
            client.get_token()
        self.assertEqual(ctx.exception.retry_after, 15)


if __name__ == "__main__":
    unittest.main()
