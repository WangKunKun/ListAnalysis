# 品类竞品与痛点分析 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增任意品类的双平台竞品与痛点分析:适配器品类搜索 → `fetch.category` CLI → `/cat-scan` skill 产出中文报告。

**Architecture:** 沿用"抓取层确定性 Python、分析层 AI skill"模式。适配器各加 `search_apps()`(iOS 走 iTunes Search API 纯标准库;Play 走 Node 桥新增 `search` 命令);新 `fetch/category.py` 做多关键词合并去重与落盘;skill 负责关键词生成、品类归属语义过滤、评论抓取与报告。

**Tech Stack:** Python 3 标准库(unittest)、Node(google-play-scraper@10 + hpagent,got@11 不读代理环境变量故桥需显式传 agent)。

**设计文档:** `docs/superpowers/specs/2026-08-25-category-analysis-design.md`

**已验证的技术事实(勿再怀疑):**
- iTunes Search API `https://itunes.apple.com/search?term=...&country=us&entity=software&limit=100` 直连可用,响应 `{resultCount, results:[...]}`,results 元素字段与 lookup 完全一致(trackId/trackName/sellerName/description/genres/formattedPrice/averageUserRating/userRatingCount/currentVersionReleaseDate/trackViewUrl)→ **`parse_lookup` 可直接复用解析 search 响应**
- google-play-scraper `search({term, num, country, lang, requestOptions})` 返回 `[{appId, title, developer, score, free, price, ...}]`(**无 genreId,无描述**——详情需再走现有 `apps` 命令)
- 当前网络直连 play.google.com 被 ECONNRESET;`HTTPS_PROXY` 环境变量对 got@11 **无效**,必须 `requestOptions: {agent: {https: new HttpsProxyAgent({proxy})}}`(hpagent,got 官方推荐,已 `npm install`,package.json 已更新但未提交)
- 本地代理可用:`http://127.0.0.1:7890`

**测试命令:** `python3 -m unittest tests.test_xxx -v`(单文件)或 `python3 -m unittest discover tests -v`(全量)

---

### Task 1: iOS 适配器 `search_apps`

**Files:**
- Create: `tests/fixtures/ios_search.json`
- Modify: `fetch/adapters/ios.py`(加 `SEARCH_URL` 常量 + `IosAdapter.search_apps` 方法)
- Modify: `tests/test_adapter_ios.py`(文件末尾 `if __name__` 前加 `TestSearchApps` 类)

- [ ] **Step 1: 写失败测试与 fixture**

先建 fixture `tests/fixtures/ios_search.json`(真实 API 响应结构;第二条故意缺 description/genres 等字段验证容忍):

```json
{
  "resultCount": 2,
  "results": [
    {
      "trackId": 1199564834,
      "trackName": "Adobe Scan: PDF & OCR Scanner",
      "sellerName": "Adobe Inc.",
      "description": "Adobe Scan is an intelligent document scanner.",
      "genres": ["Business", "Productivity"],
      "formattedPrice": "Free",
      "averageUserRating": 4.87,
      "userRatingCount": 1581517,
      "currentVersionReleaseDate": "2026-08-12T19:10:18Z",
      "trackViewUrl": "https://apps.apple.com/us/app/adobe-scan/id1199564834?uo=4"
    },
    {
      "trackId": 595628518,
      "trackName": "Scanner App: PDF Document Scan",
      "sellerName": "Example Dev",
      "formattedPrice": "Free",
      "averageUserRating": null,
      "userRatingCount": 0
    }
  ]
}
```

再在 `tests/test_adapter_ios.py` 的 `if __name__ == "__main__":` 之前加:

