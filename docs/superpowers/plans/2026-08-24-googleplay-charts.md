# Google Play 多区域榜单检索(适配器化重构) — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把抓取层重构为可拔插的平台适配器架构,新增 Google Play 适配器,分析层与调度层复用。

**Architecture:** `fetch/core.py`(平台无关编排)+ `fetch/adapters/`(ios 重构迁入 / play 新增 google-play-scraper 封装)。适配器实现 `fetch_chart`/`fetch_details` 两个方法,产出统一 apps.json 契约;`/app-scan` skill 与 launchd 参数化平台。

**Tech Stack:** Python 3;iOS 纯标准库,Play 用 `google-play-scraper==1.2.7`(运行时 import);unittest;macOS launchd。

**Spec:** `docs/superpowers/specs/2026-08-24-googleplay-charts-design.md`

## Global Constraints

- 工作目录一律为项目根 `/Users/hoymiles/Desktop/AI编程项目/Python/ListAnalysis`(spec 中历史路径已失效)
- **对 spec 的一处收敛**:spec §3.1 的 `needs_genre_filter()` 不再作为适配器接口——genre 过滤是 iOS 的解析细节,收进 `ios.fetch_chart` 内部,core 不感知(接口更简,行为不变)
- 统一数据契约字段名不变(spec §4);Play 新增键:`installs/min_installs/offers_iap/iap_price/contains_ads/updated`
- 数据布局 `data/{日期}/{platform}/`(spec §5);旧 `data/{日期}/apps.json` 不自动迁移
- 测试一律用 `tests/fixtures/` 固定 JSON,不打真实 API
- 提交信息末尾加 `Co-Authored-By: Claude <noreply@anthropic.com>`
- 每个任务结束时全量测试必须绿:`python3 -m unittest discover tests -v`

## 接口总览(各任务共用约定)

```python
# fetch/adapters/__init__.py
ADAPTERS = {"ios": IosAdapter, "play": PlayAdapter}   # Task 3 起 ios,Task 4 加 play
def get_adapter(name) -> class                        # 按名取适配器类

# 适配器类协议(实例方法)
class SomeAdapter:
    name: str                        # "ios" / "play"
    request_interval: float          # 榜单请求间隔(秒)
    def __init__(self, opener=None)  # ios 注入 opener 供测试;play 无参
    def fetch_chart(self, cc: str, chart: str, top_n: int, sleep=time.sleep) -> list[dict] | None
        # 返回 [{track_id, name, artist, genre_id, rank}];失败 None → skipped
    def fetch_details(self, ids: list[str], cc: str, sleep=time.sleep) -> dict[str, dict]
        # 返回 {track_id: 统一 details dict};单个失败容忍(缺该 id)

# fetch/core.py
load_config(path) -> dict            # 顶层公共 + 可选 "ios"/"play" 覆盖子字典
best_rank_key(ranks) -> tuple | None
merge_apps(chart_results) -> dict
run(adapter, config, data_dir, refresh=False, sleep=time.sleep) -> dict
main(argv=None) -> int               # --platform ios|play|all

# fetch/charts.py
if __name__ == "__main__":           # python3 -m fetch.charts 入口
```

---

### Task 1: fetch 包骨架与 iOS 解析层迁移(纯移动,行为不变)

**Files:**
- Create: `fetch/__init__.py`(空)、`fetch/adapters/__init__.py`(暂空)、`fetch/adapters/ios.py`
- Modify: `fetch_charts.py`(解析函数改为从包 re-export)、`tests/test_fetch_charts.py`(iOS 部分改 import)

**Interfaces:**
- Produces: `fetch.adapters.ios` 模块,含 `parse_rss/filter_utilities/parse_lookup/chunk_ids/http_get` 与常量 `UTILITIES_GENRE_ID/CHART_KEYS/RSS_URL/LOOKUP_URL/REQUEST_INTERVAL/RETRY_LIMIT/RETRY_DELAY`

- [ ] **Step 1: 创建包与 ios.py(内容=现 fetch_charts.py 第 7-25、46-153 行的原文移动)**

`fetch/__init__.py` 与 `fetch/adapters/__init__.py` 均为空文件。

`fetch/adapters/ios.py`:

```python
"""App Store(iOS)适配器:iTunes RSS 榜单与 lookup 详情,纯标准库。"""

import http.client
import json
import time
import urllib.error
import urllib.request

UTILITIES_GENRE_ID = "6002"
CHART_KEYS = {
    "free": "topfreeapplications",
    "paid": "toppaidapplications",
    "grossing": "topgrossingapplications",
}

REQUEST_INTERVAL = 3.0
RETRY_LIMIT = 2
RETRY_DELAY = 5.0

RSS_URL = "https://itunes.apple.com/{cc}/rss/{chart_key}/limit={limit}/genre={gid}/json"
LOOKUP_URL = "https://itunes.apple.com/lookup?id={ids}&country={cc}"


def parse_rss(text: str) -> list[dict]:
    """解析 iTunes RSS JSON → 按名次排序的 app 列表。"""
    feed = json.loads(text).get("feed", {})
    entries = feed.get("entry", [])
    if isinstance(entries, dict):  # 仅 1 条时是 dict
        entries = [entries]
    apps = []
    for rank, e in enumerate(entries, 1):
        apps.append({
            "track_id": str(e["id"]["attributes"]["im:id"]),
            "name": e.get("im:name", {}).get("label", ""),
            "artist": e.get("im:artist", {}).get("label", ""),
            "genre_id": e.get("category", {}).get("attributes", {}).get("im:id", ""),
            "rank": rank,
        })
    return apps


def filter_utilities(apps: list[dict]) -> list[dict]:
    """只保留工具类并按剩余顺序重排名次。

    畅销榜接口可能忽略 genre 参数,统一在客户端过滤,对两种情况都正确。
    """
    kept = [a for a in apps if a["genre_id"] == UTILITIES_GENRE_ID]
    for rank, a in enumerate(kept, 1):
        a["rank"] = rank
    return kept


def chunk_ids(ids: list, size: int = 200) -> list:
    """lookup 单次最多 200 个 id。"""
    return [ids[i:i + size] for i in range(0, len(ids), size)]


def parse_lookup(text: str) -> dict:
    """解析 lookup 响应 → {track_id: 详情}。评分缺失容忍为 None。"""
    data = json.loads(text)
    out = {}
    for r in data.get("results", []):
        if "trackId" not in r:
            continue
        out[str(r["trackId"])] = {
            "name": r.get("trackName", ""),
            "description": r.get("description", ""),
            "developer": r.get("sellerName", ""),
            "genres": r.get("genres", []),
            "price": r.get("formattedPrice", ""),
            "rating": r.get("averageUserRating"),
            "rating_count": r.get("userRatingCount"),
            "release_date": r.get("currentVersionReleaseDate", ""),
            "track_view_url": r.get("trackViewUrl", ""),
        }
    return out


def http_get(url, opener=urllib.request.urlopen, sleep=time.sleep):
    """GET 并返回响应文本;重试 RETRY_LIMIT 次,全失败返回 None。"""
    last_exc = None
    for attempt in range(1 + RETRY_LIMIT):
        try:
            with opener(url, timeout=30) as resp:
                return resp.read().decode("utf-8")
        except (urllib.error.URLError, OSError, http.client.HTTPException) as exc:
            last_exc = exc
            if attempt < RETRY_LIMIT:
                sleep(RETRY_DELAY)
    print(f"  请求失败(已重试 {RETRY_LIMIT} 次): {url} ({last_exc})", flush=True)
    return None
```

