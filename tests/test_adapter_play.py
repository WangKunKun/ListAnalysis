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

    def test_normalize_app_adsupported_compat(self):
        # Node 版字段名 adSupported,Python 版 containsAds,两者兼容
        self.assertTrue(play.normalize_app({"adSupported": True})["contains_ads"])
        self.assertTrue(play.normalize_app({"containsAds": True})["contains_ads"])

    def test_normalize_app_paid_price_format(self):
        d = play.normalize_app({"free": False, "price": 4.99, "currency": "USD"})
        self.assertEqual(d["price"], "USD 4.99")


class TestNormalizeSearch(unittest.TestCase):
    def test_normalize_search(self):
        raw = json.loads((FIXTURES / "play_search.json").read_text(encoding="utf-8"))
        apps = play.normalize_search(raw)
        self.assertEqual(len(apps), 2)
        self.assertEqual(apps[0], {
            "track_id": "com.adobe.scan.android",
            "name": "Adobe Scan AI PDF Scanner, OCR",
            "artist": "Adobe",
        })


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

    def test_fetch_chart_timeout_no_retry(self):
        import subprocess
        def slow_bridge(payload, runner=None):
            raise subprocess.TimeoutExpired(cmd="node", timeout=60)
        a = play.PlayAdapter(runner=mock.MagicMock())
        apps = a.fetch_chart("us", "free", 50, sleep=mock.MagicMock(),
                             bridge_fn=slow_bridge)
        self.assertIsNone(apps)

    def test_fetch_details_batches_and_timeout_tolerant(self):
        import subprocess
        raw = json.loads((FIXTURES / "play_app.json").read_text(encoding="utf-8"))
        calls = []

        def bridge(payload, runner=None):
            calls.append(payload)
            if len(calls) == 1:
                raise subprocess.TimeoutExpired(cmd="node", timeout=60)  # 首批超时
            return {"com.a": raw, "com.b": None}                          # 次批部分成功

        a = play.PlayAdapter(runner=mock.MagicMock())
        ids = [f"com.i{i}" for i in range(29)] + ["com.a", "com.b"]  # 31 → 2 批
        out = a.fetch_details(ids, "us", sleep=mock.MagicMock(), bridge_fn=bridge)
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(calls[0]["ids"]), 30)
        self.assertEqual(list(out), ["com.a"])  # 首批超时丢弃,次批 null 容忍

    def test_check_dependency_missing_node_exits_2(self):
        with mock.patch.object(play, "shutil", create=True) as m_shutil, \
             mock.patch.object(play, "subprocess", create=True):
            m_shutil.which.return_value = None
            with self.assertRaises(SystemExit) as cm:
                play.check_dependency()
            self.assertEqual(cm.exception.code, 2)

    def test_search_apps_maps_and_normalizes(self):
        raw = json.loads((FIXTURES / "play_search.json").read_text(encoding="utf-8"))
        bridge = self._bridge(raw)
        a = play.PlayAdapter(runner=mock.MagicMock())
        apps = a.search_apps("pdf scanner", "us", 100,
                             sleep=mock.MagicMock(), bridge_fn=bridge)
        self.assertEqual(len(apps), 2)
        self.assertEqual(apps[0]["track_id"], "com.adobe.scan.android")
        payload = bridge.calls[0]
        self.assertEqual(payload["cmd"], "search")
        self.assertEqual(payload["term"], "pdf scanner")
        self.assertEqual(payload["num"], 100)
        self.assertEqual(payload["country"], "us")
        self.assertEqual(payload["lang"], "en")

    def test_search_apps_all_fail_returns_none(self):
        def boom(payload, runner=None):
            raise RuntimeError("net down")
        a = play.PlayAdapter(runner=mock.MagicMock())
        self.assertIsNone(a.search_apps("x", "us", 10,
                                        sleep=mock.MagicMock(), bridge_fn=boom))

    def test_search_apps_timeout_no_retry(self):
        import subprocess
        def slow_bridge(payload, runner=None):
            raise subprocess.TimeoutExpired(cmd="node", timeout=60)
        a = play.PlayAdapter(runner=mock.MagicMock())
        self.assertIsNone(a.search_apps("x", "us", 10,
                                        sleep=mock.MagicMock(), bridge_fn=slow_bridge))


if __name__ == "__main__":
    unittest.main()