```python
class TestSearchApps(unittest.TestCase):
    def _opener(self, body):
        m = mock.MagicMock()
        m.__enter__.return_value.read.return_value = body
        return mock.MagicMock(return_value=m)

    def test_search_apps_parses_and_builds_url(self):
        text = (FIXTURES / "ios_search.json").read_text(encoding="utf-8").encode()
        opener = self._opener(text)
        a = fetch_charts.IosAdapter(opener=opener)
        apps = a.search_apps("pdf scanner", "us", 100, sleep=mock.MagicMock())
        self.assertEqual(len(apps), 2)
        self.assertEqual(apps[0]["track_id"], "1199564834")
        self.assertEqual(apps[0]["name"], "Adobe Scan: PDF & OCR Scanner")
        self.assertEqual(apps[0]["artist"], "Adobe Inc.")
        self.assertEqual(apps[0]["details"]["rating_count"], 1581517)
        self.assertIsNone(apps[1]["details"]["rating"])  # 缺评分容忍为 None
        url = opener.call_args.args[0]
        self.assertIn("term=pdf%20scanner", url)
        self.assertIn("country=us", url)
        self.assertIn("limit=100", url)
        self.assertIn("entity=software", url)

    def test_search_apps_empty_results_returns_empty_list(self):
        opener = self._opener(b'{"resultCount": 0, "results": []}')
        a = fetch_charts.IosAdapter(opener=opener)
        self.assertEqual(a.search_apps("x", "us", 10, sleep=mock.MagicMock()), [])

    def test_search_apps_http_fail_returns_none(self):
        opener = mock.MagicMock(side_effect=urllib.error.URLError("down"))
        a = fetch_charts.IosAdapter(opener=opener)
        self.assertIsNone(a.search_apps("x", "us", 10, sleep=mock.MagicMock()))
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m unittest tests.test_adapter_ios.TestSearchApps -v`
Expected: FAIL/ERROR,`AttributeError: 'IosAdapter' object has no attribute 'search_apps'`

- [ ] **Step 3: 实现**

`fetch/adapters/ios.py` 顶部常量区(LOOKUP_URL 之后)加:

```python
SEARCH_URL = "https://itunes.apple.com/search?term={term}&country={cc}&entity=software&limit={limit}"
```

文件顶部 import 区加 `from urllib.parse import quote`。

`IosAdapter` 类内(`fetch_details` 方法之后)加:

```python
    def search_apps(self, term, cc, limit, sleep=time.sleep):
        """关键词搜索品类样本。Search API 响应与 lookup 同构,
        复用 parse_lookup 解析,详情一次到位(无需再调 lookup)。"""
        url = SEARCH_URL.format(term=quote(term), cc=cc, limit=limit)
        text = http_get(url, opener=self._opener, sleep=sleep)
        if text is None:
            return None
        details = parse_lookup(text)
        return [{"track_id": tid, "name": d["name"], "artist": d["developer"],
                 "details": d} for tid, d in details.items()]
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m unittest tests.test_adapter_ios -v`
Expected: 全部 PASS(原有用例 + 3 个新用例)

- [ ] **Step 5: 提交**

```bash
git add tests/fixtures/ios_search.json tests/test_adapter_ios.py fetch/adapters/ios.py
git commit -m "feat: iOS 适配器品类搜索 search_apps"
```

---

### Task 2: Node 桥代理支持 + `search` 命令

**Files:**
- Modify: `scripts/play_bridge.mjs`(读 PLAY_PROXY/HTTPS_PROXY 构造 hpagent;三命令统一传 `requestOptions`;新增 `search` 分支)
- Modify: `package.json` / `package-lock.json`(hpagent 依赖——`npm install hpagent` 已执行,文件已改,只需提交)
- Modify: `tests/test_play_bridge.py`(加 1 个不依赖外网的 search 注册用例)

- [ ] **Step 1: 写失败测试**

`tests/test_play_bridge.py` 顶部 import 区改为(加 `os`):

```python
import json
import os
import subprocess
import unittest
from pathlib import Path
```

`TestPlayBridge` 类内加:

```python
    def test_search_command_registered_and_proxy_applied(self):
        # PLAY_PROXY 指向立即拒绝连接的端口:若 search 未注册会报"未知指令";
        # 已注册则报网络错误——证明命令分发与代理路径都被执行,且不依赖外网
        env = {**os.environ, "PLAY_PROXY": "http://127.0.0.1:1"}
        proc = subprocess.run(
            ["node", str(BRIDGE)], input=json.dumps(
                {"cmd": "search", "term": "x", "num": 5,
                 "country": "us", "lang": "en"}),
            capture_output=True, text=True, timeout=60, env=env)
        self.assertEqual(proc.returncode, 1)
        self.assertNotIn("未知指令", proc.stderr)
        self.assertTrue(proc.stderr.strip())
```

同时 `test_play_bridge.py` 顶部 import 区改为:

```python
import json
import os
import subprocess
import unittest
from pathlib import Path
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m unittest tests.test_play_bridge -v`
Expected: 新用例 FAIL,stderr 含 `未知指令: search`

- [ ] **Step 3: 实现桥**

`scripts/play_bridge.mjs` 中 `const sleep = ...` 行之后、`async function main()` 之前加:

```js
// 代理支持:got@11 不读代理环境变量,须显式传 agent。
// PLAY_PROXY 优先于 HTTPS_PROXY;未设置时 requestOpts 为空对象(行为与旧版一致)
let requestOpts = {};
const proxyUrl = process.env.PLAY_PROXY || process.env.HTTPS_PROXY || "";
if (proxyUrl) {
  try {
    const { HttpsProxyAgent } = require("hpagent");
    requestOpts = { agent: { https: new HttpsProxyAgent({ proxy: proxyUrl }) } };
  } catch {
    console.error("代理配置失败: hpagent 未安装,请在项目根运行 npm install");
    process.exit(3);
  }
}
```

`main()` 内命令分发改为(原 `list`/`apps` 分支加 `requestOptions`,`else` 前插 `search`):

```js
  if (cmd === "list") {
    const apps = await gplay.list({ ...opts, requestOptions: requestOpts });
    process.stdout.write(JSON.stringify(apps));
  } else if (cmd === "apps") {
    const { ids, country, lang } = opts;
    const out = {};
    for (const id of ids) {
      try {
        out[id] = await gplay.app({ appId: id, country, lang,
                                    requestOptions: requestOpts });
      } catch {
        out[id] = null; // 单 app 失败容忍
      }
      await sleep(300);
    }
    process.stdout.write(JSON.stringify(out));
  } else if (cmd === "search") {
    const results = await gplay.search({ ...opts, requestOptions: requestOpts });
    process.stdout.write(JSON.stringify(results));
  } else {
    console.error(`未知指令: ${cmd}`);
    process.exit(1);
  }
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m unittest tests.test_play_bridge -v`
Expected: 全部 PASS

- [ ] **Step 5: 手动冒烟(带代理真实搜索)**

```bash
echo '{"cmd":"search","term":"pdf scanner","num":3,"country":"us","lang":"en"}' \
  | PLAY_PROXY=http://127.0.0.1:7890 node scripts/play_bridge.mjs | head -c 300
```
Expected: JSON 数组开头,首项含 `"appId":"com.adobe.scan.android"`。若代理端口不通,换可用代理再试;此步失败不阻塞提交(单测已覆盖分支),但必须记录原因。

- [ ] **Step 6: 提交(含 hpagent 依赖)**

```bash
git add scripts/play_bridge.mjs tests/test_play_bridge.py package.json package-lock.json
git commit -m "feat: Play 桥新增 search 命令与 PLAY_PROXY 代理支持"
```

---

### Task 3: Play 适配器 `search_apps`

**Files:**
- Create: `tests/fixtures/play_search.json`
- Modify: `fetch/adapters/play.py`(加 `normalize_search` 函数 + `PlayAdapter.search_apps` 方法)
- Modify: `tests/test_adapter_play.py`(加 `TestNormalizeSearch` 类;`TestPlayAdapter` 类内加 3 个方法)

- [ ] **Step 1: 写失败测试与 fixture**

fixture `tests/fixtures/play_search.json`(真实 search 返回结构精简):

```json
[
  {"appId": "com.adobe.scan.android", "title": "Adobe Scan AI PDF Scanner, OCR",
   "developer": "Adobe", "score": 4.63, "free": true, "price": 0},
  {"appId": "com.example.docscan", "title": "DocScan - PDF Scanner",
   "developer": "Example Ltd", "score": 4.5, "free": true, "price": 0}
]
```

`tests/test_adapter_play.py` 的 `if __name__` 前加:

```python
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
```

`TestPlayAdapter` 类内(末尾方法后)加:

```python
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m unittest tests.test_adapter_play -v`
Expected: ERROR/FAIL,`AttributeError: module 'fetch.adapters.play' has no attribute 'normalize_search'`

- [ ] **Step 3: 实现**

`fetch/adapters/play.py` 中 `normalize_app` 函数之后加:

```python
def normalize_search(raw: list) -> list[dict]:
    """gplay.search 返回 → 统一样本元素(无详情;详情由 fetch_details 补)。"""
    return [{
        "track_id": r.get("appId", ""),
        "name": r.get("title", ""),
        "artist": r.get("developer", ""),
    } for r in raw]
```