- [ ] **Step 2: fetch_charts.py 改为 re-export(删除被移走的定义)**

删除 `parse_rss/filter_utilities/chunk_ids/parse_lookup/http_get` 五个函数体与 `UTILITIES_GENRE_ID/CHART_KEYS/REQUEST_INTERVAL/RETRY_LIMIT/RETRY_DELAY/RSS_URL/LOOKUP_URL` 常量定义及 `import http.client`,在 `import` 区之后加:

```python
from fetch.adapters import ios as _ios

# 兼容 re-export:旧调用方(fetch_charts.parse_rss 等)不受影响
UTILITIES_GENRE_ID = _ios.UTILITIES_GENRE_ID
CHART_KEYS = _ios.CHART_KEYS
REQUEST_INTERVAL = _ios.REQUEST_INTERVAL
RETRY_LIMIT = _ios.RETRY_LIMIT
RETRY_DELAY = _ios.RETRY_DELAY
RSS_URL = _ios.RSS_URL
LOOKUP_URL = _ios.LOOKUP_URL
parse_rss = _ios.parse_rss
filter_utilities = _ios.filter_utilities
chunk_ids = _ios.chunk_ids
parse_lookup = _ios.parse_lookup
http_get = _ios.http_get
```

注意:`run()` 内对 `filter_utilities/parse_rss/http_get/parse_lookup/chunk_ids` 的调用与 `REQUEST_INTERVAL` 引用保持原样(re-export 已覆盖);`load_config` 里对 `CHART_KEYS` 的引用同样成立。

- [ ] **Step 3: iOS 部分测试改 import 并跑全量**

`tests/test_fetch_charts.py` 顶部把 `import fetch_charts` 后加一行 `from fetch.adapters import ios`,然后把 `TestParseRss/TestFilterUtilities/TestLookup/TestHttpGet` 四个类里的 `fetch_charts.parse_rss` → `ios.parse_rss`、`fetch_charts.filter_utilities` → `ios.filter_utilities`、`fetch_charts.chunk_ids` → `ios.chunk_ids`、`fetch_charts.parse_lookup` → `ios.parse_lookup`、`fetch_charts.http_get` → `ios.http_get`、`fetch_charts.RETRY_DELAY` → `ios.RETRY_DELAY`。其余类(LoadConfig/MergeApps/Run)不动。

Run: `cd "/Users/hoymiles/Desktop/AI编程项目/Python/ListAnalysis" && python3 -m unittest discover tests -v`
Expected: 20 tests PASS

- [ ] **Step 4: 提交**

```bash
git add fetch/ fetch_charts.py tests/test_fetch_charts.py
git commit -m "refactor: iOS 解析层迁入 fetch/adapters/ios(行为不变)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: core 纯函数迁移与 charts 校验泛化

**Files:**
- Create: `fetch/core.py`、`tests/test_core.py`
- Modify: `fetch_charts.py`(删除迁移的函数,re-export)、`tests/test_fetch_charts.py`(删迁移的测试类)

**Interfaces:**
- Produces: `fetch/core.py` 含 `VALID_CHARTS/CHART_PRIORITY/DEFAULT_CONFIG/load_config/best_rank_key/merge_apps`(此任务先不含 run/main,Task 3 加)

- [ ] **Step 1: 写失败测试 `tests/test_core.py`**

```python
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
```

- [ ] **Step 2: 运行确认失败**

Run: `python3 -m unittest tests.test_core -v`
Expected: ERROR(`No module named 'fetch.core'` 之类)

- [ ] **Step 3: 实现 `fetch/core.py`**

```python
"""平台无关的榜单抓取编排:配置、去重合并、落盘、CLI。"""

import json
from pathlib import Path

# 榜单抽象名(两平台共用);平台 API 值的映射在各自适配器内
VALID_CHARTS = {"free", "paid", "grossing"}
# 最佳排名优先级:数字越小越优先
CHART_PRIORITY = {"free": 0, "paid": 1, "grossing": 2}

DEFAULT_CONFIG = {
    "regions": ["us", "gb", "de", "fr", "jp", "kr", "hk", "tw", "sg", "th"],
    "charts": ["free", "paid", "grossing"],
    "top_n": 50,
}


def load_config(path: Path) -> dict:
    """读取配置,缺省字段用 DEFAULT_CONFIG 补齐;charts 含未知值时报错。

    顶层为公共默认;"ios"/"play" 键为平台覆盖子字典,原样保留由调用方合并。
    """
    cfg = dict(DEFAULT_CONFIG)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            cfg.update(json.load(f))
    unknown = set(cfg["charts"]) - VALID_CHARTS
    if unknown:
        raise ValueError(f"未知榜单类型: {sorted(unknown)},可选: {sorted(VALID_CHARTS)}")
    return cfg


