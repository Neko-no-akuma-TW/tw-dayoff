"""Tests for Taiwan county code resolution."""

import unittest

from tw_dayoff import (
    COUNTY_CODE_TO_NAME,
    CityCountyNotFoundError,
    get_county_name,
    resolve_county_code,
)


class TestCounties(unittest.TestCase):
    def test_all_22_counties_defined(self) -> None:
        self.assertEqual(len(COUNTY_CODE_TO_NAME), 22)
        for code, name in COUNTY_CODE_TO_NAME.items():
            self.assertEqual(len(code), 5)
            self.assertTrue(code.isdigit())
            self.assertEqual(resolve_county_code(code), code)
            self.assertEqual(resolve_county_code(name), code)
            self.assertEqual(get_county_name(code), name)

    def test_chinese_variants_and_short_names(self) -> None:
        self.assertEqual(resolve_county_code("台北市"), "63000")
        self.assertEqual(resolve_county_code("台北"), "63000")
        self.assertEqual(resolve_county_code("新北市"), "65000")
        self.assertEqual(resolve_county_code("台中市"), "66000")
        self.assertEqual(resolve_county_code("台南"), "67000")
        self.assertEqual(resolve_county_code("台東縣"), "10014")
        self.assertEqual(resolve_county_code("馬祖"), "09007")
        self.assertEqual(resolve_county_code("連江"), "09007")

    def test_english_and_legacy_codes(self) -> None:
        self.assertEqual(resolve_county_code("Taipei"), "63000")
        self.assertEqual(resolve_county_code("New Taipei City"), "65000")
        self.assertEqual(resolve_county_code("kh"), "64000")
        self.assertEqual(resolve_county_code("tp"), "63000")
        self.assertEqual(resolve_county_code("ntpc"), "65000")
        self.assertEqual(resolve_county_code("Hsinchu City"), "10018")
        self.assertEqual(resolve_county_code("Hsinchu County"), "10004")
        self.assertEqual(resolve_county_code("Chiayi City"), "10020")
        self.assertEqual(resolve_county_code("Chiayi County"), "10010")

    def test_ambiguous_and_invalid_inputs(self) -> None:
        for invalid in ("", "   ", "新竹", "嘉義", "Hsinchu", "Chiayi", "99999", "Atlantis"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(CityCountyNotFoundError):
                    resolve_county_code(invalid)


if __name__ == "__main__":
    unittest.main()
