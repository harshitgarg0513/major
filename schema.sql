-- Topology Nodes table for the registry
-- SQLite: enable foreign keys before running — PRAGMA foreign_keys = ON;
CREATE TABLE topology_nodes (
    node_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    role TEXT
);

-- Topology Links table for the registry
CREATE TABLE topology_links (
    link_id TEXT PRIMARY KEY,
    endpoint_a_node_id TEXT NOT NULL,
    endpoint_a_port INTEGER NOT NULL,
    endpoint_b_node_id TEXT NOT NULL,
    endpoint_b_port INTEGER NOT NULL,
    capacity_mbps INTEGER NOT NULL,
    FOREIGN KEY (endpoint_a_node_id) REFERENCES topology_nodes(node_id),
    FOREIGN KEY (endpoint_b_node_id) REFERENCES topology_nodes(node_id)
);

-- Experiment Runs registry
CREATE TABLE experiment_runs (
    run_id TEXT PRIMARY KEY,
    condition TEXT NOT NULL,
    scenario TEXT NOT NULL,
    repetition_index INTEGER NOT NULL,
    start_ts_epoch_ms BIGINT NOT NULL,
    end_ts_epoch_ms BIGINT,
    notes TEXT
);

-- Link Telemetry data
CREATE TABLE link_telemetry (
    record_id TEXT PRIMARY KEY,
    ts_epoch_ms BIGINT NOT NULL,
    link_id TEXT NOT NULL,
    latency_ms REAL NOT NULL,
    latency_method TEXT NOT NULL,
    packet_loss_pct REAL NOT NULL,
    throughput_mbps REAL NOT NULL,
    utilization_pct REAL NOT NULL,
    queue_length INTEGER NOT NULL,
    active_flows INTEGER NOT NULL,
    poll_interval_ms INTEGER NOT NULL,
    is_partial INTEGER NOT NULL DEFAULT 0 CHECK (is_partial IN (0, 1)),
    FOREIGN KEY (link_id) REFERENCES topology_links(link_id)
);

-- Node Telemetry data
CREATE TABLE node_telemetry (
    record_id TEXT PRIMARY KEY,
    ts_epoch_ms BIGINT NOT NULL,
    node_id TEXT NOT NULL,
    cpu_pct REAL,
    ram_pct REAL,
    active_flows INTEGER NOT NULL,
    source TEXT NOT NULL,
    measurement_scope TEXT NOT NULL DEFAULT 'vm_shared'
        CHECK (measurement_scope IN ('host_isolated', 'vm_shared')),
    FOREIGN KEY (node_id) REFERENCES topology_nodes(node_id)
);

-- Fault Injection Log
-- target_link_id / target_node_id enforce polymorphic referential integrity.
CREATE TABLE fault_log (
    event_id TEXT PRIMARY KEY,
    fault_type TEXT NOT NULL,
    target_type TEXT NOT NULL CHECK (target_type IN ('link', 'node')),
    target_link_id TEXT,
    target_node_id TEXT,
    start_ts_epoch_ms BIGINT NOT NULL,
    end_ts_epoch_ms BIGINT,
    severity_params TEXT,
    seed INTEGER,
    injected_by TEXT NOT NULL,
    run_id TEXT,
    notes TEXT,
    FOREIGN KEY (target_link_id) REFERENCES topology_links(link_id),
    FOREIGN KEY (target_node_id) REFERENCES topology_nodes(node_id),
    FOREIGN KEY (run_id) REFERENCES experiment_runs(run_id),
    CHECK (
        (target_type = 'link' AND target_link_id IS NOT NULL AND target_node_id IS NULL)
        OR (target_type = 'node' AND target_node_id IS NOT NULL AND target_link_id IS NULL)
    )
);

-- Recovery Actions (combining action_request and action_confirmation)
CREATE TABLE recovery_actions (
    action_id TEXT PRIMARY KEY,
    schema_version TEXT NOT NULL,
    target_type TEXT NOT NULL CHECK (target_type IN ('link', 'node')),
    target_link_id TEXT,
    target_node_id TEXT,
    new_path TEXT,
    reason TEXT NOT NULL,
    triggering_probability REAL,
    run_id TEXT,
    requested_ts_epoch_ms BIGINT NOT NULL,
    status TEXT,
    applied_ts_epoch_ms BIGINT,
    verification_resolved BOOLEAN,
    verification_checked_ts_epoch_ms BIGINT,
    verification_method TEXT,
    FOREIGN KEY (target_link_id) REFERENCES topology_links(link_id),
    FOREIGN KEY (target_node_id) REFERENCES topology_nodes(node_id),
    FOREIGN KEY (run_id) REFERENCES experiment_runs(run_id),
    CHECK (
        (target_type = 'link' AND target_link_id IS NOT NULL AND target_node_id IS NULL)
        OR (target_type = 'node' AND target_node_id IS NOT NULL AND target_link_id IS NULL)
    )
);

-- Indexes for performance on timeseries and foreign keys
CREATE INDEX idx_link_telemetry_ts ON link_telemetry(ts_epoch_ms);
CREATE INDEX idx_link_telemetry_link_id ON link_telemetry(link_id);
CREATE INDEX idx_link_telemetry_is_partial ON link_telemetry(is_partial);

CREATE INDEX idx_node_telemetry_ts ON node_telemetry(ts_epoch_ms);
CREATE INDEX idx_node_telemetry_node_id ON node_telemetry(node_id);

CREATE INDEX idx_fault_log_ts ON fault_log(start_ts_epoch_ms);
CREATE INDEX idx_fault_log_run_id ON fault_log(run_id);
CREATE INDEX idx_fault_log_target_link ON fault_log(target_link_id);
CREATE INDEX idx_fault_log_target_node ON fault_log(target_node_id);

CREATE INDEX idx_recovery_actions_ts ON recovery_actions(requested_ts_epoch_ms);
CREATE INDEX idx_recovery_actions_run_id ON recovery_actions(run_id);
CREATE INDEX idx_recovery_actions_target_link ON recovery_actions(target_link_id);
CREATE INDEX idx_recovery_actions_target_node ON recovery_actions(target_node_id);
