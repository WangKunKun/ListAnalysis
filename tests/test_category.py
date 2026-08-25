import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fetch import category


class FakeSearchAdapter:
    """测试用:search_results 按词返回;fail 词返回 None;详情查表补全。"""
    name = "fake"
    request_interval = 0

    def __init__(self, search_results=None, fail_terms=(), details=None):
        self.search_results = search_results or {}
        self.fail_terms = set(fail_terms)
        self.details = details or {}
        self.search_calls = []
        self.detail_ids = []

    def search_apps(self, term, cc, limit, sleep=None):
        self.search_calls.append((term, cc, limit))
        if term in self.fail_terms:
            return None
        return [dict(s) for s in self.search_results.get(term, [])]

    def fetch_details(self, ids, cc, sleep=None):
        self.detail_ids = list(ids)
        return {tid: dict(self.details[tid]) for tid in ids if tid in self.details}


class FakeIos(FakeSearchAdapter):
    name = "ios"


class FakePlay(FakeSearchAdapter):
    name = "play"


def _sample(tid, name="N", artist="D", details=None):
    return {"track_id": tid, "name": name, "artist": artist, "details": details}


def _details(rc=100, installs=None):
    d = {"rating_count": rc}
    if installs is not None:
        d["min_installs"] = installs
    return d


class TestMergeSamples(unittest.TestCase):
    def test_dedup_merges_source_terms_and_keeps_richer_details(self):
        by_term = {
            "pdf scanner": [_sample("1", details=_details(rc=100)),
                            _sample("2", details=_details(rc=50))],
            "ocr scan": [_sample("1", details=_details(rc=200)),
                         _sample("3", details=None)],
        }
        merged = category.merge_samples(by_term)
        by_id = {r["track_id"]: r for r in merged}
        self.assertEqual(by_id["1"]["source_terms"], ["pdf scanner", "ocr scan"])
        self.assertEqual(by_id["1"]["details"]["rating_count"], 200)  # 择优
        self.assertIsNone(by_id["3"]["details"])
        self.assertEqual(len(merged), 3)

    def test_sorted_by_installs_then_rating_count(self):
        by_term = {
            "t": [
                _sample("a", details={"rating_count": 9999}),          # 无下载量
                _sample("b", details={"min_installs": 10, "rating_count": 5}),
                _sample("c", details={"min_installs": 10, "rating_count": 99}),
                _sample("d", details=None),
            ],
        }
        merged = category.merge_samples(by_term)
        self.assertEqual([r["track_id"] for r in merged], ["c", "b", "a", "d"])


class TestRunCategory(unittest.TestCase):
    def test_writes_platform_file_and_stats(self):
        with tempfile.TemporaryDirectory() as td:
            adapter = FakeSearchAdapter(
                search_results={"a": [_sample("1", details=_details(rc=10)),
                                      _sample("2", details=_details(rc=20))],
                                "b": [_sample("3", details=None)]},
                details={"3": _details(rc=30)},
            )
            stats = category.run_category(adapter, ["a", "b"], "us", 100, Path(td))
            self.assertEqual(stats["app_count"], 3)
            self.assertEqual(stats["per_term_counts"], {"a": 2, "b": 1})
            self.assertEqual(stats["failed_terms"], [])
            self.assertFalse(stats["all_failed"])
            apps = json.loads((Path(td) / "fake.json").read_text(encoding="utf-8"))
            self.assertEqual([a["track_id"] for a in apps], ["3", "2", "1"])
            self.assertEqual(apps[0]["details"]["rating_count"], 30)  # 详情已补
            self.assertEqual(adapter.detail_ids, ["3"])               # 无详情的才补

    def test_reuse_when_file_exists(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "fake.json").write_text("[]", encoding="utf-8")
            adapter = FakeSearchAdapter()
            stats = category.run_category(adapter, ["a"], "us", 100, Path(td))
            self.assertTrue(stats["reused"])
            self.assertEqual(adapter.search_calls, [])

    def test_refresh_refetches(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "fake.json").write_text("[]", encoding="utf-8")
            adapter = FakeSearchAdapter(search_results={"a": [_sample("1")]})
            stats = category.run_category(adapter, ["a"], "us", 100, Path(td),
                                          refresh=True)
            self.assertFalse(stats.get("reused"))
            self.assertEqual(stats["app_count"], 1)

    def test_failed_terms_recorded(self):
        with tempfile.TemporaryDirectory() as td:
            adapter = FakeSearchAdapter(search_results={"ok": [_sample("1")]},
                                        fail_terms=("bad",))
            stats = category.run_category(adapter, ["bad", "ok"], "us", 100, Path(td))
            self.assertEqual(stats["failed_terms"], ["bad"])
            self.assertFalse(stats["all_failed"])

    def test_all_failed_flag(self):
        with tempfile.TemporaryDirectory() as td:
            adapter = FakeSearchAdapter(fail_terms=("a", "b"))
            stats = category.run_category(adapter, ["a", "b"], "us", 100, Path(td))
            self.assertTrue(stats["all_failed"])


class TestMain(unittest.TestCase):
    def _chdir_tmp(self):
        # LIFO 清理:先恢复 cwd 再删目录,避免 TemporaryDirectory 删 cwd 失败
        td = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, td, ignore_errors=True)
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(td)
        return Path(td)

    def test_platform_all_writes_both_files_and_meta(self):
        self._chdir_tmp()
        adapters = {"ios": FakeIos(search_results={"t": [_sample("1")]}),
                    "play": FakePlay(search_results={"t": [_sample("2")]})}
        with mock.patch.object(category, "get_adapter",
                               side_effect=lambda n: (lambda: adapters[n])):
            rc = category.main(["--terms", "t", "--slug", "s",
                                "--date", "2099-01-01"])
        self.assertEqual(rc, 0)
        data = Path("data/2099-01-01/cat-s")
        self.assertTrue((data / "ios.json").exists())
        self.assertTrue((data / "play.json").exists())
        meta = json.loads((data / "meta.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["terms"], ["t"])
        self.assertEqual(meta["country"], "us")
        self.assertEqual(sorted(meta["platforms"]), ["ios", "play"])

    def test_all_failed_exit_code_1(self):
        self._chdir_tmp()
        adapter = FakeSearchAdapter(fail_terms=("t",))
        with mock.patch.object(category, "get_adapter",
                               return_value=lambda: adapter):
            rc = category.main(["--terms", "t", "--slug", "s",
                                "--date", "2099-01-01"])
        self.assertEqual(rc, 1)

    def test_reused_platform_keeps_old_stats_in_meta(self):
        td = self._chdir_tmp()
        data = td / "data/2099-01-01/cat-s"
        data.mkdir(parents=True)
        (data / "fake.json").write_text("[]", encoding="utf-8")
        (data / "meta.json").write_text(json.dumps(
            {"terms": ["t"], "platforms": {"fake": {"app_count": 7}}}),
            encoding="utf-8")
        adapter = FakeSearchAdapter(fail_terms=())  # 复用路径不触搜索
        with mock.patch.object(category, "get_adapter",
                               return_value=lambda: adapter):
            rc = category.main(["--terms", "t", "--slug", "s",
                                "--date", "2099-01-01"])
        self.assertEqual(rc, 0)
        meta = json.loads((data / "meta.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["platforms"]["fake"]["app_count"], 7)

    def test_empty_terms_rejected(self):
        self.assertEqual(category.main(["--terms", " , ", "--slug", "s",
                                        "--date", "2099-01-01"]), 1)


if __name__ == "__main__":
    unittest.main()
