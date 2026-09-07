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
