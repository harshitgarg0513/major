# SDN IoT Selfheal

Predictive self-healing for SDN-controlled IoT networks. This repo collects link/node telemetry from an OS-Ken controller, stores it in a contract-defined schema, runs ML failure prediction, and executes recovery actions — all wired through shared contracts in [`contracts/`](./contracts/).

## Quick setup

```bash
./setup_env.sh          # creates venv + installs deps (Mac/local dev)
source venv/bin/activate
python telemetry/db_init.py           # creates test.db from committed contracts/topology_registry.yaml
```

`network/topology_builder.py` requires Mininet (Linux/Docker only) — run it inside the Docker container when the Mininet topology changes; see **8.2b/8.2c** below.

## Phase 1 — Foundations (current milestone)

All four subsystems have independent proofs. See [`milestones/phase1/README.md`](./milestones/phase1/README.md) for the mentor walkthrough.

```bash
source venv/bin/activate
./scripts/verify_phase1.sh          # Members 2–4 (local)
# Member 1 (Docker):
docker exec -it sdn_iot_env bash /app/network/phase1_ping_demo.sh
```

Project decisions (controller, thresholds, known gaps): [`contracts/project_decisions.yaml`](./contracts/project_decisions.yaml)

Personal logs: [`docs/member1_network_log.md`](./docs/member1_network_log.md) … [`docs/member4_recovery_log.md`](./docs/member4_recovery_log.md)

## Day-0 Manual Test Checklist

Run these in order. Each block maps to Section 8 of the Day-0 contracts doc.

### 8.1 — Repo scaffold

```bash
cd sdn-iot-selfheal
find . -maxdepth 2 -not -path './venv/*' -not -path './.git/*' | sort
```

**Expect:** `network/`, `telemetry/`, `ml/`, `recovery/`, `contracts/`, `docs/`, `milestones/phase1` … `phase6`, `README.md`, `.gitignore`.

**Expect `.gitignore` works:**

```bash
touch test.db && git check-ignore -v test.db
# should print: .gitignore:5:*.db    test.db
```

Or run the bundled script:

```bash
chmod +x scripts/verify_day0_local.sh
./scripts/verify_day0_local.sh
```

---

### 8.2 — Database schema (DDL)

```bash
source venv/bin/activate
python telemetry/db_init.py
```

**Expect output:**

```
Initialized .../test.db
link_telemetry FK rejects bogus target: PASS
fault_log FK rejects bogus target: PASS
recovery_actions FK rejects bogus target: PASS
```

**Manual spot-check:**

```bash
sqlite3 test.db "SELECT node_id, kind FROM topology_nodes;"
sqlite3 test.db "SELECT link_id, capacity_mbps FROM topology_links;"
sqlite3 test.db "SELECT run_id, condition FROM experiment_runs;"
```

**Expect:** nodes `s1`, `s2`, `h1`, `h2`; link `L1` at 100 Mbps; run `run_0007`.

**FK rejection test (should error):**

```bash
sqlite3 test.db "PRAGMA foreign_keys=ON; INSERT INTO link_telemetry (record_id, ts_epoch_ms, link_id, latency_ms, latency_method, packet_loss_pct, throughput_mbps, utilization_pct, queue_length, active_flows, poll_interval_ms, is_partial) VALUES ('x', 1, 'L999', 0, 'lldp_probe', 0, 0, 0, 0, 0, 1000, 0);"
```

---

### 8.3 — Contract validation

```bash
python contracts/validate.py
```

**Expect:** seven lines, all `PASS`.

**Negative test:**

```bash
python -c "
from contracts.validate import validate_link_telemetry, _LINK_TELEMETRY
ex = dict(_LINK_TELEMETRY['example']); ex['packet_loss_pct'] = 150
validate_link_telemetry(ex)
"
# should raise ValidationError: 150 is greater than the maximum of 100
```

---

### 8.4 — Prediction service stub

**Terminal 1:**

```bash
source venv/bin/activate
uvicorn ml.prediction_stub:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 — valid request (expect HTTP 200, failure_probability 0.0, cold_start true with 1 sample):**

```bash
curl -s -X POST http://127.0.0.1:8000/predict \
  -H 'Content-Type: application/json' \
  -d '{
    "schema_version": "1.0",
    "target_type": "link",
    "target_id": "L1",
    "window_seconds": 30,
    "telemetry_window": [
      {"ts_epoch_ms": 1735999200000, "latency_ms": 4.2, "packet_loss_pct": 0.0,
       "throughput_mbps": 12.4, "utilization_pct": 12.4, "queue_length": 3, "active_flows": 5}
    ],
    "horizon_seconds": 5
  }' | python -m json.tool
```

**Invalid request (expect HTTP 422):**

```bash
curl -s -w "\nHTTP:%{http_code}\n" -X POST http://127.0.0.1:8000/predict \
  -H 'Content-Type: application/json' \
  -d '{"schema_version":"1.0","target_type":"link","window_seconds":30,"telemetry_window":[],"horizon_seconds":5}'
