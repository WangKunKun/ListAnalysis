import json
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


if __name__ == "__main__":
    unittest.main()
