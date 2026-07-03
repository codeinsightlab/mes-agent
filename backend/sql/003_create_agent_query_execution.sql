CREATE TABLE IF NOT EXISTS agent_query_execution (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    execution_key VARCHAR(64) NOT NULL UNIQUE,
    conversation_key VARCHAR(64) NULL,
    route VARCHAR(32) NOT NULL,
    user_query VARCHAR(2000) NOT NULL,
    schema_version VARCHAR(64) NULL,
    generated_sql TEXT NULL,
    validated_sql TEXT NULL,
    validation_status VARCHAR(32) NULL,
    execution_status VARCHAR(32) NULL,
    used_tables JSON NULL,
    row_count INT NULL,
    duration_ms INT NULL,
    error_code VARCHAR(128) NULL,
    model VARCHAR(128) NULL,
    prompt_version VARCHAR(64) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Agent Text-to-SQL query execution audit';
