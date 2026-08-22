# App Store 非国区工具榜扫描工作流 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建"抓取 10 区域 App Store 工具榜 → AI 分析生成中文报告"的可手动/定时触发的工作流。

**Architecture:** 三层解耦：`fetch_charts.py`（纯 Python 标准库抓取脚本，产出 `data/{日期}/apps.json`）→ `.claude/skills/app-scan`（AI 分析 skill，产出 `reports/`）→ launchd（定时无头触发 `claude -p`）。

**Tech Stack:** Python 3 标准库（urllib/json/unittest，零第三方依赖）、Claude Code skill、macOS launchd。

**Spec:** `docs/superpowers/specs/2026-08-22-appstore-utilities-charts-workflow-design.md`

## Global Constraints

- Python 3，仅标准库，无第三方依赖（设计 §3；因此配置文件用 `config.json` 而非 spec 中提到的 `config.yaml`，功能等价）
- 默认区域：`us, gb, de, fr, jp, kr, hk, tw, sg, th`；默认榜单 `free, paid, grossing`；默认 TopN `50`（spec §2）
- iTunes RSS 分类码 Utilities = `6002`（spec §4.1）
- 请求间隔 ≥ 3 秒；单请求失败重试 2 次（间隔 5 秒）后跳过并记录，不中断整体（spec §4.3）
- 畅销榜统一在客户端按 `genre_id == "6002"` 过滤并重排名次（对接口是否支持 genre 参数免疫，spec §4.1）
- 最佳排名优先级：免费榜 > 付费榜 > 畅销榜，同榜比名次（spec §4.2）
- 测试一律用 `tests/fixtures/` 固定 JSON，不打真实 API（spec §7）
- 提交信息末尾加 `Co-Authored-By: Claude <noreply@anthropic.com>`

## 接口总览（各任务共用约定）

全部函数在单文件 `fetch_charts.py` 中，测试通过 `import fetch_charts` 使用：

```python
load_config(path: Path) -> dict                 # {"regions":[...], "charts":[...], "top_n":int}
parse_rss(text: str) -> list[dict]              # [{track_id:str, name:str, artist:str, genre_id:str, rank:int}]
filter_utilities(apps: list[dict]) -> list[dict] # 过滤非 6002 并重算 rank
merge_apps(chart_results) -> dict[str, dict]    # chart_results: [(cc, chart, apps)]; 值含 name/artist/ranks/regions/best_chart/best_rank
best_rank_key(ranks: dict) -> tuple | None      # ranks={cc:{chart:rank}} → (优先级, rank)
chunk_ids(ids: list[str], size: int = 200) -> list[list[str]]
parse_lookup(text: str) -> dict[str, dict]      # {track_id: {name, description, developer, genres, price, rating, rating_count, release_date, track_view_url}}
http_get(url, opener, sleep) -> str | None      # 重试 2 次；全部失败返回 None
run(config, data_dir: Path, refresh: bool, sleep) -> dict   # 编排+落盘，返回 meta
main(argv: list[str] | None) -> int             # CLI 入口，全部失败返回 1
```

---

### Task 1: 项目脚手架与配置加载

**Files:**
- Create: `config.json`、`fetch_charts.py`、`tests/test_fetch_charts.py`、`tests/fixtures/.gitkeep`
- Create: `data/`、`reports/`、`logs/` 目录（各放 `.gitkeep`）

**Interfaces:**
- Produces: `load_config(path) -> dict`，键 `regions`/`charts`/`top_n`；`DEFAULT_CONFIG` 常量

- [ ] **Step 1: 写失败测试**

`tests/test_fetch_charts.py`：

```python
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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行确认失败**

Run: `cd "/Users/wangkun/Desktop/AI项目/app榜单分析" && python3 -m unittest tests.test_fetch_charts -v`
Expected: FAIL/ERROR（`No module named 'fetch_charts'` 或函数不存在）

- [ ] **Step 3: 最小实现**

`fetch_charts.py`：

```python
#!/usr/bin/env python3
"""抓取 App Store 非国区工具（Utilities）榜单，去重合并并补全详情。

仅使用 Python 标准库。数据落盘 data/{日期}/，元信息见 meta.json。
"""

