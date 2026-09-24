import json
import time
import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import jsonschema

app = FastAPI(title="Prediction Service Stub")

# Load contract schema from contracts/
schema_path = os.path.join(os.path.dirname(__file__), '../contracts/prediction_interface.json')

with open(schema_path, 'r') as f:
    CONTRACT_SCHEMA = json.load(f)

REQUEST_SCHEMA = CONTRACT_SCHEMA["definitions"]["request"]
RESPONSE_SCHEMA = CONTRACT_SCHEMA["definitions"]["response"]

@app.post("/predict")
async def predict(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid JSON payload")

    # 1. Validate incoming request against the JSON Schema
    try:
        jsonschema.validate(instance=body, schema=REQUEST_SCHEMA)
    except jsonschema.exceptions.ValidationError as e:
        # Return HTTP 422 with the validation error message on failure
        return JSONResponse(status_code=422, content={"detail": e.message})

    # 2. Compute cold_start logic
    # "cold_start set to true if telemetry_window has fewer than window_seconds 
    # worth of entries at the assumed poll interval (1 sec), else false"
    window_seconds = body.get("window_seconds", 30)
    telemetry_window = body.get("telemetry_window", [])
    cold_start = len(telemetry_window) < window_seconds
    
    now_ms = int(time.time() * 1000)

    # 3. Build response matching the response schema exactly
    # For Phase 2 demo, if any telemetry reading has queue > 0 or loss > 0, set prob to 0.85
    prob = 0.0
    for t in telemetry_window:
        if t.get("queue_length", 0) > 0 or t.get("packet_loss_pct", 0) > 0:
            prob = 0.85
            break

    response_body = {
        "schema_version": body.get("schema_version", "1.0"),
        "target_type": body["target_type"],
        "target_id": body["target_id"],
        "failure_probability": prob,
        "horizon_seconds": body["horizon_seconds"],
        "model_version": "stub_v0",
        "inference_ts_epoch_ms": now_ms,
        "cold_start": cold_start
    }

    # Optional internal sanity check to ensure our response actually complies with Day-0
    try:
        jsonschema.validate(instance=response_body, schema=RESPONSE_SCHEMA)
    except jsonschema.exceptions.ValidationError as e:
        return JSONResponse(status_code=500, content={"detail": f"Generated invalid response: {e.message}"})

    return JSONResponse(content=response_body)