`PlayAdapter` 类内(`fetch_details` 之后)加(重试/超时语义与 `fetch_chart` 一致):

```python
    def search_apps(self, term, cc, limit, sleep=time.sleep, bridge_fn=None):
        bridge = bridge_fn or _run_bridge
        last_exc = None
        for attempt in range(1 + RETRY_LIMIT):
            try:
                raw = bridge({"cmd": "search", "term": term, "num": limit,
                              "country": cc, "lang": "en"},
                             runner=self._runner)
                if raw is None:
                    raise RuntimeError("bridge returned None")
                return normalize_search(raw)
            except subprocess.TimeoutExpired:
                print(f"  桥接超时（放弃该词，不重试）: play search {term}", flush=True)
                return None
            except KeyError:
                raise
            except Exception as exc:
                last_exc = exc
                if attempt < RETRY_LIMIT:
                    sleep(RETRY_DELAY)
        print(f"  搜索失败（已重试 {RETRY_LIMIT} 次）: play {term} ({last_exc})",
              flush=True)
        return None
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m unittest tests.test_adapter_play -v`
Expected: 全部 PASS

- [ ] **Step 5: 提交**

```bash
git add tests/fixtures/play_search.json tests/test_adapter_play.py fetch/adapters/play.py
git commit -m "feat: Play 适配器品类搜索 search_apps"
```

---

### Task 4: `fetch/category.py` 合并去重 + CLI

**Files:**
- Create: `fetch/category.py`
- Create: `tests/test_category.py`

- [ ] **Step 1: 写失败测试(纯函数部分)**

`tests/test_category.py` 全文:

```python
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m unittest tests.test_category -v`
Expected: ERROR,`ModuleNotFoundError: No module named 'fetch.category'`

- [ ] **Step 3: 实现 `fetch/category.py` 全文**

