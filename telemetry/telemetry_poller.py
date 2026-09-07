"""DEPRECATED — use telemetry_collector.py instead."""

import warnings

warnings.warn(
    "telemetry_poller.py is deprecated; use: os-ken-manager telemetry/telemetry_collector.py",
    DeprecationWarning,
    stacklevel=2,
)

from telemetry_collector import LinkTelemetryCollector as TelemetryPoller  # noqa: F401
