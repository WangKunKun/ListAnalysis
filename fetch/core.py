"""平台无关的榜单抓取编排：配置、去重合并、落盘、CLI。"""

import json
import time
from pathlib import Path

from fetch.adapters import get_adapter

__all__ = [
    "VALID_CHARTS", "CHART_PRIORITY", "DEFAULT_CONFIG",
    "load_config", "best_rank_key", "merge_apps", "run", "main", "get_adapter",
]

# 榜单抽象名（两平台共用）；平台 API 值的映射在各自适配器内
VALID_CHARTS = {"free", "paid", "grossing"}
# 最佳排名优先级：数字越小越优先
CHART_PRIORITY = {"free": 0, "paid": 1, "grossing": 2}

DEFAULT_CONFIG = {
    "regions": ["us", "gb", "de", "fr", "jp", "kr", "hk", "tw", "sg", "th"],
    "charts": ["free", "paid", "grossing"],
    "top_n": 50,
}


def _validate_charts(cfg: dict) -> None:
    """校验 cfg["charts"] 只含已知榜单，否则抛 ValueError。"""
    unknown = set(cfg["charts"]) - VALID_CHARTS
    if unknown:
        raise ValueError(f"未知榜单类型: {sorted(unknown)}，可选: {sorted(VALID_CHARTS)}")


def load_config(path: Path) -> dict:
    """读取配置，缺省字段用 DEFAULT_CONFIG 补齐；charts 含未知值时报错。

    顶层为公共默认；"ios"/"play" 键为平台覆盖子字典，原样保留由调用方合并
    （平台子字典中的 charts 由调用方合并后自行校验）。
    """
    cfg = dict(DEFAULT_CONFIG)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            cfg.update(json.load(f))
    _validate_charts(cfg)
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


def run(adapter, config, data_dir, refresh=False, sleep=time.sleep) -> dict:
    """抓取并落盘。注意：raw/ 目录存的是解析后的统一 apps 结构（便于 diff
    与跨平台一致），并非原始 HTTP 响应文本。
    """
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

    # 详情补全：detail_top_n 截断（None=不限）；按首次上榜区域分组请求
    detail_top_n = config.get("detail_top_n")
    target = ordered[:detail_top_n] if detail_top_n is not None else ordered
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
    print(f"完成[{adapter.name}]: {len(ordered)} 个独立 app（跳过 {len(skipped)} 个榜单）",
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
            cfg.setdefault("detail_top_n", 150)  # spec §6 默认，config 可覆盖
        try:
            _validate_charts(cfg)
        except ValueError as exc:
            print(f"平台 {p} 配置错误: {exc}", flush=True)
            rc = 1
            continue
        try:
            adapter = get_adapter(p)()
        except SystemExit:
            raise  # 依赖缺失等明确退出场景：原样传播退出码
        except Exception as exc:
            print(f"平台 {p} 初始化失败: {exc}", flush=True)
            rc = 1
            continue
        meta = run(adapter, cfg, Path("data") / args.date / p, refresh=args.refresh)
        if meta.get("all_failed"):
            rc = 1
    return rc