```

---

### 8.5 — Recovery action-executor stub

**Terminal 1:**

```bash
source venv/bin/activate
uvicorn recovery.recovery_stub:app --host 127.0.0.1 --port 8001 --reload
```

**Terminal 2 — valid request (expect HTTP 200, same action_id echoed back):**

```bash
curl -s -X POST http://127.0.0.1:8001/execute_action \
  -H 'Content-Type: application/json' \
  -d '{
    "schema_version": "1.0",
    "action_id": "d5b3e4c0-3333-4a2b-9c3d-000000000001",
    "target_type": "link",
    "target_link_id": "L1",
    "target_node_id": null,
    "new_path": ["s1", "s3", "s4", "s2"],
    "reason": "predictive",
    "triggering_probability": 0.83,
    "run_id": "run_0007",
    "requested_ts_epoch_ms": 1735999230000
  }' | python -m json.tool
```

**Check:** `action_id` in response equals the one you sent; `verification.method` is `telemetry_recheck`.

---

### 8.2b / 8.2c — Unified telemetry collector (requires Linux + Docker)

Mininet/OVS cannot run natively on macOS. Use Docker:

```bash
docker-compose up -d --build
docker exec -it sdn_iot_env bash
```

**Inside the container — Terminal A (registry + DB + single collector app):**

```bash
cd /app
python3 network/topology_builder.py   # sync contracts/topology_registry.yaml from Mininet topo
python3 telemetry/db_init.py
osken-manager telemetry/telemetry_collector.py
```

Use **one** collector app — do not run `telemetry_poller.py` and `latency_probe.py` separately (deprecated; they caused split half-rows).

**Inside the container — Terminal B (Mininet):**

```bash
cd /app
mn --custom network/mininet_test_topo.py --topo mytopo \
  --controller remote,ip=127.0.0.1,port=6653 --link tc
```

At the Mininet CLI, start traffic and optional host telemetry:

```
mininet> h1 iperf3 -s -D
mininet> h2 iperf3 -c h1 -b 10M -t 120
mininet> h1 python3 telemetry/node_collector.py --node-id h1 --once
```

**Node CPU scope:** default Mininet shares the PID namespace — `cpu_pct`/`ram_pct` are VM-wide, tagged `measurement_scope='vm_shared'`. Run `./scripts/test_node_cpu_isolation.sh` inside Docker before using these columns in Stage 5B.

Wait ~30 seconds (first poll skipped for counter deltas), then query:

```bash
sqlite3 /app/test.db "
  SELECT ts_epoch_ms, link_id, throughput_mbps, utilization_pct,
         latency_ms, latency_method, queue_length, packet_loss_pct, is_partial
  FROM link_telemetry ORDER BY ts_epoch_ms DESC LIMIT 10;
"
```

**Filter partial OpenFlow stat cycles (Stage 5B):**

```bash
sqlite3 /app/test.db "SELECT COUNT(*) FROM link_telemetry WHERE is_partial = 1;"
# Use WHERE is_partial = 0 for trend analysis
```

**Expect (8.2b throughput):** one row per timestamp with **both** real `throughput_mbps` (~8–12 Mbps) **and** real `latency_ms` (~10 ms) — not separate half-rows.

**Expect (8.2c latency):** `latency_method = 'lldp_probe'` (or `configured_static` before first probe returns).

**Verify no split-write corruption:**

```bash
sqlite3 /app/test.db "
  SELECT COUNT(*) FROM link_telemetry
  WHERE latency_ms = 0.0 OR throughput_mbps = 0.0;
"
```

Should be **0** (or near-zero only during the very first cold-start second), not ~50% of rows.

**Verify queue_length (saturation test):**

```bash
# In Mininet CLI — flood past max_queue_size=100 on L1:
mininet> h2 iperf3 -c h1 -b 200M -t 30
```

Then confirm `queue_length > 0` on L1 rows during saturation.

**Polymorphic FK test (fault log):**

```bash
sqlite3 /app/test.db "PRAGMA foreign_keys=ON;
  INSERT INTO fault_log (event_id, fault_type, target_type, target_link_id, target_node_id,
    start_ts_epoch_ms, severity_params, injected_by)
  VALUES ('x', 'link_failure', 'link', 'L999', NULL, 1, '{}', 'test');"
# Expect: Error: FOREIGN KEY constraint failed
```

---

## Contracts

All machine-readable Day-0 contracts live in [`contracts/`](./contracts/):

| File | Purpose |
|------|---------|
| `topology_registry.yaml` | Node/link IDs and capacities |
| `telemetry_schema.json` | `link_telemetry` / `node_telemetry` shapes |
| `fault_log_schema.json` | Fault injection event log |
| `prediction_interface.json` | ML prediction request/response |
| `recovery_interface.json` | Recovery action request/confirmation |
| `threshold_config.yaml` | Placeholder confidence bins (Phase 5 tuning) |
| `experiment_runs.yaml` | Phase 5 trial registry |
| `validate.py` | jsonschema validators for all of the above |

## Repo layout

```
network/     Mininet/OVS topology, topology_builder.py (generates contracts/topology_registry.yaml)
telemetry/   Unified collector, DB init, node_collector.py (psutil, run inside Mininet hosts)
ml/          Feature engineering, training, prediction service
recovery/    Path computation, threshold policy, decision engine
contracts/   Shared schemas (team agreement only; topology_registry.yaml is generated)
docs/        Personal logs (see docs/personal_log_template.md)
milestones/  Phase-end integration artifacts
```

### Regenerating topology registry (Docker / Linux only)

Requires Mininet. Run inside the Docker container whenever `network/mininet_test_topo.py` changes:

```bash
python3 network/topology_builder.py
python telemetry/db_init.py   # re-seed DB after registry change
```
