"""Google Play（Android）适配器：google-play-scraper 封装（运行时导入）。"""

import sys
import time

from .ios import RETRY_LIMIT, RETRY_DELAY  # 复用重试常量语义

CHARTS = {"free": "TOP_FREE", "paid": "TOP_PAID", "grossing": "TOP_GROSSING"}
CATEGORY_TOOLS = "TOOLS"
DETAIL_INTERVAL = 1.0


def check_dependency():
    """未安装 google-play-scraper 时以退出码 2 终止。"""
    try:
        import google_play_scraper  # noqa: F401
    except ImportError:
        print("错误: Play 适配器需要 google-play-scraper。"
              "请先运行: pip3 install -r requirements.txt", file=sys.stderr, flush=True)
        raise SystemExit(2)


def normalize_top(raw: list) -> list[dict]:
    """top() 返回 → 统一榜单元素；字段缺失容忍。"""
    apps = []
    for rank, r in enumerate(raw, 1):
        apps.append({
            "track_id": r.get("appId", ""),
            "name": r.get("title", ""),
            "artist": r.get("developer", ""),
            "genre_id": r.get("genreId", ""),
            "rank": rank,
        })
    return apps


def normalize_app(d: dict) -> dict:
    """app() 返回 → 统一 details（公共字段与 iOS 同名 + Play 特有键）。"""
    genres = [d["genre"]] if d.get("genre") else []
    genres += [c["name"] for c in d.get("categories", []) if c.get("name")]
    if d.get("free"):
        price = "Free"
    else:
        price = f'{d.get("currency", "")} {d.get("price", 0)}'.strip()
    return {
        "name": d.get("title", ""),
        "developer": d.get("developer", ""),
        "description": d.get("description", ""),
        "genres": genres,
        "price": price,
        "rating": d.get("score"),
        "rating_count": d.get("ratings"),
        "release_date": d.get("released", ""),
        "track_view_url": d.get("url", ""),
        "installs": d.get("installs", ""),
        "min_installs": d.get("minInstalls"),
        "offers_iap": d.get("offersIAP"),
        "iap_price": d.get("inAppProductPrice"),
        "contains_ads": d.get("containsAds"),
        "updated": d.get("updated"),
    }


class PlayAdapter:
    name = "play"
    request_interval = 3.0

    def __init__(self, lib=None):
        # lib 注入供测试；真实运行时检查依赖并导入
        if lib is None:
            check_dependency()
            import google_play_scraper
            lib = google_play_scraper
        self._lib = lib

    def fetch_chart(self, cc, chart, top_n, sleep=time.sleep, top_fn=None):
        top = top_fn or self._lib.top
        last_exc = None
        for attempt in range(1 + RETRY_LIMIT):
            try:
                raw = top(collection=CHARTS[chart], category=CATEGORY_TOOLS,
                          num=top_n, country=cc, lang="en")
                return normalize_top(raw)
            except Exception as exc:  # 库异常类型不稳定，统一防御
                last_exc = exc
                if attempt < RETRY_LIMIT:
                    sleep(RETRY_DELAY)
        print(f"  请求失败（已重试 {RETRY_LIMIT} 次）: play {cc} {chart} ({last_exc})",
              flush=True)
        return None

    def fetch_details(self, ids, cc, sleep=time.sleep, app_fn=None):
        app = app_fn or self._lib.app
        out = {}
        for app_id in ids:
            sleep(DETAIL_INTERVAL)
            try:
                d = app(app_id, country=cc, lang="en")
            except Exception as exc:
                print(f"  详情失败（跳过）: {app_id} ({exc})", flush=True)
                continue
            out[app_id] = normalize_app(d)
        return out
