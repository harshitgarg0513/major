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

## 2026-09-25 — Phase 2 close-out
- What I built this session:
  - Updated `network/mininet_test_topo.py` to a more realistic Phase 2 topology (3 switches, 4 IoT hosts).
  - Modified `network/topology_builder.py` to dynamically infer node roles (e.g., `iot_camera`, `edge_gateway`) from hostnames and to correctly parse `bw` and `delay` from Mininet options.
  - Merged L2 forwarding capabilities from `simple_controller.py` directly into `telemetry_collector.py` to form a unified OS-Ken application, ensuring no conflicts in packet-in handling.
- Decisions made and why:
  - We decided to merge packet forwarding into the telemetry collector instead of running two separate controller applications via `osken-manager`, which avoids flow rule priority race conditions.
  - Allowed `node_id` strings to support underscores (e.g., `h_sensor1`) in `contracts/telemetry_schema.json` to properly name IoT edge nodes.
- What's blocking me:
  - Nothing, Phase 2 is now fully integrated.
- Tests run and results:
  - `python3 network/topology_builder.py` produces correct link capacities (`1000`) and delays (`5.0`) in `contracts/topology_registry.yaml`.
