# mdns-hosts

Discovers mDNS (`.local`) hosts on your local network via `avahi-browse` and writes them into `/etc/hosts`.

## Why

Flatpak-sandboxed apps (Firefox, Chromium, etc.) bypass the host's NSS/avahi stack and resolve DNS through `systemd-resolved` only. That means `.local` hostnames that work fine in your terminal won't resolve in your browser. Managing `/etc/hosts` is the pragmatic fix.

## Requirements

- Linux with `avahi-daemon` running
- `avahi-tools` installed (`avahi-browse`)
- Python 3.9+

On Fedora/Bazzite:
```
sudo rpm-ostree install avahi-tools
```

## Usage

Preview what would be written (default, no sudo needed):
```
python3 mdns-hosts.py
```

Actually update `/etc/hosts`:
```
sudo python3 mdns-hosts.py --write-hosts
```

### Output Formats

Output as JSON for use in scripts or automation:
```
python3 mdns-hosts.py --format json
```

Minimal output for automation (quiet mode):
```
python3 mdns-hosts.py --quiet --write-hosts
```

Include IPv6 addresses:
```
python3 mdns-hosts.py --ipv6 --write-hosts
```

## What it does

- Runs `avahi-browse -a -r -p -t` to enumerate all resolved mDNS services
- Filters to IPv4 `.local` hostnames only (IPv6 available with `--ipv6`)
- Skips garbage hostnames: UUIDs, raw MAC addresses, hex blobs, escape-encoded names
- Writes a managed block between marker comments in `/etc/hosts`, replacing any previous block
- Leaves all existing manual entries in `/etc/hosts` untouched

## Automatic Updates (systemd timer)

To keep `/etc/hosts` fresh without thinking about it, install the included systemd units:

```bash
sudo cp mdns-hosts.py /usr/local/bin/mdns-hosts.py
sudo cp systemd/mdns-hosts.service /etc/systemd/system/
sudo cp systemd/mdns-hosts.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mdns-hosts.timer
```

This runs the script once a minute after boot, then hourly. Check on it with:
```
journalctl -u mdns-hosts.service
```

## Example output

```
Scanning for mDNS hosts...
Found 8 host(s):
  192.168.50.185       octopi.local
  192.168.50.179       pihole.local
  192.168.50.104       gizmo.local
  ...
```

The managed block in `/etc/hosts` looks like:
```
# BEGIN MDNS-HOSTS (managed by mdns-hosts.py)
192.168.50.104       gizmo.local
192.168.50.185       octopi.local
192.168.50.179       pihole.local
# END MDNS-HOSTS
```

### JSON output example

```json
[
  {"hostname": "gizmo.local", "address": "192.168.50.104"},
  {"hostname": "octopi.local", "address": "192.168.50.185"},
  {"hostname": "pihole.local", "address": "192.168.50.179"}
]
```