import json
from pathlib import Path

UTILITIES_GENRE_ID = "6002"
CHART_KEYS = {
    "free": "topfreeapplications",
    "paid": "toppaidapplications",
    "grossing": "topgrossingapplications",
}
# 最佳排名优先级：数字越小越优先（spec §4.2）
CHART_PRIORITY = {"free": 0, "paid": 1, "grossing": 2}

REQUEST_INTERVAL = 3.0
RETRY_LIMIT = 2
RETRY_DELAY = 5.0

DEFAULT_CONFIG = {
    "regions": ["us", "gb", "de", "fr", "jp", "kr", "hk", "tw", "sg", "th"],
    "charts": ["free", "paid", "grossing"],
    "top_n": 50,
}


def load_config(path: Path) -> dict:
    """读取配置，缺省字段用 DEFAULT_CONFIG 补齐；charts 含未知值时报错。"""
    cfg = dict(DEFAULT_CONFIG)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            cfg.update(json.load(f))
    unknown = set(cfg["charts"]) - set(CHART_KEYS)
    if unknown:
        raise ValueError(f"未知榜单类型: {sorted(unknown)}，可选: {sorted(CHART_KEYS)}")
    return cfg
```

`config.json`（用户可编辑的默认配置）：

```json
{
  "regions": ["us", "gb", "de", "fr", "jp", "kr", "hk", "tw", "sg", "th"],
  "charts": ["free", "paid", "grossing"],
  "top_n": 50
}
```

- [ ] **Step 4: 运行确认通过**

Run: `python3 -m unittest tests.test_fetch_charts -v`
Expected: 3 tests PASS

- [ ] **Step 5: 提交**

```bash
git add fetch_charts.py config.json tests/ data/.gitkeep reports/.gitkeep logs/.gitkeep
git commit -m "feat: 项目脚手架与配置加载

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: RSS 榜单解析 parse_rss

**Files:**
- Create: `tests/fixtures/rss_utilities.json`
- Modify: `fetch_charts.py`（追加 `parse_rss`）、`tests/test_fetch_charts.py`（追加测试类）

**Interfaces:**
- Consumes: 无
- Produces: `parse_rss(text: str) -> list[dict]`，元素 `{track_id, name, artist, genre_id, rank}`，rank 从 1 开始

- [ ] **Step 1: 写 fixture（真实 iTunes RSS JSON 结构的浓缩）**

`tests/fixtures/rss_utilities.json`：

```json
{
  "feed": {
    "title": {"label": "Top Free Applications"},
    "entry": [
      {
        "id": {
          "label": "https://apps.apple.com/us/app/example-clean/id111111?uo=2",
          "attributes": {"im:id": "111111"}
        },
        "im:name": {"label": "Example Cleaner"},
        "im:artist": {"label": "Example Inc."},
        "category": {"attributes": {"im:id": "6002", "term": "Utilities"}},
        "im:price": {"label": "Get", "attributes": {"amount": "0.00"}}
      },
      {
        "id": {
          "label": "https://apps.apple.com/us/app/example-vpn/id222222?uo=2",
          "attributes": {"im:id": "222222"}
        },
        "im:name": {"label": "Example VPN"},
        "im:artist": {"label": "Example KK."},
        "category": {"attributes": {"im:id": "6002", "term": "Utilities"}},
        "im:price": {"label": "Get", "attributes": {"amount": "0.00"}}
      }
    ]
  }
}
```

- [ ] **Step 2: 写失败测试**

`tests/test_fetch_charts.py` 追加：

```python
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
```

（文件顶部已 `import json` 的话无需重复；若未导入，在文件头 `import unittest` 下补 `import json`。）

- [ ] **Step 3: 运行确认失败**

Run: `python3 -m unittest tests.test_fetch_charts.TestParseRss -v`
Expected: ERROR（`parse_rss` 不存在）

- [ ] **Step 4: 实现 parse_rss**

`fetch_charts.py` 追加：

```python
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
```

- [ ] **Step 5: 运行确认通过**

Run: `python3 -m unittest tests.test_fetch_charts -v`
Expected: 全部 PASS