def best_rank_key(ranks: dict) -> "tuple | None":
    """ranks={cc:{chart:rank}} → (榜单优先级, 名次) 取最小者。"""
    best = None
    for by_chart in ranks.values():
        for chart, rank in by_chart.items():
            key = (CHART_PRIORITY[chart], rank)
            if best is None or key < best:
                best = key
    return best


def merge_apps(chart_results) -> dict:
    """chart_results: [(cc, chart, [app, ...])] → {track_id: record}。

    regions 按首次上榜顺序记录;第一个区域用于后续详情请求的本地化。
    """
    merged = {}
    for cc, chart, apps in chart_results:
        for a in apps:
            rec = merged.setdefault(a["track_id"], {
                "track_id": a["track_id"],
                "name": a["name"],
                "artist": a["artist"],
                "ranks": {},
                "regions": [],
            })
            rec["ranks"].setdefault(cc, {})[chart] = a["rank"]
            if cc not in rec["regions"]:
                rec["regions"].append(cc)
    for rec in merged.values():
        key = best_rank_key(rec["ranks"])
        rec["best_chart"] = [c for c, p in CHART_PRIORITY.items() if p == key[0]][0]
        rec["best_rank"] = key[1]
    return merged
```

- [ ] **Step 4: fetch_charts.py 删除已迁移定义并 re-export**

删除 `CHART_PRIORITY/DEFAULT_CONFIG/load_config/best_rank_key/merge_apps` 定义,加:

```python
from fetch import core as _core

CHART_PRIORITY = _core.CHART_PRIORITY
DEFAULT_CONFIG = _core.DEFAULT_CONFIG
load_config = _core.load_config
best_rank_key = _core.best_rank_key
merge_apps = _core.merge_apps
```

同时从 `tests/test_fetch_charts.py` 删除 `TestLoadConfig/TestMergeApps` 两个类(已迁 test_core)。

Run: `python3 -m unittest discover tests -v`
Expected: 20 tests PASS(test_core 7 + 剩余 13)

- [ ] **Step 5: 提交**

```bash
git add fetch/core.py tests/test_core.py fetch_charts.py tests/test_fetch_charts.py
git commit -m "refactor: core 纯函数迁移与 charts 校验泛化

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: IosAdapter 与 core.run 泛化、CLI 平台参数、数据布局

**Files:**
- Create: `fetch/charts.py`、`tests/test_adapter_ios.py`
- Modify: `fetch/core.py`(加 run/main)、`fetch/adapters/ios.py`(加 IosAdapter 类)、`fetch/adapters/__init__.py`(注册表)、`fetch_charts.py`(薄转发)、`tests/test_core.py`(加 TestRun/TestMain)
- Delete: `tests/test_fetch_charts.py`(iOS 解析测试迁 test_adapter_ios,Run/Main 由 test_core 取代)

**Interfaces:**
- Consumes: Task 1/2 的函数
- Produces: 见"接口总览"。数据落 `data/{date}/{platform}/`;meta 新增 `platform`、`detail_top_n` 键;`--platform ios|play|all`(默认 ios);`detail_top_n` 配置(None=不限,ios 默认;play 默认 150 由适配器侧 DEFAULTS 提供或 config)

- [ ] **Step 1: 写失败测试(test_core.py 追加)**

```python
import json
from unittest import mock


class FakeAdapter:
    """测试用适配器:单榜单返回固定 apps,详情查表。"""
    name = "fake"
    request_interval = 0

    def __init__(self, chart_apps=None, details=None, fail=()):
        self.chart_apps = chart_apps or []
        self.details = details or {}
        self.fail = set(fail)
        self.chart_calls = []
        self.detail_ids = None

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
            # 同一 adapter 复跑:第二次应复用落盘数据,不再抓取
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
```

- [ ] **Step 2: 运行确认失败**

Run: `python3 -m unittest tests.test_core.TestRun -v`
Expected: ERROR(`core.run` 不存在)

- [ ] **Step 3: 实现 core.run/main、IosAdapter、注册表、charts.py、薄转发**

`fetch/adapters/ios.py` 追加:

```python
class IosAdapter:
    """iTunes RSS + lookup 适配器。"""
    name = "ios"
    request_interval = REQUEST_INTERVAL

    def __init__(self, opener=urllib.request.urlopen):
        self._opener = opener

    def fetch_chart(self, cc, chart, top_n, sleep=time.sleep):
        url = RSS_URL.format(cc=cc, chart_key=CHART_KEYS[chart],
                             limit=top_n, gid=UTILITIES_GENRE_ID)
        text = http_get(url, opener=self._opener, sleep=sleep)
        if text is None:
            return None
        return filter_utilities(parse_rss(text))

    def fetch_details(self, ids, cc, sleep=time.sleep):
        out = {}
        for chunk in chunk_ids(ids):
            sleep(REQUEST_INTERVAL)
            text = http_get(LOOKUP_URL.format(ids=",".join(chunk), cc=cc),
                            opener=self._opener, sleep=sleep)
            if text is None:
                continue  # 详情缺失不致命,分析层降级
            out.update(parse_lookup(text))
        return out
```

`fetch/adapters/__init__.py`:

```python
"""平台适配器注册表。新平台 = 新增 adapters/<name>.py + 在此注册一行。"""

from .ios import IosAdapter


def get_adapter(name):
    if name == "play":
        from .play import PlayAdapter   # 延迟导入:未装依赖不影响 iOS
        return PlayAdapter
    if name == "ios":
        return IosAdapter
    raise ValueError(f"未知平台: {name},可选: ios, play")
```

`fetch/core.py` 追加(`import time`、`from fetch.adapters import get_adapter` 加到模块头):

