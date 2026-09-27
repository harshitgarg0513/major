import sqlite3
import pandas as pd
import json
import logging
from pathlib import Path
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dataset_pipeline")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "test.db"
OUTPUT_PATH = PROJECT_ROOT / "ml" / "labeled_dataset.csv"

PRECURSOR_WINDOW_MS = 30000  # 30 seconds runway

def extract_and_label_dataset():
    if not DB_PATH.exists():
        logger.error(f"Database not found at {DB_PATH}")
        return

    logger.info("Connecting to database...")
    with sqlite3.connect(DB_PATH) as conn:
        # Load telemetry (excluding partials to avoid noise)
        logger.info("Loading link_telemetry (is_partial=0)...")
        telemetry_df = pd.read_sql_query("""
            SELECT ts_epoch_ms, link_id, latency_ms, packet_loss_pct, 
                   throughput_mbps, utilization_pct, queue_length, active_flows
            FROM link_telemetry
            WHERE is_partial = 0
            ORDER BY ts_epoch_ms ASC
        """, conn)

        # Load faults
        logger.info("Loading fault_log...")
        faults_df = pd.read_sql_query("""
            SELECT event_id, fault_type, target_link_id, target_node_id, 
                   start_ts_epoch_ms, severity_params
            FROM fault_log
        """, conn)

    if telemetry_df.empty:
        logger.warning("No complete telemetry rows found in DB.")
        return

    # Initialize labels
    # 0 = Normal
    # 1 = Precursor (Warning: fault coming soon)
    # -1 = Active Fault (Exclude from training)
    telemetry_df['label'] = 0
    telemetry_df['fault_type'] = 'none'

    logger.info("Applying PREDICTIVE labels based on precursor windows...")
    
    for _, fault in faults_df.iterrows():
        try:
            params = json.loads(fault['severity_params'])
            duration_ms = params.get('duration_seconds', 30) * 1000
        except Exception:
            duration_ms = 30000 # default 30s
            
        f_start = fault['start_ts_epoch_ms']
        f_end = f_start + duration_ms
        precursor_start = f_start - PRECURSOR_WINDOW_MS
        
        # 1. Label Active Fault (-1)
        active_mask = (telemetry_df['ts_epoch_ms'] >= f_start) & (telemetry_df['ts_epoch_ms'] <= f_end)
        telemetry_df.loc[active_mask, 'label'] = -1
        telemetry_df.loc[active_mask, 'fault_type'] = fault['fault_type']
        
        # 2. Label Precursor Window (1)
        # Condition: only set to 1 if it's currently 0 (don't overwrite an existing active fault -1)
        precursor_mask = (telemetry_df['ts_epoch_ms'] >= precursor_start) & \
                         (telemetry_df['ts_epoch_ms'] < f_start) & \
                         (telemetry_df['label'] == 0)
        
        telemetry_df.loc[precursor_mask, 'label'] = 1
        telemetry_df.loc[precursor_mask, 'fault_type'] = fault['fault_type']

    logger.info(f"Label distribution:\n{telemetry_df['label'].value_counts()}")
    
    telemetry_df.to_csv(OUTPUT_PATH, index=False)
    logger.info(f"Dataset successfully exported and labeled to {OUTPUT_PATH}")
    logger.info("Remember: For ML training, EXCLUDE rows where label == -1")

if __name__ == "__main__":
    extract_and_label_dataset()