```python
"""品类搜索抓取：多关键词搜索、合并去重、详情补全、落盘、CLI。

与 fetch.charts(榜单)平行的第二条取数管线；品类语义判断不在本层。
"""

import argparse
import json
import time
from datetime import date as _date
from pathlib import Path

from fetch.adapters import get_adapter

__all__ = ["merge_samples", "run_category", "main"]


def _detail_rank(details) -> tuple:
    """详情质量排序键:(min_installs, rating_count),缺失为 0。"""
    d = details or {}
    return (d.get("min_installs") or 0, d.get("rating_count") or 0)


def _better_details(a, b):
    """两条详情择优(下载量与评分量综合更高者)。"""
    return a if _detail_rank(a) >= _detail_rank(b) else b


def _sort_samples(samples: list) -> list:
    """就地排序:下载量(ios 无此键恒 0)→ 评分量,降序。"""
    samples.sort(key=lambda r: _detail_rank(r.get("details")), reverse=True)
    return samples


def merge_samples(samples_by_term) -> list:
    """{term: [sample,...]} → 去重合并并排序的样本列表。

    同 track_id:name/artist 取首见,source_terms 累积,详情择优。
    排序键见 _sort_samples;详情补全后需再排(run_category 负责)。
    """
    merged = {}
    for term, samples in samples_by_term.items():
        for s in samples:
            tid = s["track_id"]
            rec = merged.setdefault(tid, {
                "track_id": tid,
                "name": s.get("name", ""),
                "artist": s.get("artist", ""),
                "source_terms": [],
                "details": None,
            })
            if term not in rec["source_terms"]:
                rec["source_terms"].append(term)
            rec["details"] = _better_details(rec["details"], s.get("details"))
    return _sort_samples(list(merged.values()))


def run_category(adapter, terms, country, limit, data_dir, refresh=False) -> dict:
    """单平台:逐词搜索 → 合并去重 → (需要时)补详情 → 落盘 {platform}.json。

    iOS 的 search 响应自带详情;Play 搜索无详情,对缺详情的样本补拉。
    返回平台统计;文件已存在且非 refresh 时返回 {"reused": True}。
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    platform = adapter.name
    apps_path = data_dir / f"{platform}.json"
    if apps_path.exists() and not refresh:
        return {"reused": True, "platform": platform}

    samples_by_term, failed = {}, []
    for term in terms:
        if samples_by_term or failed:
            time.sleep(adapter.request_interval)  # 词间隔节流
        apps = adapter.search_apps(term, country, limit)
        if apps is None:
            failed.append(term)
            continue
        samples_by_term[term] = apps

    merged = merge_samples(samples_by_term)

    # Play 搜索结果无详情(iOS 恒有):只对缺详情的样本补拉,补完重排
    # (合并时的排序对无详情样本无效,须以补全后的数据定序)
    missing = [r["track_id"] for r in merged if not r.get("details")]
    if missing:
        by_id = {r["track_id"]: r for r in merged}
        for tid, detail in adapter.fetch_details(missing, country).items():
            by_id[tid]["details"] = detail
        merged = _sort_samples(merged)

    apps_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    return {
        "platform": platform,
        "app_count": len(merged),
        "per_term_counts": {t: len(v) for t, v in samples_by_term.items()},
        "failed_terms": failed,
        "all_failed": not samples_by_term,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--terms", required=True, help="逗号分隔英文关键词")
    parser.add_argument("--slug", required=True, help="目录与报告名标识(kebab-case)")
    parser.add_argument("--platform", default="all",
                        choices=["ios", "play", "all"])
    parser.add_argument("--date", default=_date.today().strftime("%Y-%m-%d"))
    parser.add_argument("--country", default="us")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args(argv)

    terms = [t.strip() for t in args.terms.split(",") if t.strip()]
    if not terms:
        print("错误: --terms 不能为空", flush=True)
        return 1

    data_dir = Path("data") / args.date / f"cat-{args.slug}"
    platforms = ["ios", "play"] if args.platform == "all" else [args.platform]
    rc = 0
    stats = {}
    for p in platforms:
        try:
            adapter = get_adapter(p)()
        except SystemExit:
            raise  # 依赖缺失等明确退出场景：原样传播退出码
        except Exception as exc:
            print(f"平台 {p} 初始化失败: {exc}", flush=True)
            rc = 1
            continue
        result = run_category(adapter, terms, args.country, args.limit,
                              data_dir, refresh=args.refresh)
        stats[p] = result
        if result.get("all_failed"):
            print(f"平台 {p} 全部关键词搜索失败（检查网络/代理）", flush=True)
            rc = 1

    # 复用的平台沿用旧 meta 里的统计，避免覆盖丢失
    meta_path = data_dir / "meta.json"
    old_platforms = {}
    if meta_path.exists():
        try:
            old_platforms = json.loads(
                meta_path.read_text(encoding="utf-8")).get("platforms", {})
        except (json.JSONDecodeError, ValueError):
            old_platforms = {}
    for p, r in stats.items():
        if r.get("reused") and p in old_platforms:
            stats[p] = old_platforms[p]

    meta = {"date": args.date, "slug": args.slug, "terms": terms,
            "country": args.country, "limit": args.limit, "platforms": stats}
    data_dir.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    for p, r in stats.items():
        if not r.get("reused"):
            print(f"完成[{p}]: {r.get('app_count', 0)} 个样本"
                  f"（失败关键词 {len(r.get('failed_terms', []))} 个）", flush=True)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
```

注意:`time.sleep` 直接调用(与 adapters 一致,不做注入);测试 FakeSearchAdapter 的 `request_interval = 0` 使词间隔零等待。

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m unittest tests.test_category -v`
Expected: 全部 PASS

- [ ] **Step 5: 全量回归**

Run: `python3 -m unittest discover tests -v`
Expected: 全部 PASS

- [ ] **Step 6: 提交**

```bash
git add fetch/category.py tests/test_category.py
git commit -m "feat: 品类搜索管线 fetch.category(多词合并/详情补全/CLI)"
```

---

### Task 5: `/cat-scan` skill

**Files:**
- Create: `.claude/skills/cat-scan/SKILL.md`

- [ ] **Step 1: 写 SKILL.md 全文**

```markdown
---
name: cat-scan
description: 对任意品类(如 PDF 扫描、二维码生成)做双平台竞品与痛点分析,产出中文报告。用法:/cat-scan <品类描述> [light|standard] [--refresh]。触发词:品类分析、竞品分析、行业痛点、品类扫描。
---

# 品类竞品与痛点分析

