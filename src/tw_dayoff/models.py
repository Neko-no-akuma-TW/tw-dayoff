"""Data models for Taiwan Dashboard work_closure responses."""

from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Dict, Optional

from .counties import get_county_name


class ClosureLevel(IntEnum):
    """Work and school closure severity levels defined by dashboard.tw."""

    NORMAL = 0
    PARTIAL = 1
    SUSPENDED = 2


@dataclass(frozen=True)
class WorkClosureRecord:
    """A single work/school closure announcement record from ``work_closure``."""

    county_code: Optional[str]
    county_name: Optional[str]
    day: Optional[str]
    announced_at: Optional[str]
    status: Optional[str]
    level: Optional[int]
    first_seen_at: Optional[str]
    last_seen_at: Optional[str]

    @property
    def closure_level(self) -> Optional[ClosureLevel]:
        """Return ``ClosureLevel`` enum if ``level`` is a known integer."""
        if self.level is None:
            return None
        try:
            return ClosureLevel(self.level)
        except ValueError:
            return None

    @property
    def is_day_off(self) -> bool:
        """Return True when work and school are fully suspended (``level == 2``)."""
        return self.level == ClosureLevel.SUSPENDED

    @property
    def is_partial(self) -> bool:
        """Return True when work or school is partially suspended (``level == 1``)."""
        return self.level == ClosureLevel.PARTIAL

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "WorkClosureRecord":
        """Build a ``WorkClosureRecord`` from an API JSON item."""
        county_code = payload.get("county_code")
        return cls(
            county_code=county_code,
            county_name=get_county_name(county_code),
            day=payload.get("day"),
            announced_at=payload.get("announced_at"),
            status=payload.get("status"),
            level=payload.get("level"),
            first_seen_at=payload.get("first_seen_at"),
            last_seen_at=payload.get("last_seen_at"),
        )


@dataclass(frozen=True)
class SourceInfo:
    """Attribution metadata returned in ``meta.source``."""

    agency: Optional[str] = None
    license: Optional[str] = None
    url: Optional[str] = None

    @classmethod
    def from_dict(cls, payload: Optional[Dict[str, Any]]) -> Optional["SourceInfo"]:
        if not payload:
            return None
        return cls(
            agency=payload.get("agency"),
            license=payload.get("license"),
            url=payload.get("url"),
        )


@dataclass(frozen=True)
class RateLimitInfo:
    """Rate limit and daily traffic quota headers from dashboard.tw responses."""

    limit: Optional[int] = None
    remaining: Optional[int] = None
    traffic_limit: Optional[int] = None
    traffic_used: Optional[int] = None

    @classmethod
    def from_headers(cls, headers: Any) -> "RateLimitInfo":
        def _parse_int(name: str) -> Optional[int]:
            raw = headers.get(name)
            if raw is None:
                return None
            try:
                return int(raw)
            except (TypeError, ValueError):
                return None

        return cls(
            limit=_parse_int("X-RateLimit-Limit"),
            remaining=_parse_int("X-RateLimit-Remaining"),
            traffic_limit=_parse_int("X-Traffic-Limit"),
            traffic_used=_parse_int("X-Traffic-Used"),
        )
