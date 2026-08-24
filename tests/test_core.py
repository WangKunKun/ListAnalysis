import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

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


class FakeAdapter:
    """测试用适配器：单榜单返回固定 apps，详情查表。支持无参构造（main 用）。"""
    name = "fake"
    request_interval = 0

    def __init__(self, chart_apps=None, details=None, fail=()):
        self.chart_apps = chart_apps or []
        self.details = details or {}
        self.fail = set(fail)
        self.chart_calls = []
        self.detail_ids = []

    def fetch_chart(self, cc, chart, top_n, sleep=None):
        self.chart_calls.append((cc, chart, top_n))
        if f"{cc}_{chart}" in self.fail:
            return None
        return [dict(a) for a in self.chart_apps]

    def fetch_details(self, ids, cc, sleep=None):
        self.detail_ids = list(ids)
        return {tid: dict(self.details[tid]) for tid in ids if tid in self.details}


def _fake_apps():
    return [
        {"track_id": "1", "name": "Cleaner", "artist": "Dev A",
         "genre_id": "6002", "rank": 1},
        {"track_id": "2", "name": "VPN", "artist": "Dev B",
         "genre_id": "6002", "rank": 2},
    ]


def _fake_details():
    return {
        "1": {"name": "Cleaner", "developer": "Dev A", "description": "clean it",
              "rating": 4.5, "rating_count": 100, "price": "Free",
              "genres": ["Utilities"], "release_date": "2026-01-01",
              "track_view_url": "https://example.com/1"},
        "2": {"name": "VPN", "developer": "Dev B", "description": "fast vpn",
              "rating": 4.0, "rating_count": 50, "price": "Free",
              "genres": ["Utilities"], "release_date": "2026-02-02",
              "track_view_url": "https://example.com/2"},
    }


class TestRun(unittest.TestCase):
    def _run(self, td, refresh=False, fail=(), detail_top_n=None):
        adapter = FakeAdapter(_fake_apps(), _fake_details(), fail=fail)
        cfg = {"regions": ["us"], "charts": ["free"], "top_n": 5,
               "detail_top_n": detail_top_n}
        return core.run(adapter, cfg, Path(td), refresh=refresh,
                        sleep=mock.MagicMock()), adapter

    def test_writes_data_files_with_platform_layout(self):
        with TemporaryDirectory() as td:
            base = Path(td)           # 直接把 td 当 data/{date}/{platform}
            meta, _ = self._run(td)
            self.assertTrue((base / "raw" / "us_free.json").exists())
            apps = json.loads((base / "apps.json").read_text(encoding="utf-8"))
            self.assertEqual(apps[0]["track_id"], "1")
            self.assertIn("description", apps[0]["details"])
            meta_disk = json.loads((base / "meta.json").read_text(encoding="utf-8"))
            self.assertEqual(meta_disk["platform"], "fake")
            self.assertEqual(meta_disk["app_count"], len(apps))
            self.assertEqual(meta_disk["skipped"], [])
            self.assertIn("detail_top_n", meta_disk)

    def test_detail_top_n_limits_detail_fetch(self):
        with TemporaryDirectory() as td:
            _, adapter = self._run(td, detail_top_n=1)
            self.assertEqual(adapter.detail_ids, ["1"])  # 只有最佳排名第 1

    def test_skips_when_data_exists_unless_refresh(self):
        with TemporaryDirectory() as td:
            # 同一 adapter 复跑：第二次应复用落盘数据，不再抓取
            adapter = FakeAdapter(_fake_apps(), _fake_details())
            cfg = {"regions": ["us"], "charts": ["free"], "top_n": 5}
            core.run(adapter, cfg, Path(td), sleep=mock.MagicMock())
            meta = core.run(adapter, cfg, Path(td), sleep=mock.MagicMock())
            self.assertIn("reused", meta)
            self.assertEqual(len(adapter.chart_calls), 1)

    def test_failed_chart_recorded_in_skipped(self):
        with TemporaryDirectory() as td:
            meta, _ = self._run(td, fail=("us_free",))
            self.assertEqual(meta["skipped"], ["us_free"])
            self.assertTrue(meta.get("all_failed"))

    def test_detail_top_n_zero_means_no_details(self):
        with TemporaryDirectory() as td:
            adapter = FakeAdapter(_fake_apps(), _fake_details())
            cfg = {"regions": ["us"], "charts": ["free"], "top_n": 5,
                   "detail_top_n": 0}
            meta = core.run(adapter, cfg, Path(td), sleep=mock.MagicMock())
            self.assertEqual(adapter.detail_ids, [])   # 0 = 不拉详情
            self.assertEqual(meta["detail_top_n"], 0)

    def test_consecutive_failures_abort_remaining(self):
        with TemporaryDirectory() as td:
            # 全部榜单失败的 FakeAdapter，regions 2×charts 3：第 5 个失败后剩余全部进 skipped
            adapter = FakeAdapter(_fake_apps(), _fake_details(),
                                  fail=("us_free", "us_paid", "us_grossing",
                                        "gb_free", "gb_paid", "gb_grossing"))
            cfg = {"regions": ["us", "gb"], "charts": ["free", "paid", "grossing"],
                   "top_n": 5}
            meta = core.run(adapter, cfg, Path(td), sleep=mock.MagicMock())
            self.assertEqual(meta["skipped"],
                             ["us_free", "us_paid", "us_grossing",
                              "gb_free", "gb_paid", "gb_grossing"])
            self.assertTrue(meta["all_failed"])
            # 第 5 个失败后放弃，第 6 个榜单不再实际请求
            self.assertEqual(len(adapter.chart_calls), 5)

    def test_success_resets_consecutive_counter(self):
        with TemporaryDirectory() as td:
            # 4 连败后成功，计数清零，不触发放弃；共 6 榜，前 4 失败第 5 成功第 6 失败
            adapter = FakeAdapter(_fake_apps(), _fake_details(),
                                  fail=("us_free", "us_paid", "us_grossing", "gb_free",
                                        "gb_grossing"))
            cfg = {"regions": ["us", "gb"], "charts": ["free", "paid", "grossing"],
                   "top_n": 5}
            meta = core.run(adapter, cfg, Path(td), sleep=mock.MagicMock())
            self.assertEqual(meta["skipped"],
                             ["us_free", "us_paid", "us_grossing", "gb_free",
                              "gb_grossing"])
            self.assertEqual(meta["app_count"], 2)  # gb_paid 成功产出
            self.assertFalse(meta["all_failed"])


