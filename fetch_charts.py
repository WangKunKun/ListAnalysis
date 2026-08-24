#!/usr/bin/env python3
"""抓取 App Store 非国区工具（Utilities）榜单，去重合并并补全详情。

仅使用 Python 标准库。数据落盘 data/{日期}/，元信息见 meta.json。
"""

import json
import time
import urllib.request
from pathlib import Path

from fetch.adapters import ios as _ios

# 兼容 re-export：旧调用方（fetch_charts.parse_rss 等）不受影响
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

# 最佳排名优先级：数字越小越优先（spec §4.2）
CHART_PRIORITY = {"free": 0, "paid": 1, "grossing": 2}

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
