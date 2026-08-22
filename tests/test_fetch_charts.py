import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

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


if __name__ == "__main__":
    unittest.main()