class TestMain(unittest.TestCase):
    def test_exit_code_all_failed_and_platform_dir(self):
        with mock.patch.object(core, "load_config",
                               return_value={"regions": [], "charts": [], "top_n": 5}), \
             mock.patch.object(core, "get_adapter", return_value=FakeAdapter), \
             mock.patch.object(core, "run",
                               return_value={"all_failed": True}) as m_run:
            rc = core.main(["--date", "2099-01-01"])
            self.assertEqual(rc, 1)
            self.assertEqual(m_run.call_args.args[2], Path("data/2099-01-01/ios"))
            self.assertEqual(m_run.call_args.kwargs.get("refresh"), False)

    def test_platform_arg_selects_dir_and_adapter(self):
        calls = []

        class RecordingAdapter(FakeAdapter):
            def __init__(self, *a, **k):
                super().__init__(*a, **k)
                calls.append(self.name)

        with mock.patch.object(core, "load_config",
                               return_value={"regions": [], "charts": [], "top_n": 5}), \
             mock.patch.object(core, "get_adapter", return_value=RecordingAdapter), \
             mock.patch.object(core, "run", return_value={}):
            rc = core.main(["--date", "2099-01-01", "--platform", "all"])
            self.assertEqual(rc, 0)
            self.assertEqual(len(calls), 2)  # ios + play 各跑一遍

    def test_play_defaults_detail_top_n(self):
        cfg_holder = {}

        def fake_run(adapter, cfg, data_dir, refresh=False, sleep=None):
            cfg_holder[data_dir.parent.name + "/" + data_dir.name] = dict(cfg)
            return {}

        with mock.patch.object(core, "load_config",
                               return_value={"regions": [], "charts": [], "top_n": 5}), \
             mock.patch.object(core, "get_adapter", return_value=FakeAdapter), \
             mock.patch.object(core, "run", side_effect=fake_run):
            core.main(["--date", "2099-01-01", "--platform", "play"])
            self.assertEqual(cfg_holder["2099-01-01/play"]["detail_top_n"], 150)

    def test_platform_all_continues_when_play_fails(self):
        # play 适配器缺失/初始化失败时,all 模式 iOS 仍执行且 rc=1
        ran = []

        def boom(name):
            def _cls():
                if name == "play":
                    raise ModuleNotFoundError("no module play")
                a = FakeAdapter()
                a.name = name
                return a
            return _cls

        with mock.patch.object(core, "load_config",
                               return_value={"regions": [], "charts": [], "top_n": 5}), \
             mock.patch.object(core, "get_adapter",
                               side_effect=lambda n: boom(n)), \
             mock.patch.object(core, "run",
                               side_effect=lambda a, c, d, **k: ran.append(a.name) or {}):
            rc = core.main(["--date", "2099-01-01", "--platform", "all"])
            self.assertEqual(rc, 1)
            self.assertEqual(ran, ["ios"])   # play 失败被跳过,iOS 照跑

    def test_platform_subconfig_invalid_charts_rejected(self):
        import os
        path = self._bad_cfg()
        self.addCleanup(os.unlink, path)
        with mock.patch.object(core, "get_adapter", return_value=FakeAdapter), \
             mock.patch.object(core, "run", return_value={}) as m_run:
            rc = core.main(["--date", "2099-01-01", "--platform", "play", "--config",
                            path])
            self.assertEqual(rc, 1)
            m_run.assert_not_called()        # 配置错误不进入抓取

    @staticmethod
    def _bad_cfg():
        from tempfile import NamedTemporaryFile
        f = NamedTemporaryFile("w", suffix=".json", delete=False)
        f.write('{"charts": ["free"], "play": {"charts": ["bogus"]}}')
        f.close()
        return f.name


if __name__ == "__main__":
    unittest.main()
