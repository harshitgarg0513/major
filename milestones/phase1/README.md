# Phase 1 — Foundations & Environment Proof

**Status:** Complete (solo integration — all four subsystems demonstrated independently)  
**Date:** 2026-09-07

## Goal

Prove each core subsystem works on its own before wiring them together in Phase 2.

| Subsystem | Owner (role) | Proof artifact | How to run |
|-----------|--------------|----------------|------------|
| Network emulation | Member 1 | `network/phase1_ping_demo.sh` | Docker only |
| Data storage | Member 2 | `telemetry/seed_demo_record.py` | Local venv |
| ML pipeline | Member 3 | `ml/toy_classifier.py` | Local venv |
| Path algorithms | Member 4 | `recovery/path_algorithms.py` | Local venv |

## Quick verify (local — Members 2–4)

```bash
cd sdn-iot-selfheal
source venv/bin/activate
./scripts/verify_phase1.sh
```

## Member 1 — Network (Docker)

```bash
docker-compose up -d --build
docker exec -it sdn_iot_env bash /app/network/phase1_ping_demo.sh
```

**Expect:** `pingall` completes with **0% dropped** between h1 and h2 through s1–L1–s2.

**Stack:** Mininet + Open vSwitch + OS-Ken (`network/simple_controller.py`)

## Member 2 — Telemetry / DB

```bash
python telemetry/seed_demo_record.py
```

**Expect:** Contract validation PASS, one `link_telemetry` + one `node_telemetry` row inserted and read back.

## Member 3 — ML

```bash
python ml/toy_classifier.py
```

**Expect:** Iris dataset, test accuracy ≥ 0.90, classification report printed.

## Member 4 — Path algorithms

```bash
python recovery/path_algorithms.py
```

**Expect:** Dijkstra primary path `h1 → s1 → s2 → h2` (cost 4), plus ≥2 k-shortest alternates.

---

## 5-minute mentor walkthrough script

1. **Network (1 min):** Show Docker ping demo output — real Mininet, real OVS, real controller, not a mock.
2. **Data (1 min):** Run `seed_demo_record.py` — show JSON-shaped rows validated against `contracts/telemetry_schema.json`.
3. **ML (1 min):** Run `toy_classifier.py` — show accuracy + report on public iris data.
4. **Algorithms (1 min):** Run `path_algorithms.py` — show primary + alternate paths on 6-node graph.
5. **Honest gaps (1 min):** Open `contracts/project_decisions.yaml` — controller chosen (OS-Ken), thresholds provisional, queue_length and host CPU scope flagged as not yet live-verified.

---

## Decisions locked at Phase 1 (provisional)

See [`contracts/project_decisions.yaml`](../contracts/project_decisions.yaml):

- **Controller:** OS-Ken
- **Thresholds:** Placeholder bins in `threshold_config.yaml` (Phase 5 tuning)
- **Repetitions:** 5 per scenario (working default until Stage 4 variance)
- **Queue length:** Implemented, saturation test pending
- **Host CPU scope:** Tagged `vm_shared` by default; lockstep test pending

---

## Integration note

Nothing is wired together yet — by design. Phase 2 connects telemetry collector → DB → prediction stub → recovery stub on the live Mininet topology.
