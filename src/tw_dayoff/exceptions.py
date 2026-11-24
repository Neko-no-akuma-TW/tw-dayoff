"""Custom exceptions for tw_dayoff."""

from typing import Optional


class TwDayOffError(Exception):
    """Base exception for all tw_dayoff errors."""


class CityCountyNotFoundError(TwDayOffError):
    """Raised when a city/county name or code cannot be resolved."""


class AuthenticationError(TwDayOffError):
    """Raised when OAuth authentication or access token validation fails."""


class RateLimitError(TwDayOffError):
    """Raised when dashboard.tw API rate, daily quota, or traffic limit is exceeded."""

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        retry_after: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retry_after = retry_after


class ApiError(TwDayOffError):
    """Raised when the dashboard.tw API returns an unexpected HTTP or payload error."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
