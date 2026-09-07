#!/usr/bin/env python3
"""
Host node telemetry collector (psutil).

Run inside a Mininet host namespace, e.g. from the Mininet CLI:
  mininet> h1 python3 telemetry/node_collector.py --node-id h1

Writes one node_telemetry row per poll interval to the shared SQLite DB.
"""

from __future__ import annotations

import argparse
import sqlite3
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


def collect_once(conn: sqlite3.Connection, node_id: str) -> None:
    cpu = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory().percent
    now_ms = int(time.time() * 1000)
    conn.execute(
        """
        INSERT INTO node_telemetry (
            record_id, ts_epoch_ms, node_id, cpu_pct, ram_pct, active_flows, source
        ) VALUES (?, ?, ?, ?, ?, 0, 'psutil')
        """,
        (str(uuid.uuid4()), now_ms, node_id, cpu, ram),
    )
    conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect host node telemetry via psutil")
    parser.add_argument("--node-id", required=True, help="Host node_id from topology_registry (e.g. h1)")
    parser.add_argument("--once", action="store_true", help="Collect a single sample and exit")
    args = parser.parse_args()

    hosts = load_host_nodes()
    if args.node_id not in hosts:
        raise SystemExit(f"{args.node_id} is not a registered host in topology_registry.yaml")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON;")

    if args.once:
        collect_once(conn, args.node_id)
        print(f"Wrote one node_telemetry row for {args.node_id}")
        return

    print(f"Collecting node telemetry for {args.node_id} every {POLL_INTERVAL_S}s (Ctrl+C to stop)")
    psutil.cpu_percent(interval=None)  # prime the counter
    while True:
        collect_once(conn, args.node_id)
        time.sleep(POLL_INTERVAL_S)


if __name__ == "__main__":
    main()
