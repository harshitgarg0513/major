#!/usr/bin/env bash
# Verify whether node_collector cpu_pct is per-host or VM-wide (Docker/Mininet only).
#
# Expected on default Mininet: h1 and h2 cpu_pct move in lockstep -> vm_shared.
# Only trust cpu_pct for per-host analysis when measurement_scope = host_isolated.
set -euo pipefail

echo "=== Node CPU isolation test (run inside Docker after Mininet is up) ==="
echo ""
echo "1. Start collectors on h1 and h2 (Mininet CLI, two terminals or background):"
echo "     mininet> h1 python3 telemetry/node_collector.py --node-id h1 --once"
echo "     mininet> h2 python3 telemetry/node_collector.py --node-id h2 --once"
echo ""
echo "2. Baseline: note both cpu_pct values in node_telemetry."
echo ""
echo "3. Load h1 only (Mininet CLI):"
echo "     mininet> h1 python3 -c \"while True: pass\" &"
echo ""
echo "4. Wait ~5s, collect again:"
echo "     mininet> h1 python3 telemetry/node_collector.py --node-id h1 --once"
echo "     mininet> h2 python3 telemetry/node_collector.py --node-id h2 --once"
echo ""
echo "5. Compare in SQLite:"
cat <<'SQL'
sqlite3 /app/test.db "
  SELECT node_id, ts_epoch_ms, cpu_pct, measurement_scope
  FROM node_telemetry ORDER BY ts_epoch_ms DESC LIMIT 6;
"
SQL
echo ""
echo "If h2's cpu_pct rose with h1's load loop, measurement_scope should be vm_shared"
echo "and cpu_pct must NOT be used as a per-host precursor signal without cgroup isolation."
