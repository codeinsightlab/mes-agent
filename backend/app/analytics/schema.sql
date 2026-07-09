CREATE TABLE IF NOT EXISTS agent_trace (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  trace_id VARCHAR(64) NOT NULL,
  user_query TEXT NOT NULL,
  plan_json JSON NOT NULL,
  final_result JSON NOT NULL,
  status VARCHAR(32) NOT NULL,
  loop_depth INT UNSIGNED NOT NULL DEFAULT 1,
  created_at DATETIME(3) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_agent_trace_trace_id (trace_id),
  KEY idx_agent_trace_created_at (created_at),
  KEY idx_agent_trace_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS agent_event (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  event_type VARCHAR(64) NOT NULL,
  trace_id VARCHAR(64) NOT NULL,
  step_id INT UNSIGNED NULL,
  component VARCHAR(64) NOT NULL,
  input_json JSON NULL,
  output_json JSON NULL,
  latency_ms INT UNSIGNED NULL,
  timestamp DATETIME(3) NOT NULL,
  created_at DATETIME(3) NOT NULL,
  PRIMARY KEY (id),
  KEY idx_agent_event_trace_id (trace_id),
  KEY idx_agent_event_type_time (event_type, timestamp),
  KEY idx_agent_event_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS agent_failure (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  trace_id VARCHAR(64) NOT NULL,
  failure_type VARCHAR(64) NULL,
  source_layer VARCHAR(64) NULL,
  error_code VARCHAR(128) NULL,
  summary TEXT NOT NULL,
  detail_json JSON NULL,
  created_at DATETIME(3) NOT NULL,
  PRIMARY KEY (id),
  KEY idx_agent_failure_trace_id (trace_id),
  KEY idx_agent_failure_type_time (failure_type, created_at),
  KEY idx_agent_failure_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS agent_metrics_snapshot (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  total_requests INT UNSIGNED NOT NULL DEFAULT 0,
  success_rate DECIMAL(10,4) NOT NULL DEFAULT 0,
  tool_hit_rate DECIMAL(10,4) NOT NULL,
  sql_success_rate DECIMAL(10,4) NOT NULL,
  replan_rate DECIMAL(10,4) NOT NULL,
  avg_loop_depth DECIMAL(10,4) NOT NULL,
  execution_error_rate DECIMAL(10,4) NOT NULL DEFAULT 0,
  window_start DATETIME(3) NOT NULL,
  window_end DATETIME(3) NOT NULL,
  created_at DATETIME(3) NOT NULL,
  PRIMARY KEY (id),
  KEY idx_agent_metrics_snapshot_window (window_start, window_end),
  KEY idx_agent_metrics_snapshot_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