```python
def run(adapter, config, data_dir, refresh=False, sleep=time.sleep) -> dict:
    data_dir.mkdir(parents=True, exist_ok=True)
    apps_path = data_dir / "apps.json"
    meta_path = data_dir / "meta.json"
    if apps_path.exists() and not refresh:
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta["reused"] = True
            return meta
        return {"reused": True}

    raw_dir = data_dir / "raw"
    raw_dir.mkdir(exist_ok=True)

    chart_results, skipped = [], []
    for cc in config["regions"]:
        for chart in config["charts"]:
            sleep(adapter.request_interval)
            apps = adapter.fetch_chart(cc, chart, config["top_n"], sleep=sleep)
            if apps is None:
                skipped.append(f"{cc}_{chart}")
                continue
            (raw_dir / f"{cc}_{chart}.json").write_text(
                json.dumps(apps, ensure_ascii=False), encoding="utf-8")
            chart_results.append((cc, chart, apps))

    merged = merge_apps(chart_results)
    ordered = sorted(merged.values(),
                     key=lambda r: (CHART_PRIORITY[r["best_chart"]], r["best_rank"]))

    # 详情补全:detail_top_n 截断(None=不限);按首次上榜区域分组请求
    detail_top_n = config.get("detail_top_n")
    target = ordered[:detail_top_n] if detail_top_n else ordered
    by_region = {}
    for rec in target:
        by_region.setdefault(rec["regions"][0], []).append(rec["track_id"])
    for cc, ids in by_region.items():
        for tid, detail in adapter.fetch_details(ids, cc, sleep=sleep).items():
            if tid in merged:
                merged[tid]["details"] = detail

    apps_path.write_text(json.dumps(ordered, ensure_ascii=False, indent=2),
                         encoding="utf-8")

    meta = {
        "platform": adapter.name,
        "date": data_dir.name,
        "regions": config["regions"],
        "charts": config["charts"],
        "top_n": config["top_n"],
        "detail_top_n": detail_top_n,
        "app_count": len(ordered),
        "region_count": config["regions"],
        "skipped": skipped,
        "all_failed": len(chart_results) == 0,
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    print(f"完成[{adapter.name}]: {len(ordered)} 个独立 app(跳过 {len(skipped)} 个榜单)",
          flush=True)
    return meta


def main(argv=None) -> int:
    import argparse
    from datetime import date as _date
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--date", default=_date.today().strftime("%Y-%m-%d"))
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--platform", default="ios", choices=["ios", "play", "all"])
    args = parser.parse_args(argv)

    base = load_config(Path(args.config))
    platforms = ["ios", "play"] if args.platform == "all" else [args.platform]
    rc = 0
    for p in platforms:
        cfg = {k: v for k, v in base.items() if k not in ("ios", "play")}
        cfg.update(base.get(p, {}))
        if p == "play":
            cfg.setdefault("detail_top_n", 150)  # spec §6 默认,config 可覆盖
        adapter = get_adapter(p)()
        meta = run(adapter, cfg, Path("data") / args.date / p, refresh=args.refresh)
        if meta.get("all_failed"):
            rc = 1
    return rc
```

`fetch/charts.py`:

```python
"""CLI 入口:python3 -m fetch.charts"""

from fetch.core import main

if __name__ == "__main__":
    raise SystemExit(main())
```

创建 `tests/test_adapter_ios.py`:内容 = 旧 `tests/test_fetch_charts.py` 的 `TestParseRss/TestFilterUtilities/TestLookup/TestHttpGet` 四个类原文(断言不变),import 区改为:

```python
import http.client
import json
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from fetch.adapters import ios as fetch_charts  # 兼容别名,类内容零改动

FIXTURES = Path(__file__).parent / "fixtures"
```

(用 `ios as fetch_charts` 别名,四个测试类的函数体一字不改。)

根 `fetch_charts.py` 全文替换为薄转发(旧 run/main 测试类已由 test_core 的 FakeAdapter 版本取代):

```python
#!/usr/bin/env python3
"""兼容入口:转发到 fetch 包。新代码请用 python3 -m fetch.charts。"""

from fetch.core import *          # noqa: F401,F403
from fetch.core import main


if __name__ == "__main__":
    raise SystemExit(main())
```

注意 `fetch/core.py` 的 `__all__` 未定义,`import *` 只带走公共名,足够兼容。删除 `tests/test_fetch_charts.py`(其 iOS 类已迁,Run/Main 类由 test_core 取代;文件删除后 `git rm`)。

- [ ] **Step 4: 跑全量并修复回归**

Run: `python3 -m unittest discover tests -v`
Expected: 22 tests PASS(test_core 13 + test_adapter_ios 9)

同时冒烟兼容入口:
Run: `python3 -c "import fetch_charts; print(fetch_charts.DEFAULT_CONFIG['top_n'])"`
Expected: `50`

- [ ] **Step 5: 提交**

```bash
git add fetch/ fetch_charts.py tests/test_core.py
git rm tests/test_fetch_charts.py
git commit -m "feat: 适配器架构与平台参数(--platform ios|play|all)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4: Play 适配器(TDD)

**Files:**
- Create: `requirements.txt`、`fetch/adapters/play.py`、`tests/fixtures/play_top.json`、`tests/fixtures/play_app.json`、`tests/test_adapter_play.py`

**Interfaces:**
- Produces: `PlayAdapter`(协议同 IosAdapter);`normalize_top/normalize_app` 模块级纯函数;`check_dependency()` import 失败时 `raise SystemExit(2)`

- [ ] **Step 1: requirements.txt**

```
google-play-scraper==1.2.7
```

- [ ] **Step 2: 写 fixture(浓缩自库文档真实响应结构)**

`tests/fixtures/play_top.json`(`top()` 返回,list):

```json
[
  {
    "appId": "com.example.cleaner",
    "title": "Example Cleaner",
    "developer": "Example Inc.",
    "score": 4.6,
    "ratings": 128000,
    "price": 0,
    "free": true,
    "currency": "USD",
    "genre": "Tools",
    "genreId": "TOOLS"
  },
  {
    "appId": "com.example.vpn",
    "title": "Example VPN",
    "developer": "Example KK.",
    "score": 4.2,
    "ratings": 98000,
    "price": 4.99,
    "free": false,
    "currency": "USD",
    "genre": "Tools",
    "genreId": "TOOLS"
  }
]
```

`tests/fixtures/play_app.json`(`app()` 返回,dict,字段同库文档):

```json
{
  "appId": "com.example.cleaner",
  "title": "Example Cleaner",
  "description": "Clean your phone. Free up storage.",
  "summary": "Cleaner & booster",
  "installs": "100,000,000+",
  "minInstalls": 100000000,
  "score": 4.6,
  "ratings": 128000,
  "price": 0,
  "free": true,
  "currency": "USD",
  "offersIAP": true,
  "inAppProductPrice": "$0.99 - $99.99 per item",
  "developer": "Example Inc.",
  "genre": "Tools",
  "genreId": "TOOLS",
  "categories": [{"name": "Performance", "id": null}],
  "released": "Aug 1, 2019",
  "updated": 1755000000,
  "url": "https://play.google.com/store/apps/details?id=com.example.cleaner"
}
```

- [ ] **Step 3: 写失败测试 `tests/test_adapter_play.py`**

```python
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
        # 与 iOS 同名的公共字段(分析层复用)
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
        # Play 特有键(spec §4)
        self.assertEqual(d["installs"], "100,000,000+")
        self.assertTrue(d["offers_iap"])
        self.assertEqual(d["iap_price"], "$0.99 - $99.99 per item")

    def test_normalize_app_paid_price_format(self):
        d = play.normalize_app({"free": False, "price": 4.99, "currency": "USD"})
        self.assertEqual(d["price"], "USD 4.99")


