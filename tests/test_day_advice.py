import unittest

from main import make_day_advice


class DayAdviceTest(unittest.TestCase):
    def test_advice_is_specific_to_each_part_of_the_day(self):
        hourly = {
            "time": [
                "2026-11-13T06:00",
                "2026-11-13T09:00",
                "2026-11-13T12:00",
                "2026-11-13T15:00",
                "2026-11-13T18:00",
                "2026-11-13T21:00",
            ],
            "temperature_2m": [12, 15, 29, 31, 14, 15],
            "precipitation_probability": [70, 60, 0, 10, 0, 0],
            "weather_code": [61, 61, 1, 1, 2, 2],
            "wind_speed_10m": [5, 5, 5, 5, 40, 35],
        }

        advice = make_day_advice(hourly)

        self.assertEqual([item["period"] for item in advice], ["朝", "昼", "夕方・夜"])
        self.assertIn("雨具", advice[0]["tip"])
        self.assertIn("水分補給", advice[1]["tip"])
        self.assertIn("風が強まり", advice[2]["tip"])

    def test_cold_forecast_recommends_warm_clothes(self):
        hourly = {
            "time": ["2026-11-13T18:00"],
            "temperature_2m": [8],
            "precipitation_probability": [0],
            "weather_code": [0],
            "wind_speed_10m": [5],
        }

        advice = make_day_advice(hourly)

        self.assertIn("上着", advice[0]["tip"])

    def test_missing_periods_are_omitted(self):
        hourly = {
            "time": ["2026-11-13T12:00"],
            "temperature_2m": [20],
            "precipitation_probability": [0],
            "weather_code": [2],
            "wind_speed_10m": [5],
        }

        advice = make_day_advice(hourly)

        self.assertEqual([item["period"] for item in advice], ["昼"])


if __name__ == "__main__":
    unittest.main()
