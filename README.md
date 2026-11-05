# showPortsWidget

A small desktop window that lists every network port your Linux machine is listening on, who can reach it, which program owns it and what it is for. A second tab lists the services that exist only inside Kubernetes (no real port on this system). Read-only: it never changes anything.

| Column | Meaning |
|---|---|
| Port, Proto | Port number and protocol (tcp or udp) |
| Reachable from | This machine only, all networks, Tailscale network only, and so on |
| Program | The program that owns the port (some owners need admin rights to be visible) |
| Purpose | Found from Docker containers, Kubernetes services, your own notes, a built-in table of well-known ports, or the program name, in that order |

## The two tabs

| Tab | What it lists | Visible to the operating system? |
|---|---|---|
| Listening ports on this system | Real ports this system listens on, from Docker, Kubernetes (k3s), Tailscale and the system (columns above) | Yes |
| Kubernetes-only services (virtual ports) | Services with a private (virtual) address that exist only inside Kubernetes. Columns: Namespace, Service, Address, Ports, Ready backends (running copies ready to answer; 0 means nobody stands behind the service) | No, they open no real port |

Rest the mouse on a column title, a tab name or the search box for a plain-language explanation.

## Use

    ./showPortsWidget.sh          # opens the window with two tabs: sortable columns (click a title) and a port number search (digits only, up to 65535); Refresh reads everything again
    ./showPortsWidget.sh --text   # prints the same tables in the terminal

To create a desktop icon and a menu entry for this tool only, run `./install.sh` (use `./install.sh --remove` to take them away again, `--dry-run` to see what it would do).

## Requirements

| Software | Needed for |
|---|---|
| `ss` (iproute2), `awk`, `sort` | Required |
| `python3-gi` with GTK 3 (`gir1.2-gtk-3.0`) | The window with sorting and port search |
| `zenity` | A simpler fallback window (no sorting or search) when Python GTK is missing; without both, the table is printed in the terminal |
| `docker`, `kubectl` | Optional: container and service names as purposes, and the Kubernetes-only services tab |

## Your own notes (optional)

Create `~/.config/showPortsWidget/knownPorts.conf` with one line per port, `port|purpose`, for example `8080|My test web server`. This file stays on your machine.

## Limits

Without admin rights the Program column shows "hidden (needs admin)" for ports owned by other users. The purpose column still works for those through the other sources.

The Kubernetes-only tab reads the cluster with `kubectl` (read-only, using your own `~/.kube/config` when `KUBECONFIG` is not set). If the cluster is stopped or not reachable, the tab shows a notice instead of rows.

## Platforms

Linux only for now (tested on ARM64). Windows and macOS are not supported yet.

## Status

Tested on an NVIDIA DGX Spark (DGX OS, Ubuntu 24.04, ARM64). Unofficial and not affiliated with NVIDIA. Provided as is, without warranty (see the license).

## License

MIT, see `LICENSE`.