- [ ] **Step 6: 提交**

```bash
git add fetch_charts.py tests/
git commit -m "feat: iTunes RSS 榜单解析

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: 畅销榜分类过滤 filter_utilities

**Files:**
- Create: `tests/fixtures/rss_mixed_genres.json`
- Modify: `fetch_charts.py`、`tests/test_fetch_charts.py`

**Interfaces:**
- Consumes: `parse_rss` 的输出结构
- Produces: `filter_utilities(apps) -> list[dict]`，保留 `genre_id == "6002"`，rank 重排

- [ ] **Step 1: 写 fixture（模拟畅销榜忽略 genre 参数返回混合分类）**

`tests/fixtures/rss_mixed_genres.json`：

```json
{
  "feed": {
    "entry": [
      {
        "id": {"attributes": {"im:id": "100001"}},
        "im:name": {"label": "Utility A"},
        "im:artist": {"label": "Dev A"},
        "category": {"attributes": {"im:id": "6002"}}
      },
      {
        "id": {"attributes": {"im:id": "100002"}},
        "im:name": {"label": "Game B"},
        "im:artist": {"label": "Dev B"},
        "category": {"attributes": {"im:id": "6014"}}
      },
      {
        "id": {"attributes": {"im:id": "100003"}},
        "im:name": {"label": "Utility C"},
        "im:artist": {"label": "Dev C"},
        "category": {"attributes": {"im:id": "6002"}}
      }
    ]
  }
}
```

- [ ] **Step 2: 写失败测试**

```python
class TestFilterUtilities(unittest.TestCase):
    def test_filters_non_utilities_and_reranks(self):
        text = (FIXTURES / "rss_mixed_genres.json").read_text(encoding="utf-8")
        apps = fetch_charts.parse_rss(text)
        kept = fetch_charts.filter_utilities(apps)
        self.assertEqual([a["track_id"] for a in kept], ["100001", "100003"])
        self.assertEqual([a["rank"] for a in kept], [1, 2])
```

- [ ] **Step 3: 运行确认失败**

Run: `python3 -m unittest tests.test_fetch_charts.TestFilterUtilities -v`
Expected: ERROR

- [ ] **Step 4: 实现**

`fetch_charts.py` 追加：

```python
def filter_utilities(apps: list[dict]) -> list[dict]:
    """只保留工具类并按剩余顺序重排名次。

    畅销榜接口可能忽略 genre 参数，统一在客户端过滤，对两种情况都正确。
    """
    kept = [a for a in apps if a["genre_id"] == UTILITIES_GENRE_ID]
    for rank, a in enumerate(kept, 1):
        a["rank"] = rank
    return kept
```

- [ ] **Step 5: 运行确认通过 + 提交**

Run: `python3 -m unittest tests.test_fetch_charts -v` → 全部 PASS

```bash
git add fetch_charts.py tests/
git commit -m "feat: 畅销榜工具类客户端过滤

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4: 去重合并与最佳排名 merge_apps / best_rank_key

**Files:**
- Modify: `fetch_charts.py`、`tests/test_fetch_charts.py`

**Interfaces:**
- Consumes: `parse_rss` 输出结构；`CHART_PRIORITY`
- Produces:
  - `best_rank_key(ranks: dict) -> tuple | None`：`ranks={cc:{chart:rank}}` → `(优先级数字, rank)`，取最小
  - `merge_apps(chart_results) -> dict[str, dict]`：值结构
    `{track_id, name, artist, ranks: {cc: {chart: rank}}, regions: [cc, ...]（首次上榜顺序）, best_chart: str, best_rank: int}`

- [ ] **Step 1: 写失败测试**

```python
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
```

- [ ] **Step 2: 运行确认失败**

Run: `python3 -m unittest tests.test_fetch_charts.TestMergeApps -v`
Expected: ERROR

- [ ] **Step 3: 实现**

`fetch_charts.py` 追加：

```python
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

    regions 按首次上榜顺序记录；第一个区域用于后续 lookup 的本地化。
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

- [ ] **Step 4: 运行确认通过 + 提交**

Run: `python3 -m unittest tests.test_fetch_charts -v` → 全部 PASS

```bash
git add fetch_charts.py tests/
git commit -m "feat: 榜单去重合并与最佳排名计算

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 5: lookup 详情解析 parse_lookup / chunk_ids

