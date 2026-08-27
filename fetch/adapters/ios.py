"""App Store（iOS）适配器：iTunes RSS 榜单与 lookup 详情，纯标准库。"""

import http.client
import json
import time
import urllib.error
import urllib.request
from urllib.parse import quote

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
SEARCH_URL = "https://itunes.apple.com/search?term={term}&country={cc}&entity=software&limit={limit}"


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


class IosAdapter:
    """iTunes RSS + lookup 适配器。"""
    name = "ios"
    request_interval = REQUEST_INTERVAL

    def __init__(self, opener=urllib.request.urlopen):
        self._opener = opener

    def fetch_chart(self, cc, chart, top_n, sleep=time.sleep):
        url = RSS_URL.format(cc=cc, chart_key=CHART_KEYS[chart],
                             limit=top_n, gid=UTILITIES_GENRE_ID)
        text = http_get(url, opener=self._opener, sleep=sleep)
        if text is None:
            return None
        return filter_utilities(parse_rss(text))

    def fetch_details(self, ids, cc, sleep=time.sleep):
        out = {}
        for chunk in chunk_ids(ids):
            sleep(REQUEST_INTERVAL)
            text = http_get(LOOKUP_URL.format(ids=",".join(chunk), cc=cc),
                            opener=self._opener, sleep=sleep)
            if text is None:
                continue  # 详情缺失不致命，分析层降级
            out.update(parse_lookup(text))
        return out

    def search_apps(self, term, cc, limit, sleep=time.sleep):
        """关键词搜索品类样本。Search API 响应与 lookup 同构，
        复用 parse_lookup 解析，详情一次到位（无需再调 lookup）。

        Args:
            term: 搜索关键词(英文)
            cc: 国家代码
            limit: 返回数量上限(API上限200)
            sleep: 休眠函数(可注入用于测试)

        Returns:
            应用列表，失败返回None
        """
        url = SEARCH_URL.format(term=quote(term), cc=cc, limit=limit)
        text = http_get(url, opener=self._opener, sleep=sleep)
        if text is None:
            return None
        details = parse_lookup(text)
        return [{"track_id": tid, "name": d["name"], "artist": d["developer"],
                 "details": d} for tid, d in details.items()]

    def parse_search(text: str) -> list[dict]:
        """解析iTunes搜索响应

        Args:
            text: API响应文本

        Returns:
            应用列表
        """
        data = json.loads(text)
        results = []
        for app in data.get("results", []):
            results.append({
                "track_id": str(app.get("trackId", "")),
                "name": app.get("trackName", ""),
                "artist": app.get("sellerName", ""),
                "details": {
                    "description": app.get("description", ""),
                    "price": app.get("formattedPrice", ""),
                    "rating": app.get("averageUserRating"),
                    "rating_count": app.get("userRatingCount", 0),
                    "genres": app.get("genres", []),
                    "release_date": app.get("currentVersionReleaseDate", ""),
                    "track_view_url": app.get("trackViewUrl", "")
                }
            })
        return results
