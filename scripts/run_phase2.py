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

def get_latest_telemetry(cursor):
    """Fetch the latest telemetry window for all links."""
    # To keep it simple, just grab the most recent row for each link_id
    cursor.execute("""
        SELECT link_id, ts_epoch_ms, latency_ms, packet_loss_pct, throughput_mbps, utilization_pct, queue_length, active_flows
        FROM link_telemetry
        WHERE (link_id, ts_epoch_ms) IN (
            SELECT link_id, MAX(ts_epoch_ms)
            FROM link_telemetry
            GROUP BY link_id
        )
    """)
    return cursor.fetchall()

def run_integration_loop():
    if not os.path.exists(DB_PATH):
        print(f"Waiting for database {DB_PATH} to be created...")
        return
        
    print("=== Phase 2 Integration Engine Started ===")
    
    while True:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            latest_rows = get_latest_telemetry(cursor)
            if not latest_rows:
                print("No telemetry data found. Waiting...")
                time.sleep(2)
                continue
                
            for row in latest_rows:
                link_id, ts, lat, ploss, tput, util, qlen, flows = row
                
                # 1. Build Prediction Request
                pred_req = {
                    "schema_version": "1.0",
                    "target_type": "link",
                    "target_id": link_id,
                    "window_seconds": 30,
                    "telemetry_window": [{
                        "ts_epoch_ms": ts,
                        "latency_ms": lat,
                        "packet_loss_pct": ploss,
                        "throughput_mbps": tput,
                        "utilization_pct": util,
                        "queue_length": qlen,
                        "active_flows": flows
                    }],
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
                    from recovery.path_algorithms import build_sample_graph, cspf_path
                    graph = build_sample_graph()
                    path, cost = cspf_path(graph, "h1", "h2")
                    if not path:
                        path = ["s1", "s2"] # Fallback

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
