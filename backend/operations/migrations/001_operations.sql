CREATE TABLE IF NOT EXISTS alarm_acknowledgement (
    alarm_id TEXT PRIMARY KEY,
    actor TEXT NOT NULL,
    acknowledged_at TEXT NOT NULL,
    note TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS scenario_run (
    run_hash TEXT PRIMARY KEY,
    actor TEXT NOT NULL,
    created_at TEXT NOT NULL,
    request_json TEXT NOT NULL,
    result_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_event (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    occurred_at TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    target TEXT NOT NULL,
    details_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS audit_event_time ON audit_event(occurred_at DESC);
