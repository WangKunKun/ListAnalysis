"""App Store（iOS）适配器：iTunes RSS 榜单与 lookup 详情，纯标准库。"""

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

    畅销榜接口可能忽略 genre 参数，统一在客户端过滤，对两种情况都正确。
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
