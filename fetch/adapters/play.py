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


def _run_bridge(payload, timeout=300, runner=None):
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
        "contains_ads": d.get("containsAds"),
        "updated": d.get("updated"),
    }


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
        last_exc = None
        for attempt in range(1 + RETRY_LIMIT):
            try:
                raw = bridge({"cmd": "list", "collection": collection,
                              "category": CATEGORY_TOOLS, "num": top_n,
                              "country": cc, "lang": "en"},
                             runner=self._runner)
                if raw is None:
                    raise RuntimeError("bridge returned None")
                return normalize_top(raw)
            except KeyError:
                raise
            except Exception as exc:
                last_exc = exc
                if attempt < RETRY_LIMIT:
                    sleep(RETRY_DELAY)
        print(f"  请求失败（已重试 {RETRY_LIMIT} 次）: play {cc} {chart} ({last_exc})",
              flush=True)
        return None

    def fetch_details(self, ids, cc, sleep=time.sleep, bridge_fn=None):
        bridge = bridge_fn or _run_bridge
        raw = bridge({"cmd": "apps", "ids": list(ids), "country": cc, "lang": "en"},
                     runner=self._runner)
        if raw is None:
            return {}
        out = {}
        for app_id, d in raw.items():
            if d is None:
                print(f"  详情失败（跳过）: {app_id}", flush=True)
                continue
            out[app_id] = normalize_app(d)
        return out
