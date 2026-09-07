"""Day-0 contract validation — jsonschema wrappers for every machine-readable contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema
from jsonschema import Draft7Validator

CONTRACTS_DIR = Path(__file__).resolve().parent


def _load_json(name: str) -> dict:
    with open(CONTRACTS_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def _validator(schema: dict) -> Draft7Validator:
    return Draft7Validator(schema)


_TELEMETRY = _load_json("telemetry_schema.json")
_FAULT_LOG = _load_json("fault_log_schema.json")
_PREDICTION = _load_json("prediction_interface.json")
_RECOVERY = _load_json("recovery_interface.json")

_LINK_TELEMETRY = _TELEMETRY["definitions"]["link_telemetry"]
_NODE_TELEMETRY = _TELEMETRY["definitions"]["node_telemetry"]
_PREDICTION_REQUEST = _PREDICTION["definitions"]["request"]
_PREDICTION_RESPONSE = _PREDICTION["definitions"]["response"]
_RECOVERY_REQUEST = _RECOVERY["definitions"]["action_request"]
_RECOVERY_CONFIRMATION = _RECOVERY["definitions"]["action_confirmation"]


def validate_link_telemetry(record: dict) -> None:
    _validator(_LINK_TELEMETRY).validate(record)


def validate_node_telemetry(record: dict) -> None:
    _validator(_NODE_TELEMETRY).validate(record)


def validate_fault_log(record: dict) -> None:
    _validator(_FAULT_LOG).validate(record)


def validate_prediction_request(record: dict) -> None:
    _validator(_PREDICTION_REQUEST).validate(record)


def validate_prediction_response(record: dict) -> None:
    _validator(_PREDICTION_RESPONSE).validate(record)


def validate_recovery_request(record: dict) -> None:
    _validator(_RECOVERY_REQUEST).validate(record)


def validate_recovery_confirmation(record: dict) -> None:
    _validator(_RECOVERY_CONFIRMATION).validate(record)


def _example(schema: dict) -> dict:
    return schema["example"]


def _run_checks() -> int:
    checks = [
        ("link_telemetry", validate_link_telemetry, _example(_LINK_TELEMETRY)),
        ("node_telemetry", validate_node_telemetry, _example(_NODE_TELEMETRY)),
        ("fault_log", validate_fault_log, _example(_FAULT_LOG)),
        ("prediction_request", validate_prediction_request, _example(_PREDICTION_REQUEST)),
        ("prediction_response", validate_prediction_response, _example(_PREDICTION_RESPONSE)),
        ("recovery_request", validate_recovery_request, _example(_RECOVERY_REQUEST)),
        ("recovery_confirmation", validate_recovery_confirmation, _example(_RECOVERY_CONFIRMATION)),
    ]

    failed = 0
    for name, fn, example in checks:
        try:
            fn(example)
            print(f"{name}: PASS")
        except jsonschema.ValidationError as exc:
            print(f"{name}: FAIL — {exc.message}")
            failed += 1

    return failed


if __name__ == "__main__":
    sys.exit(_run_checks())
