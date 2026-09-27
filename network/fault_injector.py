import time
import random
import uuid
import sqlite3
import json
import os
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "test.db"

def log_fault_to_db(fault_type, target_type, target_link_id, target_node_id, severity_params, seed):
    """Logs the fault to the fault_log DB table conforming to the Day-0 contract."""
    event_id = str(uuid.uuid4())
    start_ts_epoch_ms = int(time.time() * 1000)
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute('PRAGMA foreign_keys = ON;')
            conn.execute(
                """
                INSERT INTO fault_log (
                    event_id, fault_type, target_type, target_link_id, target_node_id,
                    start_ts_epoch_ms, severity_params, injected_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id, fault_type, target_type, target_link_id, target_node_id,
                    start_ts_epoch_ms, json.dumps(severity_params), "automated_injector"
                )
            )
            conn.commit()
            logger.info(f"Logged fault {event_id} ({fault_type}) at {start_ts_epoch_ms}")
    except Exception as e:
        logger.error(f"Failed to log fault: {e}")
        
    return start_ts_epoch_ms

def inject_congestion_burst(net, seed, run_id, duration_seconds=30):
    """Injects a UDP congestion burst of varying severity."""
    random.seed(seed)
    
    # Severe congestion on L1 or L2 (1000M links)
    bw = random.randint(1100, 3000) # 110% to 300% of link capacity
    
    h_server = net.get('h_server')
    h_sensor1 = net.get('h_sensor1')
    
    severity_params = {
        "bandwidth_mbps": bw,
        "duration_seconds": duration_seconds,
        "run_id": run_id,
        "seed": seed
    }
    
    # Target L1 (sensor1 is on edge1, server is on edge2)
    # The shortest path usually goes edge1 -> core -> edge2 (which is L1 -> L2)
    start_ts = log_fault_to_db("congestion_burst", "link", "L1", None, severity_params, seed)
    
    logger.info(f"Injecting congestion burst: {bw}M for {duration_seconds}s")
    h_sensor1.cmd(f'iperf -c {h_server.IP()} -u -b {bw}M -t {duration_seconds}')
    return start_ts

def inject_link_failure(net, seed, run_id, duration_seconds=30):
    """Injects a link failure (cable cut) and restores it after duration."""
    random.seed(seed)
    
    link_to_fail = random.choice([('s1', 's2'), ('s1', 's3')])
    target_link_id = "L1" if link_to_fail == ('s1', 's2') else "L2"
    
    severity_params = {
        "duration_seconds": duration_seconds,
        "failed_link_nodes": list(link_to_fail),
        "run_id": run_id,
        "seed": seed
    }
    
    start_ts = log_fault_to_db("link_failure", "link", target_link_id, None, severity_params, seed)
    
    logger.info(f"Failing link {link_to_fail} for {duration_seconds}s")
    net.configLinkStatus(link_to_fail[0], link_to_fail[1], 'down')
    
    time.sleep(duration_seconds)
    
    logger.info(f"Restoring link {link_to_fail}")
    net.configLinkStatus(link_to_fail[0], link_to_fail[1], 'up')
    return start_ts

def inject_node_failure(net, seed, run_id, duration_seconds=30):
    """Injects a node failure (switch crash) and recovers it."""
    random.seed(seed)
    
    node_to_fail = "s2"
    
    severity_params = {
        "duration_seconds": duration_seconds,
        "run_id": run_id,
        "seed": seed
    }
    
    start_ts = log_fault_to_db("node_failure", "node", None, node_to_fail, severity_params, seed)
    
    logger.info(f"Failing node {node_to_fail} for {duration_seconds}s")
    switch = net.get(node_to_fail)
    switch.stop()
    
    time.sleep(duration_seconds)
    
    logger.info(f"Restoring node {node_to_fail}")
    switch.start(net.controllers)
    return start_ts
