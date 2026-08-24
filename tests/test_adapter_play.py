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
    def _bridge(self, result):
        """返回一个 fake bridge_fn：忽略 payload，返回固定结果。"""
        calls = []
        def fn(payload, runner=None):
            calls.append(payload)
            return result
        fn.calls = calls
        return fn

    def test_fetch_chart_maps_and_retries(self):
        raw = json.loads((FIXTURES / "play_top.json").read_text(encoding="utf-8"))
        bridge = self._bridge(raw)
        a = play.PlayAdapter(runner=mock.MagicMock())  # 注入，不触发依赖检查
        apps = a.fetch_chart("us", "free", 50, sleep=mock.MagicMock(), bridge_fn=bridge)
        self.assertEqual(apps[0]["track_id"], "com.example.cleaner")
        payload = bridge.calls[0]
        self.assertEqual(payload["cmd"], "list")
        self.assertEqual(payload["country"], "us")
        self.assertEqual(payload["num"], 50)
        self.assertEqual(payload["lang"], "en")
        self.assertEqual(payload["collection"], "TOP_FREE")
        self.assertEqual(payload["category"], "TOOLS")

    def test_fetch_chart_grossing_collection_name(self):
        bridge = self._bridge([])
        a = play.PlayAdapter(runner=mock.MagicMock())
        a.fetch_chart("us", "grossing", 50, sleep=mock.MagicMock(), bridge_fn=bridge)
        self.assertEqual(bridge.calls[0]["collection"], "GROSSING")

    def test_fetch_chart_all_fail_returns_none(self):
        def boom(payload, runner=None):
            raise RuntimeError("net down")
        a = play.PlayAdapter(runner=mock.MagicMock())
        apps = a.fetch_chart("us", "paid", 50, sleep=mock.MagicMock(), bridge_fn=boom)
        self.assertIsNone(apps)

    def test_fetch_details_per_app_fail_tolerant(self):
        raw = json.loads((FIXTURES / "play_app.json").read_text(encoding="utf-8"))
        bridge = self._bridge({"com.example.cleaner": raw, "com.bad": None})
        a = play.PlayAdapter(runner=mock.MagicMock())
        out = a.fetch_details(["com.example.cleaner", "com.bad"], "us",
                              sleep=mock.MagicMock(), bridge_fn=bridge)
        self.assertEqual(list(out), ["com.example.cleaner"])  # null 被容忍
        self.assertEqual(bridge.calls[0]["cmd"], "apps")
        self.assertEqual(bridge.calls[0]["ids"], ["com.example.cleaner", "com.bad"])

    def test_check_dependency_missing_node_exits_2(self):
        with mock.patch.object(play, "shutil", create=True) as m_shutil, \
             mock.patch.object(play, "subprocess", create=True):
            m_shutil.which.return_value = None
            with self.assertRaises(SystemExit) as cm:
                play.check_dependency()
            self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
