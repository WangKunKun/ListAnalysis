"""平台无关的榜单抓取编排：配置、去重合并、落盘、CLI。"""

import json
from pathlib import Path

# 榜单抽象名（两平台共用）；平台 API 值的映射在各自适配器内
VALID_CHARTS = {"free", "paid", "grossing"}
# 最佳排名优先级：数字越小越优先
CHART_PRIORITY = {"free": 0, "paid": 1, "grossing": 2}

DEFAULT_CONFIG = {
    "regions": ["us", "gb", "de", "fr", "jp", "kr", "hk", "tw", "sg", "th"],
    "charts": ["free", "paid", "grossing"],
    "top_n": 50,
}


def load_config(path: Path) -> dict:
    """读取配置，缺省字段用 DEFAULT_CONFIG 补齐；charts 含未知值时报错。

    顶层为公共默认；"ios"/"play" 键为平台覆盖子字典，原样保留由调用方合并。
    """
    cfg = dict(DEFAULT_CONFIG)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            cfg.update(json.load(f))
    unknown = set(cfg["charts"]) - VALID_CHARTS
    if unknown:
        raise ValueError(f"未知榜单类型: {sorted(unknown)}，可选: {sorted(VALID_CHARTS)}")
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

    regions 按首次上榜顺序记录；第一个区域用于后续详情请求的本地化。
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
