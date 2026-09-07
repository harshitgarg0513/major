#!/usr/bin/env bash
# Phase 1 local verification (Members 2–4; Member 1 needs Docker).
set -euo pipefail
cd "$(dirname "$0")/.."
source venv/bin/activate

echo "=== Phase 1 / Member 2 — Telemetry seed demo ==="
python telemetry/seed_demo_record.py

echo ""
echo "=== Phase 1 / Member 3 — ML toy classifier ==="
python ml/toy_classifier.py

echo ""
echo "=== Phase 1 / Member 4 — Path algorithms ==="
python recovery/path_algorithms.py

echo ""
echo "Phase 1 local checks complete."
echo "Member 1 (Mininet ping): run inside Docker — see milestones/phase1/README.md"
