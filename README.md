# SDN IoT Selfheal

This project provides an automated, self-healing architecture for Software-Defined Networking (SDN) in IoT environments. It integrates network telemetry, machine learning, and automated recovery mechanisms to detect and mitigate anomalies in real-time. By leveraging these technologies, the system ensures high availability and robustness for critical IoT deployments. For information on smart contracts used in the recovery and auditing processes, please refer to the [contracts](./contracts/) directory.

## Getting Started

### 1. Fix IDE Errors (On your Mac)
Run the setup script in your terminal to create the python virtual environment:
```bash
./setup_env.sh
```
*After this, configure your IDE (VSCode/PyCharm) to use the Python interpreter located inside the newly created `venv/` folder.*

### 2. Run the Mininet Environment (Docker)
Ensure Docker Desktop is running, then start the environment:
```bash
docker-compose up -d --build
```

### 3. Test the Telemetry App Inside Docker
Now, jump into the container to run your code exactly as if you were on a Linux machine:
```bash
docker exec -it sdn_iot_env bash
```

Once inside the container shell, you can run the exact commands to start the controllers:
```bash
# Terminal 1 inside docker (OS-Ken running both apps):
os-ken-manager telemetry/telemetry_poller.py telemetry/latency_probe.py

# Terminal 2 inside docker (Mininet):
mn --custom telemetry/mininet_test_topo.py --topo mytopo --controller remote,ip=127.0.0.1,port=6653 --link tc
```

### 4. Run the Machine Learning & Recovery Service Stubs
These are built on FastAPI and can be run locally directly from your Mac terminal (since the `venv` has all dependencies installed). 

**Start the Prediction stub:**
```bash
source venv/bin/activate
uvicorn ml.prediction_stub:app --host 127.0.0.1 --port 8000 --reload
```

**Start the Recovery stub (on a different port):**
```bash
source venv/bin/activate
uvicorn recovery.recovery_stub:app --host 127.0.0.1 --port 8001 --reload
```
