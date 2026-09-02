import json
import time
import os
import asyncio
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import jsonschema

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("recovery_stub")

app = FastAPI(title="Recovery Action-Executor Stub")

# Load the Day-0 Contract schema
schema_path = os.path.join(os.path.dirname(__file__), '../Day-0/recovery_interface.json')
if not os.path.exists(schema_path):
    schema_path = os.path.join(os.path.dirname(__file__), '../../Day-0/recovery_interface.json')

with open(schema_path, 'r') as f:
    CONTRACT_SCHEMA = json.load(f)

REQUEST_SCHEMA = CONTRACT_SCHEMA["definitions"]["action_request"]
RESPONSE_SCHEMA = CONTRACT_SCHEMA["definitions"]["action_confirmation"]

@app.post("/execute_action")
async def execute_action(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid JSON payload")

    # 1. Validate incoming request against the JSON Schema
    try:
        jsonschema.validate(instance=body, schema=REQUEST_SCHEMA)
    except jsonschema.exceptions.ValidationError as e:
        return JSONResponse(status_code=422, content={"detail": e.message})

    # Log the incoming valid request
    action_id = body["action_id"]
    logger.info(f"Received action request for action_id: {action_id}")
    logger.info(f"Target: {body['target']} | Reason: {body['reason']}")

    # 2. Sleep 200ms (simulating flow-rule install latency)
    await asyncio.sleep(0.2)
    
    now_ms = int(time.time() * 1000)

    # 3. Build response matching the action_confirmation schema exactly
    response_body = {
        "schema_version": body.get("schema_version", "1.0"),
        "action_id": action_id,  # IMPORTANT: Echo the caller's action_id
        "status": "success",
        "applied_ts_epoch_ms": now_ms - 200, # Approximate applied time
        "verification": {
            "resolved": True,
            "checked_ts_epoch_ms": now_ms,
            "method": "stub_verification"
        }
    }

    # 4. Validate outgoing confirmation against the JSON Schema before sending
    try:
        jsonschema.validate(instance=response_body, schema=RESPONSE_SCHEMA)
    except jsonschema.exceptions.ValidationError as e:
        return JSONResponse(status_code=500, content={"detail": f"Generated invalid response: {e.message}"})

    return JSONResponse(content=response_body)
