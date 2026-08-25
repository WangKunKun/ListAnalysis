import json
import os
import subprocess
import unittest
from pathlib import Path

BRIDGE = Path(__file__).resolve().parent.parent / "scripts" / "play_bridge.mjs"
NODE_MODULES = BRIDGE.parent.parent / "node_modules" / "google-play-scraper"


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


if __name__ == "__main__":
    unittest.main()
