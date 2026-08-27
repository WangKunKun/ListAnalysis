"""Google Play（Android）适配器：经 Node 桥接（scripts/play_bridge.mjs）调用 google-play-scraper。"""

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from .ios import RETRY_LIMIT, RETRY_DELAY  # 复用重试常量语义

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

CHARTS = {"free": "TOP_FREE", "paid": "TOP_PAID", "grossing": "GROSSING"}
CATEGORY_TOOLS = "TOOLS"

BRIDGE_TIMEOUT = 60  # 无代理（黑洞网络）时快速放弃，避免长时间挂起
DETAIL_BATCH = 30  # 桥内节流约 300ms/个，30×~0.8s≈24s < 60s 超时余量充足
DETAIL_INTERVAL = 1.0  # 详情批间隔


def _bridge_with_retry(call, describe, sleep, retry_limit=RETRY_LIMIT):
    """执行一次桥调用并按需重试;超时立即放弃(不重试)。

    call: 无参函数,返回解析结果(内部抛异常表示可重试失败);
    describe: 失败消息里的定位描述。返回结果或 None。
    """
    last_exc = None
    for attempt in range(1 + retry_limit):
        try:
            return call()
        except subprocess.TimeoutExpired:
            print(f"  桥接超时（放弃，不重试）: {describe}", flush=True)
            return None
        except Exception as exc:
            last_exc = exc
            if attempt < retry_limit:
                sleep(RETRY_DELAY)
    print(f"  请求失败（已重试 {retry_limit} 次）: {describe} ({last_exc})",
          flush=True)
    return None


def check_dependency():
    """node 或 npm 依赖缺失时以退出码 2 终止。"""
    if not shutil.which("node"):
        print("错误: Play 适配器需要 Node.js。请先安装 node。", file=sys.stderr, flush=True)
        raise SystemExit(2)
    probe = subprocess.run(
        ["node", "-e", "require('google-play-scraper')"],
        capture_output=True, cwd=PROJECT_ROOT)
    if probe.returncode != 0:
        print("错误: Play 适配器缺少 npm 依赖。请先在项目根运行: npm install",
              file=sys.stderr, flush=True)
        raise SystemExit(2)


def _run_bridge(payload, timeout=BRIDGE_TIMEOUT, runner=None):
    """调 scripts/play_bridge.mjs，返回解析后的 JSON；失败返回 None。"""
    run = runner or subprocess.run
    proc = run(["node", str(PROJECT_ROOT / "scripts" / "play_bridge.mjs")],
               input=json.dumps(payload), capture_output=True, text=True,
               timeout=timeout, cwd=str(PROJECT_ROOT))
    if proc.returncode != 0:
        err = (proc.stderr or "").strip().splitlines()
        print(f"  桥接失败（rc={proc.returncode}）: {err[-1] if err else '未知错误'}",
              flush=True)
        return None
    try:
        return json.loads(proc.stdout)
    except (json.JSONDecodeError, ValueError):
        print("  桥接输出无法解析为 JSON", flush=True)
        return None


def normalize_top(raw: list) -> list[dict]:
    """gplay.list 返回 → 统一榜单元素；字段缺失容忍。"""
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
    """gplay.app 返回 → 统一 details（公共字段与 iOS 同名 + Play 特有键）。"""
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
        # Node 版字段名是 adSupported,Python 版是 containsAds,两者兼容
        "contains_ads": d.get("containsAds", d.get("adSupported")),
        "updated": d.get("updated"),
    }


def normalize_search(raw: list) -> list[dict]:
    """gplay.search 返回 → 统一样本元素（无详情；详情由 fetch_details 补）。"""
    return [{
        "track_id": r.get("appId", ""),
        "name": r.get("title", ""),
        "artist": r.get("developer", ""),
    } for r in raw]


class PlayAdapter:
    name = "play"
    request_interval = 3.0

    def __init__(self, runner=None):
        # runner 注入 subprocess.run 供测试；真实运行时检查依赖
        if runner is None:
            check_dependency()
        self._runner = runner

    def fetch_chart(self, cc, chart, top_n, sleep=time.sleep, bridge_fn=None):
        bridge = bridge_fn or _run_bridge
        collection = CHARTS[chart]  # 循环外取，KeyError 不进重试

        def call():
            raw = bridge({"cmd": "list", "collection": collection,
                          "category": CATEGORY_TOOLS, "num": top_n,
                          "country": cc, "lang": "en"},
                         runner=self._runner)
            if raw is None:
                raise RuntimeError("bridge returned None")
            return normalize_top(raw)

        return _bridge_with_retry(call, f"play {cc} {chart}", sleep)

    def fetch_details(self, ids, cc, sleep=time.sleep, bridge_fn=None):
        """批量拉详情；按 DETAIL_BATCH 分批，超时批丢弃不炸流程。

        sleep 参数为兼容 core 统一签名保留（Play 的节流在桥内，此参数忽略）。
        """
        bridge = bridge_fn or _run_bridge
        out = {}
        id_list = list(ids)
        for start in range(0, len(id_list), DETAIL_BATCH):
            batch = id_list[start:start + DETAIL_BATCH]
            if start > 0:
                time.sleep(DETAIL_INTERVAL)
            try:
                raw = bridge({"cmd": "apps", "ids": batch, "country": cc,
                              "lang": "en"}, runner=self._runner)
            except subprocess.TimeoutExpired:
                print(f"  详情批超时（跳过该批 {len(batch)} 个）", flush=True)
                continue
            if raw is None:
                print(f"  详情批失败（跳过该批 {len(batch)} 个）", flush=True)
                continue
            for app_id, d in raw.items():
                if d is None:
                    print(f"  详情失败（跳过）: {app_id}", flush=True)
                    continue
                out[app_id] = normalize_app(d)
        return out

    def fetch_reviews(self, app_id, cc, num=100, sleep=time.sleep,
                      bridge_fn=None):
        """抓用户评论(桥 reviews 命令,sort=2 最新优先);失败返回 None。

        sleep 参数为兼容签名保留(节流在 fetch.reviews 编排层)。
        """
        from fetch.reviews import normalize_play_reviews  # 延迟导入避免环
        bridge = bridge_fn or _run_bridge
        try:
            raw = bridge({"cmd": "reviews", "appId": app_id, "country": cc,
                          "lang": "en", "num": num, "sort": 2},
                         runner=self._runner)
        except subprocess.TimeoutExpired:
            print(f"  评论抓取超时: play {app_id}", flush=True)
            return None
        return normalize_play_reviews(raw)

    def search_apps(self, term, cc, limit, sleep=time.sleep, bridge_fn=None):
        """Google Play搜索应用

        Args:
            term: 搜索关键词(英文)
            cc: 国家代码
            limit: 返回数量上限
            sleep: 休眠函数
            bridge_fn: 桥接函数(可注入用于测试)

        Returns:
            应用列表，失败返回None
        """
        bridge = bridge_fn or _run_bridge

        def call():
            raw = bridge({"cmd": "search", "term": term, "num": limit,
                          "country": cc, "lang": "en"},
                         runner=self._runner)
            if raw is None:
                raise RuntimeError("bridge returned None")
            return normalize_search(raw)

        return _bridge_with_retry(call, f"play search {term}", sleep)
