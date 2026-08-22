import http.client
import json
import unittest
import urllib.error
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import fetch_charts


class TestLoadConfig(unittest.TestCase):
    def test_missing_file_returns_defaults(self):
        cfg = fetch_charts.load_config(Path("/nonexistent/config.json"))
        self.assertEqual(cfg["regions"], fetch_charts.DEFAULT_CONFIG["regions"])
        self.assertEqual(cfg["top_n"], 50)

    def test_user_config_overrides_defaults(self):
        with TemporaryDirectory() as td:
            p = Path(td) / "config.json"
            p.write_text('{"top_n": 100, "regions": ["us"]}', encoding="utf-8")
            cfg = fetch_charts.load_config(p)
            self.assertEqual(cfg["top_n"], 100)
            self.assertEqual(cfg["regions"], ["us"])
            self.assertEqual(cfg["charts"], fetch_charts.DEFAULT_CONFIG["charts"])

    def test_invalid_chart_key_raises(self):
        with TemporaryDirectory() as td:
            p = Path(td) / "config.json"
            p.write_text('{"charts": ["free", "bogus"]}', encoding="utf-8")
            with self.assertRaises(ValueError):
                fetch_charts.load_config(p)


FIXTURES = Path(__file__).parent / "fixtures"


class TestParseRss(unittest.TestCase):
    def test_parses_entries_with_rank(self):
        text = (FIXTURES / "rss_utilities.json").read_text(encoding="utf-8")
        apps = fetch_charts.parse_rss(text)
        self.assertEqual(len(apps), 2)
        self.assertEqual(apps[0], {
            "track_id": "111111",
            "name": "Example Cleaner",
            "artist": "Example Inc.",
            "genre_id": "6002",
            "rank": 1,
        })
        self.assertEqual(apps[1]["track_id"], "222222")
        self.assertEqual(apps[1]["rank"], 2)

    def test_single_entry_dict_is_normalized(self):
        # JSON feed 只有 1 条时 entry 是 dict 不是 list（接口经典坑）
        text = json.dumps({"feed": {"entry": {
            "id": {"attributes": {"im:id": "333333"}},
            "im:name": {"label": "Solo"},
            "im:artist": {"label": "Solo Dev"},
            "category": {"attributes": {"im:id": "6002"}},
        }}})
        apps = fetch_charts.parse_rss(text)
        self.assertEqual(len(apps), 1)
        self.assertEqual(apps[0]["rank"], 1)

    def test_empty_feed(self):
        self.assertEqual(fetch_charts.parse_rss('{"feed": {}}'), [])


class TestFilterUtilities(unittest.TestCase):
    def test_filters_non_utilities_and_reranks(self):
        text = (FIXTURES / "rss_mixed_genres.json").read_text(encoding="utf-8")
        apps = fetch_charts.parse_rss(text)
        kept = fetch_charts.filter_utilities(apps)
        self.assertEqual([a["track_id"] for a in kept], ["100001", "100003"])
        self.assertEqual([a["rank"] for a in kept], [1, 2])


class TestMergeApps(unittest.TestCase):
    def _app(self, tid, name="N", artist="D"):
        return {"track_id": tid, "name": name, "artist": artist,
                "genre_id": "6002", "rank": 1}

    def test_dedup_and_rank_merge(self):
        a = self._app("1", "Cleaner")
        a["rank"] = 3
        b = self._app("1", "Cleaner")
        b["rank"] = 5
        c = self._app("2", "VPN")
        merged = fetch_charts.merge_apps([
            ("us", "free", [a]),
            ("jp", "free", [b]),
            ("us", "paid", [c]),
        ])
        self.assertEqual(len(merged), 2)
        rec = merged["1"]
        self.assertEqual(rec["ranks"], {"us": {"free": 3}, "jp": {"free": 5}})
        self.assertEqual(rec["regions"], ["us", "jp"])

    def test_best_rank_prefers_free_over_paid(self):
        # 免费榜第 10 应优于付费榜第 1（优先级 free > paid > grossing）
        rec = {"1": {"ranks": {"us": {"paid": 1}, "gb": {"free": 10}}}}
        key = fetch_charts.best_rank_key(rec["1"]["ranks"])
        self.assertEqual(key, (0, 10))

    def test_merge_sets_best_fields(self):
        a1 = self._app("1")
        a1["rank"] = 7
        a2 = self._app("1")
        a2["rank"] = 2
        merged = fetch_charts.merge_apps([
            ("us", "grossing", [a1]),
            ("jp", "paid", [a2]),
        ])
        self.assertEqual(merged["1"]["best_chart"], "paid")
        self.assertEqual(merged["1"]["best_rank"], 2)


