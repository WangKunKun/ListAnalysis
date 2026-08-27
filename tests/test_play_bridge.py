import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path

BRIDGE = Path(__file__).resolve().parent.parent / "scripts" / "play_bridge.mjs"
NODE_MODULES = BRIDGE.parent.parent / "node_modules" / "google-play-scraper"


def _node_available() -> bool:
    return shutil.which("node") is not None


@unittest.skipIf(not NODE_MODULES.exists(), "npm 依赖未装")
class TestPlayBridge(unittest.TestCase):
    def _run(self, stdin_text):
        return subprocess.run(
            ["node", str(BRIDGE)], input=stdin_text, capture_output=True,
            text=True, timeout=30)

    def test_invalid_json_exits_1(self):
        proc = self._run("not json at all")
        self.assertEqual(proc.returncode, 1)
        self.assertTrue(proc.stderr.strip())
        self.assertEqual(proc.stdout, "")

    def test_unknown_command_exits_1(self):
        proc = self._run(json.dumps({"cmd": "bogus"}))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("未知指令", proc.stderr)

    def test_search_command_registered_and_proxy_applied(self):
        # PLAY_PROXY 指向立即拒绝连接的端口:若 search 未注册会报"未知指令";
        # 已注册则报网络错误——证明命令分发与代理路径都被执行,且不依赖外网
        env = {**os.environ, "PLAY_PROXY": "http://127.0.0.1:1"}
        proc = subprocess.run(
            ["node", str(BRIDGE)], input=json.dumps(
                {"cmd": "search", "term": "x", "num": 5,
                 "country": "us", "lang": "en"}),
            capture_output=True, text=True, timeout=60, env=env)
        self.assertEqual(proc.returncode, 1)
        self.assertNotIn("未知指令", proc.stderr)
        self.assertTrue(proc.stderr.strip())


@unittest.skipIf(not _node_available(), "node 未安装")
@unittest.skipIf(not NODE_MODULES.exists(), "npm 依赖未装")
class TestSearchOutputContract(unittest.TestCase):
    """锁住桥↔Python 的输出协议:桥的导出函数输出必须能被
    fetch.adapters.play 对应 normalize 函数直接消化。此前桥改成
    {success,results:[appId]} 包装导致 Play 品类搜索全挂而单测全绿,
    本组测试防再次漂移。"""

    def _run_node(self, script):
        return subprocess.run(
            ["node", "--input-type=module", "-e", script],
            capture_output=True, text=True, timeout=30)

    def test_bridge_search_output_consumable_by_normalize_search(self):
        from fetch.adapters.play import normalize_search
        script = (
            f"const {{ formatSearchResults }} = await import({json.dumps(BRIDGE.as_uri())});"
            "process.stdout.write(JSON.stringify(formatSearchResults([{"
            "appId: 'com.example.app', title: 'Example App',"
            "developer: 'Example Ltd', score: 4.5, free: true"
            "}])))"
        )
        proc = self._run_node(script)
        self.assertEqual(
            proc.returncode, 0,
            f"桥缺少可导出的 formatSearchResults 或顶层有副作用: {proc.stderr}")
        apps = normalize_search(json.loads(proc.stdout))
        self.assertEqual(apps, [{
            "track_id": "com.example.app",
            "name": "Example App",
            "artist": "Example Ltd",
        }])

    def test_bridge_reviews_output_is_flat_score_text_list(self):
        """reviews 命令的输出契约:[{score, text}, ...] 平铺列表。

        formatReviews 接收 gplay.reviews(...).data 数组(桥内部即如此传)。
        """
        from fetch.reviews import normalize_play_reviews
        script = (
            f"const {{ formatReviews }} = await import({json.dumps(BRIDGE.as_uri())});"
            "process.stdout.write(JSON.stringify(formatReviews([{"
            "score: 5, text: 'great', userName: 'x', replyDate: null"
            "}, {score: 1}])))"
        )
        proc = self._run_node(script)
        self.assertEqual(
            proc.returncode, 0, f"桥缺少可导出的 formatReviews: {proc.stderr}")
        self.assertEqual(normalize_play_reviews(json.loads(proc.stdout)), [
            {"score": 5, "text": "great"},
            {"score": 1, "text": ""},
        ])


@unittest.skipUnless(os.environ.get("PLAY_SMOKE"), "需网络/代理,设 PLAY_SMOKE=1 启用")
@unittest.skipIf(not _node_available(), "node 未安装")
@unittest.skipIf(not NODE_MODULES.exists(), "npm 依赖未装")
class TestBridgeSearchSmoke(unittest.TestCase):
    """端到端冒烟:真实调桥 search,验证输出协议与数据完整性。"""

    def test_real_search_end_to_end(self):
        from fetch.adapters.play import normalize_search
        env = {**os.environ}
        env.pop("PLAY_PROXY", None)  # 让桥走默认网络/HTTPS_PROXY
        proc = subprocess.run(
            ["node", str(BRIDGE)], input=json.dumps(
                {"cmd": "search", "term": "pdf scanner", "num": 3,
                 "country": "us", "lang": "en"}),
            capture_output=True, text=True, timeout=60, env=env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        raw = json.loads(proc.stdout)
        self.assertIsInstance(raw, list)
        apps = normalize_search(raw)
        self.assertGreaterEqual(len(apps), 1)
        self.assertTrue(apps[0]["track_id"])
        self.assertTrue(apps[0]["name"], "桥输出丢了 title,报告表格会全空名")


if __name__ == "__main__":
    unittest.main()