对指定品类做 iOS + Google Play 双平台分析:关键词搜索圈样本、榜单交叉标注、
头部 app 评论深挖,产出竞争格局/功能矩阵/用户痛点/机会点报告。
设计文档:docs/superpowers/specs/2026-08-25-category-analysis-design.md

## 参数解析

从用户输入解析:品类描述(自由文本,必填);模式 light(不抓评论)/
standard(默认,头部 10 个抓评论);--refresh(强制重抓)。

## 流程

1. **生成关键词**:把品类描述译成 3-5 个英文搜索关键词(含功能变体,
   如 PDF 扫描 → pdf scanner / document scanner / cam scanner / ocr scanner),
   并生成 kebab-case slug(如 pdf-scanner)。
2. **抓样本**(工作目录项目根):
   `python3 -m fetch.category --terms "kw1,kw2,..." --slug {slug} --platform all [--refresh]`
   - Play 超时/ECONNRESET → 网络需代理:`export PLAY_PROXY=http://127.0.0.1:7890`
     (或可用 HTTPS_PROXY)后重跑;iOS 直连无需代理。
   - 退出码非 0 → 向用户报告错误并停止。
   - 落盘:`data/{日期}/cat-{slug}/{ios|play}.json`(含 source_terms 与 details)
     与 `meta.json`(terms/country/per_term_counts/failed_terms)。
3. **交叉标注**:取最近一期 `data/{最新日期}/{ios|play}/apps.json`(当天没有
   往前找,最多回溯 7 天;没有 → 纯搜索样本并在报告注明"无榜单交叉数据")。
   把榜内属于该品类的 app 按 track_id 与搜索样本合并,标注上榜情况/最好名次/
   区域覆盖(榜单数据格式见 app-scan skill)。
4. **归属过滤与头部圈定**(语义判断,本 skill 核心职责):
   - 剔除搜索噪声:名字带关键词但不属于品类的(如"二维码生成"里的扫码器、
     收款机;PDF 工具里的阅读器/签名器按目标品类判断去留)。
   - 过滤后样本 < 5 → 告知用户样本过少、给出建议关键词,停止。
   - 头部排序:上榜优先(榜单位置),未上榜按评分量/下载量。standard 模式
     取头部 10 个抓评论:
     - ios:WebFetch 抓
       `https://itunes.apple.com/us/rss/customerreviews/id={track_id}/sortBy=mostRecent/page=1/json`
       提炼好评/差评主题;抓不到标注"信息有限"。
     - play:Bash 写临时脚本 `/tmp/play_reviews.mjs`(内容如下)执行后删除,
       cwd 为项目根;需代理时 export PLAY_PROXY=...:
       ```js
       const gplay = require('google-play-scraper').default;
       const proxy = process.env.PLAY_PROXY || process.env.HTTPS_PROXY || '';
       const ro = proxy ? { agent: { https: new (require('hpagent').HttpsProxyAgent)({ proxy }) } } : {};
       gplay.reviews({ appId: process.argv[2], lang: 'en', country: 'us', sort: 2, num: 100, requestOptions: ro })
         .then(r => r.data.forEach(c => console.log(`${c.score}★ | ${(c.text || '').slice(0, 200)}`)))
         .catch(e => { console.error(e.message); process.exit(1); });
       ```
       运行 `node /tmp/play_reviews.mjs {track_id}`,据输出提炼好评/差评主题。
     - 评论抓取失败的 app 标"信息有限",不中断。
5. **写报告**到 `reports/{日期}-品类分析-{slug}.md`(结构见下),完整样本表
   直接写进报告第 7 节。最后向用户输出 3-5 句执行摘要(竞争格局一句话 +
   最痛的 2-3 个痛点 + 最大机会点)。

## 报告结构

1. **品类概览**:品类定义、样本圈定方式(关键词/原始搜索数/过滤后数/榜单
   交叉情况)、头部玩家一句话概览
2. **竞争格局**:双平台头部矩阵表——名称/开发者/评分/评分量/下载量(play)/
   价格/内购/广告/最近更新/榜单表现
3. **双平台生态对比**:变现模式分布差异(订阅 vs 广告)、竞争密度、头部重合度
4. **功能矩阵与差异化**:品类标配功能(人人都有→无效竞争区)vs 各家差异化
   卖点(有效区隔);从 details.description 提炼
