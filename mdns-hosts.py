#!/usr/bin/env python3
"""
mdns-hosts.py — discover mDNS hosts on the local network and update /etc/hosts

Usage:
    python3 mdns-hosts.py               # print what would be written, don't touch hosts
    sudo python3 mdns-hosts.py --write-hosts  # discover and update /etc/hosts
"""

import os
import subprocess
import sys
import re
from pathlib import Path

HOSTS_FILE = Path("/etc/hosts")
MARKER_START = "# BEGIN MDNS-HOSTS (managed by mdns-hosts.py)"
MARKER_END   = "# END MDNS-HOSTS"


def is_clean_hostname(hostname: str) -> bool:
    """Return False for garbage hostnames: UUIDs, MACs, escaped chars, long hex blobs."""
    name = hostname.removesuffix(".local")

    # backslash-escaped chars (e.g. crumb-\040)
    if "\\" in name:
        return False

    # UUID with dashes: 8-4-4-4-12
    if re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", name, re.IGNORECASE):
        return False

    # pure hex blob (MAC = 12 chars, or longer hash)
    if re.fullmatch(r"[0-9a-f]{12,}", name, re.IGNORECASE):
        return False

    # name ending in a long uppercase hex/MAC suffix (e.g. iRobot-C16AF110688F4A6C...)
    if re.search(r"-[0-9A-F]{16,}$", name):
        return False

    return True


def discover_hosts() -> dict[str, str]:
    """Run avahi-browse and return {hostname: ipv4} for all resolved local hosts."""
    result = subprocess.run(
        ["avahi-browse", "-a", "-r", "-p", "-t"],
        capture_output=True, text=True
    )

    hosts = {}
    for line in result.stdout.splitlines():
        parts = line.split(";")
        # resolved lines start with '=' and have at least 9 fields
        if len(parts) < 9 or parts[0] != "=":
            continue
        protocol = parts[2]   # IPv4 or IPv6
        hostname = parts[6]   # e.g. octopi.local
        address  = parts[7]   # e.g. 192.168.50.185

        if protocol != "IPv4":
            continue
        if not hostname.endswith(".local"):
            continue
        if not re.match(r"^\d+\.\d+\.\d+\.\d+$", address):
            continue

        if not is_clean_hostname(hostname):
            continue

        # keep first seen (avahi may report same host multiple times for different services)
        if hostname not in hosts:
            hosts[hostname] = address

    return hosts


def build_block(hosts: dict[str, str]) -> str:
    lines = [MARKER_START]
    for hostname, address in sorted(hosts.items()):
        lines.append(f"{address:<20} {hostname}")
    lines.append(MARKER_END)
    return "\n".join(lines) + "\n"


def update_hosts(hosts: dict[str, str], dry_run: bool = False) -> None:
    current = HOSTS_FILE.read_text()

    # strip out any existing managed block
    pattern = re.compile(
        rf"^{re.escape(MARKER_START)}.*?^{re.escape(MARKER_END)}\n?",
        re.MULTILINE | re.DOTALL
    )
    stripped = pattern.sub("", current).rstrip("\n") + "\n"

    block = build_block(hosts)
    new_content = stripped + "\n" + block

    if dry_run:
        print("--- /etc/hosts would become ---")
        print(new_content)
        return

    HOSTS_FILE.write_text(new_content)
    print(f"Updated /etc/hosts with {len(hosts)} mDNS host(s).")


def main():
    dry_run = "--write-hosts" not in sys.argv

    if not dry_run and os.geteuid() != 0:
        print("error: run with sudo to write /etc/hosts (or omit --write-hosts for dry run)")
        sys.exit(1)

    print("Scanning for mDNS hosts...", flush=True)
    hosts = discover_hosts()

    if not hosts:
        print("No mDNS hosts found.")
        sys.exit(0)

    print(f"Found {len(hosts)} host(s):")
    for hostname, address in sorted(hosts.items()):
        print(f"  {address:<20} {hostname}")

    update_hosts(hosts, dry_run=dry_run)


if __name__ == "__main__":
    main()
