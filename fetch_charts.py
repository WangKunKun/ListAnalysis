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

    畅销榜接口可能忽略 genre 参数，统一在客户端过滤，对两种情况都正确。
    """
    kept = [a for a in apps if a["genre_id"] == UTILITIES_GENRE_ID]
    for rank, a in enumerate(kept, 1):
        a["rank"] = rank
    return kept
