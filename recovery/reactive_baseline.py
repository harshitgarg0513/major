import time
import logging
import sqlite3
import requests
import uuid
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reactive_baseline")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "test.db"
RECOVERY_API = "http://127.0.0.1:8001/execute_action"

def run_reactive_loop():
    logger.info("Starting Reactive Baseline Loop...")
    while True:
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Check for active failures (Reactive: reacting only AFTER fault degrades network)
                # E.g. packet loss > 10% or queue > 50
                cursor.execute("""
                    SELECT link_id, packet_loss_pct, queue_length 
                    FROM link_telemetry 
                    WHERE is_partial = 0
                    ORDER BY ts_epoch_ms DESC LIMIT 5
                """)
                rows = cursor.fetchall()
                
                for row in rows:
                    if row['packet_loss_pct'] > 10.0 or row['queue_length'] > 50:
                        logger.warning(f"REACTIVE TRIGGER: High congestion detected on {row['link_id']}")
                        
                        # Trigger recovery
                        payload = {
                            "action_id": str(uuid.uuid4()),
                            "schema_version": "1.0",
                            "target_type": "link",
                            "target_link_id": row['link_id'],
                            "target_node_id": None,
                            "reason": "reactive",
                            "requested_ts_epoch_ms": int(time.time() * 1000)
                        }
                        
                        try:
                            resp = requests.post(RECOVERY_API, json=payload, timeout=2)
                            if resp.status_code == 200:
                                logger.info(f"Recovery executed reactively for {row['link_id']}")
                                time.sleep(30) # Cool-down
                                break
                        except requests.exceptions.RequestException as e:
                            logger.error(f"Recovery API failed: {e}")
                            
        except Exception as e:
            logger.error(f"Error in reactive loop: {e}")
            
        time.sleep(2)

if __name__ == "__main__":
    run_reactive_loop()
