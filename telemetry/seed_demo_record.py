#!/usr/bin/env python3
"""
Phase 1 — Member 2 proof: insert fabricated telemetry rows matching Day-0 schema,
validate with contracts/validate.py, read them back.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from contracts.validate import validate_link_telemetry, validate_node_telemetry
from telemetry.db_init import init_db

DB_PATH = PROJECT_ROOT / "test.db"

LINK_RECORD = {
    "record_id": str(uuid.uuid4()),
    "ts_epoch_ms": 1735999200000,
    "link_id": "L1",
    "latency_ms": 10.2,
    "latency_method": "lldp_probe",
    "packet_loss_pct": 0.0,
    "throughput_mbps": 12.4,
    "utilization_pct": 12.4,
    "queue_length": 3,
    "active_flows": 5,
    "poll_interval_ms": 1000,
    "is_partial": False,
}

NODE_RECORD = {
    "record_id": str(uuid.uuid4()),
    "ts_epoch_ms": 1735999201000,
    "node_id": "h_sensor1",
    "cpu_pct": 8.5,
    "ram_pct": 41.2,
    "active_flows": 0,
    "source": "psutil",
    "measurement_scope": "vm_shared",
}


def insert_link(conn: sqlite3.Connection, rec: dict) -> None:
    conn.execute(
        """
        INSERT INTO link_telemetry (
            record_id, ts_epoch_ms, link_id, latency_ms, latency_method,
            packet_loss_pct, throughput_mbps, utilization_pct,
            queue_length, active_flows, poll_interval_ms, is_partial
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            rec["record_id"],
            rec["ts_epoch_ms"],
            rec["link_id"],
            rec["latency_ms"],
            rec["latency_method"],
            rec["packet_loss_pct"],
            rec["throughput_mbps"],
            rec["utilization_pct"],
            rec["queue_length"],
            rec["active_flows"],
            rec["poll_interval_ms"],
            1 if rec["is_partial"] else 0,
        ),
    )


def insert_node(conn: sqlite3.Connection, rec: dict) -> None:
    conn.execute(
        """
        INSERT INTO node_telemetry (
            record_id, ts_epoch_ms, node_id, cpu_pct, ram_pct,
            active_flows, source, measurement_scope
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            rec["record_id"],
            rec["ts_epoch_ms"],
            rec["node_id"],
            rec["cpu_pct"],
            rec["ram_pct"],
            rec["active_flows"],
            rec["source"],
            rec["measurement_scope"],
        ),
    )


def read_back(conn: sqlite3.Connection, link_record_id: str, node_record_id: str) -> tuple[list, list]:
    links = conn.execute(
        "SELECT link_id, throughput_mbps, latency_ms, is_partial FROM link_telemetry WHERE record_id = ?",
        (link_record_id,)
    ).fetchall()
    nodes = conn.execute(
        "SELECT node_id, cpu_pct, measurement_scope FROM node_telemetry WHERE record_id = ?",
        (node_record_id,)
    ).fetchall()
    return links, nodes


def main() -> int:
    print("=== Phase 1 / Member 2 — Telemetry seed + read demo ===")

    validate_link_telemetry(LINK_RECORD)
    validate_node_telemetry(NODE_RECORD)
    print("Contract validation: PASS (link + node records)")

    init_db(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON;")

    insert_link(conn, LINK_RECORD)
    insert_node(conn, NODE_RECORD)
    conn.commit()

    links, nodes = read_back(conn, LINK_RECORD["record_id"], NODE_RECORD["record_id"])
    conn.close()

    print("Read back link_telemetry:", links)
    print("Read back node_telemetry:", nodes)

    if len(links) != 1 or len(nodes) != 1:
        print("FAIL: expected exactly one row in each table")
        return 1

    print("PASS: fabricated records inserted, validated, and read back.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
