"""dashboard.tw API client and high-level TyphoonDayOff wrapper."""

from datetime import date, datetime, timedelta, timezone
import os
from typing import Any, Dict, List, Optional, Tuple, Union

import requests

from .auth import DEFAULT_BASE_URL, OAuthTokenClient, _parse_retry_after
from .counties import resolve_county_code
from .exceptions import ApiError, AuthenticationError, RateLimitError, TwDayOffError
from .models import RateLimitInfo, SourceInfo, WorkClosureRecord

TAIWAN_TZ = timezone(timedelta(hours=8))

ENV_CLIENT_ID = "DASHBOARD_TW_CLIENT_ID"
ENV_CLIENT_SECRET = "DASHBOARD_TW_CLIENT_SECRET"
ENV_ACCESS_TOKEN = "DASHBOARD_TW_ACCESS_TOKEN"


def _format_time_param(value: Union[str, date, datetime]) -> str:
    """Format a date, datetime, or string into dashboard.tw's accepted time parameter."""
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=TAIWAN_TZ)
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(f"Expected str, date, or datetime, got {type(value).__name__}")


class DashboardClient:
    """Client for the dashboard.tw ``work_closure`` open data API.

    Supports OAuth 2.0 Client Credentials token caching/refresh, ETag
    conditional requests (``304 Not Modified``), cursor pagination, and quota
    header tracking.
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        *,
        access_token: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 10.0,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = session or requests.Session()
        self._owns_session = session is None

        resolved_id = client_id if client_id is not None else os.environ.get(ENV_CLIENT_ID)
        resolved_secret = (
            client_secret
            if client_secret is not None
            else os.environ.get(ENV_CLIENT_SECRET)
        )
        resolved_token = (
            access_token
            if access_token is not None
            else os.environ.get(ENV_ACCESS_TOKEN)
        )

        self._static_token: Optional[str] = None
        self._token_client: Optional[OAuthTokenClient] = None
        if resolved_id and resolved_secret:
            self._token_client = OAuthTokenClient(
                resolved_id,
                resolved_secret,
                base_url=self.base_url,
                timeout=self.timeout,
                session=self._session,
            )
        elif resolved_token:
            self._static_token = resolved_token

        self._etag_cache: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], Tuple[str, Dict[str, Any]]] = {}
        self.last_rate_limit: Optional[RateLimitInfo] = None
        self.last_source: Optional[SourceInfo] = None
        self.last_next_cursor: Optional[str] = None

    def __enter__(self) -> "DashboardClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP session if created by this client."""
        if self._owns_session:
            self._session.close()

    def get_latest(
        self,
        county: Optional[str] = None,
        *,
        use_etag: bool = True,
    ) -> List[WorkClosureRecord]:
        """Fetch the latest ``work_closure`` announcements.

        Args:
            county: Optional county code, Chinese name, English name, or
                abbreviation. Omit for all counties nationwide.
            use_etag: Send ``If-None-Match`` when an ETag was cached from a
                previous call, returning cached records on ``304 Not Modified``.

        Returns:
            List of ``WorkClosureRecord`` items.
        """
        params: Dict[str, str] = {}
        if county is not None:
            params["county"] = resolve_county_code(county)

        payload = self._request_json(
            "/datasets/work_closure/latest",
            params=params,
            use_etag=use_etag,
        )
        return self._extract_records(payload)

    def get_county_latest(
        self,
        county: str,
        *,
        use_etag: bool = True,
    ) -> Optional[WorkClosureRecord]:
        """Fetch the most recent ``work_closure`` record for a single county."""
        records = self.get_latest(county=county, use_etag=use_etag)
        if not records:
            return None
        return max(records, key=lambda r: (r.day or "", r.announced_at or ""))

    def get_history(
        self,
        county: Optional[str] = None,
        *,
        from_time: Optional[Union[str, date, datetime]] = None,
        to_time: Optional[Union[str, date, datetime]] = None,
        cursor: Optional[str] = None,
        fetch_all: bool = False,
    ) -> List[WorkClosureRecord]:
        """Fetch historical ``work_closure`` announcements (up to 31 days per query).

        Args:
            county: Optional county code, name, or abbreviation.
            from_time: Inclusive start time (``date``, ``datetime``, or ISO string).
            to_time: Exclusive end time (``date``, ``datetime``, or ISO string).
            cursor: Pagination cursor returned by a previous call.
            fetch_all: When True, automatically follows ``next_cursor`` pages.
        """
        base_params: Dict[str, str] = {}
        if county is not None:
            base_params["county"] = resolve_county_code(county)
        if from_time is not None:
            base_params["from"] = _format_time_param(from_time)
        if to_time is not None:
            base_params["to"] = _format_time_param(to_time)

        all_records: List[WorkClosureRecord] = []
        next_cursor = cursor

        while True:
            params = dict(base_params)
            if next_cursor is not None:
                params["cursor"] = next_cursor

            payload = self._request_json(
                "/datasets/work_closure/history",
                params=params,
                use_etag=False,
            )
            all_records.extend(self._extract_records(payload))
            next_cursor = self.last_next_cursor
            if not fetch_all or not next_cursor:
                break

        return all_records

    def _get_bearer_token(self, *, force_refresh: bool = False) -> str:
        if self._token_client is not None:
            return self._token_client.get_token(force_refresh=force_refresh)
        if self._static_token is not None and not force_refresh:
            return self._static_token
        raise AuthenticationError(
            "Missing dashboard.tw credentials. Provide client_id & client_secret "
            f"(or set {ENV_CLIENT_ID} / {ENV_CLIENT_SECRET}), or pass access_token "
            f"(or set {ENV_ACCESS_TOKEN})."
        )

    def _extract_records(self, payload: Dict[str, Any]) -> List[WorkClosureRecord]:
        meta = payload.get("meta") or {}
        self.last_source = SourceInfo.from_dict(meta.get("source"))
        self.last_next_cursor = meta.get("next_cursor")
        items = payload.get("data") or []
        return [WorkClosureRecord.from_dict(item) for item in items]

    def _request_json(
        self,
        path: str,
        *,
        params: Dict[str, str],
        use_etag: bool,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        cache_key = (path, tuple(sorted(params.items())))

        for attempt in range(2):
            token = self._get_bearer_token(force_refresh=(attempt == 1))
            headers: Dict[str, str] = {"Authorization": f"Bearer {token}"}

            cached = self._etag_cache.get(cache_key) if use_etag else None
            if cached is not None:
                headers["If-None-Match"] = cached[0]

            try:
                response = self._session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                )
            except requests.RequestException as exc:
                raise TwDayOffError(
                    f"Request to dashboard.tw failed: {exc}"
                ) from exc

            self.last_rate_limit = RateLimitInfo.from_headers(response.headers)

            if response.status_code == 304 and cached is not None:
                return cached[1]

            if response.status_code == 401:
                if attempt == 0 and self._token_client is not None:
                    self._token_client.invalidate()
                    continue
                code, message = self._parse_error_payload(response)
                raise AuthenticationError(
                    f"{code or 'invalid_token'}: {message or 'Unauthorized'}"
                )

            if response.status_code == 429:
                code, message = self._parse_error_payload(response)
                raise RateLimitError(
                    message or "dashboard.tw API rate or quota limit exceeded.",
                    code=code,
                    retry_after=_parse_retry_after(response.headers),
                )

            if response.status_code >= 400:
                code, message = self._parse_error_payload(response)
                raise ApiError(
                    f"HTTP {response.status_code} ({code or 'api_error'}): {message or response.reason}",
                    status_code=response.status_code,
                    code=code,
                )

            try:
                payload = response.json()
            except ValueError as exc:
                raise ApiError(
                    f"API returned non-JSON response (HTTP {response.status_code}).",
                    status_code=response.status_code,
                ) from exc

            etag = response.headers.get("ETag")
            if use_etag and etag:
                self._etag_cache[cache_key] = (etag, payload)
            return payload

        raise AuthenticationError("Authentication failed after refreshing access token.")

    @staticmethod
    def _parse_error_payload(response: requests.Response) -> Tuple[Optional[str], Optional[str]]:
        try:
            body = response.json()
        except ValueError:
            return None, response.text or None
        err = body.get("error")
        if isinstance(err, dict):
            return err.get("code"), err.get("message")
        return None, str(body)


