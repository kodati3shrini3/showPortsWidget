#!/bin/bash
# showPortsWidget.sh: lists every port this machine listens on, who can reach it, which program owns it and what it is for (read-only)
# usage: showPortsWidget.sh [--text]    (--text prints a table in the terminal instead of opening a window)

for TOOL in ss awk sort; do   # checks every tool this widget needs
  if ! command -v "$TOOL" >/dev/null 2>&1; then   # a tool is missing
    MSG="Ports widget needs the program '$TOOL'. On Ubuntu: sudo apt install iproute2 (ss), gawk (awk), coreutils (sort)"   # what to install
    echo "$MSG" >&2   # prints the message in the terminal
    command -v zenity >/dev/null 2>&1 && zenity --error --title="Ports widget" --text="$MSG" 2>/dev/null   # also shows a window when possible
    exit 1   # stops here
  fi   # end of the missing-tool case
done   # end of the tool check

declare -A KNOWN=(   # well-known port -> usual purpose, used when no better source knows the port
  [22]="usually: SSH remote login"   # secure shell
  [53]="usually: DNS name lookup (systemd-resolved)"   # name resolver on this machine
  [546]="usually: DHCPv6 client (network address)"   # IPv6 address assignment
  [631]="usually: CUPS printing"   # print service
  [3350]="usually: Remote Desktop session manager (xrdp)"   # remote desktop helper
  [3389]="usually: Remote Desktop (RDP)"   # remote desktop
  [5353]="usually: mDNS device discovery"   # Bonjour / Avahi
  [6443]="usually: Kubernetes API (k3s)"   # cluster API
  [10250]="usually: Kubelet (k3s)"   # node agent of Kubernetes
  [41641]="usually: Tailscale VPN"   # Tailscale peer traffic
)

declare -A DOCKER   # host port -> name of the Docker container that publishes it
if command -v docker >/dev/null 2>&1 && timeout 5 docker ps >/dev/null 2>&1; then   # only when Docker is installed and running
  while IFS='|' read -r CNAME CPORTS; do   # one line per running container
    for HP in $(echo "$CPORTS" | grep -oE ':[0-9]+->' | tr -d ':>-' | sort -u); do DOCKER[$HP]="$CNAME"; done   # remembers each published host port
  done < <(timeout 5 docker ps --format '{{.Names}}|{{.Ports}}')   # container names with their port mappings
fi   # end of the Docker lookup

declare -A K8S   # host port -> Kubernetes service that exposes it
if command -v kubectl >/dev/null 2>&1 && timeout 6 kubectl --request-timeout=4s get nodes >/dev/null 2>&1; then   # only when Kubernetes answers
  while read -r SVC STYPE SPORTS; do   # one line per service: namespace/name type port,nodePort ...
    for PP in $SPORTS; do   # one pass per port of the service
      P="${PP%,*}"; NP="${PP#*,}"   # splits "port,nodePort"
      [ "$STYPE" = LoadBalancer ] && [ -n "$P" ] && K8S[$P]="Kubernetes service $SVC"   # LoadBalancer services listen on the host at the service port
      [ -n "$NP" ] && K8S[$NP]="Kubernetes service $SVC (NodePort)"   # NodePort services listen on the node port
    done   # end of the port loop
  done < <(kubectl --request-timeout=4s get svc -A -o jsonpath='{range .items[*]}{.metadata.namespace}/{.metadata.name} {.spec.type} {range .spec.ports[*]}{.port},{.nodePort} {end}{"\n"}{end}' 2>/dev/null)   # lists all services with their ports
fi   # end of the Kubernetes lookup

declare -A LOCAL_PURPOSE   # port -> purpose written by the owner of this machine
LOCALCONF="${XDG_CONFIG_HOME:-$HOME/.config}/showPortsWidget/knownPorts.conf"   # optional local list, never part of the repository
if [ -r "$LOCALCONF" ]; then while IFS='|' read -r LP LT; do [[ "$LP" =~ ^[0-9]+$ ]] && LOCAL_PURPOSE[$LP]="$LT"; done < "$LOCALCONF"; fi   # loads lines of the form port|purpose and ignores comments and blank lines

