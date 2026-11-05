#!/usr/bin/env python3
# showPortsWidgetK8s.py: prints the cluster-internal (ClusterIP) Kubernetes services, one tab-separated line each (read-only, standard library only)
# columns: namespace, service, address, ports, ready backends
import json   # reads the JSON that kubectl prints
import subprocess   # runs kubectl
import sys   # lets the program end early
import os   # reads and sets environment settings
KUBE = os.path.expanduser("~/.kube/config")   # your own kubeconfig, the standard location
if "KUBECONFIG" not in os.environ and os.path.isfile(KUBE):   # a desktop icon has no KUBECONFIG, a terminal does
    os.environ["KUBECONFIG"] = KUBE   # kubectl then uses your own file instead of the root-only k3s file

def kubectl(*args):   # runs kubectl read-only and returns the parsed JSON, or None when it fails
    try:   # kubectl may be missing or too slow
        out = subprocess.run(["kubectl", "--request-timeout=4s", "get", *args, "-o", "json"], capture_output=True, text=True, timeout=10)   # asks the cluster
    except Exception:   # kubectl missing or timeout
        return None   # no data
    if out.returncode != 0:   # the cluster answered with an error (for example k3s is stopped)
        return None   # no data
    return json.loads(out.stdout)   # the answer as Python data

svcs = kubectl("svc", "-A")   # all services of all namespaces
if svcs is None:   # the cluster is not reachable
    print("NOTE\tKubernetes is not running or not reachable\t\t")   # one explanatory row with five cells
    sys.exit(0)   # nothing more to show
slices = kubectl("endpointslices.discovery.k8s.io", "-A") or {"items": []}   # the backends behind each service; empty when unavailable
ready = {}   # (namespace, service) -> number of ready backends
for sl in slices["items"]:   # one slice at a time
    name = sl["metadata"].get("labels", {}).get("kubernetes.io/service-name")   # the service this slice belongs to
    if not name:   # a slice without a service label
        continue   # is skipped
    key = (sl["metadata"]["namespace"], name)   # identifies the service
    eps = sl.get("endpoints") or []   # a slice without backends has endpoints: null, so null becomes an empty list
    n = sum(1 for e in eps if (e.get("conditions") or {}).get("ready") is not False)   # counts backends not marked not-ready (an unknown state counts as ready)
    ready[key] = ready.get(key, 0) + n   # adds them to the service total
rows = []   # the output rows
for sv in svcs["items"]:   # one service at a time
    spec = sv["spec"]   # the service definition
    if spec.get("type", "ClusterIP") != "ClusterIP":   # LoadBalancer and NodePort services are open on the machine, so they belong to the other table
        continue   # skipped here
    ip = spec.get("clusterIP", "")   # the virtual address of the service
    addr = "headless (no address)" if ip == "None" else ip   # headless services have no virtual address
    ports = ",".join(sorted({"%s/%s" % (p["port"], p.get("protocol", "TCP")) for p in spec.get("ports", [])}))   # unique port/protocol pairs
    ns = sv["metadata"]["namespace"]   # namespace of the service
    nm = sv["metadata"]["name"]   # name of the service
    rows.append((ns, nm, addr, ports, str(ready.get((ns, nm), 0))))   # one row
for r in sorted(rows):   # sorted by namespace, then service
    print("\t".join(r))   # tab-separated output
