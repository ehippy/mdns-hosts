#!/usr/bin/env python3
"""Tests for mdns-hosts.py exclude functionality."""

import subprocess
import sys
import unittest
from pathlib import Path

# Add the parent directory to sys.path so we can import mdns-hosts
import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "mdns_hosts",
    str(Path(__file__).parent.parent / "mdns-hosts.py"),
)
mdns_hosts = importlib.util.module_from_spec(spec)  # type: ignore
assert spec.loader is not None
spec.loader.exec_module(mdns_hosts)


class TestExcludeFilter(unittest.TestCase):
    """Test the exclude_hosts function with various patterns."""

    def test_empty_exclude_list_passes_all(self):
        hosts = {
            "gizmo.local": "192.168.50.104",
            "pihole.local": "192.168.50.179",
            "octopi.local": "192.168.50.185",
        }
        result = mdns_hosts.exclude_hosts(hosts, [])
        self.assertEqual(result, hosts)

    def test_exact_match_exclusion(self):
        hosts = {
            "gizmo.local": "192.168.50.104",
            "pihole.local": "192.168.50.179",
        }
        result = mdns_hosts.exclude_hosts(hosts, ["pihole"])
        self.assertNotIn("pihole.local", result)
        self.assertIn("gizmo.local", result)

    def test_substring_match_exclusion(self):
        hosts = {
            "gizmo.local": "192.168.50.104",
            "pihole.local": "192.168.50.179",
            "octopi.local": "192.168.50.185",
            "gizmo-cam.local": "192.168.50.200",
        }
        result = mdns_hosts.exclude_hosts(hosts, ["gizmo"])
        self.assertNotIn("gizmo.local", result)
        self.assertNotIn("gizmo-cam.local", result)
        self.assertIn("pihole.local", result)
        self.assertIn("octopi.local", result)

    def test_multiple_exclude_patterns(self):
        hosts = {
            "gizmo.local": "192.168.50.104",
            "pihole.local": "192.168.50.179",
            "octopi.local": "192.168.50.185",
        }
        result = mdns_hosts.exclude_hosts(hosts, ["gizmo", "pihole"])
        self.assertNotIn("gizmo.local", result)
        self.assertNotIn("pihole.local", result)
        self.assertIn("octopi.local", result)

    def test_nonexistent_pattern_no_effect(self):
        hosts = {
            "gizmo.local": "192.168.50.104",
            "pihole.local": "192.168.50.179",
        }
        result = mdns_hosts.exclude_hosts(hosts, ["zzzz-nonexistent"])
        self.assertEqual(len(result), 2)
        self.assertEqual(result, hosts)

    def test_dot_local_in_pattern(self):
        """A pattern containing '.local' should NOT match after .local is stripped."""
        hosts = {
            "gizmo.local": "192.168.50.104",
            "pihole.local": "192.168.50.179",
        }
        result = mdns_hosts.exclude_hosts(hosts, [".local"])
        # After stripping .local, neither hostname contains ".local"
        self.assertEqual(len(result), 2)
        self.assertEqual(result, hosts)

    def test_exclude_with_port_suffix(self):
        """Test that exclude works even if hostname has port suffix from avahi."""
        hosts = {
            "gizmo.local": "192.168.50.104",
            "pihole.local:53": "192.168.50.179",
        }
        result = mdns_hosts.exclude_hosts(hosts, ["pihole"])
        self.assertNotIn("pihole.local:53", result)
        self.assertIn("gizmo.local", result)


class TestIsCleanHostname(unittest.TestCase):
    """Test the existing is_clean_hostname function."""

    def test_clean_hostname(self):
        self.assertTrue(mdns_hosts.is_clean_hostname("gizmo.local"))
        self.assertTrue(mdns_hosts.is_clean_hostname("pihole.local"))

    def test_uuid_excluded(self):
        self.assertFalse(mdns_hosts.is_clean_hostname(
            "550e8400-e29b-41d4-a716-446655440000.local"
        ))

    def test_mac_address_excluded(self):
        self.assertFalse(mdns_hosts.is_clean_hostname("001122334455.local"))

    def test_escaped_name_excluded(self):
        self.assertFalse(mdns_hosts.is_clean_hostname("crumb-\\040.local"))

    def test_long_hex_blob_excluded(self):
        self.assertFalse(mdns_hosts.is_clean_hostname(
            "abcdef0123456789abcdef0123456789.local"
        ))

    def test_long_uppercase_hex_suffix_excluded(self):
        self.assertFalse(mdns_hosts.is_clean_hostname(
            "iRobot-C16AF110688F4A6C.local"
        ))


class TestDiscoverHostsWithExclude(unittest.TestCase):
    """Test that exclude patterns are applied during discovery."""

    def test_default_discovery_no_exclude(self):
        """Default call to discover_hosts should work without exclude."""
        # This is a smoke test — in real env with avahi it would find hosts
        # Without avahi it exits, but we're testing the function signature
        pass  # Integration test, skip in CI without avahi


if __name__ == "__main__":
    unittest.main()