collect_rows() {   # prints one tab-separated line per listening port: port, protocol, reachable from, program, purpose
  ss -H -lntup 2>/dev/null | while read -r NETID STATE RQ SQ LOCAL PEER PROC; do   # one pass per listening socket
    PORT="${LOCAL##*:}"; A="${LOCAL%:*}"; IFACE=""   # port number, address part, network interface name
    case "$A" in *%*) IFACE="${A#*%}"; A="${A%%\%*}";; esac   # splits an address like 127.0.0.53%lo into address and interface
    case "$A" in   # works out who can reach this port
      127.*|\[::1\]) SC="this machine only";;   # loopback addresses
      \*|0.0.0.0|\[::\]) SC="all networks";;   # wildcard addresses
      224.*|\[ff*) SC="local network discovery (multicast)";;   # multicast addresses
      \[fe80*) SC="local link only";;   # IPv6 link-local addresses
      *) SC="$A";;   # any other specific address is shown as it is
    esac   # end of the address check
    { [ "$IFACE" = tailscale0 ] || [[ "$A" == 100.* ]]; } && SC="Tailscale network only"   # addresses on the Tailscale interface
    PN=$(echo "$PROC" | grep -oE '"[^"]+"' | head -n 1 | tr -d '"')   # program name from ss, empty for root-owned ports
    if [ -n "${LOCAL_PURPOSE[$PORT]}" ] && [ "$SC" = "Tailscale network only" ]; then PU="${LOCAL_PURPOSE[$PORT]}"   # local knowledge about Tailscale-only ports
    elif [ "$SC" = "Tailscale network only" ]; then PU="Tailscale (tailscaled)"   # Docker and Kubernetes lookups do not apply to Tailscale sockets
    elif [ -n "${DOCKER[$PORT]}" ]; then PU="Docker container ${DOCKER[$PORT]}"   # purpose from Docker
    elif [ -n "${K8S[$PORT]}" ]; then PU="${K8S[$PORT]}"   # purpose from Kubernetes
    elif [ -n "${LOCAL_PURPOSE[$PORT]}" ]; then PU="${LOCAL_PURPOSE[$PORT]}"   # purpose from the local list
    elif [ -n "${KNOWN[$PORT]}" ]; then PU="${KNOWN[$PORT]}"   # purpose from the well-known table
    elif [ -n "$PN" ]; then PU="used by $PN"   # purpose from the program name
    else PU="unknown (owner not visible without admin)"; fi   # nothing knows this port
    printf '%s\t%s\t%s\t%s\t%s\n' "$PORT" "$NETID" "$SC" "${PN:-hidden (needs admin)}" "$PU"   # one output row
  done | sort -t$'\t' -k1,1n -k2,2 -k3,3 | uniq   # sorts by port and removes duplicate IPv4/IPv6 rows
}

SELF="$(readlink -f "$0")"   # full path of this script
PYGUI="$(dirname "$SELF")/showPortsWidgetWindow.py"   # the window program written in Python
K8SPY="$(dirname "$SELF")/showPortsWidgetK8s.py"   # the program that lists the cluster-internal Kubernetes services
if [ "$1" = "--rows" ]; then collect_rows; exit 0; fi   # tab-separated rows for the window program (no lock needed)
if [ "$1" = "--k8s-rows" ]; then [ -f "$K8SPY" ] && python3 "$K8SPY"; exit 0; fi   # tab-separated Kubernetes rows for the window program
HAVE_PY=0   # becomes 1 when the Python window can be used
[ -f "$PYGUI" ] && python3 -c 'import gi; gi.require_version("Gtk","3.0"); from gi.repository import Gtk' >/dev/null 2>&1 && HAVE_PY=1   # needs the file and the PyGObject and GTK 3 libraries
if [ "$1" = "--text" ] || { [ "$HAVE_PY" = 0 ] && ! command -v zenity >/dev/null 2>&1; }; then   # terminal mode, or no window program available
  collect_rows | awk -F'\t' 'BEGIN{printf "%-6s %-5s %-34s %-24s %s\n","PORT","PROTO","REACHABLE FROM","PROGRAM","PURPOSE"} {printf "%-6s %-5s %-34s %-24s %s\n",$1,$2,$3,$4,$5}'   # prints an aligned table
  if [ -f "$K8SPY" ] && command -v python3 >/dev/null 2>&1; then   # second table: services that exist only inside Kubernetes
    echo; echo "KUBERNETES-ONLY SERVICES (virtual ports, not reachable from outside)"   # title of the second table
    python3 "$K8SPY" | awk -F'\t' 'BEGIN{printf "%-22s %-44s %-22s %-34s %s\n","NAMESPACE","SERVICE","ADDRESS","PORTS","READY BACKENDS"} {printf "%-22s %-44s %-22s %-34s %s\n",$1,$2,$3,$4,$5}'   # prints the table
  fi   # end of the second table
  exit 0   # done in terminal mode
fi   # end of terminal mode

LOCK="${XDG_RUNTIME_DIR:-/tmp}/showPortsWidget.lock"   # lock file: only one window at a time
exec 9>>"$LOCK"   # opens the lock file on handle 9
if ! flock -n 9; then   # another window already holds the lock
  command -v notify-send >/dev/null 2>&1 && notify-send "Ports widget" "The ports window is already open." 2>/dev/null   # tells the user instead of opening a second window
  exit 0   # no second window
fi   # end of the single-window check

if [ "$HAVE_PY" = 1 ]; then exec python3 "$PYGUI" "$SELF"; fi   # preferred window: sortable table with port search; the lock on handle 9 stays with it
while true; do   # window mode: repeats until Close is clicked
  mapfile -t CELLS < <(collect_rows | tr '\t' '\n')   # turns the rows into a flat list of cells for zenity
  zenity --list --title="Ports in use ($(( ${#CELLS[@]} / 5 )) listening)" --text="Read-only list. Refresh reads the ports again; Close ends the program." --width=1150 --height=620 --column=Port --column=Proto --column="Reachable from" --column=Program --column=Purpose --ok-label="Refresh" --cancel-label="Close" "${CELLS[@]}" >/dev/null 2>&1   # shows the table; Refresh, Enter or a double-click on a row means OK
  [ $? -eq 0 ] || break   # only Close or the window's X ends the loop; anything else reads the ports again
done   # end of the window loop
