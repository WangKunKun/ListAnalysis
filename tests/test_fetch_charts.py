import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import fetch_charts


class TestLoadConfig(unittest.TestCase):
    def test_missing_file_returns_defaults(self):
        cfg = fetch_charts.load_config(Path("/nonexistent/config.json"))
        self.assertEqual(cfg["regions"], fetch_charts.DEFAULT_CONFIG["regions"])
        self.assertEqual(cfg["top_n"], 50)

    def test_user_config_overrides_defaults(self):
        with TemporaryDirectory() as td:
            p = Path(td) / "config.json"
            p.write_text('{"top_n": 100, "regions": ["us"]}', encoding="utf-8")
            cfg = fetch_charts.load_config(p)
            self.assertEqual(cfg["top_n"], 100)
            self.assertEqual(cfg["regions"], ["us"])
            self.assertEqual(cfg["charts"], fetch_charts.DEFAULT_CONFIG["charts"])

    def test_invalid_chart_key_raises(self):
        with TemporaryDirectory() as td:
            p = Path(td) / "config.json"
            p.write_text('{"charts": ["free", "bogus"]}', encoding="utf-8")
            with self.assertRaises(ValueError):
                fetch_charts.load_config(p)


if __name__ == "__main__":
    unittest.main()
