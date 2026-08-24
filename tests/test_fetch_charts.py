import http.client
import json
import unittest
import urllib.error
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import fetch_charts
from fetch.adapters import ios


FIXTURES = Path(__file__).parent / "fixtures"


class TestParseRss(unittest.TestCase):
    def test_parses_entries_with_rank(self):
        text = (FIXTURES / "rss_utilities.json").read_text(encoding="utf-8")
        apps = ios.parse_rss(text)
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
        apps = ios.parse_rss(text)
        self.assertEqual(len(apps), 1)
        self.assertEqual(apps[0]["rank"], 1)

    def test_empty_feed(self):
        self.assertEqual(ios.parse_rss('{"feed": {}}'), [])


class TestFilterUtilities(unittest.TestCase):
    def test_filters_non_utilities_and_reranks(self):
        text = (FIXTURES / "rss_mixed_genres.json").read_text(encoding="utf-8")
        apps = ios.parse_rss(text)
        kept = ios.filter_utilities(apps)
        self.assertEqual([a["track_id"] for a in kept], ["100001", "100003"])
        self.assertEqual([a["rank"] for a in kept], [1, 2])


class TestLookup(unittest.TestCase):
    def test_chunk_ids(self):
        ids = [str(i) for i in range(450)]
        chunks = ios.chunk_ids(ids, size=200)
        self.assertEqual([len(c) for c in chunks], [200, 200, 50])

    def test_parse_lookup_fields(self):
        text = (FIXTURES / "lookup.json").read_text(encoding="utf-8")
        details = ios.parse_lookup(text)
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
        result = ios.http_get("http://x", opener=opener, sleep=sleep)
        self.assertEqual(result, "ok")
        opener.assert_called_once()
        sleep.assert_not_called()

    def test_retries_then_succeeds(self):
        fail = urllib.error.URLError("boom")
        opener = mock.MagicMock(side_effect=[fail, fail, self._resp(b"fine")])
        sleep = mock.MagicMock()
        result = ios.http_get("http://x", opener=opener, sleep=sleep)
        self.assertEqual(result, "fine")
        self.assertEqual(opener.call_count, 3)   # 1 + RETRY_LIMIT
        self.assertEqual(sleep.call_count, 2)
        sleep.assert_called_with(ios.RETRY_DELAY)

    def test_all_failures_return_none(self):
        opener = mock.MagicMock(side_effect=urllib.error.URLError("down"))
        sleep = mock.MagicMock()
        self.assertIsNone(ios.http_get("http://x", opener=opener, sleep=sleep))
        self.assertEqual(opener.call_count, 3)

    def test_http_exception_during_read_is_retried(self):
        # 首次 read() 抛 IncompleteRead（截断响应），第二次成功
        good = mock.MagicMock()
        good.__enter__.return_value.read.return_value = b"recovered"
        bad = mock.MagicMock()
        bad.__enter__.return_value.read.side_effect = http.client.IncompleteRead(b"par")
        opener = mock.MagicMock(side_effect=[bad, good])
        sleep = mock.MagicMock()
        result = ios.http_get("http://x", opener=opener, sleep=sleep)
        self.assertEqual(result, "recovered")
        self.assertEqual(opener.call_count, 2)
        sleep.assert_called_once()


class TestRun(unittest.TestCase):
    RSS = (FIXTURES / "rss_utilities.json").read_text(encoding="utf-8")
    LOOKUP = (FIXTURES / "lookup.json").read_text(encoding="utf-8")

    def _run(self, td, charts=("free",), regions=("us",), refresh=False):
        cfg = {"regions": list(regions), "charts": list(charts), "top_n": 5}

        def serve(url, timeout=30):  # lookup 请求返回 LOOKUP，其余返回 RSS
            body = self.LOOKUP if "/lookup?" in url else self.RSS
            return mock.MagicMock(
                __enter__=lambda s: mock.MagicMock(read=lambda: body.encode()),
                __exit__=lambda *a: False)

        opener = mock.MagicMock(side_effect=serve)
        return fetch_charts.run(cfg, Path(td), refresh=refresh,
                                sleep=mock.MagicMock(), opener=opener), opener

    def test_writes_data_files(self):
        with TemporaryDirectory() as td:
            meta, _ = self._run(td)
            base = Path(td)
            self.assertTrue((base / "raw" / "us_free.json").exists())
            apps = json.loads((base / "apps.json").read_text(encoding="utf-8"))
            self.assertIsInstance(apps, list)
            self.assertEqual(apps[0]["track_id"], "111111")
            self.assertIn("description", apps[0]["details"])  # lookup 详情已合并
            meta_disk = json.loads((base / "meta.json").read_text(encoding="utf-8"))
            self.assertEqual(meta_disk["app_count"], len(apps))
            self.assertEqual(meta_disk["skipped"], [])

    def test_skips_when_data_exists_unless_refresh(self):
        with TemporaryDirectory() as td:
            self._run(td)
            meta, opener = self._run(td)                    # 第二次：应复用
            self.assertIn("reused", meta)
            self.assertEqual(opener.call_count, 0)

    def test_failed_chart_recorded_in_skipped(self):
        with TemporaryDirectory() as td:
            cfg = {"regions": ["us"], "charts": ["free"], "top_n": 5}
            opener = mock.MagicMock(side_effect=urllib.error.URLError("net down"))
            meta = fetch_charts.run(cfg, Path(td), refresh=False,
                                    sleep=mock.MagicMock(), opener=opener)
            self.assertEqual(meta["skipped"], ["us_free"])
            self.assertTrue(meta.get("all_failed"))

    def test_main_exit_codes(self):
        cfg_path = Path("config.json")  # 项目根存在，仅用于参数解析
        with mock.patch.object(fetch_charts, "load_config",
                               return_value={"regions": [], "charts": [], "top_n": 5}), \
             mock.patch.object(fetch_charts, "run",
                               return_value={"all_failed": True}) as m_run:
            rc = fetch_charts.main(["--config", str(cfg_path), "--date", "2099-01-01"])
            self.assertEqual(rc, 1)
            self.assertEqual(m_run.call_args.kwargs.get("refresh"), False)
        with mock.patch.object(fetch_charts, "load_config",
                               return_value={"regions": [], "charts": [], "top_n": 5}), \
             mock.patch.object(fetch_charts, "run", return_value={}):
            rc = fetch_charts.main(["--config", str(cfg_path), "--date", "2099-01-01",
                                    "--refresh"])
            self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
