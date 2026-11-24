"""Taiwan Day Off API Wrapper (powered by dashboard.tw).

:copyright: (c) 2024-present Neko No Akuma
:license: GNU GPLv3, see LICENSE for more details.
"""

__title__ = "tw_dayoff"
__author__ = "Neko no akuma"
__license__ = "GNU GPLv3"
__copyright__ = "Copyright 2024-present Neko No Akuma"
__version__ = "0.2.0"

from .auth import OAuthTokenClient
from .client import DashboardClient, TyphoonDayOff
from .counties import COUNTY_CODE_TO_NAME, get_county_name, resolve_county_code
from .exceptions import (
    ApiError,
    AuthenticationError,
    CityCountyNotFoundError,
    RateLimitError,
    TwDayOffError,
)
from .models import ClosureLevel, RateLimitInfo, SourceInfo, WorkClosureRecord

__all__ = (
    "__version__",
    "ApiError",
    "AuthenticationError",
    "CityCountyNotFoundError",
    "ClosureLevel",
    "COUNTY_CODE_TO_NAME",
    "DashboardClient",
    "OAuthTokenClient",
    "RateLimitError",
    "RateLimitInfo",
    "SourceInfo",
    "TwDayOffError",
    "TyphoonDayOff",
    "WorkClosureRecord",
    "get_county_name",
    "resolve_county_code",
)
