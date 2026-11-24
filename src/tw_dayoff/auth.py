"""OAuth 2.0 Client Credentials token management for dashboard.tw."""

import threading
import time
from typing import Optional

import requests

from .exceptions import ApiError, AuthenticationError, RateLimitError

DEFAULT_BASE_URL = "https://dashboard.tw/api/v1"


def _parse_retry_after(headers: object) -> Optional[int]:
    raw = getattr(headers, "get", lambda _k: None)("Retry-After")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


class OAuthTokenClient:
    """Fetches and caches Bearer tokens via ``POST /auth/token``."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 10.0,
        refresh_margin_seconds: float = 60.0,
        session: Optional[requests.Session] = None,
    ) -> None:
        if not client_id or not client_secret:
            raise AuthenticationError(
                "Both client_id and client_secret are required for OAuth client_credentials."
            )
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = f"{base_url.rstrip('/')}/auth/token"
        self.timeout = timeout
        self.refresh_margin_seconds = max(0.0, refresh_margin_seconds)
        self._session = session or requests.Session()
        self._owns_session = session is None

        self._lock = threading.Lock()
        self._access_token: Optional[str] = None
        self._expires_at: float = 0.0

    def get_token(self, *, force_refresh: bool = False) -> str:
        """Return a valid cached access token, or request a new one if expired."""
        with self._lock:
            now = time.monotonic()
            if (
                not force_refresh
                and self._access_token is not None
                and now < self._expires_at
            ):
                return self._access_token

            token, expires_in = self._request_token()
            # Refresh slightly ahead of actual expiry when lifetime allows.
            margin = (
                self.refresh_margin_seconds
                if expires_in > self.refresh_margin_seconds
                else 0.0
            )
            self._access_token = token
            self._expires_at = time.monotonic() + max(0.0, expires_in - margin)
            return token

    def invalidate(self) -> None:
        """Clear any cached access token."""
        with self._lock:
            self._access_token = None
            self._expires_at = 0.0

    def close(self) -> None:
        """Close the owned HTTP session, if created internally."""
        if self._owns_session:
            self._session.close()

    def _request_token(self) -> tuple:
        try:
            response = self._session.post(
                self.token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise AuthenticationError(
                f"Failed to connect to dashboard.tw token endpoint: {exc}"
            ) from exc

        if response.status_code == 429:
            raise RateLimitError(
                "Rate limit exceeded while requesting OAuth access token.",
                code="rate_limited",
                retry_after=_parse_retry_after(response.headers),
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise ApiError(
                f"Token endpoint returned non-JSON response (HTTP {response.status_code}).",
                status_code=response.status_code,
            ) from exc

        if response.status_code in (400, 401):
            err = payload.get("error") or "authentication_failed"
            desc = payload.get("error_description") or response.reason or "Unauthorized"
            raise AuthenticationError(f"{err}: {desc}")

        if response.status_code >= 400:
            raise ApiError(
                f"Token endpoint error (HTTP {response.status_code}): {payload}",
                status_code=response.status_code,
            )

        access_token = payload.get("access_token")
        if not access_token:
            raise AuthenticationError("Token response did not contain 'access_token'.")

        expires_in = payload.get("expires_in", 86400)
        try:
            expires_in_float = float(expires_in)
        except (TypeError, ValueError):
            expires_in_float = 86400.0

        return access_token, expires_in_float
