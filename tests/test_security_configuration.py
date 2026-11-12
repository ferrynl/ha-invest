"""Regression checks for Home Assistant exposure-sensitive add-on defaults.

Run with: python -m unittest discover -s tests
This is a configuration guard, not a penetration test.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "portfolio" / "config.yaml"


class SecurityConfigurationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = CONFIG.read_text(encoding="utf-8")

    def test_ingress_is_enabled(self):
        self.assertRegex(self.config, r"(?m)^ingress:\s*true\s*$")

    def test_sensor_api_is_opt_in(self):
        # Explicitly null means HA does not publish the host port by default.
        self.assertRegex(self.config, r"(?m)^ports:\s*\n\s+8100/tcp:\s*null\s*$")

    def test_sensor_api_token_is_password_option(self):
        self.assertRegex(self.config, r"(?m)^\s+home_assistant_token:\s*password\?\s*$")
        self.assertRegex(self.config, r'(?m)^\s+home_assistant_token:\s*""\s*$')

    def test_no_database_or_debug_port_published(self):
        # Guard against accidental future exposure of common database ports.
        ports = re.findall(r"(?m)^\s{2,}(\d+/tcp):", self.config)
        self.assertNotIn("5432/tcp", ports)
        self.assertNotIn("3306/tcp", ports)
        self.assertNotIn("6379/tcp", ports)
        self.assertNotIn("8000/tcp", ports)

if __name__ == "__main__":
    unittest.main()