**Files:**
- Create: `tests/fixtures/lookup.json`
- Modify: `fetch_charts.py`、`tests/test_fetch_charts.py`

**Interfaces:**
- Consumes: 无（解析独立）
- Produces:
  - `chunk_ids(ids, size=200) -> list[list[str]]`
  - `parse_lookup(text) -> dict[str, dict]`，值 `{name, description, developer, genres: list, price, rating: float|None, rating_count: int|None, release_date, track_view_url}`（lookup 无内购字段，变现模式由 AI 从价格+描述推断）

- [ ] **Step 1: 写 fixture（真实 lookup 响应浓缩）**

`tests/fixtures/lookup.json`：

```json
{
  "resultCount": 2,
  "results": [
    {
      "trackId": 111111,
      "trackName": "Example Cleaner",
      "sellerName": "Example Inc.",
      "description": "Clean your phone. Free up storage.",
      "genres": ["Utilities", "Productivity"],
      "formattedPrice": "Free",
      "averageUserRating": 4.7,
      "userRatingCount": 128000,
      "currentVersionReleaseDate": "2026-08-01T00:00:00Z",
      "trackViewUrl": "https://apps.apple.com/us/app/id111111"
    },
    {
      "trackId": 222222,
      "trackName": "Example VPN Pro",
      "sellerName": "Example KK.",
      "description": "Fast and secure VPN.",
      "genres": ["Utilities"],
      "formattedPrice": "$4.99",
      "averageUserRating": null,
      "userRatingCount": 0,
      "trackViewUrl": "https://apps.apple.com/us/app/id222222"
    }
  ]
}
```

- [ ] **Step 2: 写失败测试**

```python
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
```

- [ ] **Step 3: 运行确认失败**

Run: `python3 -m unittest tests.test_fetch_charts.TestLookup -v`
Expected: ERROR

- [ ] **Step 4: 实现**

`fetch_charts.py` 追加：

```python
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
```

- [ ] **Step 5: 运行确认通过 + 提交**

Run: `python3 -m unittest tests.test_fetch_charts -v` → 全部 PASS

```bash
git add fetch_charts.py tests/
git commit -m "feat: lookup 详情解析与 id 分块

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 6: HTTP 层 http_get（重试）与节流

**Files:**
- Modify: `fetch_charts.py`、`tests/test_fetch_charts.py`

**Interfaces:**
- Consumes: 无
- Produces: `http_get(url, opener=urllib.request.urlopen, sleep=time.sleep) -> str | None`——共尝试 `1 + RETRY_LIMIT` 次，失败间隔 `RETRY_DELAY`，全失败返回 None。opener/sleep 可注入供测试。

- [ ] **Step 1: 写失败测试**

```python
from unittest import mock
import urllib.error


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
```

（`from unittest import mock` 放到文件 import 区。）

- [ ] **Step 2: 运行确认失败**

Run: `python3 -m unittest tests.test_fetch_charts.TestHttpGet -v`
Expected: ERROR

- [ ] **Step 3: 实现**

`fetch_charts.py` 头部补 `import time`、`import urllib.error`、`import urllib.request`，追加：

```python
def http_get(url, opener=urllib.request.urlopen, sleep=time.sleep):
    """GET 并返回响应文本；重试 RETRY_LIMIT 次，全失败返回 None。"""
    last_exc = None
    for attempt in range(1 + RETRY_LIMIT):
        try:
            with opener(url, timeout=30) as resp:
                return resp.read().decode("utf-8")
        except (urllib.error.URLError, OSError) as exc:
            last_exc = exc
            if attempt < RETRY_LIMIT:
                sleep(RETRY_DELAY)
    print(f"  请求失败（已重试 {RETRY_LIMIT} 次）: {url} ({last_exc})", flush=True)
    return None
