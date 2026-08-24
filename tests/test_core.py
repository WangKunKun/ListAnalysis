import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fetch import core


class TestLoadConfig(unittest.TestCase):
    def test_missing_file_returns_defaults(self):
        cfg = core.load_config(Path("/nonexistent/config.json"))
        self.assertEqual(cfg["regions"], core.DEFAULT_CONFIG["regions"])
        self.assertEqual(cfg["top_n"], 50)

    def test_user_config_overrides_defaults(self):
        with TemporaryDirectory() as td:
            p = Path(td) / "config.json"
            p.write_text('{"top_n": 100, "regions": ["us"], "play": {"top_n": 30}}',
                         encoding="utf-8")
            cfg = core.load_config(p)
            self.assertEqual(cfg["top_n"], 100)
            self.assertEqual(cfg["regions"], ["us"])
            self.assertEqual(cfg["charts"], core.DEFAULT_CONFIG["charts"])
            self.assertEqual(cfg["play"], {"top_n": 30})  # 平台子字典原样保留

    def test_invalid_chart_key_raises(self):
        with TemporaryDirectory() as td:
            p = Path(td) / "config.json"
            p.write_text('{"charts": ["free", "bogus"]}', encoding="utf-8")
            with self.assertRaises(ValueError):
                core.load_config(p)


class TestMergeApps(unittest.TestCase):
    def _app(self, tid, name="N", artist="D"):
        return {"track_id": tid, "name": name, "artist": artist,
                "genre_id": "6002", "rank": 1}

    def test_dedup_and_rank_merge(self):
        a = self._app("1", "Cleaner"); a["rank"] = 3
        b = self._app("1", "Cleaner"); b["rank"] = 5
        c = self._app("2", "VPN")
        merged = core.merge_apps([
            ("us", "free", [a]), ("jp", "free", [b]), ("us", "paid", [c]),
        ])
        self.assertEqual(len(merged), 2)
        rec = merged["1"]
        self.assertEqual(rec["ranks"], {"us": {"free": 3}, "jp": {"free": 5}})
        self.assertEqual(rec["regions"], ["us", "jp"])

    def test_best_rank_prefers_free_over_paid(self):
        rec = {"1": {"ranks": {"us": {"paid": 1}, "gb": {"free": 10}}}}
        self.assertEqual(core.best_rank_key(rec["1"]["ranks"]), (0, 10))

    def test_merge_sets_best_fields(self):
        a1 = self._app("1"); a1["rank"] = 7
        a2 = self._app("1"); a2["rank"] = 2
        merged = core.merge_apps([("us", "grossing", [a1]), ("jp", "paid", [a2])])
        self.assertEqual(merged["1"]["best_chart"], "paid")
        self.assertEqual(merged["1"]["best_rank"], 2)


if __name__ == "__main__":
    unittest.main()
