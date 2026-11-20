import unittest

from main import (
    group_recommendations,
    make_hourly_forecast,
    make_multi_day_forecast,
    make_day_advice,
    make_recommendations,
    make_weather_alert,
)


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

    def test_recommendations_include_multiple_categories(self):
        weather = {
            "rain": 20,
            "code": 1,
            "max": 22,
            "current": {"wind_speed_10m": 8},
        }

        recommendations = make_recommendations(weather)

        self.assertGreater(len(recommendations), 3)
        self.assertTrue(any(item["kind"] == "外出" for item in recommendations))
        self.assertTrue(any(item["kind"] == "室内" for item in recommendations))
        self.assertTrue(any(item["kind"] == "休憩" for item in recommendations))
        self.assertTrue(all(item["reason"] for item in recommendations))
        self.assertIn(
            "外でやりたかったことをひとつ実行する",
            [item["text"] for item in recommendations],
        )

    def test_action_hint_categories_offer_multiple_choices(self):
        weather = {
            "rain": 20,
            "code": 1,
            "max": 22,
            "current": {"wind_speed_10m": 8},
        }

        recommendations = make_recommendations(weather)

        for category in ("外出", "運動", "室内", "休憩"):
            with self.subTest(category=category):
                self.assertGreaterEqual(
                    sum(item["kind"] == category for item in recommendations),
                    2,
                )

    def test_rainy_weather_still_offers_varied_action_categories(self):
        weather = {
            "rain": 70,
            "code": 61,
            "max": 18,
            "current": {"wind_speed_10m": 10},
        }

        recommendations = make_recommendations(weather)

        for category in ("外出", "運動", "室内", "休憩"):
            with self.subTest(category=category):
                self.assertGreaterEqual(
                    sum(item["kind"] == category for item in recommendations),
                    2,
                )

    def test_weather_alert_includes_relevant_warning_conditions(self):
        weather = {
            "city": "Tokyo",
            "rain": 70,
            "code": 61,
            "max": 32,
            "current": {"wind_speed_10m": 40},
        }

        alert = make_weather_alert(weather)

        self.assertIn("Tokyo", alert["title"])
        self.assertIn("降水確率 70%", alert["body"])
        self.assertIn("最高気温は32℃", alert["body"])
        self.assertIn("風速は40 km/h", alert["body"])

    def test_weather_alert_is_omitted_when_no_warning_threshold_is_met(self):
        weather = {
            "city": "Tokyo",
            "rain": 20,
            "code": 1,
            "max": 22,
            "current": {"wind_speed_10m": 8},
        }

        self.assertIsNone(make_weather_alert(weather))

    def test_safety_recommendations_are_shown_before_other_categories(self):
        weather = {
            "rain": 0,
            "code": 1,
            "max": 32,
            "current": {"wind_speed_10m": 40},
        }

        recommendations = make_recommendations(weather)

        self.assertEqual(recommendations[0]["kind"], "安全")
        self.assertIn("自転車や屋外作業", recommendations[0]["text"])
        self.assertIn("風速が40 km/h", recommendations[0]["reason"])

    def test_recommendations_are_grouped_by_time_and_can_be_filtered(self):
        recommendations = [
            {"period": "昼", "kind": "外出", "text": "昼に散歩"},
            {"period": "朝", "kind": "持ち物", "text": "傘を用意"},
            {"period": "いつでも", "kind": "外出", "text": "水分補給"},
        ]

        grouped = group_recommendations(recommendations)
        filtered = group_recommendations(recommendations, "外出")

        self.assertEqual([period for period, _ in grouped], ["朝", "昼", "いつでも"])
        self.assertEqual(
            [item["text"] for _, items in filtered for item in items],
            ["昼に散歩", "水分補給"],
        )

    def test_recommendations_can_be_filtered_by_category_and_period(self):
        recommendations = [
            {"period": "朝", "kind": "持ち物", "text": "傘を用意"},
            {"period": "昼", "kind": "外出", "text": "昼に散歩"},
            {"period": "昼", "kind": "休憩", "text": "昼休みに休む"},
        ]

        filtered = group_recommendations(recommendations, "外出", "昼")

        self.assertEqual(
            [item["text"] for _, items in filtered for item in items],
            ["昼に散歩"],
        )

    def test_multi_day_forecast_contains_seven_days(self):
        weather = {
            "daily": {
                "time": ["2026-11-20", "2026-11-21", "2026-11-22"],
                "max": [18, 19, 20],
                "min": [10, 11, 12],
                "rain": [20, 60, 0],
                "code": [1, 61, 0],
                "uv_index_max": [2.4, 3.1, 4.0],
                "sunrise": [
                    "2026-11-20T06:30",
                    "2026-11-21T06:31",
                    "2026-11-22T06:32",
                ],
                "sunset": [
                    "2026-11-20T16:40",
                    "2026-11-21T16:39",
                    "2026-11-22T16:38",
                ],
            }
        }

        forecast = make_multi_day_forecast(weather)

        self.assertEqual(len(forecast), 3)
        self.assertEqual(forecast[1]["rain"], 60)
        self.assertIn("雨", forecast[1]["label"])
        self.assertEqual([item["weekday"] for item in forecast], ["金", "土", "日"])
        self.assertEqual(forecast[1]["uv_index_max"], 3.1)
        self.assertEqual(forecast[1]["sunrise"], "2026-11-21T06:31")
        self.assertEqual(forecast[1]["sunset"], "2026-11-21T16:39")

    def test_hourly_forecast_starts_at_current_hour_and_limits_to_one_day(self):
        hourly = {
            "time": [
                f"2026-11-20T{hour:02d}:00"
                for hour in range(24)
            ],
            "temperature_2m": list(range(24)),
            "precipitation_probability": [0] * 24,
            "weather_code": [1] * 24,
            "wind_speed_10m": [5] * 24,
        }

        forecast = make_hourly_forecast(hourly, "2026-11-20T08:30", limit=4)

        self.assertEqual(
            [item["time"] for item in forecast],
            [
                "2026-11-20T08:00",
                "2026-11-20T09:00",
                "2026-11-20T10:00",
                "2026-11-20T11:00",
            ],
        )
        self.assertEqual(forecast[0]["temperature"], 8)


if __name__ == "__main__":
    unittest.main()
