PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS cases (
  case_id TEXT PRIMARY KEY,
  snapshot_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS review_decisions (
  id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL REFERENCES cases(case_id),
  review_id TEXT NOT NULL,
  decision TEXT NOT NULL CHECK (decision IN ('reviewed','returned','abstained')),
  note TEXT NOT NULL DEFAULT '',
  actor TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS case_records (
  id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL REFERENCES cases(case_id),
  kind TEXT NOT NULL CHECK (kind IN ('acquisition','report','export')),
  status TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS media_runs (
  id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL REFERENCES cases(case_id),
  artifact_id TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('queued','running','completed','failed')),
  request_json TEXT NOT NULL,
  result_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS artifact_files (
  artifact_id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL REFERENCES cases(case_id),
  original_name TEXT NOT NULL,
  media_type TEXT NOT NULL,
  source_label TEXT NOT NULL,
  byte_size INTEGER NOT NULL,
  sha256 TEXT NOT NULL,
  stored_path TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_events (
  id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL REFERENCES cases(case_id),
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  details_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS idempotency_keys (
  case_id TEXT NOT NULL REFERENCES cases(case_id),
  key TEXT NOT NULL,
  response_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (case_id, key)
);
CREATE TABLE IF NOT EXISTS agent_memory (
  id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL REFERENCES cases(case_id),
  agent_id TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  sources_json TEXT NOT NULL,
  result_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_case_time ON audit_events(case_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_records_case_kind ON case_records(case_id, kind, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_case_artifact ON media_runs(case_id, artifact_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_memory_case_time ON agent_memory(case_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_artifact_files_case_time ON artifact_files(case_id, created_at DESC);
CREATE TABLE IF NOT EXISTS report_snapshots (
  id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL REFERENCES cases(case_id),
  title TEXT NOT NULL,
  summary_episode_id TEXT NOT NULL,
  envelope_json TEXT NOT NULL,
  content_sha256 TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_report_snapshots_case_time ON report_snapshots(case_id, created_at DESC);
CREATE TABLE IF NOT EXISTS artifact_inspections (
  id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL REFERENCES cases(case_id),
  artifact_id TEXT NOT NULL,
  result_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_inspection_case_artifact ON artifact_inspections(case_id,artifact_id,created_at DESC);
CREATE TABLE IF NOT EXISTS audio_screenings (
  id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL REFERENCES cases(case_id),
  artifact_id TEXT NOT NULL,
  result_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audio_screenings_case ON audio_screenings(case_id,artifact_id,created_at DESC);
