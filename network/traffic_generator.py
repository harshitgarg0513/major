import time
import random
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def start_normal_traffic(net, duration_seconds=900, seed=42):
    """Starts normal background traffic between hosts."""
    random.seed(seed)
    
    h_server = net.get('h_server')
    h_camera1 = net.get('h_camera1')
    h_sensor1 = net.get('h_sensor1')
    h_sensor2 = net.get('h_sensor2')

    # Start iperf servers on h_server (TCP and UDP)
    h_server.cmd('iperf -s &')
    h_server.cmd('iperf -s -u &')
    time.sleep(1)

    logger.info(f"Starting normal background traffic for {duration_seconds} seconds...")
    
    # Camera traffic (10-20M)
    bw_camera = random.randint(10, 20)
    h_camera1.cmd(f'iperf -c {h_server.IP()} -u -b {bw_camera}M -t {duration_seconds} &')
    
    # Sensor1 traffic (1-5M)
    bw_sensor1 = random.randint(1, 5)
    h_sensor1.cmd(f'iperf -c {h_server.IP()} -u -b {bw_sensor1}M -t {duration_seconds} &')

    # Sensor2 traffic (1-5M)
    bw_sensor2 = random.randint(1, 5)
    h_sensor2.cmd(f'iperf -c {h_server.IP()} -u -b {bw_sensor2}M -t {duration_seconds} &')
    
    logger.info(f"Traffic running: Camera1={bw_camera}M, Sensor1={bw_sensor1}M, Sensor2={bw_sensor2}M")

def stop_all_traffic(net):
    """Kills all iperf processes on all hosts."""
    logger.info("Stopping all traffic on all hosts...")
    for h in net.hosts:
        h.cmd('pkill -9 iperf')
