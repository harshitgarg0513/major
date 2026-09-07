#!/usr/bin/env bash
# Day-0 local verification (no Mininet/Docker required).
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== Regenerate topology registry ==="
source venv/bin/activate
python3 network/topology_builder.py

echo ""
echo "=== 8.1 Repo structure ==="
find . -maxdepth 2 -not -path './venv/*' -not -path './.git/*' | sort

echo ""
echo "=== 8.2 Database schema + polymorphic FK tests ==="
python telemetry/db_init.py

echo ""
echo "=== 8.3 Contract validation ==="
python contracts/validate.py

echo ""
echo "=== .gitignore check ==="
git check-ignore -v test.db

echo ""
echo "Day-0 local checks complete."
echo "For unified telemetry collector (8.2b/8.2c), use Docker — see README.md."