class TestPlayAdapter(unittest.TestCase):
    def test_fetch_chart_maps_and_retries(self):
        top_fn = mock.MagicMock(return_value=json.loads(
            (FIXTURES / "play_top.json").read_text(encoding="utf-8")))
        a = play.PlayAdapter(lib=mock.MagicMock())  # 注入,无需安装库
        apps = a.fetch_chart("us", "free", 50, sleep=mock.MagicMock(), top_fn=top_fn)
        self.assertEqual(apps[0]["track_id"], "com.example.cleaner")
        kwargs = top_fn.call_args.kwargs
        self.assertEqual(kwargs["country"], "us")
        self.assertEqual(kwargs["num"], 50)
        self.assertEqual(kwargs["lang"], "en")
        self.assertEqual(kwargs["collection"], "TOP_FREE")

    def test_fetch_chart_all_fail_returns_none(self):
        top_fn = mock.MagicMock(side_effect=RuntimeError("net down"))
        a = play.PlayAdapter(lib=mock.MagicMock())
        apps = a.fetch_chart("us", "paid", 50, sleep=mock.MagicMock(), top_fn=top_fn)
        self.assertIsNone(apps)
        self.assertEqual(top_fn.call_count, 3)  # 1 + RETRY_LIMIT

    def test_fetch_details_per_app_fail_tolerant(self):
        calls = []

        def app_fn(app_id, country="us", lang="en"):
            calls.append(app_id)
            if app_id == "com.bad":
                raise RuntimeError("gone")
            return json.loads((FIXTURES / "play_app.json").read_text(encoding="utf-8"))

        a = play.PlayAdapter(lib=mock.MagicMock())
        out = a.fetch_details(["com.example.cleaner", "com.bad"], "us",
                              sleep=mock.MagicMock(), app_fn=app_fn)
        self.assertEqual(list(out), ["com.example.cleaner"])  # 失败的被容忍
        self.assertEqual(calls, ["com.example.cleaner", "com.bad"])

    def test_check_dependency_missing_exits_2(self):
        with mock.patch.dict("sys.modules", {"google_play_scraper": None}):
            with self.assertRaises(SystemExit) as cm:
                play.check_dependency()
            self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: 运行确认失败**

Run: `python3 -m unittest tests.test_adapter_play -v`
Expected: ERROR(`No module named 'fetch.adapters.play'`)

- [ ] **Step 5: 实现 `fetch/adapters/play.py`**

```python
"""Google Play(Android)适配器:google-play-scraper 封装(运行时导入)。"""

import json
import sys
import time

from .ios import RETRY_LIMIT, RETRY_DELAY  # 复用重试常量语义

CHARTS = {"free": "TOP_FREE", "paid": "TOP_PAID", "grossing": "TOP_GROSSING"}
CATEGORY_TOOLS = "TOOLS"
DETAIL_INTERVAL = 1.0


def check_dependency():
    """未安装 google-play-scraper 时以退出码 2 终止。"""
    try:
        import google_play_scraper  # noqa: F401
    except ImportError:
        print("错误: Play 适配器需要 google-play-scraper。"
              "请先运行: pip3 install -r requirements.txt", file=sys.stderr, flush=True)
        raise SystemExit(2)


def normalize_top(raw: list) -> list[dict]:
    """top() 返回 → 统一榜单元素;字段缺失容忍。"""
    apps = []
    for rank, r in enumerate(raw, 1):
        apps.append({
            "track_id": r.get("appId", ""),
            "name": r.get("title", ""),
            "artist": r.get("developer", ""),
            "genre_id": r.get("genreId", ""),
            "rank": rank,
        })
    return apps


def normalize_app(d: dict) -> dict:
    """app() 返回 → 统一 details(公共字段与 iOS 同名 + Play 特有键)。"""
    genres = [d["genre"]] if d.get("genre") else []
    genres += [c["name"] for c in d.get("categories", []) if c.get("name")]
    if d.get("free"):
        price = "Free"
    else:
        price = f'{d.get("currency", "")} {d.get("price", 0)}'.strip()
    return {
        "name": d.get("title", ""),
        "developer": d.get("developer", ""),
        "description": d.get("description", ""),
        "genres": genres,
        "price": price,
        "rating": d.get("score"),
        "rating_count": d.get("ratings"),
        "release_date": d.get("released", ""),
        "track_view_url": d.get("url", ""),
        "installs": d.get("installs", ""),
        "min_installs": d.get("minInstalls"),
        "offers_iap": d.get("offersIAP"),
        "iap_price": d.get("inAppProductPrice"),
        "contains_ads": d.get("containsAds"),
        "updated": d.get("updated"),
    }


class PlayAdapter:
    name = "play"
    request_interval = 3.0

    def __init__(self, lib=None):
        # lib 注入供测试;真实运行时检查依赖并导入
        if lib is None:
            check_dependency()
            import google_play_scraper
            lib = google_play_scraper
        self._lib = lib

    def fetch_chart(self, cc, chart, top_n, sleep=time.sleep, top_fn=None):
        top = top_fn or self._lib.top
        last_exc = None
        for attempt in range(1 + RETRY_LIMIT):
            try:
                raw = top(collection=CHARTS[chart], category=CATEGORY_TOOLS,
                          num=top_n, country=cc, lang="en")
                return normalize_top(raw)
            except Exception as exc:  # 库异常类型不稳定,统一防御
                last_exc = exc
                if attempt < RETRY_LIMIT:
                    sleep(RETRY_DELAY)
        print(f"  请求失败(已重试 {RETRY_LIMIT} 次): play {cc} {chart} ({last_exc})",
              flush=True)
        return None

    def fetch_details(self, ids, cc, sleep=time.sleep, app_fn=None):
        app = app_fn or self._lib.app
        out = {}
        for app_id in ids:
            sleep(DETAIL_INTERVAL)
            try:
                d = app(app_id, country=cc, lang="en")
            except Exception as exc:
                print(f"  详情失败(跳过): {app_id} ({exc})", flush=True)
                continue
            out[app_id] = normalize_app(d)
        return out
```

