import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from main import PREFECTURE_CITIES, fetch_weather, resolve_place_name


class PrefectureLookupTest(unittest.TestCase):
    def test_all_prefectures_resolve_to_their_capital(self):
        self.assertEqual(len(PREFECTURE_CITIES), 47)
        for prefecture, capital in PREFECTURE_CITIES.items():
            with self.subTest(prefecture=prefecture):
                self.assertEqual(resolve_place_name(prefecture), capital)
                if prefecture.endswith(("都", "府", "県")):
                    self.assertEqual(resolve_place_name(prefecture[:-1]), capital)

    def test_prefecture_geocoding_is_limited_to_japan(self):
        class FakeResponse:
            def __init__(self, body):
                self.body = body

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def read(self):
                return self.body

        geocoding_response = b'{"results":[{"latitude":34.73,"longitude":136.51,"name":"Tsu","country":"Japan"}]}'
        forecast_response = (
            b'{"current":{"temperature_2m":20,"weather_code":1,"wind_speed_10m":5},'
            b'"hourly":{"time":["2026-11-13T06:00"],"temperature_2m":[15],'
            b'"precipitation_probability":[0],"weather_code":[1],"wind_speed_10m":[5]},'
            b'"daily":{"time":["2026-11-13"],"temperature_2m_max":[22],"temperature_2m_min":[15],'
            b'"precipitation_probability_max":[10],"weather_code":[1],"uv_index_max":[2.5],'
            b'"sunrise":["2026-11-13T06:30"],"sunset":["2026-11-13T16:40"]}}'
        )
        with patch("main.urlopen", side_effect=[
            FakeResponse(geocoding_response),
            FakeResponse(forecast_response),
        ]) as mocked_urlopen:
            weather = fetch_weather("三重県")

        query = parse_qs(urlparse(mocked_urlopen.call_args_list[0].args[0]).query)
        self.assertEqual(query["name"], ["Tsu"])
        self.assertEqual(query["countryCode"], ["JP"])
        self.assertEqual(weather["country"], "Japan")
        forecast_query = parse_qs(urlparse(mocked_urlopen.call_args_list[1].args[0]).query)
        self.assertIn("precipitation_probability", forecast_query["hourly"][0])
        self.assertEqual(forecast_query["forecast_days"], ["7"])
        self.assertIn("uv_index_max", forecast_query["daily"][0])
        self.assertIn("sunrise", forecast_query["daily"][0])
        self.assertIn("sunset", forecast_query["daily"][0])
        self.assertEqual(weather["hourly"]["temperature_2m"], [15])

    def test_prefecture_name_is_resolved(self):
        self.assertEqual(resolve_place_name("東京都"), "Tokyo")
        self.assertEqual(resolve_place_name("大阪府"), "Osaka")
        self.assertEqual(resolve_place_name("福岡県"), "Fukuoka")
        self.assertEqual(resolve_place_name("埼玉県"), "Saitama")

    def test_japanese_city_name_uses_gsi_coordinates(self):
        class FakeResponse:
            def __init__(self, body):
                self.body = body

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def read(self):
                return self.body

        location_response = (
            '[{"geometry":{"coordinates":[137.025711,36.754074]},'
            '"properties":{"title":"富山県高岡市"}}]'
        ).encode()
        forecast_response = (
            b'{"current":{"temperature_2m":20,"weather_code":1,"wind_speed_10m":5},'
            b'"hourly":{"time":["2026-11-13T06:00"],"temperature_2m":[15],'
            b'"precipitation_probability":[0],"weather_code":[1],"wind_speed_10m":[5]},'
            b'"daily":{"time":["2026-11-13"],"temperature_2m_max":[22],'
            b'"temperature_2m_min":[15],"precipitation_probability_max":[10],'
            b'"weather_code":[1],"uv_index_max":[2.5],'
            b'"sunrise":["2026-11-13T06:30"],"sunset":["2026-11-13T16:40"]}}'
        )
        with patch(
            "main.urlopen",
            side_effect=[FakeResponse(location_response), FakeResponse(forecast_response)],
        ) as mocked_urlopen:
            weather = fetch_weather("高岡")

        geocoding_url = mocked_urlopen.call_args_list[0].args[0]
        query = parse_qs(urlparse(geocoding_url).query)
        self.assertIn("AddressSearch", geocoding_url)
        self.assertEqual(query["q"], ["高岡市"])
        forecast_query = parse_qs(
            urlparse(mocked_urlopen.call_args_list[1].args[0]).query
        )
        self.assertEqual(forecast_query["latitude"], ["36.754074"])
        self.assertEqual(forecast_query["longitude"], ["137.025711"])
        self.assertEqual(weather["city"], "富山県高岡市")


if __name__ == "__main__":
    unittest.main()
