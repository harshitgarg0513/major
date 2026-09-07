# Member 1 (Network/SDN) — Project Log

## 2026-09-07 — Phase 1 close-out
- What I built this session:
  - `network/simple_controller.py` — OS-Ken L2 learning switch for Phase 1 ping
  - `network/phase1_ping_demo.sh` — automated pingAll proof inside Docker
  - Existing `network/mininet_test_topo.py` (2-switch, h1/h2) used as topology
- Decisions made and why:
  - **Controller: OS-Ken** (see `contracts/project_decisions.yaml`) — Python stack alignment
  - ONOS deferred; we own LLDP probe in `telemetry_collector.py` instead
- What's blocking me:
  - Nothing for Phase 1; live ping demo requires Docker on Mac
- Tests run and results:
  - `bash network/phase1_ping_demo.sh` inside Docker → pingAll 0% loss (run manually)

## Phase 1 close-out
- What got integrated:
  - Standalone network proof only — not wired to telemetry yet
- What the demo showed:
  - h1 ↔ h2 ping through s1–L1–s2 with remote OS-Ken controller
- What didn't go as planned:
  - N/A — scope was intentionally minimal L2 switch, not full telemetry controller
