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

# 兼容 re-export：纯函数已迁 fetch/core.py
from fetch import core as _core

CHART_PRIORITY = _core.CHART_PRIORITY
DEFAULT_CONFIG = _core.DEFAULT_CONFIG
load_config = _core.load_config
best_rank_key = _core.best_rank_key
merge_apps = _core.merge_apps


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