```

- [ ] **Step 4: 运行确认通过 + 提交**

Run: `python3 -m unittest tests.test_fetch_charts -v` → 全部 PASS

```bash
git add fetch_charts.py tests/
git commit -m "feat: HTTP 抓取层（重试与可注入依赖）

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 7: 主流程编排 run() 与 CLI main()

**Files:**
- Modify: `fetch_charts.py`、`tests/test_fetch_charts.py`

**Interfaces:**
- Consumes: 上述全部函数；`DEFAULT_CONFIG`
- Produces:
  - `run(config, data_dir, refresh=False, sleep=time.sleep, opener=urllib.request.urlopen) -> dict`（meta）。行为：
    - `data_dir` 已存在且含 `apps.json` 且非 refresh → 直接读回 meta 返回（stdout 提示复用）
    - 抓取：`https://itunes.apple.com/{cc}/rss/{CHART_KEYS[chart]}/limit={top_n}/genre=6002/json`，原始响应存 `raw/{cc}_{chart}.json`；grossing 解析后过 `filter_utilities`（free/paid 也过，逻辑统一无害）；每次请求前 `sleep(REQUEST_INTERVAL)`
    - 失败区域/榜单记入 `meta["skipped"]: ["{cc}_{chart}", ...]`
    - lookup：按 `regions[0]` 分组 track_id，chunk 后请求 `https://itunes.apple.com/lookup?id={ids}&country={cc}`，详情合并进记录
    - 落盘 `apps.json`（按 best_rank_key 排序的列表）、`meta.json`（含 `generated_at` 仅日期字符串、`skipped`、`app_count`、`region_count`）
    - 全部榜单都失败 → meta["all_failed"] = True
  - `main(argv=None) -> int`：参数 `--config`（默认 `config.json`）、`--date`（默认今天 `%Y-%m-%d`）、`--refresh`；`all_failed` 时返回 1

- [ ] **Step 1: 写失败测试（mock 掉网络与时间）**

```python
class TestRun(unittest.TestCase):
    RSS = (FIXTURES / "rss_utilities.json").read_text(encoding="utf-8")
    LOOKUP = (FIXTURES / "lookup.json").read_text(encoding="utf-8")

    def _run(self, td, charts=("free",), regions=("us",), refresh=False):
        cfg = {"regions": list(regions), "charts": list(charts), "top_n": 5}
        opener = mock.MagicMock(return_value=mock.MagicMock(
            __enter__=lambda s: mock.MagicMock(read=lambda: self.RSS.encode()),
            __exit__=lambda *a: False))
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
            self.assertIn("description", apps[0])          # lookup 详情已合并
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
```

注：测试文件顶部需同时有 `import urllib.error`（Task 6 已加）。

- [ ] **Step 2: 运行确认失败**

Run: `python3 -m unittest tests.test_fetch_charts.TestRun -v`
Expected: ERROR（`run` 不存在）

- [ ] **Step 3: 实现 run 与 main**

`fetch_charts.py` 追加：

