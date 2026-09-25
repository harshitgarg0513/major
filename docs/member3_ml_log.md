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

## 2026-09-25 — Phase 2 close-out
- What I built this session:
  - Updated `train_models.py` by removing deprecated arguments (like `use_label_encoder=False`) and implementing proper model validation.
  - Set `class_weight='balanced'` in basic algorithms and `scale_pos_weight=10` in XGBoost to handle class imbalance transparently.
  - Implemented real cross-validation (`cross_val_score`) to produce accurate validation metrics.
  - Updated `prediction_stub.py` (via integration scripts) to properly process a real 30-second sliding window telemetry payload instead of just a dummy fallback.
- Decisions made and why:
  - Added an explicit disclaimer to the `train_models.py` outputs stating the synthetic data is trivially separable, preventing accidental misinterpretation of Phase 2 logic checks as Phase 4 capability.
- What's blocking me:
  - Awaiting Phase 3 and 4 to feed real fault data to transition the stub into a real trained model serving predictions.
- Tests run and results:
  - Verified `train_models.py` executes successfully locally with proper 5-fold CV outputs.
