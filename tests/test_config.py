import json
import tempfile
import unittest
from pathlib import Path

from soc_toolkit.config import DEFAULT_MAX_SPEED_KMH, ConfigError, load_config


class TestConfig(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def write_config(self, text: str) -> Path:
        path = Path(self._tmp.name) / "config.json"
        path.write_text(text, encoding="utf-8")
        return path

    def test_default_threshold(self):
        config = load_config()
        self.assertEqual(config.max_speed_kmh, DEFAULT_MAX_SPEED_KMH)
        self.assertEqual(config.source, "built-in default")

    def test_config_file_overrides_default(self):
        config = load_config(self.write_config(json.dumps({"max_speed_kmh": 750})))
        self.assertEqual(config.max_speed_kmh, 750.0)
        self.assertIn("config file", config.source)

    def test_command_line_overrides_config_file(self):
        path = self.write_config(json.dumps({"max_speed_kmh": 750}))
        config = load_config(path, max_speed_override=500)
        self.assertEqual(config.max_speed_kmh, 500.0)
        self.assertIn("command line", config.source)

    def test_invalid_override_values(self):
        for value in (0, -5, float("nan"), float("inf")):
            with self.subTest(value=value), self.assertRaises(ConfigError):
                load_config(max_speed_override=value)

    def test_invalid_config_files(self):
        cases = {
            "not JSON": "max_speed_kmh = 900",
            "not an object": "[900]",
            "unknown key": json.dumps({"max_speed_kmh": 900, "max_speed_kph": 500}),
            "missing key": json.dumps({}),
            "string value": json.dumps({"max_speed_kmh": "900"}),
            "boolean value": json.dumps({"max_speed_kmh": True}),
            "negative value": json.dumps({"max_speed_kmh": -1}),
        }
        for name, text in cases.items():
            with self.subTest(name), self.assertRaises(ConfigError):
                load_config(self.write_config(text))

    def test_missing_config_file(self):
        with self.assertRaises(ConfigError):
            load_config(Path(self._tmp.name) / "missing.json")


if __name__ == "__main__":
    unittest.main()
