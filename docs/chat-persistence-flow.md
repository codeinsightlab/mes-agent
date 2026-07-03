# 单次问答入库流程

## 2026-07-03 - 初始实现

### 当前范围

每次 `POST /api/chat` 都创建一个独立会话，并保存：

- `agent_conversation`：一条会话记录。
- `agent_message`：一条用户消息。
- `agent_model_call`：一条模型调用中记录。
- `agent_message`：模型成功时额外保存一条助手消息。

当前不实现多轮上下文、历史会话列表、会话详情、反馈、问题处理、回归验证接口、MES 数据查询、工具调用或 Agent 循环。

### 数据库访问方案

后端使用同步 SQLAlchemy 2.x 和 PyMySQL。

- `engine.py`：创建 MySQL Engine 和连接池。
- `session.py`：创建 Session Factory 和 session 生命周期上下文。
- `models/`：映射已有 MySQL 表，不自动建表。
- `repositories/`：只负责持久化，不调用模型、不处理 HTTP。

配置从 `backend/.env` 读取，路径由 `backend/app/core/config.py` 根据代码位置推导，不依赖启动命令所在目录。

应用启动时会执行只读数据库检查：

- `SELECT DATABASE()`
- `SELECT 1`

日志只记录 driver、host、port、database、user 和检查结果，不记录密码或完整连接 URL。

### Repository 职责

- `ConversationRepository`
  - 创建会话。
  - 更新 `message_count`、`last_message_at` 和必要状态。
- `MessageRepository`
  - 创建用户消息，固定 `sequence_no=1`。
  - 创建助手消息，固定 `sequence_no=2`。
- `ModelCallRepository`
  - 创建调用中记录。
  - 更新调用成功现场。
  - 更新调用失败或超时现场。

### 两段事务

模型调用期间不持有数据库长事务。

第一段事务：

1. 创建 `agent_conversation`，状态为进行中。
2. 创建用户 `agent_message`。
3. 创建 `agent_model_call`，状态为调用中。
4. 更新会话 `message_count=1` 和 `last_message_at`。
5. 提交并关闭 Session。

随后调用通用 `LlmClient`，记录真实耗时。

第二段成功事务：

1. 创建助手 `agent_message`。
2. 更新 `agent_model_call` 的 `response_message_id`、`response_snapshot`、Token、耗时、状态和结束原因。
3. 更新会话 `message_count=2`、`last_message_at` 和结束状态。
4. 提交并关闭 Session。

第二段失败事务：

1. 不创建助手消息。
2. 更新 `agent_model_call` 的耗时、失败或超时状态、稳定错误码和脱敏错误信息。
3. 更新会话结束状态，保留 `message_count=1`。
4. 提交并关闭 Session。

### 持久化日志

关键日志阶段：

- `stage=initializing`：第一段事务开始，包含 `conversation_key` 和 `call_key`。
- `stage=initialized`：第一段事务提交成功，包含 `conversation_key`、`user_message_key`、`call_key`。
- `Chat model call result=success|failed`：模型调用完成，包含 `call_key`、`duration_ms` 和错误码。
- `stage=success_saved`：第二段成功事务提交。
- `stage=failure_saved`：第二段失败事务提交。

日志不记录用户完整长文本、模型完整回答、request/response snapshot 全文、数据库密码、API Key 或 Authorization Header。

### 不入库排查顺序

1. `/api/chat` 响应是否包含 `conversation_key`、`response_message_key`、`call_key`。
2. 当前请求是否命中新代码进程，而不是旧 `uvicorn`。
3. `backend/.env` 是否包含 DB 配置，且启动日志显示加载该文件。
4. 启动数据库检查是否连接到 `mes_agent`。
5. 日志是否出现 `stage=initialized` 和 `stage=success_saved` 或 `stage=failure_saved`。
6. 如果只有模型 200 日志但没有持久化阶段日志，说明请求没有进入持久化版本的 `ChatApplicationService`。
7. 如果出现 `stage=initialized` 但没有第二段日志，检查模型调用异常和持久化失败错误。

### API 响应标识

`POST /api/chat` 保留原有响应字段，并新增：

- `conversation_key`
- `response_message_key`
- `call_key`

这些是对外稳定业务标识。API 不返回 `conversation_id`、`message_id` 或 `model_call_id`。

### 快照策略

`request_snapshot` 保存发送给通用 `LlmClient` 的消息、模型、temperature 和 max_tokens，不保存 API Key 或 Authorization Header。

`response_snapshot` 保存统一响应现场，包括 content、provider、model、finish_reason 和 usage，不保存第三方原始响应头或 HTTP 客户端内部对象。

错误信息写入前会做基本脱敏和长度限制；完整堆栈只允许进入服务端日志，并且不得泄漏密钥。

### 最小权限账号

FastAPI 不得使用长期 `root` 账号。应用账号应限制在 `mes_agent` 数据库，至少具备 `SELECT`、`INSERT`、`UPDATE`。是否授予 `DELETE` 取决于后续逻辑删除策略。应用账号禁止拥有 `CREATE`、`DROP`、`ALTER` 和其他数据库权限。
