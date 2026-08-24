import json
import unittest
from pathlib import Path
from unittest import mock

from fetch.adapters import play

FIXTURES = Path(__file__).parent / "fixtures"


class TestNormalize(unittest.TestCase):
    def test_normalize_top(self):
        raw = json.loads((FIXTURES / "play_top.json").read_text(encoding="utf-8"))
        apps = play.normalize_top(raw)
        self.assertEqual(apps[0], {
            "track_id": "com.example.cleaner",
            "name": "Example Cleaner",
            "artist": "Example Inc.",
            "genre_id": "TOOLS",
            "rank": 1,
        })
        self.assertEqual(apps[1]["track_id"], "com.example.vpn")
        self.assertEqual(apps[1]["rank"], 2)

    def test_normalize_app_public_contract(self):
        raw = json.loads((FIXTURES / "play_app.json").read_text(encoding="utf-8"))
        d = play.normalize_app(raw)
        # 与 iOS 同名的公共字段（分析层复用）
        self.assertEqual(d["name"], "Example Cleaner")
        self.assertEqual(d["developer"], "Example Inc.")
        self.assertIn("storage", d["description"])
        self.assertEqual(d["price"], "Free")
        self.assertEqual(d["rating"], 4.6)
        self.assertEqual(d["rating_count"], 128000)
        self.assertEqual(d["release_date"], "Aug 1, 2019")
        self.assertEqual(d["track_view_url"], raw["url"])
        self.assertIn("Tools", d["genres"])
        self.assertIn("Performance", d["genres"])
        # Play 特有键（spec §4）
        self.assertEqual(d["installs"], "100,000,000+")
        self.assertTrue(d["offers_iap"])
        self.assertEqual(d["iap_price"], "$0.99 - $99.99 per item")

    def test_normalize_app_paid_price_format(self):
        d = play.normalize_app({"free": False, "price": 4.99, "currency": "USD"})
        self.assertEqual(d["price"], "USD 4.99")


class TestPlayAdapter(unittest.TestCase):
    def test_fetch_chart_maps_and_retries(self):
        top_fn = mock.MagicMock(return_value=json.loads(
            (FIXTURES / "play_top.json").read_text(encoding="utf-8")))
        a = play.PlayAdapter(lib=mock.MagicMock())  # 注入，无需安装库
        apps = a.fetch_chart("us", "free", 50, sleep=mock.MagicMock(), top_fn=top_fn)
        self.assertEqual(apps[0]["track_id"], "com.example.cleaner")
        kwargs = top_fn.call_args.kwargs
        self.assertEqual(kwargs["country"], "us")
        self.assertEqual(kwargs["num"], 50)
        self.assertEqual(kwargs["lang"], "en")
        self.assertEqual(kwargs["collection"], "TOP_FREE")

    def test_fetch_chart_all_fail_returns_none(self):
        top_fn = mock.MagicMock(side_effect=RuntimeError("net down"))
        a = play.PlayAdapter(lib=mock.MagicMock())
        apps = a.fetch_chart("us", "paid", 50, sleep=mock.MagicMock(), top_fn=top_fn)
        self.assertIsNone(apps)
        self.assertEqual(top_fn.call_count, 3)  # 1 + RETRY_LIMIT

    def test_fetch_details_per_app_fail_tolerant(self):
        calls = []

        def app_fn(app_id, country="us", lang="en"):
            calls.append(app_id)
            if app_id == "com.bad":
                raise RuntimeError("gone")
            return json.loads((FIXTURES / "play_app.json").read_text(encoding="utf-8"))

        a = play.PlayAdapter(lib=mock.MagicMock())
        out = a.fetch_details(["com.example.cleaner", "com.bad"], "us",
                              sleep=mock.MagicMock(), app_fn=app_fn)
        self.assertEqual(list(out), ["com.example.cleaner"])  # 失败的被容忍
        self.assertEqual(calls, ["com.example.cleaner", "com.bad"])

    def test_check_dependency_missing_exits_2(self):
        with mock.patch.dict("sys.modules", {"google_play_scraper": None}):
            with self.assertRaises(SystemExit) as cm:
                play.check_dependency()
            self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
