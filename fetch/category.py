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
        stats[result.get("platform", p)] = result
        if result.get("all_failed"):
            print(f"平台 {p} 全部关键词搜索失败（检查网络/代理）", flush=True)
            rc = 1

    # 复用的平台沿用旧 meta 里的统计,避免覆盖丢失
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
