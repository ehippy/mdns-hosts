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

## What it does

- Runs `avahi-browse -a -r -p -t` to enumerate all resolved mDNS services
- Filters to IPv4 `.local` hostnames only
- Skips garbage hostnames: UUIDs, raw MAC addresses, hex blobs, escape-encoded names
- Writes a managed block between marker comments in `/etc/hosts`, replacing any previous block
- Leaves all existing manual entries in `/etc/hosts` untouched

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