- [ ] **Step 6: 跑全量**

Run: `python3 -m unittest discover tests -v`
Expected: 全部 PASS(约 18 个)

注意:适配器测试全部通过 `lib=`/`top_fn=`/`app_fn=` 注入,**无需安装 google-play-scraper 即可跑全量测试**(真实库仅在 Task 5 冒烟时安装)。`test_check_dependency_missing_exits_2` 用 `mock.patch.dict("sys.modules", {"google_play_scraper": None})` 模拟未安装,若真实环境已装库,该 mock 确保测试仍走 ImportError 分支。

- [ ] **Step 7: 提交**

```bash
git add requirements.txt fetch/adapters/play.py tests/
git commit -m "feat: Google Play 适配器(统一契约映射与容错)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4B: Play 适配器改 Node 桥接(2026-08-24 修订)

> **修订原因**:冒烟发现 Python 版 google-play-scraper 1.2.7 **没有 top() 榜单功能**(只有 app/search/reviews;调研阶段的搜索结果把 Node 原版功能误记到了 Python 版)。经用户确认改用 **Node 桥接**:榜单与详情统一走 Node 版 google-play-scraper@^10.1.3(已真实验证:`list()` 支持 TOOLS 分类 × TOP_FREE/TOP_PAID/**GROSSING**(注意:畅销榜常量是 `GROSSING`,非 TOP_GROSSING)× country × num;字段名与 Python 版 app() 一致,normalize_top/normalize_app 契约映射无需改动)。
> **网络前置条件**:play.google.com 需代理访问(DNS 污染)。用户选择"手动开代理跑"——脚本/launchd 不配代理,冒烟与定时任务运行时须保证代理已开启。

**Files:**
- Create: `scripts/play_bridge.mjs`、`package.json`
- Modify: `fetch/adapters/play.py`(fetch_chart/fetch_details/check_dependency 改走桥)、`tests/test_adapter_play.py`(注入点从 top_fn/app_fn 改为 bridge_fn)
- Delete: `requirements.txt`(Python 版库不再使用)

**play_bridge.mjs 设计:**读 stdin JSON 指令,stdout 输出 JSON 结果:
- `{"cmd": "list", "collection": "...", "category": "TOOLS", "num": N, "country": "cc", "lang": "en"}` → `[{appId,title,developer,score,...}]`(gplay.list 原样)
- `{"cmd": "apps", "ids": ["com.x",...], "country": "cc", "lang": "en"}` → `{"com.x": {...app详情...}, ...}`(Node 内部逐个 gplay.app,单 app 失败置 null 容忍)
- 错误:stderr 一行 + exit 1(非零);`node_modules` 缺失依赖时给明确提示

**play.py 改造要点:**
- `CHARTS = {"free": "TOP_FREE", "paid": "TOP_PAID", "grossing": "GROSSING"}`
- `check_dependency()`:校验 `node` 可用且 `node_modules/google-play-scraper` 存在(或 `node -e "require('google-play-scraper')"` 成功);失败打印"请先运行: npm install"+ SystemExit(2)
- `_run_bridge(payload, timeout=120) -> dict|list|None`:subprocess 跑 `node scripts/play_bridge.mjs`,stdin 传 JSON;失败返回 None(重试逻辑在 fetch_chart 层)
- `fetch_chart`:构造 list 指令 → _run_bridge(重试 1+RETRY_LIMIT,间隔 RETRY_DELAY)→ normalize_top;CHARTS[chart] 在循环外取(KeyError 不进重试)
- `fetch_details`:一次 _run_bridge(apps 指令,全部 ids)→ 过滤 null → normalize_app
- 测试:fetch_chart/fetch_details 注入 `bridge_fn`(fake 返回 fixture JSON 的**原始 Node 字段**),保留全部既有 normalize/容错断言语义;test_check_dependency_missing_exits_2 改 mock node 缺失场景

**验收:** 全量测试绿(Python 侧全部 mock node,无需装 npm 依赖);`python3 -m fetch.charts --platform play ...` 在未 npm install 时给友好提示退出码 2。

**提交:** `feat: Play 适配器改 Node 桥接(榜单与详情统一走 google-play-scraper@10)`

---

### Task 5: Play 真实 API 冒烟验证(手动,不进自动测试)

**Files:**
- 无新文件;产出 `data/smoke/play/`(验证后删除)

- [ ] **Step 0: 前置条件(用户已确认)**:代理软件已开启(play.google.com 可达);`npm install` 已在项目根执行

- [ ] **Step 1: 冒烟**

```bash
cd "/Users/hoymiles/Desktop/AI编程项目/Python/ListAnalysis" && \
  pip3 install -r requirements.txt && \
  python3 -m fetch.charts --platform play --date smoke
```

(默认全区域;若想快,可临时建 `smoke_cfg.json` `{"regions":["us"],"charts":["free","paid","grossing"],"top_n":10,"play":{"detail_top_n":5}}` 加 `--config smoke_cfg.json`。)

- [ ] **Step 2: 人工核验 spec §10 三点**

1. `top()` num 上限/分页:top_n=50 时 `data/smoke/play/raw/us_free.json` 是否有 50 条(若被截断,记录实际上限并在 config 把 play.top_n 调整为上限)
2. TOOLS 分类:`fetch_chart` 用 `category="TOOLS"` 是否正常返回(若空结果,尝试 `google_play_scraper` 的分类常量确切写法并修正 `CATEGORY_TOOLS`)
3. `top()` 字段集:raw 里解析后 track_id/name/artist 是否非空;`apps.json` 前 5 名有完整 details(description/installs/offers_iap)

Expected: `完成[play]: N 个独立 app`;meta.json skipped 为空

- [ ] **Step 3: 清理**

```bash
rm -rf data/smoke smoke_cfg.json
```

- [ ] **Step 4: 提交(如有修正)**

```bash
git add -A && git commit -m "fix: Play 冒烟发现的问题修正

