# showPortsWidget

A small desktop window that lists every network port your Linux machine is listening on, who can reach it, which program owns it and what it is for. Read-only: it never changes anything.

| Column | Meaning |
|---|---|
| Port, Proto | Port number and protocol (tcp or udp) |
| Reachable from | This machine only, all networks, Tailscale network only, and so on |
| Program | The program that owns the port (some owners need admin rights to be visible) |
| Purpose | Found from Docker containers, Kubernetes services, your own notes, a built-in table of well-known ports, or the program name, in that order |

## Use

    ./showPortsWidget.sh          # opens the window: sortable columns (click a title) and a port number search (digits only, up to 65535); Refresh reads everything again
    ./showPortsWidget.sh --text   # prints the same table in the terminal

To create a desktop icon and a menu entry for this tool only, run `./install.sh` (use `./install.sh --remove` to take them away again, `--dry-run` to see what it would do).

## Requirements

| Software | Needed for |
|---|---|
| `ss` (iproute2), `awk`, `sort` | Required |
| `python3-gi` with GTK 3 (`gir1.2-gtk-3.0`) | The window with sorting and port search |
| `zenity` | A simpler fallback window (no sorting or search) when Python GTK is missing; without both, the table is printed in the terminal |
| `docker`, `kubectl` | Optional: container and service names as purposes |

## Your own notes (optional)

Create `~/.config/showPortsWidget/knownPorts.conf` with one line per port, `port|purpose`, for example `8080|My test web server`. This file stays on your machine.

## Limits

Without admin rights the Program column shows "hidden (needs admin)" for ports owned by other users. The purpose column still works for those through the other sources.

## Platforms

Linux only for now (tested on ARM64). Windows and macOS are not supported yet.

## Status

Tested on an NVIDIA DGX Spark (DGX OS, Ubuntu 24.04, ARM64). Unofficial and not affiliated with NVIDIA. Provided as is, without warranty (see the license).

## License

MIT, see `LICENSE`.