class TestLookup(unittest.TestCase):
    def test_chunk_ids(self):
        ids = [str(i) for i in range(450)]
        chunks = fetch_charts.chunk_ids(ids, size=200)
        self.assertEqual([len(c) for c in chunks], [200, 200, 50])

    def test_parse_lookup_fields(self):
        text = (FIXTURES / "lookup.json").read_text(encoding="utf-8")
        details = fetch_charts.parse_lookup(text)
        d = details["111111"]
        self.assertEqual(d["name"], "Example Cleaner")
        self.assertEqual(d["developer"], "Example Inc.")
        self.assertEqual(d["price"], "Free")
        self.assertEqual(d["rating"], 4.7)
        self.assertEqual(d["rating_count"], 128000)
        self.assertEqual(d["release_date"], "2026-08-01T00:00:00Z")
        # 评分缺失时保持 None/0，不抛异常
        self.assertIsNone(details["222222"]["rating"])


class TestHttpGet(unittest.TestCase):
    def _resp(self, body=b"{}"):
        m = mock.MagicMock()
        m.__enter__.return_value.read.return_value = body
        return m

    def test_success_first_try_no_retry_sleep(self):
        opener = mock.MagicMock(return_value=self._resp(b"ok"))
        sleep = mock.MagicMock()
        result = fetch_charts.http_get("http://x", opener=opener, sleep=sleep)
        self.assertEqual(result, "ok")
        opener.assert_called_once()
        sleep.assert_not_called()

    def test_retries_then_succeeds(self):
        fail = urllib.error.URLError("boom")
        opener = mock.MagicMock(side_effect=[fail, fail, self._resp(b"fine")])
        sleep = mock.MagicMock()
        result = fetch_charts.http_get("http://x", opener=opener, sleep=sleep)
        self.assertEqual(result, "fine")
        self.assertEqual(opener.call_count, 3)   # 1 + RETRY_LIMIT
        self.assertEqual(sleep.call_count, 2)
        sleep.assert_called_with(fetch_charts.RETRY_DELAY)

    def test_all_failures_return_none(self):
        opener = mock.MagicMock(side_effect=urllib.error.URLError("down"))
        sleep = mock.MagicMock()
        self.assertIsNone(fetch_charts.http_get("http://x", opener=opener, sleep=sleep))
        self.assertEqual(opener.call_count, 3)

    def test_http_exception_during_read_is_retried(self):
        # 首次 read() 抛 IncompleteRead（截断响应），第二次成功
        good = mock.MagicMock()
        good.__enter__.return_value.read.return_value = b"recovered"
        bad = mock.MagicMock()
        bad.__enter__.return_value.read.side_effect = http.client.IncompleteRead(b"par")
        opener = mock.MagicMock(side_effect=[bad, good])
        sleep = mock.MagicMock()
        result = fetch_charts.http_get("http://x", opener=opener, sleep=sleep)
        self.assertEqual(result, "recovered")
        self.assertEqual(opener.call_count, 2)
        sleep.assert_called_once()


if __name__ == "__main__":
    unittest.main()
