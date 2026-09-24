#!/usr/bin/env python3
"""
Phase 2 — Synthetic Data Generation for ML Scaffolding
"""
import pandas as pd
import numpy as np
import time
import os

def generate_telemetry_csv(filename="ml/synthetic_telemetry.csv", rows=1000):
    np.random.seed(42)
    start_ts = int(time.time() * 1000)
    
    data = {
        "ts_epoch_ms": [start_ts + (i * 1000) for i in range(rows)],
        "link_id": ["L1"] * rows,
        "throughput_mbps": np.random.normal(50, 10, rows).clip(0, 100),
        "latency_ms": np.random.normal(5, 1, rows).clip(1, 100),
        "packet_loss_pct": np.zeros(rows),
        "utilization_pct": np.random.normal(50, 10, rows).clip(0, 100),
        "queue_length": np.random.poisson(2, rows),
        "active_flows": np.random.poisson(10, rows),
        "will_fail_in_5s": np.zeros(rows, dtype=int)
    }

    # Simulate failures: Every 100th row is a failure precursor
    for i in range(50, rows, 100):
        # 5 seconds before failure (5 rows before)
        data["latency_ms"][i-5:i] = [10, 20, 50, 80, 99]
        data["packet_loss_pct"][i-5:i] = [0, 5, 20, 50, 100]
        data["queue_length"][i-5:i] = [10, 30, 60, 90, 100]
        data["will_fail_in_5s"][i-5:i] = 1
        
    df = pd.DataFrame(data)
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    df.to_csv(filename, index=False)
    print(f"Synthetic data generated at {filename} with {rows} rows.")

if __name__ == "__main__":
    generate_telemetry_csv()
