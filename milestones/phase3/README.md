# Phase 3: Automated Dataset Generation & Emulation

This phase handles the transition from Phase 2's synthetic math-based telemetry to real, hardware-emulated OpenFlow telemetry datasets. It provides the automated infrastructure to generate the baseline dataset required for Phase 4 (ML Training) and Phase 5 (Evaluation).

## What Was Built
1. **Network Automation (`network/`)**:
   - `traffic_generator.py`: Runs a reproducible baseline of random TCP/UDP iperf traffic representing IoT cameras and sensors.
   - `fault_injector.py`: Programmatically induces `congestion_burst`, `link_failure`, and `node_failure`. It injects varying severities (e.g., 110%-300% link capacity) to ensure realistic borderline cases exist. It strictly adheres to the Day 0 `fault_log` contract.
   
2. **Phase 3 Orchestrator (`scripts/run_phase3_dataset_gen.py`)**:
   - The master script that boots the OS-Ken controller, Mininet topology, runs the normal traffic, and loops through 5 repetitions of every fault type.
   
3. **Data Pipeline (`ml/dataset_pipeline.py`)**:
   - Joins `test.db` telemetry with the `fault_log` and correctly implements **Predictive Labeling**.
   - It labels rows occurring in the 30-second precursor window *before* a fault as `1`, normal traffic as `0`, and explicitly filters/excludes rows occurring *during* the active fault (`-1`).

4. **Predictability Audit (`ml/predictability_audit.py`)**:
   - Implements Stage 5B of the research proposal. It analyzes the labeled CSV and plots Violin distributions of the 6 telemetry features comparing "Normal" vs "Precursor" windows, outputting a clear High/Moderate/Low detectability classification.

5. **Reactive Baseline (`recovery/reactive_baseline.py`)**:
   - A standalone reactive loop that detects failures only *after* they happen (e.g., packet loss > 10%) and triggers the recovery API. This serves as the static baseline control group for Phase 5.

## How to Run It

**Step 1: Generate the DB Dataset**
*(Run inside the Docker container — takes ~18 minutes)*
```bash
docker exec -it sdn_iot_env python3 scripts/run_phase3_dataset_gen.py
```

**Step 2: Export & Label the Dataset**
```bash
python3 ml/dataset_pipeline.py
```

**Step 3: Run the Predictability Audit (Stage 5B)**
```bash
python3 ml/predictability_audit.py
```
*(Check `ml/audit_plots/` for the visual signature of each fault type).*
