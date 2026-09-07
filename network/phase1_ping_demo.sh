#!/usr/bin/env bash
# Phase 1 — Member 1 proof: 2-switch Mininet topology, end-to-end ping via OS-Ken.
# Run inside Docker: docker exec -it sdn_iot_env bash /app/network/phase1_ping_demo.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== Phase 1 / Member 1 — Network ping demo ==="

if ! command -v mn >/dev/null; then
  echo "FAIL: mininet (mn) not found — run this inside the Docker container."
  exit 1
fi

service openvswitch-switch start >/dev/null 2>&1 || true

# Start controller in background
echo "Starting OS-Ken simple controller..."
os-ken-manager network/simple_controller.py &
CTRL_PID=$!
sleep 3

cleanup() {
  kill "$CTRL_PID" 2>/dev/null || true
  mn -c 2>/dev/null || true
}
trap cleanup EXIT

echo "Starting Mininet and running pingAll..."
mn --custom network/mininet_test_topo.py --topo mytopo \
  --controller remote,ip=127.0.0.1,port=6653 \
  --link tc \
  --test pingall

echo ""
echo "PASS: pingAll completed (see 0% packet loss above)."
