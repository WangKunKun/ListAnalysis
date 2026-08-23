#!/usr/bin/env python3
"""抓取 App Store 非国区工具（Utilities）榜单，去重合并并补全详情。

仅使用 Python 标准库。数据落盘 data/{日期}/，元信息见 meta.json。
"""

import http.client
import json
import time
import urllib.error
import urllib.request
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
    """GET 并返回响应文本；重试 RETRY_LIMIT 次，全失败返回 None。"""
    last_exc = None
    for attempt in range(1 + RETRY_LIMIT):
        try:
            with opener(url, timeout=30) as resp:
                return resp.read().decode("utf-8")
        except (urllib.error.URLError, OSError, http.client.HTTPException) as exc:
            last_exc = exc
            if attempt < RETRY_LIMIT:
                sleep(RETRY_DELAY)
    print(f"  请求失败（已重试 {RETRY_LIMIT} 次）: {url} ({last_exc})", flush=True)
    return None


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
