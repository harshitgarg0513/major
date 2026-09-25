# Member 2 (Telemetry/Data) — Project Log

## 2026-09-07 — Phase 1 close-out
- What I built this session:
  - `telemetry/db_init.py` — schema + topology seed + FK tests
  - `telemetry/seed_demo_record.py` — Phase 1 fabricated insert/read demo
  - `telemetry/telemetry_collector.py` — unified collector (Phase 2 prep, built early)
- Decisions made and why:
  - SQLite through Phase 3; Postgres before Phase 5 large runs (Day 0 decision)
  - Added `is_partial` and `measurement_scope` columns (v1.2 schema) for honest data quality
- What's blocking me:
  - **queue_length:** pyroute2 collector implemented but NOT confirmed on saturated queue yet
- Tests run and results:
  - `python telemetry/seed_demo_record.py` → PASS
  - `./scripts/verify_day0_local.sh` → PASS

## Phase 1 close-out
- What got integrated:
  - DB schema matches contracts; demo script proves write/read path
- What the demo showed:
  - Fabricated link + node rows validate against JSON Schema and persist in SQLite
- What didn't go as planned:
  - Built real collector ahead of schedule; saturation verification still pending

## 2026-09-25 — Phase 2 close-out
- What I built this session:
  - Merged L2 forwarding into `telemetry_collector.py` so we don't have to launch two OS-Ken apps simultaneously. This resolves the split-write database bugs and guarantees LLDP probes don't clash with normal IoT traffic flow-mods.
  - Added a staleness assertion in `db_init.py` so the database won't initialize if `topology_registry.yaml` is out of date compared to the Mininet topology definition.
  - Made `seed_demo_record.py` fully idempotent by returning exactly the `record_id` it just inserted in `read_back`.
  - Fixed `live_dashboard.py` to use a robust SQL `GROUP BY link_id` query ensuring it pulls the latest timestamps appropriately for each link.
- Decisions made and why:
  - We decided to ignore SQLite cache files (`*.db-shm` and `*.db-wal`) via `.gitignore` to avoid repository clutter during active orchestration.
- What's blocking me:
  - Nothing, telemetry collection and DB population is fully functional.
- Tests run and results:
  - Phase 1 local tests `verify_phase1.sh` now pass safely regardless of how many times they are executed sequentially.