Co-Authored-By: Claude <noreply@anthropic.com>"
```

(无修正则跳过。)

---

### Task 6: /app-scan skill 参数化与 Play 报告验收

**Files:**
- Modify: `.claude/skills/app-scan/SKILL.md`(全文替换)

- [ ] **Step 1: SKILL.md 全文替换为**

````markdown
---
name: app-scan
description: 扫描 App Store(iOS)或 Google Play(Android)非国区工具榜并生成中文分析报告。用法:/app-scan [ios|play] [light|standard|deep] [--refresh]。默认 ios。触发词:扫榜、工具榜分析、app榜单。
---

# App Store / Google Play 工具榜扫描分析

分析 `data/{今天日期 YYYY-MM-DD}/{platform}/apps.json` 中的非国区工具榜数据
(platform=ios 或 play),生成中文分析报告到 `reports/{日期}-工具榜分析-{platform}.md`。

## 参数解析

从用户输入解析:平台 `ios`(默认)/ `play`;模式 `light` / `standard`(默认)/ `deep`;`--refresh`。

## 流程

1. **取数**:若 `data/{日期}/{platform}/apps.json` 不存在或带 `--refresh`,
   先运行 `python3 -m fetch.charts --platform {platform} [--refresh]`(工作目录为项目根)。
   脚本失败(退出码非 0)→ 向用户报告错误并停止。
2. **读数据**:读 `apps.json`(已按最佳排名排序)与 `meta.json`。
   `meta.json` 的 `skipped` 非空 → 报告"本期总览"须注明缺失的区域/榜单。
3. **类型分布**(所有模式):把 app 归入细分赛道(如 清理加速 / 网络VPN /
   文件管理 / 格式转换 / 效率工具 / 安全隐私 / 输入法 / 小组件壁纸 /
   扫描识别 / 测试与其他)。依据 `details.genres`、名称与描述关键词。
   统计各赛道数量与占比,指出跨区域共性赛道与区域特色赛道。
4. **分层分析**:
   - `light`:无逐个详析,全部表格化。
   - `standard`:取前 120 个逐个详析,其余表格化。
   - `deep`:取前 30 个逐个详析;评论与页面信息按下平台获取:
     - ios:用 WebFetch 抓
       `https://itunes.apple.com/{regions[0]}/rss/customerreviews/id={track_id}/sortBy=mostRecent/page=1/json`
       提炼好评/差评主题,并抓 `details.track_view_url` 补充页面信息
       (抓不到就跳过并标注"信息有限")。
     - play:用 Bash 写临时脚本 `/tmp/play_reviews.py` 执行后删除,
       脚本调用 `google_play_scraper.reviews('{track_id}', lang='en',
       country='{regions[0]}', sort=Sort.NEWEST, count=100)` 并逐行打印
       `评分★ | 前200字评论`,据此提炼好评/差评主题;
       无需抓页面(details 已含 installs/内购/广告)。
5. **写报告**到 `reports/{日期}-工具榜分析-{platform}.md`,结构见下。
   完整榜单表格必须直接写进报告第 4 节(不要只留在中间文件)。
6. 最后向用户输出 3-5 句执行摘要(本期亮点赛道、值得注意的 app)。

## 重点 app 详析格式(standard/deep 共用)

每个 app 一小节:核心功能(2-4 条中文)/ 目标用户与场景 /
变现模式(免费、买断、订阅、内购或广告——ios 从 `details.price` 与描述推断;
play 直接看 `details.offers_iap`/`iap_price`/`contains_ads` 并引用
`details.installs` 下载量级)/ 一句点评(上榜原因或可借鉴之处)。
`details` 缺失的 app:基于名称与分类推断,并标注"信息有限"。

## 报告结构

1. **本期总览**:日期、平台、区域数、各榜 app 数、数据完整性(skipped)
2. **类型分布**:细分赛道表格(数量/占比/代表 app)+ 共性 vs 区域特色分析
3. **重点 App 分析**:按细分赛道分组逐个详析(数量按模式)
4. **完整榜单表格**:分区域 × 分榜单,列=排名/名称/开发者/评分/价格(play 可加下载量)
5. **观察与机会**:3-6 条跨区域趋势观察与机会点

## 约束

- 全程中文输出;app 名称保留原文(可附中文释义)
- 报告中数字必须来自数据文件,不臆造
- light 模式整份报告控制在 300 行内
````

- [ ] **Step 2: play light 模式验收**

在项目目录 Claude Code 会话运行 `/app-scan play light`(当天 play 数据不存在会先抓全量)。
Expected: `reports/{今天}-工具榜分析-play.md` 生成,五节结构完整、第 4 节表格内联、≤300 行、详析含下载量/内购信息

- [ ] **Step 3: 提交**

```bash
git add .claude/skills/app-scan/SKILL.md
git commit -m "feat: /app-scan 参数化平台(ios|play)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 7: launchd 参数化与迁移安装

**Files:**
- Modify: `scripts/install_launchd.sh`(全文替换)

- [ ] **Step 1: 脚本全文替换为**

```bash
#!/bin/zsh
# 安装/卸载/验证 App 榜单扫描的 launchd 定时任务(按平台)
# 用法: scripts/install_launchd.sh install|uninstall|verify [ios|play]

set -euo pipefail
ACTION="${1:-}"
PLATFORM="${2:-ios}"
LABEL="com.appcharts.scan.${PLATFORM}"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "${PROJECT_DIR}/logs"

case "$PLATFORM" in
ios)   RUN_AT=("1" "9" "30") ;;   # 周一 09:30
play)  RUN_AT=("1" "9" "50") ;;   # 周一 09:50,与 ios 错开
*) echo "平台须为 ios 或 play"; exit 1 ;;
esac
WEEKDAY="${RUN_AT[1]}" HOUR="${RUN_AT[2]}" MINUTE="${RUN_AT[3]}"
# zsh 数组从 1 开始:RUN_AT[1]=周一, [2]=时, [3]=分