class TyphoonDayOff:
    """High-level helper to query a single Taiwan county/city's day-off status.

    Args:
        city_county_name: County code (e.g. ``"63000"``), Chinese name (e.g.
            ``"臺北市"`` / ``"台北市"``), English name (e.g. ``"Taipei"``), or
            legacy abbreviation (e.g. ``"tp"``, ``"kh"``).
        client_id: Optional dashboard.tw OAuth Client ID (falls back to
            ``DASHBOARD_TW_CLIENT_ID``).
        client_secret: Optional dashboard.tw OAuth Client Secret (falls back to
            ``DASHBOARD_TW_CLIENT_SECRET``).
        access_token: Optional pre-issued Bearer token (falls back to
            ``DASHBOARD_TW_ACCESS_TOKEN``).
        client: Optional shared ``DashboardClient`` instance.
    """

    def __init__(
        self,
        city_county_name: str,
        *,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        client: Optional[DashboardClient] = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 10.0,
    ) -> None:
        self.city_county_name = city_county_name
        self.county_code = resolve_county_code(city_county_name)
        self._owns_client = client is None
        self.client = client or DashboardClient(
            client_id=client_id,
            client_secret=client_secret,
            access_token=access_token,
            base_url=base_url,
            timeout=timeout,
        )

    def __enter__(self) -> "TyphoonDayOff":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def close(self) -> None:
        """Close the internal ``DashboardClient`` if owned by this instance."""
        if self._owns_client:
            self.client.close()

    def get_record(self, *, use_etag: bool = True) -> Optional[WorkClosureRecord]:
        """Return the latest ``WorkClosureRecord`` for the configured county."""
        return self.client.get_county_latest(self.county_code, use_etag=use_etag)

    def get_dayoff(self, *, use_etag: bool = True) -> Optional[str]:
        """Return the latest closure announcement text, or ``None`` if none exists."""
        record = self.get_record(use_etag=use_etag)
        return record.status if record is not None else None

    def get_day_off(self, *, use_etag: bool = True) -> Optional[str]:
        """Alias for ``get_dayoff()`` matching README usage."""
        return self.get_dayoff(use_etag=use_etag)

    def is_dayoff(self, *, use_etag: bool = True) -> bool:
        """Return True if work and school are fully suspended (``level == 2``)."""
        record = self.get_record(use_etag=use_etag)
        return bool(record is not None and record.is_day_off)
