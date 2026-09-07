#!/usr/bin/env python3
"""
Host node telemetry collector (psutil).

Run inside a Mininet host namespace, e.g. from the Mininet CLI:
  mininet> h1 python3 telemetry/node_collector.py --node-id h1

IMPORTANT — measurement scope:
  Default Mininet hosts get their own network namespace but share the host PID
  namespace. psutil.cpu_percent() reads /proc/stat, which is VM/container-wide.
  Rows are tagged measurement_scope='vm_shared' in that case — cpu_pct/ram_pct
  must NOT be treated as per-host isolated usage in Stage 5B unless you have
  verified host_isolated (see scripts/test_node_cpu_isolation.sh).

Writes one node_telemetry row per poll interval to the shared SQLite DB.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
import uuid
from pathlib import Path

import psutil
import yaml

POLL_INTERVAL_S = 1.0
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "test.db"
TOPOLOGY_PATH = PROJECT_ROOT / "contracts" / "topology_registry.yaml"


def load_host_nodes() -> set[str]:
    topo = yaml.safe_load(TOPOLOGY_PATH.read_text(encoding="utf-8"))
    return {n["node_id"] for n in topo.get("nodes", []) if n.get("kind") == "host"}


def detect_measurement_scope() -> str:
    """
    Detect whether psutil CPU/RAM readings are host-isolated or VM-wide.

    Mininet default: separate net ns, shared PID ns -> vm_shared.
    """
    try:
        self_pid = os.readlink("/proc/self/ns/pid")
        init_pid = os.readlink("/proc/1/ns/pid")
        if self_pid != init_pid:
            return "host_isolated"
        self_net = os.readlink("/proc/self/ns/net")
        init_net = os.readlink("/proc/1/ns/net")
        if self_net != init_net:
            return "vm_shared"
    except OSError:
        pass
    return "vm_shared"


def collect_once(
    conn: sqlite3.Connection, node_id: str, measurement_scope: str
) -> None:
    cpu = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory().percent
    now_ms = int(time.time() * 1000)
    conn.execute(
        """
        INSERT INTO node_telemetry (
            record_id, ts_epoch_ms, node_id, cpu_pct, ram_pct,
            active_flows, source, measurement_scope
        ) VALUES (?, ?, ?, ?, ?, 0, 'psutil', ?)
        """,
        (str(uuid.uuid4()), now_ms, node_id, cpu, ram, measurement_scope),
    )
    conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect host node telemetry via psutil")
    parser.add_argument("--node-id", required=True, help="Host node_id from topology_registry (e.g. h1)")
    parser.add_argument("--once", action="store_true", help="Collect a single sample and exit")
    parser.add_argument(
        "--measurement-scope",
        choices=("host_isolated", "vm_shared"),
        default=None,
        help="Override auto-detected scope (testing only)",
    )
    args = parser.parse_args()

    hosts = load_host_nodes()
    if args.node_id not in hosts:
        raise SystemExit(f"{args.node_id} is not a registered host in topology_registry.yaml")

    scope = args.measurement_scope or detect_measurement_scope()
    if scope == "vm_shared":
        print(
            "WARNING: cpu_pct/ram_pct reflect VM/container-wide /proc stats, "
            "not per-Mininet-host isolation (default Mininet PID namespace sharing). "
            "Run scripts/test_node_cpu_isolation.sh before trusting these columns in Stage 5B.",
            file=sys.stderr,
        )

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON;")

    if args.once:
        collect_once(conn, args.node_id, scope)
        print(f"Wrote one node_telemetry row for {args.node_id} (measurement_scope={scope})")
        return

    print(
        f"Collecting node telemetry for {args.node_id} every {POLL_INTERVAL_S}s "
        f"(measurement_scope={scope}; Ctrl+C to stop)"
    )
    psutil.cpu_percent(interval=None)
    while True:
        collect_once(conn, args.node_id, scope)
        time.sleep(POLL_INTERVAL_S)


if __name__ == "__main__":
    main()
