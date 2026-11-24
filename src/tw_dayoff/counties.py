"""Taiwan county/city code mappings (Ministry of the Interior 5-digit codes)."""

from typing import Dict, Optional

from .exceptions import CityCountyNotFoundError

# Official MOI 5-digit county/city codes -> Traditional Chinese canonical names
COUNTY_CODE_TO_NAME: Dict[str, str] = {
    "63000": "臺北市",
    "65000": "新北市",
    "68000": "桃園市",
    "66000": "臺中市",
    "67000": "臺南市",
    "64000": "高雄市",
    "10017": "基隆市",
    "10002": "宜蘭縣",
    "10004": "新竹縣",
    "10018": "新竹市",
    "10005": "苗栗縣",
    "10007": "彰化縣",
    "10008": "南投縣",
    "10009": "雲林縣",
    "10010": "嘉義縣",
    "10020": "嘉義市",
    "10013": "屏東縣",
    "10014": "臺東縣",
    "10015": "花蓮縣",
    "10016": "澎湖縣",
    "09020": "金門縣",
    "09007": "連江縣",
}

_AMBIGUOUS_ALIASES: Dict[str, str] = {
    "新竹": "Ambiguous county name '新竹'; please specify '新竹市' (10018) or '新竹縣' (10004).",
    "嘉義": "Ambiguous county name '嘉義'; please specify '嘉義市' (10020) or '嘉義縣' (10010).",
    "hsinchu": "Ambiguous county name 'Hsinchu'; please specify 'Hsinchu City' (10018) or 'Hsinchu County' (10004).",
    "chiayi": "Ambiguous county name 'Chiayi'; please specify 'Chiayi City' (10020) or 'Chiayi County' (10010).",
}

# Lowercase lookup map for Chinese names, short names, English names, and legacy abbreviations.
# Note: "台" is normalized to "臺" before lookup.
_ALIAS_TO_CODE: Dict[str, str] = {
    # 臺北市
    "臺北市": "63000",
    "臺北": "63000",
    "taipei": "63000",
    "taipei city": "63000",
    "tp": "63000",
    "tpe": "63000",
    # 新北市
    "新北市": "65000",
    "新北": "65000",
    "new taipei": "65000",
    "new taipei city": "65000",
    "ntpc": "65000",
    # 桃園市
    "桃園市": "68000",
    "桃園": "68000",
    "桃園縣": "68000",
    "taoyuan": "68000",
    "taoyuan city": "68000",
    "ty": "68000",
    "tyn": "68000",
    # 臺中市
    "臺中市": "66000",
    "臺中": "66000",
    "taichung": "66000",
    "taichung city": "66000",
    "tc": "66000",
    "txg": "66000",
    # 臺南市
    "臺南市": "67000",
    "臺南": "67000",
    "tainan": "67000",
    "tainan city": "67000",
    "tn": "67000",
    "tnn": "67000",
    # 高雄市
    "高雄市": "64000",
    "高雄": "64000",
    "kaohsiung": "64000",
    "kaohsiung city": "64000",
    "kh": "64000",
    "khh": "64000",
    # 基隆市
    "基隆市": "10017",
    "基隆": "10017",
    "keelung": "10017",
    "keelung city": "10017",
    "kl": "10017",
    "kee": "10017",
    # 宜蘭縣
    "宜蘭縣": "10002",
    "宜蘭": "10002",
    "yilan": "10002",
    "yilan county": "10002",
    "ilan": "10002",
    "il": "10002",
    # 新竹縣
    "新竹縣": "10004",
    "hsinchu county": "10004",
    "hcc": "10004",
    # 新竹市
    "新竹市": "10018",
    "hsinchu city": "10018",
    "hc": "10018",
    "hsz": "10018",
    # 苗栗縣
    "苗栗縣": "10005",
    "苗栗": "10005",
    "miaoli": "10005",
    "miaoli county": "10005",
    "ml": "10005",
    # 彰化縣
    "彰化縣": "10007",
    "彰化": "10007",
    "changhua": "10007",
    "changhua county": "10007",
    "ch": "10007",
    # 南投縣
    "南投縣": "10008",
    "南投": "10008",
    "nantou": "10008",
    "nantou county": "10008",
    "nt": "10008",
    # 雲林縣
    "雲林縣": "10009",
    "雲林": "10009",
    "yunlin": "10009",
    "yunlin county": "10009",
    "yl": "10009",
    # 嘉義縣
    "嘉義縣": "10010",
    "chiayi county": "10010",
    "cyc": "10010",
    # 嘉義市
    "嘉義市": "10020",
    "chiayi city": "10020",
    "cy": "10020",
    "cyi": "10020",
    # 屏東縣
    "屏東縣": "10013",
    "屏東": "10013",
    "pingtung": "10013",
    "pingtung county": "10013",
    "pt": "10013",
    # 臺東縣
    "臺東縣": "10014",
    "臺東": "10014",
    "taitung": "10014",
    "taitung county": "10014",
    "tt": "10014",
    "ttt": "10014",
    # 花蓮縣
    "花蓮縣": "10015",
    "花蓮": "10015",
    "hualien": "10015",
    "hualien county": "10015",
    "hl": "10015",
    "hun": "10015",
    # 澎湖縣
    "澎湖縣": "10016",
    "澎湖": "10016",
    "penghu": "10016",
    "penghu county": "10016",
    "ph": "10016",
    # 金門縣
    "金門縣": "09020",
    "金門": "09020",
    "kinmen": "09020",
    "kinmen county": "09020",
    "km": "09020",
    "knh": "09020",
    # 連江縣
    "連江縣": "09007",
    "連江": "09007",
    "馬祖": "09007",
    "lienchiang": "09007",
    "lienchiang county": "09007",
    "matsu": "09007",
    "lj": "09007",
    "mz": "09007",
}


def resolve_county_code(county: str) -> str:
    """Resolve a county/city name, alias, or 5-digit code into a MOI 5-digit code.

    Args:
        county: County code (e.g. ``"63000"``), Chinese name (e.g. ``"臺北市"``,
            ``"台北市"``, ``"台北"``), English name (e.g. ``"Taipei"``), or
            abbreviation (e.g. ``"tp"``, ``"kh"``).

    Returns:
        Five-digit MOI county code string.

    Raises:
        CityCountyNotFoundError: If the input is empty, ambiguous, or unknown.
    """
    if not isinstance(county, str) or not county.strip():
        raise CityCountyNotFoundError("County name or code cannot be empty.")

    cleaned = " ".join(county.strip().split())
    if cleaned in COUNTY_CODE_TO_NAME:
        return cleaned

    normalized = cleaned.replace("台", "臺").lower()
    if normalized in _AMBIGUOUS_ALIASES:
        raise CityCountyNotFoundError(_AMBIGUOUS_ALIASES[normalized])

    code = _ALIAS_TO_CODE.get(normalized)
    if code is None:
        raise CityCountyNotFoundError(f"Unknown county or city: {county!r}")
    return code


def get_county_name(county_code: Optional[str]) -> Optional[str]:
    """Return the canonical Traditional Chinese name for a 5-digit county code."""
    if county_code is None:
        return None
    return COUNTY_CODE_TO_NAME.get(county_code)
