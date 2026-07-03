CREATE DATABASE IF NOT EXISTS `mes_agent`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `mes_agent`;

CREATE TABLE IF NOT EXISTS `agent_conversation` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'Internal auto-increment primary key',
  `conversation_key` VARCHAR(64) NOT NULL COMMENT 'Stable external conversation identifier',
  `user_id` VARCHAR(64) NULL COMMENT 'Future logged-in user identifier',
  `visitor_id` VARCHAR(64) NULL COMMENT 'Anonymous visitor identifier',
  `title` VARCHAR(255) NULL COMMENT 'Conversation title',
  `status` TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT 'Conversation status: 1 active, 2 ended, 3 archived',
  `message_count` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT 'Number of messages in the conversation',
  `last_message_at` DATETIME(3) NULL COMMENT 'Time of the latest message',
  `created_at` DATETIME(3) NOT NULL COMMENT 'Creation time',
  `updated_at` DATETIME(3) NOT NULL COMMENT 'Last update time',
  `deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT 'Logical delete flag: 0 active, 1 deleted',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_agent_conversation_key` (`conversation_key`),
  KEY `idx_agent_conversation_user_created` (`user_id`, `created_at`),
  KEY `idx_agent_conversation_visitor_created` (`visitor_id`, `created_at`),
  KEY `idx_agent_conversation_status_updated` (`status`, `updated_at`),
  CONSTRAINT `chk_agent_conversation_status` CHECK (`status` IN (1, 2, 3)),
  CONSTRAINT `chk_agent_conversation_deleted` CHECK (`deleted` IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Conversation container for MES Agent chat context';

CREATE TABLE IF NOT EXISTS `agent_message` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'Internal auto-increment primary key',
  `message_key` VARCHAR(64) NOT NULL COMMENT 'Stable external message identifier',
  `conversation_id` BIGINT UNSIGNED NOT NULL COMMENT 'Conversation id',
  `parent_message_id` BIGINT UNSIGNED NULL COMMENT 'Parent message id for reply relationship',
  `role` TINYINT UNSIGNED NOT NULL COMMENT 'Message role: 1 system, 2 user, 3 assistant, 4 tool',
  `content` LONGTEXT NOT NULL COMMENT 'Message content',
  `content_type` TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT 'Content type: 1 text, 2 JSON, 3 Markdown',
  `sequence_no` INT UNSIGNED NOT NULL COMMENT 'Message sequence number inside the conversation',
  `message_status` TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT 'Message status: 1 normal, 2 generation failed, 3 revoked',
  `created_at` DATETIME(3) NOT NULL COMMENT 'Creation time',
  `updated_at` DATETIME(3) NOT NULL COMMENT 'Last update time',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_agent_message_key` (`message_key`),
  UNIQUE KEY `uk_agent_message_conversation_sequence` (`conversation_id`, `sequence_no`),
  KEY `idx_agent_message_conversation_created` (`conversation_id`, `created_at`),
  KEY `idx_agent_message_parent` (`parent_message_id`),
  CONSTRAINT `fk_agent_message_conversation` FOREIGN KEY (`conversation_id`) REFERENCES `agent_conversation` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `fk_agent_message_parent` FOREIGN KEY (`parent_message_id`) REFERENCES `agent_message` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `chk_agent_message_role` CHECK (`role` IN (1, 2, 3, 4)),
  CONSTRAINT `chk_agent_message_content_type` CHECK (`content_type` IN (1, 2, 3)),
  CONSTRAINT `chk_agent_message_status` CHECK (`message_status` IN (1, 2, 3))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Conversation message records for users, assistants, systems, and tools';

CREATE TABLE IF NOT EXISTS `agent_model_call` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'Internal auto-increment primary key',
  `call_key` VARCHAR(64) NOT NULL COMMENT 'Stable external model call identifier',
  `conversation_id` BIGINT UNSIGNED NOT NULL COMMENT 'Conversation id',
  `request_message_id` BIGINT UNSIGNED NOT NULL COMMENT 'User request message id',
  `response_message_id` BIGINT UNSIGNED NULL COMMENT 'Assistant response message id',
  `provider` VARCHAR(64) NOT NULL COMMENT 'Model provider name',
  `model` VARCHAR(128) NOT NULL COMMENT 'Model name',
  `agent_version` VARCHAR(64) NOT NULL COMMENT 'Agent version at call time',
  `prompt_version` VARCHAR(64) NOT NULL COMMENT 'Prompt version at call time',
  `tool_version` VARCHAR(64) NULL COMMENT 'Tool version at call time',
  `system_prompt_snapshot` LONGTEXT NULL COMMENT 'System prompt snapshot used for the call',
  `request_snapshot` LONGTEXT NOT NULL COMMENT 'Serialized provider request snapshot without secrets',
  `response_snapshot` LONGTEXT NULL COMMENT 'Serialized provider response snapshot without secrets',
  `prompt_tokens` INT UNSIGNED NULL COMMENT 'Prompt token count',
  `completion_tokens` INT UNSIGNED NULL COMMENT 'Completion token count',
  `total_tokens` INT UNSIGNED NULL COMMENT 'Total token count',
  `duration_ms` INT UNSIGNED NULL COMMENT 'Model call duration in milliseconds',
  `call_status` TINYINT UNSIGNED NOT NULL COMMENT 'Call status: 1 calling, 2 success, 3 failed, 4 timeout, 5 canceled',
  `finish_reason` VARCHAR(64) NULL COMMENT 'Provider finish reason',
  `error_code` VARCHAR(128) NULL COMMENT 'Sanitized error code',
  `error_message` TEXT NULL COMMENT 'Sanitized error message',
  `created_at` DATETIME(3) NOT NULL COMMENT 'Creation time',
  `updated_at` DATETIME(3) NOT NULL COMMENT 'Last update time',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_agent_model_call_key` (`call_key`),
  KEY `idx_agent_model_call_conversation_created` (`conversation_id`, `created_at`),
  KEY `idx_agent_model_call_request_message` (`request_message_id`),
  KEY `idx_agent_model_call_response_message` (`response_message_id`),
  KEY `idx_agent_model_call_status_created` (`call_status`, `created_at`),
  KEY `idx_agent_model_call_agent_prompt` (`agent_version`, `prompt_version`),
  KEY `idx_agent_model_call_provider_model_created` (`provider`, `model`, `created_at`),
  CONSTRAINT `fk_agent_model_call_conversation` FOREIGN KEY (`conversation_id`) REFERENCES `agent_conversation` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `fk_agent_model_call_request_message` FOREIGN KEY (`request_message_id`) REFERENCES `agent_message` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `fk_agent_model_call_response_message` FOREIGN KEY (`response_message_id`) REFERENCES `agent_message` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `chk_agent_model_call_status` CHECK (`call_status` IN (1, 2, 3, 4, 5))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Model call records with provider, version, prompt, request, response, token, and duration snapshots';

CREATE TABLE IF NOT EXISTS `agent_feedback` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'Internal auto-increment primary key',
  `feedback_key` VARCHAR(64) NOT NULL COMMENT 'Stable external feedback identifier',
  `conversation_id` BIGINT UNSIGNED NOT NULL COMMENT 'Conversation id',
  `message_id` BIGINT UNSIGNED NOT NULL COMMENT 'Assistant message id evaluated by the user',
  `user_id` VARCHAR(64) NULL COMMENT 'Future logged-in user identifier',
  `visitor_id` VARCHAR(64) NULL COMMENT 'Anonymous visitor identifier',
  `feedback_owner_key` VARCHAR(140) GENERATED ALWAYS AS (
    CASE
      WHEN `user_id` IS NOT NULL THEN CONCAT('user:', `user_id`)
      WHEN `visitor_id` IS NOT NULL THEN CONCAT('visitor:', `visitor_id`)
      ELSE 'anonymous'
    END
  ) STORED COMMENT 'Normalized feedback owner for active feedback uniqueness',
  `active_feedback_owner_key` VARCHAR(140) GENERATED ALWAYS AS (
    CASE WHEN `deleted` = 0 THEN `feedback_owner_key` ELSE NULL END
  ) STORED COMMENT 'Active feedback owner key; NULL for logically deleted feedback',
  `feedback_type` TINYINT UNSIGNED NOT NULL COMMENT 'Feedback type: 1 like, 2 dislike',
  `reason_type` TINYINT UNSIGNED NULL COMMENT 'Dislike reason: 1 irrelevant, 2 fact or data error, 3 misunderstanding, 4 missing key info, 5 unclear expression, 6 too slow, 7 other',
  `comment` TEXT NULL COMMENT 'User feedback comment',
  `created_at` DATETIME(3) NOT NULL COMMENT 'Creation time',
  `updated_at` DATETIME(3) NOT NULL COMMENT 'Last update time',
  `deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT 'Logical delete flag: 0 active, 1 deleted',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_agent_feedback_key` (`feedback_key`),
  UNIQUE KEY `uk_agent_feedback_active_message_owner` (`message_id`, `active_feedback_owner_key`),
  KEY `idx_agent_feedback_message_type` (`message_id`, `feedback_type`),
  KEY `idx_agent_feedback_conversation_created` (`conversation_id`, `created_at`),
  KEY `idx_agent_feedback_type_created` (`feedback_type`, `created_at`),
  KEY `idx_agent_feedback_reason_created` (`reason_type`, `created_at`),
  CONSTRAINT `fk_agent_feedback_conversation` FOREIGN KEY (`conversation_id`) REFERENCES `agent_conversation` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `fk_agent_feedback_message` FOREIGN KEY (`message_id`) REFERENCES `agent_message` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `chk_agent_feedback_type` CHECK (`feedback_type` IN (1, 2)),
  CONSTRAINT `chk_agent_feedback_reason_type` CHECK (`reason_type` IS NULL OR `reason_type` IN (1, 2, 3, 4, 5, 6, 7)),
  CONSTRAINT `chk_agent_feedback_deleted` CHECK (`deleted` IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='User feedback for a specific assistant message';

CREATE TABLE IF NOT EXISTS `agent_issue` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'Internal auto-increment primary key',
  `issue_key` VARCHAR(64) NOT NULL COMMENT 'Stable external issue identifier',
  `feedback_id` BIGINT UNSIGNED NOT NULL COMMENT 'Feedback id that generated this issue',
  `process_status` TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT 'Internal process status: 1 pending, 2 analyzing, 3 located, 4 fixed, 5 ignored, 6 closed',
  `priority` TINYINT UNSIGNED NOT NULL DEFAULT 2 COMMENT 'Priority: 1 low, 2 medium, 3 high, 4 urgent',
  `root_cause_type` TINYINT UNSIGNED NULL COMMENT 'Root cause type: 1 prompt, 2 model capability, 3 context, 4 tool selection, 5 tool data, 6 business rule, 7 frontend display, 8 system exception, 9 unclear input, 10 other',
  `root_cause` TEXT NULL COMMENT 'Root cause analysis',
  `solution` TEXT NULL COMMENT 'Solution or handling record',
  `processed_by` VARCHAR(64) NULL COMMENT 'Processor identifier',
  `processed_at` DATETIME(3) NULL COMMENT 'Processing time',
  `created_at` DATETIME(3) NOT NULL COMMENT 'Creation time',
  `updated_at` DATETIME(3) NOT NULL COMMENT 'Last update time',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_agent_issue_key` (`issue_key`),
  UNIQUE KEY `uk_agent_issue_feedback` (`feedback_id`),
  KEY `idx_agent_issue_status_priority_created` (`process_status`, `priority`, `created_at`),
  KEY `idx_agent_issue_root_cause_created` (`root_cause_type`, `created_at`),
  KEY `idx_agent_issue_processed_by_at` (`processed_by`, `processed_at`),
  CONSTRAINT `fk_agent_issue_feedback` FOREIGN KEY (`feedback_id`) REFERENCES `agent_feedback` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `chk_agent_issue_process_status` CHECK (`process_status` IN (1, 2, 3, 4, 5, 6)),
  CONSTRAINT `chk_agent_issue_priority` CHECK (`priority` IN (1, 2, 3, 4)),
  CONSTRAINT `chk_agent_issue_root_cause_type` CHECK (`root_cause_type` IS NULL OR `root_cause_type` IN (1, 2, 3, 4, 5, 6, 7, 8, 9, 10))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Internal issue tracking generated from negative user feedback';

CREATE TABLE IF NOT EXISTS `agent_issue_verification` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'Internal auto-increment primary key',
  `verification_key` VARCHAR(64) NOT NULL COMMENT 'Stable external verification identifier',
  `issue_id` BIGINT UNSIGNED NOT NULL COMMENT 'Issue id',
  `agent_version` VARCHAR(64) NOT NULL COMMENT 'Agent version under verification',
  `prompt_version` VARCHAR(64) NOT NULL COMMENT 'Prompt version under verification',
  `tool_version` VARCHAR(64) NULL COMMENT 'Tool version under verification',
  `provider` VARCHAR(64) NOT NULL COMMENT 'Model provider name under verification',
  `model` VARCHAR(128) NOT NULL COMMENT 'Model name under verification',
  `verification_status` TINYINT UNSIGNED NOT NULL COMMENT 'Verification status: 1 pending, 2 passed, 3 failed, 4 cannot verify, 5 execution error',
  `input_snapshot` LONGTEXT NOT NULL COMMENT 'Input snapshot for verification',
  `expected_output` LONGTEXT NULL COMMENT 'Expected output or acceptance criteria',
  `actual_output` LONGTEXT NULL COMMENT 'Actual output produced during verification',
  `failure_reason` TEXT NULL COMMENT 'Reason why verification failed or could not run',
  `verified_by` VARCHAR(64) NULL COMMENT 'Verifier identifier',
  `verified_at` DATETIME(3) NULL COMMENT 'Verification time',
  `created_at` DATETIME(3) NOT NULL COMMENT 'Creation time',
  `updated_at` DATETIME(3) NOT NULL COMMENT 'Last update time',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_agent_issue_verification_key` (`verification_key`),
  KEY `idx_agent_issue_verification_version` (`issue_id`, `agent_version`, `prompt_version`, `tool_version`, `provider`, `model`),
  KEY `idx_agent_issue_verification_issue_created` (`issue_id`, `created_at`),
  KEY `idx_agent_issue_verification_status_created` (`verification_status`, `created_at`),
  KEY `idx_agent_issue_verification_agent_prompt_status` (`agent_version`, `prompt_version`, `verification_status`),
  CONSTRAINT `fk_agent_issue_verification_issue` FOREIGN KEY (`issue_id`) REFERENCES `agent_issue` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `chk_agent_issue_verification_status` CHECK (`verification_status` IN (1, 2, 3, 4, 5))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Versioned regression verification records for issues';
