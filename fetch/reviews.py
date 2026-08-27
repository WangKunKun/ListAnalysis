"""评论抓取管线:iOS iTunes RSS / Play 桥 reviews 命令 → 落盘缓存。

app-scan(deep) 与 cat-scan(standard) 共用,替代各自内联的临时评论脚本;
评论落盘 data/{日期}/reviews/{platform}/{track_id}.json(数组 [{score,text}]),
已存在的 app 自动跳过(缓存),跨 skill/跨次运行不重复抓。
"""

import argparse
import json
import time
from datetime import date as _date
from pathlib import Path

__all__ = ["parse_ios_reviews", "normalize_play_reviews",
           "fetch_and_save", "main"]

REVIEWS_URL = ("https://itunes.apple.com/{cc}/rss/customerreviews/"
               "id={tid}/sortBy=mostRecent/page={page}/json")
MAX_PAGES = 2  # 每页约 50 条,2 页对痛点提炼已足够


def parse_ios_reviews(text: str) -> list:
    """解析 iTunes 评论 RSS JSON → [{score, text}, ...]。"""
    feed = json.loads(text).get("feed", {})
    entries = feed.get("entry", [])
    if isinstance(entries, dict):  # 仅 1 条时是 dict
        entries = [entries]
    out = []
    for e in entries:
        rating = e.get("im:rating", {}).get("label", "")
        text_val = e.get("content", {}).get("label", "")
        score = int(rating) if rating.isdigit() else None
        out.append({"score": score, "text": text_val})
    return out


def normalize_play_reviews(raw):
    """桥 reviews 输出([{score,text},...])透传统一;None 透传。"""
    if raw is None:
        return None
    return [{"score": r.get("score"), "text": r.get("text") or ""}
            for r in raw]


def fetch_and_save(adapter, track_ids, country, out_dir: Path, num=100,
                   sleep=time.sleep) -> dict:
    """逐 app 抓评论落盘 {track_id}.json;已存在跳过(缓存),失败容忍。

    返回 {"saved": [...], "cached": [...], "failed": [...]};
    failed 不落盘,下次运行自然重试。
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    saved, cached, failed = [], [], []
    for tid in track_ids:
        path = out_dir / f"{tid}.json"
        if path.exists():
            cached.append(tid)
            continue
        result = adapter.fetch_reviews(tid, country, num=num)
        if result is None:
            failed.append(tid)
            continue
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2),
                        encoding="utf-8")
        saved.append(tid)
        sleep(adapter.request_interval)
    return {"saved": saved, "cached": cached, "failed": failed}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", required=True, choices=["ios", "play"])
    parser.add_argument("--ids", required=True, help="逗号分隔 track_id/appId")
    parser.add_argument("--country", default="us")
    parser.add_argument("--num", type=int, default=100)
    parser.add_argument("--date", default=_date.today().strftime("%Y-%m-%d"))
    args = parser.parse_args(argv)

    ids = [t.strip() for t in args.ids.split(",") if t.strip()]
    if not ids:
        print("错误: --ids 不能为空", flush=True)
        return 1

    from fetch.adapters import get_adapter
    try:
        adapter = get_adapter(args.platform)()
    except SystemExit:
        raise  # 依赖缺失等明确退出场景:原样传播退出码
    out_dir = Path("data") / args.date / "reviews" / args.platform
    stats = fetch_and_save(adapter, ids, args.country, out_dir, num=args.num)
    print(f"评论[{args.platform}]: 新抓 {len(stats['saved'])} / 缓存 "
          f"{len(stats['cached'])} / 失败 {len(stats['failed'])}"
          + (f"({','.join(stats['failed'])})" if stats["failed"] else ""),
          flush=True)
    return 1 if not stats["saved"] and not stats["cached"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