```python
RSS_URL = "https://itunes.apple.com/{cc}/rss/{chart_key}/limit={limit}/genre={gid}/json"
LOOKUP_URL = "https://itunes.apple.com/lookup?id={ids}&country={cc}"


def run(config, data_dir, refresh=False, sleep=time.sleep,
        opener=urllib.request.urlopen) -> dict:
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
            url = RSS_URL.format(cc=cc, chart_key=CHART_KEYS[chart],
                                 limit=config["top_n"], gid=UTILITIES_GENRE_ID)
            sleep(REQUEST_INTERVAL)
            text = http_get(url, opener=opener, sleep=sleep)
            if text is None:
                skipped.append(f"{cc}_{chart}")
                continue
            (raw_dir / f"{cc}_{chart}.json").write_text(text, encoding="utf-8")
            apps = filter_utilities(parse_rss(text))  # 统一客户端过滤
            chart_results.append((cc, chart, apps))

    merged = merge_apps(chart_results)

    # lookup 补全：按首次上榜区域分组
    by_region = {}
    for rec in merged.values():
        by_region.setdefault(rec["regions"][0], []).append(rec["track_id"])
    for cc, ids in by_region.items():
        for chunk in chunk_ids(ids):
            sleep(REQUEST_INTERVAL)
            text = http_get(LOOKUP_URL.format(ids=",".join(chunk), cc=cc),
                            opener=opener, sleep=sleep)
            if text is None:
                continue  # 详情缺失不致命，分析层降级
            for tid, detail in parse_lookup(text).items():
                if tid in merged:
                    merged[tid]["details"] = detail

    ordered = sorted(merged.values(),
                     key=lambda r: (CHART_PRIORITY[r["best_chart"]], r["best_rank"]))
    apps_path.write_text(json.dumps(ordered, ensure_ascii=False, indent=2),
                         encoding="utf-8")

    meta = {
        "date": data_dir.name,
        "regions": config["regions"],
        "charts": config["charts"],
        "top_n": config["top_n"],
        "app_count": len(ordered),
        "region_count": config["regions"],
        "skipped": skipped,
        "all_failed": len(chart_results) == 0,
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    print(f"完成: {len(ordered)} 个独立 app（跳过 {len(skipped)} 个榜单）", flush=True)
    return meta


def main(argv=None) -> int:
    import argparse
    from datetime import date as _date
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--date", default=_date.today().strftime("%Y-%m-%d"))
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args(argv)

    config = load_config(Path(args.config))
    data_dir = Path("data") / args.date
    meta = run(config, data_dir, refresh=args.refresh)
    return 1 if meta.get("all_failed") else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 运行全部测试确认通过**

Run: `python3 -m unittest tests.test_fetch_charts -v`
Expected: 全部 PASS

- [ ] **Step 5: 提交**

```bash
git add fetch_charts.py tests/
git commit -m "feat: 主流程编排与 CLI（落盘/复用/跳过记录）

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 8: 真实 API 冒烟验证（手动，不进自动测试）

**Files:**
- 无新文件；产出 `data/smoke/`（验证后删除）

**Interfaces:**
- Consumes: Task 7 的完整脚本
- Produces: 对 spec §4.1 端点与字段假设的验证结论（写入本文件勾选记录）

- [ ] **Step 1: 冒烟运行（只跑美区，临时改配置而非改代码）**

```bash
cd "/Users/wangkun/Desktop/AI项目/app榜单分析" && \
  python3 -c "import json;json.dump({'regions':['us'],'charts':['free','paid','grossing'],'top_n':10},open('data_smoke_cfg.json','w'))" && \
  python3 fetch_charts.py --config data_smoke_cfg.json --date smoke
```

Expected: 约 3 个榜单请求 + lookup，终端打印 `完成: N 个独立 app`；退出码 0

- [ ] **Step 2: 人工核验三点**

1. `data/smoke/apps.json` 有 description/评分字段且非空
2. `data/smoke/raw/us_grossing.json` 中 category 是否全为 Utilities——无论是否全为，客户端过滤已保证正确，记录观察结论即可
3. `data/smoke/meta.json` 的 `skipped` 为空

- [ ] **Step 3: 清理冒烟产物**

```bash
rm -rf data/smoke data_smoke_cfg.json
```

- [ ] **Step 4: 提交（如有因冒烟发现的修复）**

```bash
git add -A && git commit -m "fix: 真实 API 冒烟发现的问题修正

Co-Authored-By: Claude <noreply@anthropic.com>"
```

（无修复则跳过本步。）

---

### Task 9: /app-scan 分析 skill

**Files:**
- Create: `.claude/skills/app-scan/SKILL.md`

**Interfaces:**
- Consumes: `data/{日期}/apps.json`（列表，元素含 `track_id/name/artist/ranks/regions/best_chart/best_rank/details{...}`）、`meta.json`（`skipped` 等）
- Produces: `reports/{YYYY-MM-DD}-工具榜分析.md`

- [ ] **Step 1: 写 SKILL.md（完整内容如下）**

