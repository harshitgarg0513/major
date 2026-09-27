import sys
import os
import time
import subprocess
import logging
from pathlib import Path

# Add parent directory to path so we can import network modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

# We must import these after appending to sys.path
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.link import TCLink
from network.mininet_test_topo import MyTopo
from network.traffic_generator import start_normal_traffic, stop_all_traffic
from network.fault_injector import inject_congestion_burst, inject_link_failure, inject_node_failure

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("phase3_orchestrator")

def main():
    # 1. Wipe DB and re-init
    logger.info("Initializing database...")
    subprocess.run(["python3", "telemetry/db_init.py"], check=True, cwd=PROJECT_ROOT)
    
    # 2. Start OS-Ken Controller in background
    logger.info("Starting OS-Ken controller...")
    log_file = open(PROJECT_ROOT / "controller_phase3.log", "w")
    controller_proc = subprocess.Popen(
        ["osken-manager", "telemetry/telemetry_collector.py"],
        stdout=log_file, stderr=log_file, cwd=PROJECT_ROOT
    )
    time.sleep(5) # Wait for controller to boot
    
    # 3. Start Mininet
    logger.info("Starting Mininet...")
    topo = MyTopo()
    net = Mininet(
        topo=topo,
        controller=lambda name: RemoteController(name, ip="127.0.0.1", port=6653),
        link=TCLink
    )
    net.start()
    
    try:
        # Wait for LLDP discovery
        logger.info("Waiting 15 seconds for LLDP discovery...")
        time.sleep(15)
        
        run_id = "run_phase3" 
        seed_base = 42
        
        logger.info("Starting normal background traffic...")
        # 3600 seconds is 1 hour, enough to cover our experiment time
        start_normal_traffic(net, duration_seconds=3600, seed=seed_base)
        
        # Give normal traffic time to establish baseline
        logger.info("Gathering initial baseline for 30 seconds...")
        time.sleep(30)
        
        # 4. Inject Faults sequentially with cool-down periods
        faults = [
            ("congestion_burst", inject_congestion_burst),
            ("link_failure", inject_link_failure),
            ("node_failure", inject_node_failure)
        ]
        
        for i in range(5): # 5 repetitions per fault type
            logger.info(f"--- Starting Repetition {i+1}/5 ---")
            for fault_name, fault_func in faults:
                logger.info(f"Waiting for stable baseline (45s)...")
                time.sleep(45) # Baseline before fault (this is the precursor window)
                
                logger.info(f"Injecting {fault_name}...")
                fault_func(net, seed=seed_base+i, run_id=run_id, duration_seconds=30)
                
                logger.info(f"Fault {fault_name} finished. Cooling down...")
        
        logger.info("Dataset generation complete. Stopping traffic...")
        stop_all_traffic(net)
        
    finally:
        logger.info("Stopping Mininet...")
        net.stop()
        logger.info("Stopping OS-Ken controller...")
        controller_proc.terminate()
        controller_proc.wait()
        log_file.close()
        
    logger.info("Phase 3 Emulation finished. test.db now contains the dataset!")

if __name__ == "__main__":
    if os.geteuid() != 0:
        logger.error("This script must be run as root (or inside the Docker container).")
        sys.exit(1)
    main()
