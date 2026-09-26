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


import os

def init_db(db_path: Path = DEFAULT_DB) -> sqlite3.Connection:
    topo_py = PROJECT_ROOT / "network" / "mininet_test_topo.py"
    if topo_py.exists() and TOPOLOGY_PATH.exists():
        if os.path.getmtime(topo_py) > os.path.getmtime(TOPOLOGY_PATH):
            raise RuntimeError(f"topology_registry.yaml is stale! {topo_py.name} has been modified more recently. Please run `python3 network/topology_builder.py` first.")

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
                queue_length, active_flows, poll_interval_ms, is_partial
            ) VALUES ('bad-link', 1, 'L999', 0, 'lldp_probe', 0, 0, 0, 0, 0, 1000, 0)
            """
        )
        conn.commit()
        return False
    except sqlite3.IntegrityError:
        return True


def verify_fk_rejects_bad_fault_target(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute(
            """
            INSERT INTO fault_log (
                event_id, fault_type, target_type, target_link_id, target_node_id,
                start_ts_epoch_ms, severity_params, injected_by
            ) VALUES ('bad-fault', 'link_failure', 'link', 'L999', NULL, 1, '{}', 'test')
            """
        )
        conn.commit()
        return False
    except sqlite3.IntegrityError:
        return True


def verify_fk_rejects_bad_recovery_target(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute(
            """
            INSERT INTO recovery_actions (
                action_id, schema_version, target_type, target_link_id, target_node_id,
                reason, requested_ts_epoch_ms
            ) VALUES ('bad-action', '1.0', 'link', 'L999', NULL, 'manual', 1)
            """
        )
        conn.commit()
        return False
    except sqlite3.IntegrityError:
        return True


def verify_unmanaged_connection_fk_rejects(db_path: Path) -> bool:
    try:
        # Simulate recovery_stub.py's actual connection pattern
        with sqlite3.connect(db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute(
                """
                INSERT INTO recovery_actions (
                    action_id, schema_version, target_type, target_link_id, target_node_id,
                    reason, requested_ts_epoch_ms
                ) VALUES ('bad-action-unmanaged', '1.0', 'link', 'L999', NULL, 'manual', 1)
                """
            )
        return False
    except sqlite3.IntegrityError:
        return True

if __name__ == "__main__":
    db = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DB
    conn = init_db(db)
    results = {
        "link_telemetry FK": verify_fk_rejects_bad_link(conn),
        "fault_log FK": verify_fk_rejects_bad_fault_target(conn),
        "recovery_actions FK": verify_fk_rejects_bad_recovery_target(conn),
    }
    conn.close()
    
    # Run the unmanaged connection test after init_db closes
    results["recovery_actions unmanaged FK"] = verify_unmanaged_connection_fk_rejects(db)
    
    print(f"Initialized {db}")
    failed = 0
    for name, ok in results.items():
        status = "PASS" if ok else "FAIL"
        print(f"{name} rejects bogus target: {status}")
        if not ok:
            failed += 1
    sys.exit(1 if failed else 0)