```markdown
---
name: app-scan
description: 扫描 App Store 非国区工具榜并生成中文分析报告。用法：/app-scan [light|standard|deep] [--refresh]。触发词：扫榜、工具榜分析、app榜单。
---

# App Store 工具榜扫描分析

分析 `data/{今天日期 YYYY-MM-DD}/apps.json` 中的非国区工具榜数据，
生成中文分析报告到 `reports/{日期}-工具榜分析.md`。

## 参数解析

从用户输入解析：模式 `light` / `standard`（默认）/ `deep`，以及 `--refresh`。

## 流程

1. **取数**：若 `data/{日期}/apps.json` 不存在或带 `--refresh`，
   先运行 `python3 fetch_charts.py [--refresh]`（工作目录为项目根）。
   脚本失败（退出码非 0）→ 向用户报告错误并停止。
2. **读数据**：读 `apps.json`（已按最佳排名排序）与 `meta.json`。
   `meta.json` 的 `skipped` 非空 → 报告"本期总览"须注明缺失的区域/榜单。
3. **类型分布**（所有模式）：把 app 归入细分赛道（如 清理加速 / 网络VPN /
   文件管理 / 格式转换 / 效率工具 / 安全隐私 / 输入法 / 小组件壁纸 /
   扫描识别 / 测试与其他）。依据 `details.genres`、名称与描述关键词。
   统计各赛道数量与占比，指出跨区域共性赛道与区域特色赛道。
4. **分层分析**：
   - `light`：无逐个详析，全部表格化。
   - `standard`：取前 120 个逐个详析，其余表格化。
   - `deep`：取前 30 个逐个详析；对其中每个，再用 WebFetch 抓
     `https://itunes.apple.com/{regions[0]}/rss/customerreviews/id={track_id}/sortBy=mostRecent/page=1/json`
     提炼好评/差评主题，并抓 `details.track_view_url`（App Store 页面）补充
     截图描述与"App 隐私"等页面信息（两处都抓不到就跳过并标注"信息有限"）。
5. **写报告**到 `reports/{日期}-工具榜分析.md`，结构见下。
6. 最后向用户输出 3-5 句执行摘要（本期亮点赛道、值得注意的 app）。

## 重点 app 详析格式（standard/deep 共用）

每个 app 一小节：核心功能（2-4 条中文）/ 目标用户与场景 /
变现模式（免费、买断、订阅、内购或广告——从 `details.price` 与描述推断）/
一句点评（上榜原因或可借鉴之处）。
`details` 缺失的 app：基于名称与分类推断，并标注"信息有限"。

## 报告结构

1. **本期总览**：日期、区域数、各榜 app 数、数据完整性（skipped）
2. **类型分布**：细分赛道表格（数量/占比/代表 app）+ 共性 vs 区域特色分析
3. **重点 App 分析**：按细分赛道分组逐个详析（数量按模式）
4. **完整榜单表格**：分区域 × 分榜单，列=排名/名称/开发者/评分/价格
5. **观察与机会**：3-6 条跨区域趋势观察与机会点

## 约束

- 全程中文输出；app 名称保留原文（可附中文释义）
- 报告中数字必须来自数据文件，不臆造
- light 模式整份报告控制在 300 行内
```

- [ ] **Step 2: light 模式验收**

在项目目录 Claude Code 会话运行 `/app-scan light`（当天数据不存在会先抓全量 10 区域，约 2-3 分钟）。
Expected: `reports/{今天}-工具榜分析.md` 生成，含 5 节结构、类型分布表、完整榜单表，≤300 行。

- [ ] **Step 3: 提交**

```bash
git add .claude/
git commit -m "feat: /app-scan 分析 skill

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 10: launchd 定时任务

**Files:**
- Create: `scripts/install_launchd.sh`

**Interfaces:**
- Consumes: Task 9 的 `/app-scan`
- Produces: `~/Library/LaunchAgents/com.appcharts.scan.plist`（每周一 09:30 触发）；脚本支持 `install` / `uninstall` / `verify` 三个子命令

- [ ] **Step 1: 写安装脚本**

`scripts/install_launchd.sh`：

