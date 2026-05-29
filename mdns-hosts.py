#!/usr/bin/env python3
"""
mdns-hosts.py — discover mDNS hosts on the local network and update /etc/hosts

Usage:
    python3 mdns-hosts.py               # print what would be written, don't touch hosts
    sudo python3 mdns-hosts.py --write-hosts  # discover and update /etc/hosts
    python3 mdns-hosts.py --format json # output as JSON
    python3 mdns-hosts.py --quiet       # minimal output, ideal for automation
    python3 mdns-hosts.py --ipv6        # include IPv6 addresses
"""

import os
import subprocess
import sys
import json
import re
import argparse
from pathlib import Path

VERSION = "1.1.0"

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


def discover_hosts(include_ipv6: bool = False) -> dict[str, str]:
    """Run avahi-browse and return {hostname: ipv4} for all resolved local hosts."""
    try:
        result = subprocess.run(
            ["avahi-browse", "-a", "-r", "-p", "-t"],
            capture_output=True, text=True, timeout=30, errors='replace'
        )
    except FileNotFoundError:
        print("error: avahi-browse not found. Install avahi-tools:", file=sys.stderr)
        print("  Fedora/Bazzite: sudo rpm-ostree install avahi-tools", file=sys.stderr)
        print("  Debian/Ubuntu: sudo apt install avahi-utils", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("error: avahi-browse timed out after 30 seconds", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"error: failed to run avahi-browse: {e}", file=sys.stderr)
        sys.exit(1)

    if result.returncode != 0:
        print(f"error: avahi-browse exited with code {result.returncode}", file=sys.stderr)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        sys.exit(1)

    hosts = {}
    for line in result.stdout.splitlines():
        parts = line.split(";")
        # resolved lines start with '=' and have at least 9 fields
        if len(parts) < 9 or parts[0] != "=":
            continue
        protocol = parts[2]   # IPv4 or IPv6
        hostname = parts[6]   # e.g. octopi.local
        address  = parts[7]   # e.g. 192.168.50.185

        if not hostname.endswith(".local"):
            continue
        if protocol == "IPv4" and re.match(r"^\d+\.\d+\.\d+\.\d+$", address):
            if include_ipv6 or protocol == "IPv4":
                pass  # continue below
        elif protocol == "IPv6" and not include_ipv6:
            continue
        elif protocol == "IPv6" and not re.match(r"^([0-9a-fA-F]{1,4}:){1,7}[0-9a-fA-F]{1,4}$", address):
            continue
        else:
            continue

        if not is_clean_hostname(hostname):
            continue

        # keep first seen (avahi may report same host multiple times for different services)
        if hostname not in hosts:
            hosts[hostname] = address

    return hosts


def build_block(hosts: dict[str, str], include_ipv6: bool = False) -> str:
    lines = [MARKER_START]
    for hostname, address in sorted(hosts.items()):
        if include_ipv6:
            # Pad IPv6 addresses to ~40 chars for alignment
            lines.append(f"{address:<40} {hostname}")
        else:
            lines.append(f"{address:<20} {hostname}")
    lines.append(MARKER_END)
    return "\n".join(lines) + "\n"


def update_hosts(hosts: dict[str, str], dry_run: bool = False, include_ipv6: bool = False) -> None:
    try:
        current = HOSTS_FILE.read_text()
    except FileNotFoundError:
        print(f"error: {HOSTS_FILE} not found", file=sys.stderr)
        sys.exit(1)
    except PermissionError:
        print(f"error: permission denied reading {HOSTS_FILE}", file=sys.stderr)
        sys.exit(1)

    # strip out any existing managed block
    pattern = re.compile(
        rf"^.{re.escape(MARKER_START)}.*?^.{re.escape(MARKER_END)}\n?",
        re.MULTILINE | re.DOTALL
    )
    stripped = pattern.sub("", current).rstrip("\n") + "\n"

    block = build_block(hosts, include_ipv6=include_ipv6)
    new_content = stripped + "\n" + block

    if dry_run:
        print("--- /etc/hosts would become ---")
        print(new_content)
        return

    try:
        HOSTS_FILE.write_text(new_content)
    except PermissionError:
        print(f"error: permission denied writing {HOSTS_FILE}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Updated /etc/hosts with {len(hosts)} mDNS host(s).")


def print_json(hosts: dict[str, str]) -> None:
    """Output hosts as a JSON array of objects."""
    output = [
        {"hostname": host, "address": addr}
        for host, addr in sorted(hosts.items())
    ]
    print(json.dumps(output, indent=2))


def print_help():
    print(__doc__)
    print("Options:")
    print("  --write-hosts    Actually update /etc/hosts (requires sudo)")
    print("  --format json    Output as JSON (disables --write-hosts)")
    print("  --quiet          Minimal output; ideal for automation/scripts")
    print("  --ipv6           Include IPv6 addresses in results")
    print("  --help           Show this help message")
    print("  --version        Show version")


def main():
    parser = argparse.ArgumentParser(
        description="Discover mDNS hosts and update /etc/hosts",
        add_help=False
    )
    parser.add_argument("--write-hosts", action="store_true", help="Actually update /etc/hosts (requires sudo)")
    parser.add_argument("--format", choices=["json"], default=None, help="Output format (default: text)")
    parser.add_argument("--quiet", action="store_true", help="Minimal output for automation")
    parser.add_argument("--ipv6", action="store_true", help="Include IPv6 addresses")
    parser.add_argument("--help", "-h", action="store_true", help="Show help message")
    parser.add_argument("--version", action="store_true", help="Show version")

    args = parser.parse_args()

    if args.help:
        print_help()
        sys.exit(0)

    if args.version:
        print(f"mdns-hosts {VERSION}")
        sys.exit(0)

    if args.format == "json" and args.write_hosts:
        print("error: --format json and --write-hosts cannot be used together", file=sys.stderr)
        sys.exit(1)

    dry_run = not args.write_hosts

    if not dry_run and os.geteuid() != 0:
        print("error: --write-hosts requires root. Run with sudo or omit for dry-run", file=sys.stderr)
        sys.exit(1)

    if not args.quiet:
        print("Scanning for mDNS hosts...", flush=True)

    hosts = discover_hosts(include_ipv6=args.ipv6)

    if not hosts:
        if not args.quiet:
            print("No mDNS hosts found.")
        sys.exit(1)

    if args.format == "json":
        print_json(hosts)
        sys.exit(0)

    if not args.quiet:
        print(f"Found {len(hosts)} host(s):")
        for hostname, address in sorted(hosts.items()):
            print(f"  {address:<20} {hostname}")

    if args.write_hosts:
        update_hosts(hosts, dry_run=False, include_ipv6=args.ipv6)
    else:
        if not args.quiet:
            print()
            update_hosts(hosts, dry_run=True, include_ipv6=args.ipv6)


if __name__ == "__main__":
    main()
