# Member 4 (Algorithms/Recovery) — Project Log

## 2026-09-07 — Phase 1 close-out
- What I built this session:
  - `recovery/path_algorithms.py` — Dijkstra + k-shortest on 6-node sample graph
  - `recovery/recovery_stub.py` — FastAPI action executor stub (Day 0)
- Decisions made and why:
  - **Threshold bins:** kept as placeholders in `contracts/threshold_config.yaml` (Phase 5 empirical Q6)
  - **Repetitions:** 5 per scenario provisional default in `contracts/project_decisions.yaml`
- What's blocking me:
  - Nothing for Phase 1
- Tests run and results:
  - `python recovery/path_algorithms.py` → primary path + alternates PASS

## Phase 1 close-out
- What got integrated:
  - Path algorithms standalone — not yet driving live flow rules
- What the demo showed:
  - Sane primary path h1→s1→s2→h2 and at least two alternates via s3/s4
- What didn't go as planned:
  - N/A

## 2026-09-25 — Phase 2 close-out
- What I built this session:
  - Wrote `build_registry_graph()` in `path_algorithms.py` so path computation is dynamically based on `topology_registry.yaml` capacities and delays rather than a hardcoded sample graph.
  - Implemented the full schema-compliant `INSERT` statement in `recovery_stub.py`, writing all 15 columns of `recovery_actions` (including `new_path`, `status`, and `verification_method`) to the database.
  - Added `functools.lru_cache` to `decision_engine.py`'s `load_thresholds()` to stop redundant config re-parsing on every poll.
- Decisions made and why:
  - Ensured `run_phase2.py` gracefully catches `nx.NodeNotFound` and `nx.NetworkXNoPath` during path recomputation and falls back to a primary default (`s1`, `s2`), ensuring the orchestrator doesn't crash if the graph breaks.
  - Registered `run_phase2` in `contracts/experiment_runs.yaml` to ensure the simulated Phase 2 orchestrator runs successfully pass foreign key constraint checks.
- What's blocking me:
  - Ready for Phase 3 and beyond.
- Tests run and results:
  - Validated local path resolution successfully executes the fallback logic.
  - Verified `recovery_actions` properly records the 15 required row properties when triggered.
