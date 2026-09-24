#!/usr/bin/env python3
"""
Phase 2 — Live Telemetry Dashboard
Continuously reads from test.db and displays the latest network state.
"""

import sqlite3
import time
import os

DB_PATH = "test.db"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_dashboard():
    if not os.path.exists(DB_PATH):
        print(f"Waiting for database {DB_PATH} to be created...")
        return False

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get the latest timestamp
        cursor.execute("SELECT MAX(ts_epoch_ms) FROM link_telemetry")
        latest_ts = cursor.fetchone()[0]
        
        if not latest_ts:
            print("Database exists, waiting for telemetry data...")
            return True
            
        # Get all records for that timestamp
        cursor.execute("""
            SELECT link_id, throughput_mbps, latency_ms, packet_loss_pct, queue_length, utilization_pct, active_flows
            FROM link_telemetry 
            WHERE ts_epoch_ms = ?
            ORDER BY link_id
        """, (latest_ts,))
        
        rows = cursor.fetchall()
        
        clear_screen()
        print(f"=== SDN IoT Live Telemetry Dashboard ===")
        print(f"Last Update: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(latest_ts/1000))}")
        print("-" * 110)
        print(f"{'Link ID':<10} | {'Throughput (Mbps)':<18} | {'Latency (ms)':<15} | {'Packet Loss (%)':<16} | {'Queue Length':<15} | {'Util (%)':<10} | {'Flows':<10}")
        print("-" * 110)
        
        for row in rows:
            link, tp, lat, ploss, qlen, util, flows = row
            print(f"{link:<10} | {tp:<18.2f} | {lat:<15.2f} | {ploss:<16.2f} | {qlen:<15} | {util:<10.2f} | {flows:<10}")
            
        print("-" * 110)
        print("Press Ctrl+C to exit.")
        return True
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return True
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    try:
        while True:
            print_dashboard()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting dashboard.")
