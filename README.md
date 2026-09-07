# SDN IoT Selfheal

Predictive self-healing for SDN-controlled IoT networks. This repo collects link/node telemetry from an OS-Ken controller, stores it in a contract-defined schema, runs ML failure prediction, and executes recovery actions — all wired through shared contracts in [`contracts/`](./contracts/).

## Quick setup

```bash
./setup_env.sh          # creates venv + installs deps (Mac/local dev)
source venv/bin/activate
python telemetry/db_init.py   # creates test.db with topology + schema
```

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
FK constraint rejects unknown link_id: PASS
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
sqlite3 test.db "PRAGMA foreign_keys=ON; INSERT INTO link_telemetry (record_id, ts_epoch_ms, link_id, latency_ms, latency_method, packet_loss_pct, throughput_mbps, utilization_pct, queue_length, active_flows, poll_interval_ms) VALUES ('x', 1, 'L999', 0, 'lldp_probe', 0, 0, 0, 0, 0, 1000);"
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
    "target": {"type": "link", "id": "L1"},
    "new_path": ["s1", "s3", "s4", "s2"],
    "reason": "predictive",
    "triggering_probability": 0.83,
    "run_id": "run_0007",
    "requested_ts_epoch_ms": 1735999230000
  }' | python -m json.tool
```

**Check:** `action_id` in response equals the one you sent; `verification.method` is `telemetry_recheck`.

---

### 8.2b / 8.2c — OS-Ken telemetry + latency probe (requires Linux + Docker)

Mininet/OVS cannot run natively on macOS. Use Docker:

```bash
docker-compose up -d --build
docker exec -it sdn_iot_env bash
```

**Inside the container — Terminal A (init DB + controller):**

```bash
cd /app
python3 telemetry/db_init.py
os-ken-manager telemetry/telemetry_poller.py telemetry/latency_probe.py
```

**Inside the container — Terminal B (Mininet):**

```bash
cd /app
mn --custom telemetry/mininet_test_topo.py --topo mytopo \
  --controller remote,ip=127.0.0.1,port=6653 --link tc
```

At the Mininet CLI, start a 10 Mbps stream:

```
mininet> h1 iperf3 -s -D
mininet> h2 iperf3 -c h1 -b 10M -t 120
```

Wait ~30 seconds (first poll is skipped for delta math), then in **Terminal C**:

```bash
docker exec -it sdn_iot_env bash
sqlite3 /app/test.db "
  SELECT ts_epoch_ms, link_id, throughput_mbps, utilization_pct, latency_ms, latency_method
  FROM link_telemetry ORDER BY ts_epoch_ms DESC LIMIT 10;
"
```

**Expect for 8.2b (throughput):** `throughput_mbps` on `L1` roughly 8–12 Mbps (±20% of 10 Mbps iperf target).

**Expect for 8.2c (latency):** rows with `latency_method = 'lldp_probe'` and `latency_ms` near **10 ms** (link has `delay='10ms'` in `mininet_test_topo.py`). Values near 0 ms usually mean the probe is measuring controller↔switch delay, not link delay.

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
network/     Mininet/OVS/controller, fault injection, action-executor
telemetry/   Collector, DB init, dataset builder
ml/          Feature engineering, training, prediction service
recovery/    Path computation, threshold policy, decision engine
contracts/   Shared schemas (team agreement only)
docs/        Personal logs (see docs/personal_log_template.md)
milestones/  Phase-end integration artifacts
```