```bash
#!/bin/zsh
# 安装/卸载/验证 App 榜单扫描的 launchd 定时任务
# 用法: scripts/install_launchd.sh install|uninstall|verify

set -euo pipefail
LABEL="com.appcharts.scan"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "${PROJECT_DIR}/logs}"

case "${1:-}" in
install)
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
    <string>cd '${PROJECT_DIR}' && claude -p '/app-scan standard' >> '${PROJECT_DIR}/logs/scan-\$(date +%F).log' 2>&1</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Weekday</key><integer>1</integer>
    <key>Hour</key><integer>9</integer>
    <key>Minute</key><integer>30</integer>
  </dict>
  <key>StandardOutPath</key><string>${PROJECT_DIR}/logs/launchd.out</string>
  <key>StandardErrorPath</key><string>${PROJECT_DIR}/logs/launchd.err</string>
</dict>
</plist>
EOF
  launchctl unload "$PLIST" 2>/dev/null || true
  launchctl load "$PLIST"
  echo "已安装: $PLIST（每周一 09:30 运行）"
  "$0" verify
  ;;
uninstall)
  launchctl unload "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
  echo "已卸载: $PLIST"
  ;;
verify)
  launchctl list | grep -q "$LABEL" && echo "✓ launchd 任务已加载" || { echo "✗ 未加载"; exit 1; }
  CLAUDE_BIN="$(zsh -lc 'command -v claude' || true)"
  [ -n "$CLAUDE_BIN" ] && echo "✓ claude 可用: $CLAUDE_BIN" || { echo "✗ 登录 shell 找不到 claude"; exit 1; }
  ;;
*)
  echo "用法: $0 install|uninstall|verify"; exit 1
  ;;
esac
```

- [ ] **Step 2: 加执行权限并验证**

```bash
chmod +x scripts/install_launchd.sh && scripts/install_launchd.sh verify
```

Expected: 输出 claude 可用路径（若 `✗`，检查 claude 安装方式后再继续）

- [ ] **Step 3: 安装并确认**

```bash
scripts/install_launchd.sh install && launchctl list | grep com.appcharts.scan
```

Expected: 列表中有 `com.appcharts.scan`

- [ ] **Step 4: 手动触发一次验证端到端（不等周一）**

```bash
launchctl start com.appcharts.scan && sleep 60 && tail -5 logs/launchd.out logs/scan-*.log 2>/dev/null
```

Expected: 日志出现 claude 运行痕迹；当天报告生成或日志中有可读的错误信息

- [ ] **Step 5: 提交**

```bash
git add scripts/
git commit -m "feat: launchd 每周定时任务与安装脚本

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 11: README 与最终验收

**Files:**
- Create: `README.md`

**Interfaces:**
- Consumes: 全部
- Produces: 使用文档

- [ ] **Step 1: 写 README**

```markdown
# App Store 非国区工具榜扫描

定期抓取 10 个区域（美/英/德/法/日/韩/港/台/新/泰）的 App Store
工具类免费/付费/畅销榜，AI 分析每个上榜 App 的功能与类型分布，
产出中文报告。设计文档见 `docs/superpowers/specs/`。

## 使用

    # 手动扫描（默认 standard 档）
    /app-scan
    # 快速扫榜 / 深度研究
    /app-scan light
    /app-scan deep
    # 强制重抓当天数据
    /app-scan --refresh

只抓数据不分析：`python3 fetch_charts.py [--date YYYY-MM-DD] [--refresh]`

## 定时任务

    scripts/install_launchd.sh install    # 安装（每周一 09:30）
    scripts/install_launchd.sh verify     # 检查任务与 claude 可用性
    scripts/install_launchd.sh uninstall  # 卸载

## 配置

`config.json`：`regions`（区域码）、`charts`（free/paid/grossing）、`top_n`。

## 目录

- `data/{日期}/`：原始 RSS（raw/）、合并清单（apps.json）、运行元信息（meta.json）
- `reports/`：中文分析报告
- `logs/`：定时任务日志

## 测试

    python3 -m unittest discover tests -v
```

- [ ] **Step 2: 全量验收**

1. `python3 -m unittest discover tests -v` → 全部 PASS
2. `/app-scan`（standard 全量）→ 报告含 Top 120 详析、类型分布、五节结构完整
3. 检查 `data/{今天}/meta.json` 的 `skipped`，与报告"本期总览"注明一致

- [ ] **Step 3: 提交**

```bash
git add README.md
git commit -m "docs: 使用说明

Co-Authored-By: Claude <noreply@anthropic.com>"
```
