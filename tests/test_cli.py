import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from soc_toolkit.cli import main

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE = str(PROJECT_ROOT / "data" / "sample" / "synthetic_logins.csv")
CONFIG = str(PROJECT_ROOT / "config" / "impossible_travel.json")


def run_cli(*args):
    stdout, stderr = io.StringIO(), io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        exit_code = main(list(args))
    return exit_code, stdout.getvalue(), stderr.getvalue()


class TestCli(unittest.TestCase):
    def test_sample_data_produces_one_finding(self):
        exit_code, out, _ = run_cli(SAMPLE)
        self.assertEqual(exit_code, 0)
        self.assertIn("Login events     : 12", out)
        self.assertIn("Users analysed   : 5", out)
        self.assertIn("Login pairs      : 7", out)
        self.assertIn("Pairs flagged    : 1", out)
        self.assertIn("User             : bob@example.com", out)
        self.assertIn("NOT a determination", out)

    def test_config_file_is_used(self):
        exit_code, out, _ = run_cli(SAMPLE, "--config", CONFIG)
        self.assertEqual(exit_code, 0)
        self.assertIn("source: config file", out)

    def test_lower_threshold_flags_more_pairs(self):
        # dave's New York -> London flight needs ~655 km/h.
        exit_code, out, _ = run_cli(SAMPLE, "--max-speed-kmh", "500")
        self.assertEqual(exit_code, 0)
        self.assertIn("Pairs flagged    : 2", out)
        self.assertIn("User             : dave@example.com", out)

    def test_missing_input_file_fails_without_report(self):
        exit_code, out, err = run_cli(str(PROJECT_ROOT / "no_such_file.csv"))
        self.assertEqual(exit_code, 1)
        self.assertEqual(out, "")
        self.assertIn("ERROR:", err)

    def test_invalid_threshold_fails(self):
        exit_code, out, err = run_cli(SAMPLE, "--max-speed-kmh", "0")
        self.assertEqual(exit_code, 1)
        self.assertEqual(out, "")
        self.assertIn("max_speed_kmh", err)

    def test_same_timestamp_different_location_fails_without_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.csv"
            path.write_text(
                "user,timestamp,ip_address,latitude,longitude,location\n"
                'bob@example.com,2026-03-02T09:00:00Z,192.0.2.1,51.5074,-0.1278,"London, GB"\n'
                'bob@example.com,2026-03-02T09:00:00Z,192.0.2.2,-33.8688,151.2093,"Sydney, AU"\n',
                encoding="utf-8",
            )
            exit_code, out, err = run_cli(str(path))
        self.assertEqual(exit_code, 1)
        self.assertEqual(out, "")
        self.assertIn("same timestamp", err)


if __name__ == "__main__":
    unittest.main()
