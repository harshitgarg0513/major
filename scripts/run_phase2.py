#!/usr/bin/env python3
"""
Phase 2 — Full Integration Script
Connects Telemetry DB -> Prediction Stub -> Decision Engine -> Recovery Stub
"""

import sqlite3
import time
import requests
import json
import uuid
import os
import sys

# Add parent directory to path so we can import local modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from recovery.decision_engine import evaluate_probability

DB_PATH = "test.db"
PREDICT_URL = "http://127.0.0.1:8000/predict"
RECOVERY_URL = "http://127.0.0.1:8001/execute_action"

def get_telemetry_windows(cursor, window_seconds=30):
    """Fetch the trailing window of telemetry for all links."""
    cursor.execute("""
        SELECT link_id, ts_epoch_ms, latency_ms, packet_loss_pct, throughput_mbps, utilization_pct, queue_length, active_flows
        FROM link_telemetry
        WHERE ts_epoch_ms >= (
            SELECT MAX(ts_epoch_ms) FROM link_telemetry
        ) - (? * 1000)
        ORDER BY link_id, ts_epoch_ms ASC
    """, (window_seconds,))
    
    windows = {}
    for row in cursor.fetchall():
        link_id = row[0]
        if link_id not in windows:
            windows[link_id] = []
        windows[link_id].append({
            "ts_epoch_ms": row[1],
            "latency_ms": row[2],
            "packet_loss_pct": row[3],
            "throughput_mbps": row[4],
            "utilization_pct": row[5],
            "queue_length": row[6],
            "active_flows": row[7]
        })
    return windows

def run_integration_loop():
    print("=== Phase 2 Integration Engine Started ===")
    
    while True:
        if not os.path.exists(DB_PATH):
            print(f"Waiting for database {DB_PATH} to be created...")
            time.sleep(2)
            continue

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            windows = get_telemetry_windows(cursor, window_seconds=30)
            if not windows:
                print("No telemetry data found. Waiting...")
                time.sleep(2)
                continue
                
            for link_id, window in windows.items():
                # 1. Build Prediction Request
                pred_req = {
                    "schema_version": "1.0",
                    "target_type": "link",
                    "target_id": link_id,
                    "window_seconds": 30,
                    "telemetry_window": window,
                    "horizon_seconds": 5
                }
                
                # 2. Call Prediction Stub
                try:
                    resp = requests.post(PREDICT_URL, json=pred_req, timeout=2)
                    if resp.status_code == 200:
                        pred_data = resp.json()
                        prob = pred_data.get("failure_probability", 0.0)
                    else:
                        print(f"Prediction failed for {link_id}: {resp.status_code}")
                        continue
                except requests.exceptions.RequestException as e:
                    print(f"Error reaching prediction service: {e}")
                    continue
                
                # 3. Decision Engine
                action = evaluate_probability(prob)
                print(f"[{time.strftime('%H:%M:%S')}] Link {link_id} | Prob: {prob:.2f} | Action: {action}")
                
                # 4. Trigger Recovery if needed
                if action in ["prepare_backup", "reroute"]:
                    # Compute a real path using the CSPF path algorithm
                    from recovery.path_algorithms import build_registry_graph, cspf_path
                    import yaml
                    import networkx as nx
                    
                    graph = build_registry_graph()
                    endpoint_a, endpoint_b = "s1", "s2"
                    try:
                        with open("contracts/topology_registry.yaml") as f:
                            topo = yaml.safe_load(f)
                        for l in topo.get("links", []):
                            if l["link_id"] == link_id:
                                endpoint_a = l["endpoint_a"]["node_id"]
                                endpoint_b = l["endpoint_b"]["node_id"]
                                break
                    except Exception:
                        pass
                        
                    try:
                        path, cost = cspf_path(graph, endpoint_a, endpoint_b)
                        if not path:
                            path = ["s1", "s2"] # Fallback
                    except (nx.NodeNotFound, nx.NetworkXNoPath):
                        path = ["s1", "s2"]

                    action_req = {
                        "schema_version": "1.0",
                        "action_id": str(uuid.uuid4()),
                        "target_type": "link",
                        "target_link_id": link_id,
                        "target_node_id": None,
                        "new_path": path,
                        "reason": "predictive",
                        "triggering_probability": prob,
                        "run_id": "run_phase2",
                        "requested_ts_epoch_ms": int(time.time() * 1000)
                    }
                    try:
                        rec_resp = requests.post(RECOVERY_URL, json=action_req, timeout=2)
                        if rec_resp.status_code == 200:
                            print(f"  -> Recovery triggered successfully! ID: {action_req['action_id']}")
                        else:
                            print(f"  -> Recovery trigger failed: {rec_resp.status_code}")
                    except requests.exceptions.RequestException as e:
                        print(f"  -> Error reaching recovery service: {e}")

        except sqlite3.Error as e:
            print(f"Database error: {e}")
        finally:
            if 'conn' in locals():
                conn.close()
                
        time.sleep(2) # Poll every 2 seconds

if __name__ == "__main__":
    try:
        run_integration_loop()
    except KeyboardInterrupt:
        print("\nExiting Phase 2 Integration Engine.")
