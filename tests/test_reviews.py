import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fetch import reviews
from fetch.adapters import ios as ios_mod
from fetch.adapters import play as play_mod

FIXTURES = Path(__file__).parent / "fixtures"


class TestParseIosReviews(unittest.TestCase):
    def test_parse_list_entries(self):
        text = (FIXTURES / "ios_reviews.json").read_text(encoding="utf-8")
        self.assertEqual(reviews.parse_ios_reviews(text), [
            {"score": 5, "text": "Works perfectly for scanning docs"},
            {"score": 2, "text": "Subscription pushed everywhere"},
        ])

    def test_parse_single_entry_dict(self):
        text = json.dumps({"feed": {"entry": {
            "im:rating": {"label": "4"},
            "content": {"label": "good"}}}})
        self.assertEqual(reviews.parse_ios_reviews(text),
                         [{"score": 4, "text": "good"}])

    def test_parse_empty_feed(self):
        self.assertEqual(reviews.parse_ios_reviews('{"feed": {}}'), [])


class TestIosFetchReviews(unittest.TestCase):
    def _adapter(self, pages):
        """pages: {页码: 响应文本};按 URL 中 page=N 分发。"""
        def fake_http_get(url, opener=None, sleep=None):
            for page, text in pages.items():
                if f"/page={page}/" in url:
                    return text
            return None
        a = ios_mod.IosAdapter(opener=None)
        return a, fake_http_get

    def test_paginates_until_num_and_stops_on_empty(self):
        page1 = json.dumps({"feed": {"entry": [
            {"im:rating": {"label": "5"}, "content": {"label": f"r{i}"}}
            for i in range(50)]}})
        a, get = self._adapter({1: page1, 2: '{"feed": {}}'})
        with mock.patch.object(ios_mod, "http_get", side_effect=get):
            out = a.fetch_reviews("123", "us", num=100, sleep=mock.MagicMock())
        self.assertEqual(len(out), 50)  # 第 2 页空 → 停止,不臆造补齐

    def test_none_when_first_page_fails(self):
        a, get = self._adapter({})
        with mock.patch.object(ios_mod, "http_get", side_effect=get):
            self.assertIsNone(a.fetch_reviews("123", "us", sleep=mock.MagicMock()))


class TestPlayFetchReviews(unittest.TestCase):
    def test_maps_bridge_output(self):
        captured = {}

        def bridge(payload, runner=None):
            captured.update(payload)
            return [{"score": 5, "text": "great"}, {"score": 1}]

        a = play_mod.PlayAdapter(runner=mock.MagicMock())
        out = a.fetch_reviews("com.x", "us", num=50, bridge_fn=bridge)
        self.assertEqual(out, [{"score": 5, "text": "great"},
                               {"score": 1, "text": ""}])
        self.assertEqual(captured["cmd"], "reviews")
        self.assertEqual(captured["appId"], "com.x")
        self.assertEqual(captured["num"], 50)

    def test_none_on_bridge_failure(self):
        a = play_mod.PlayAdapter(runner=mock.MagicMock())
        self.assertIsNone(
            a.fetch_reviews("com.x", "us", bridge_fn=lambda p, runner=None: None))


class TestNormalizePlayReviews(unittest.TestCase):
    def test_normalizes_raw_list(self):
        self.assertEqual(
            reviews.normalize_play_reviews([{"score": 4, "text": "ok"}]),
            [{"score": 4, "text": "ok"}])

    def test_handles_bridge_none(self):
        self.assertIsNone(reviews.normalize_play_reviews(None))


class TestFetchAndSave(unittest.TestCase):
    def _adapter(self, results):
        class FakeAdapter:
            name = "fake"
            request_interval = 0

            def __init__(self):
                self.calls = []

            def fetch_reviews(self, tid, cc, num=100):
                self.calls.append(tid)
                return results.get(tid)

        return FakeAdapter()

    def test_writes_saves_and_uses_cache_on_second_run(self):
        results = {"a": [{"score": 5, "text": "x"}],
                   "b": [{"score": 1, "text": "y"}]}
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "reviews"
            adapter = self._adapter(results)
            r1 = reviews.fetch_and_save(adapter, ["a", "b"], "us", out_dir)
            self.assertEqual(r1["saved"], ["a", "b"])
            self.assertEqual(r1["failed"], [])
            self.assertEqual(
                json.loads((out_dir / "a.json").read_text(encoding="utf-8")),
                [{"score": 5, "text": "x"}])
            # 第二次:已落盘的走缓存,不再抓
            adapter.calls.clear()
            r2 = reviews.fetch_and_save(adapter, ["a", "b"], "us", out_dir)
            self.assertEqual(r2["cached"], ["a", "b"])
            self.assertEqual(adapter.calls, [])

    def test_failure_tolerated_and_not_cached(self):
        results = {"a": None, "b": [{"score": 3, "text": "z"}]}
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "reviews"
            r = reviews.fetch_and_save(
                self._adapter(results), ["a", "b"], "us", out_dir)
            self.assertEqual(r["saved"], ["b"])
            self.assertEqual(r["failed"], ["a"])
            self.assertFalse((out_dir / "a.json").exists())


if __name__ == "__main__":
    unittest.main()