case "$ACTION" in
install)
  # 迁移:卸载旧的单平台任务 com.appcharts.scan(如存在)
  OLD_PLIST="$HOME/Library/LaunchAgents/com.appcharts.scan.plist"
  if [ -f "$OLD_PLIST" ]; then
    launchctl unload "$OLD_PLIST" 2>/dev/null || true
    rm -f "$OLD_PLIST"
    echo "已迁移移除旧任务: com.appcharts.scan"
  fi
  cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>-lc</string>
    <string>cd '${PROJECT_DIR}' && claude -p '/app-scan ${PLATFORM} standard' >> "${PROJECT_DIR}/logs/scan-${PLATFORM}-\$(date +%F).log" 2>&1</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Weekday</key><integer>${WEEKDAY}</integer>
    <key>Hour</key><integer>${HOUR}</integer>
    <key>Minute</key><integer>${MINUTE}</integer>
  </dict>
  <key>StandardOutPath</key><string>${PROJECT_DIR}/logs/launchd-${PLATFORM}.out</string>
  <key>StandardErrorPath</key><string>${PROJECT_DIR}/logs/launchd-${PLATFORM}.err</string>
</dict>
</plist>
EOF
  launchctl unload "$PLIST" 2>/dev/null || true
  launchctl load "$PLIST"
  echo "已安装: $PLIST(每周一 ${HOUR}:${MINUTE} 运行 /app-scan ${PLATFORM} standard)"
  "$0" verify "$PLATFORM"
  ;;
uninstall)
  launchctl unload "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
  echo "已卸载: $PLIST"
  ;;
verify)
  launchctl list | grep -q "$LABEL" && echo "✓ ${LABEL} 已加载" || { echo "✗ ${LABEL} 未加载"; exit 1; }
  CLAUDE_BIN="$(zsh -lc 'command -v claude' || true)"
  [ -n "$CLAUDE_BIN" ] && echo "✓ claude 可用: $CLAUDE_BIN" || { echo "✗ 登录 shell 找不到 claude"; exit 1; }
  if [ "$PLATFORM" = "play" ]; then
    NODE_BIN="$(zsh -lc 'command -v node' || true)"
    [ -n "$NODE_BIN" ] && echo "✓ node 可用: $NODE_BIN" || { echo "✗ 登录 shell 找不到 node(Play 需要)"; exit 1; }
    [ -d "${PROJECT_DIR}/node_modules/google-play-scraper" ] && echo "✓ npm 依赖已装" || { echo "✗ 缺 npm 依赖:请在项目根 npm install"; exit 1; }
  fi
  ;;
*)
  echo "用法: $0 install|uninstall|verify [ios|play]"; exit 1
  ;;
esac
```

- [ ] **Step 2: 安装两个平台并确认旧任务已迁移**

```bash
cd "/Users/hoymiles/Desktop/AI编程项目/Python/ListAnalysis" && \
  scripts/install_launchd.sh install ios && \
  scripts/install_launchd.sh install play && \
  launchctl list | grep com.appcharts
```

Expected: 列出 `com.appcharts.scan.ios` 与 `com.appcharts.scan.play`,且无旧的 `com.appcharts.scan`

- [ ] **Step 3: 提交**

```bash
git add scripts/install_launchd.sh
git commit -m "feat: launchd 按平台参数化并迁移旧任务

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 8: README 更新与全量验收

**Files:**
- Modify: `README.md`

- [ ] **Step 1: README 全文替换为**

````markdown
# App Store / Google Play 非国区工具榜扫描

定期抓取 10 个区域(美/英/德/法/日/韩/港/台/新/泰)的 **iOS App Store** 与
**Google Play** 工具类免费/付费/畅销榜,AI 分析每个上榜 App 的功能与类型分布,
产出中文报告。设计文档见 `docs/superpowers/specs/`。

平台可拔插:抓取层为 `fetch/adapters/` 下的适配器(ios / play),
新增平台只需实现 `fetch_chart`/`fetch_details` 并注册。

## 使用

    # 手动扫描(默认 ios,standard 档)
    /app-scan
    # Google Play 扫描
    /app-scan play
    # 快速扫榜 / 深度研究
    /app-scan [ios|play] light
    /app-scan [ios|play] deep
    # 强制重抓当天数据
    /app-scan [ios|play] --refresh

只抓数据不分析:

    python3 -m fetch.charts --platform ios|play|all [--date YYYY-MM-DD] [--refresh]

Play 首次使用需安装依赖:`pip3 install -r requirements.txt`

## 定时任务

    scripts/install_launchd.sh install ios     # 每周一 09:30
    scripts/install_launchd.sh install play    # 每周一 09:50
    scripts/install_launchd.sh verify [ios|play]
    scripts/install_launchd.sh uninstall [ios|play]

## 配置

`config.json`:顶层 `regions`/`charts`/`top_n` 为公共默认;
`"ios"`/`"play"` 子字典按平台覆盖(如 `{"play": {"top_n": 50, "detail_top_n": 150}}`)。

## 目录

- `data/{日期}/{平台}/`:原始榜单(raw/)、合并清单(apps.json)、运行元信息(meta.json)
- `reports/`:中文分析报告(`{日期}-工具榜分析-{平台}.md`)
- `logs/`:定时任务日志

> 2026-08-24 前的旧 iOS 数据在 `data/{日期}/apps.json`,如需纳入新布局可执行:
> `mkdir -p data/{日期}/ios && mv data/{日期}/apps.json data/{日期}/meta.json data/{日期}/raw data/{日期}/ios/`

## 测试

    python3 -m unittest discover tests -v
````

- [ ] **Step 2: 全量验收**

1. `python3 -m unittest discover tests -v` → 全部 PASS
2. `python3 -m fetch.charts --platform ios --date 2026-08-24` → 复用提示(数据已在则迁移后验证;或任选空日期验证新布局 `data/{日期}/ios/`)
3. `/app-scan play standard` 报告五节结构完整(Top 120 详析含 installs/内购维度)
4. `launchctl list | grep com.appcharts` 两条任务在列

- [ ] **Step 3: 提交**

```bash
git add README.md
git commit -m "docs: 双平台使用说明

Co-Authored-By: Claude <noreply@anthropic.com>"
```
