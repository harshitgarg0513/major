# Member 3 (ML) — Project Log

## 2026-09-07 — Phase 1 close-out
- What I built this session:
  - `ml/toy_classifier.py` — iris dataset train/eval pipeline proof
  - `ml/prediction_stub.py` — FastAPI stub (Day 0, ready for Phase 2 wiring)
- Decisions made and why:
  - sklearn RandomForest for Phase 1 proof (simple, no GPU); XGBoost import checked for env readiness
  - Real failure prediction model deferred to Phase 4+ on project telemetry data
- What's blocking me:
  - Nothing for Phase 1
- Tests run and results:
  - `python ml/toy_classifier.py` → accuracy ≥ 0.90 PASS

## Phase 1 close-out
- What got integrated:
  - ML environment only — not connected to telemetry DB yet
- What the demo showed:
  - Public dummy data → train → evaluate with printed metrics
- What didn't go as planned:
  - N/A
