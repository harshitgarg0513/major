"""Initialize SQLite database from schema.sql and seed topology/experiment registries."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = PROJECT_ROOT / "schema.sql"
TOPOLOGY_PATH = PROJECT_ROOT / "contracts" / "topology_registry.yaml"
EXPERIMENT_PATH = PROJECT_ROOT / "contracts" / "experiment_runs.yaml"
DEFAULT_DB = PROJECT_ROOT / "test.db"


def init_db(db_path: Path = DEFAULT_DB) -> sqlite3.Connection:
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

    topo = yaml.safe_load(TOPOLOGY_PATH.read_text(encoding="utf-8"))
    for node in topo.get("nodes", []):
        conn.execute(
            "INSERT INTO topology_nodes (node_id, kind, role) VALUES (?, ?, ?)",
            (node["node_id"], node["kind"], node.get("role")),
        )

    for link in topo.get("links", []):
        conn.execute(
            """
            INSERT INTO topology_links (
                link_id, endpoint_a_node_id, endpoint_a_port,
                endpoint_b_node_id, endpoint_b_port, capacity_mbps
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                link["link_id"],
                link["endpoint_a"]["node_id"],
                link["endpoint_a"]["port"],
                link["endpoint_b"]["node_id"],
                link["endpoint_b"]["port"],
                link["capacity_mbps"],
            ),
        )

    if EXPERIMENT_PATH.exists():
        exp = yaml.safe_load(EXPERIMENT_PATH.read_text(encoding="utf-8"))
        for run in exp.get("runs", []):
            conn.execute(
                """
                INSERT INTO experiment_runs (
                    run_id, condition, scenario, repetition_index,
                    start_ts_epoch_ms, end_ts_epoch_ms, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run["run_id"],
                    run["condition"],
                    run["scenario"],
                    run["repetition_index"],
                    run["start_ts_epoch_ms"],
                    run.get("end_ts_epoch_ms"),
                    run.get("notes"),
                ),
            )

    conn.commit()
    return conn


def verify_fk_rejects_bad_link(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute(
            """
            INSERT INTO link_telemetry (
                record_id, ts_epoch_ms, link_id, latency_ms, latency_method,
                packet_loss_pct, throughput_mbps, utilization_pct,
                queue_length, active_flows, poll_interval_ms
            ) VALUES ('bad', 1, 'L999', 0, 'lldp_probe', 0, 0, 0, 0, 0, 1000)
            """
        )
        conn.commit()
        return False
    except sqlite3.IntegrityError:
        return True


if __name__ == "__main__":
    db = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DB
    conn = init_db(db)
    ok = verify_fk_rejects_bad_link(conn)
    conn.close()
    print(f"Initialized {db}")
    print(f"FK constraint rejects unknown link_id: {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)