5. **用户痛点**:差评主题提炼,每条附证据(评论摘录+出现频率+来自哪款 app),
   区分双平台痛点异同;light 模式此节基于低分 app 共性与描述推断,标注可信度较低
6. **机会点**:3-6 条产品切入建议(痛点 × 竞争空白交叉推导)
7. **完整样本表**:过滤后全部 app 一览

## 约束

- 全程中文输出;app 名称保留原文(可附中文释义)
- 报告中数字必须来自数据文件,不臆造
- light 模式整份报告控制在 300 行内
```

- [ ] **Step 2: 提交**

```bash
git add .claude/skills/cat-scan/SKILL.md
git commit -m "feat: /cat-scan 品类竞品与痛点分析 skill"
```

---

### Task 6: README 更新

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 更新 README**

标题 `# App Store / Google Play 非国区工具榜扫描` 下简介段之后(或"使用"小节内)插入品类分析小节:

```markdown
## 品类分析

    # 任意品类双平台竞品与痛点分析(AI 编排,双平台一份报告)
    /cat-scan PDF 扫描
    /cat-scan 个性化二维码生成 light
    # 只抓品类样本数据(不分析)
    python3 -m fetch.category --terms "pdf scanner,ocr scan" --slug pdf-scanner --platform all

Play 需代理时:`export PLAY_PROXY=http://127.0.0.1:7890`(桥自动识别,
HTTPS_PROXY 亦可;iOS 直连)。数据落 `data/{日期}/cat-{slug}/`,
报告落 `reports/{日期}-品类分析-{slug}.md`。
```

"目录"小节的列表中,`reports/` 行之前加一行:

```markdown
- `data/{日期}/cat-{slug}/`：品类搜索样本（{ios|play}.json 含 source_terms/details、meta.json 记录关键词与统计）
```

- [ ] **Step 2: 提交**

```bash
git add README.md
git commit -m "docs: 品类分析使用说明"
```

---

### Task 7: 端到端验收(手动,需网络/代理)

**Files:** 无新文件;产出 `data/2026-08-25/cat-pdf-scanner/` 与验收报告

- [ ] **Step 1: 真实抓取双平台样本**

```bash
export PLAY_PROXY=http://127.0.0.1:7890
python3 -m fetch.category --terms "pdf scanner,document scanner,cam scanner,ocr scanner" --slug pdf-scanner --platform all
```
Expected: 退出码 0;`data/{今天}/cat-pdf-scanner/ios.json`(约 50-100 条,首项应为 Adobe Scan 级别的头部)与 `play.json`(详情含 installs)生成;meta.json 的 failed_terms 为空。
失败处理:iOS 失败检查网络;Play 超时检查代理端口是否可用(`curl -x http://127.0.0.1:7890 https://play.google.com -o /dev/null -w '%{http_code}'` 应为 200)。

- [ ] **Step 2: 全量回归测试**

```bash
python3 -m unittest discover tests -v
```
Expected: 全部 PASS

- [ ] **Step 3: 运行 `/cat-scan PDF 扫描` 完整流程**

在本会话(或新会话)执行 `/cat-scan PDF 扫描`,确认:
- 生成 `reports/{日期}-品类分析-pdf-scanner.md`,7 节结构齐全
- 第 5 节痛点有评论证据;第 2 节矩阵数字与数据文件一致
- 输出了执行摘要

- [ ] **Step 4: 记录验收结果并提交(如验收中修了问题)**

```bash
git status   # 确认无意外改动;验收产生的 data/reports 已被 .gitignore 或按项目惯例不入库
```

---

## 自审记录(计划完成后填写)

- Spec 覆盖:§2.1 适配器 search_apps(Task 1/3)、§2.2 CLI(Task 4)、桥 search(Task 2)、§3 skill(Task 5)、§4 报告结构(Task 5 内嵌)、§5 测试(各任务)、验收(Task 7)——全覆盖
- 代理支持是 spec §2.1 Play 部分的前置事实(spec 未单列,已在计划"已验证的技术事实"与 Task 2 落地;spec 的"运行时需代理"约束由 PLAY_PROXY 落实)
- 类型一致性:`search_apps(term, cc, limit)` 双平台签名一致;`normalize_search` 仅 Play 需要(iOS 详情内联);`merge_samples`/`run_category`/`main` 在 Task 4 定义并被测试引用,名称一致
