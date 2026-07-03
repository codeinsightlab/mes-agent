# 通用模型接入层

## 2026-07-03 - 最小闭环设计

### 目标

本轮实现普通非流式文本对话的最小闭环：

```text
frontend
-> POST /api/chat
-> ChatApplicationService
-> LlmClient
-> DeepSeekLlmClient
-> ChatResponse
```

当前只支持 DeepSeek 作为第一个 Provider，但 API 层和 Application 层只依赖通用模型接口与通用请求/响应模型。

### 分层边界

- `api/`：HTTP 请求校验、调用应用服务、稳定错误转换。
- `application/`：聊天用例编排，把单条用户输入转换为通用 `ChatRequest`。
- `domain/llm/`：厂商无关的 `LlmClient` 协议、通用模型和统一异常。
- `infrastructure/llm/`：DeepSeek HTTP 请求、响应解析、第三方错误到统一异常的转换。
- `core/config.py`：集中读取 CORS 和 LLM 环境变量。
- `schemas/`：FastAPI 请求/响应 DTO，不复用 domain 模型。

依赖方向保持：

```text
api -> application -> domain
infrastructure -> domain
api/application -> LlmClient protocol
```

### 通用模型

`domain/llm/models.py` 定义：

- `LlmMessage`
- `ChatRequest`
- `TokenUsage`
- `ChatResponse`

这些模型不包含 DeepSeek 专属字段，不依赖 FastAPI，也不依赖 HTTP 客户端。

### DeepSeek Provider

`DeepSeekLlmClient` 只负责：

- 将通用 `ChatRequest` 转换为 DeepSeek `/chat/completions` 请求。
- 设置 Bearer Token 鉴权。
- 使用带超时的 `httpx.Client`。
- 将 DeepSeek 响应转换为通用 `ChatResponse`。
- 将鉴权、超时、限流、不可用和响应格式异常转换为统一 LLM 异常。

Provider 不处理 MES 业务、不拼复杂 Prompt、不保存会话、不透传 DeepSeek 原始 JSON。

### 配置

后端从环境变量读取：

- `LLM_PROVIDER`
- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`
- `LLM_TIMEOUT_SECONDS`

`LLM_PROVIDER` 默认 `deepseek`，`LLM_BASE_URL` 默认 `https://api.deepseek.com`，`LLM_MODEL` 默认 `deepseek-chat`。`LLM_API_KEY` 必须由本地 `.env` 提供，不写入 README、日志或测试。

### 当前限制

- 只支持非流式普通文本对话。
- 不支持 Agent 编排。
- 不支持工具调用、Function Calling、SSE、WebSocket。
- 不接入 MES 数据库或 MES 接口。
- 不保存多轮会话。
- 不做多 Provider 自动路由、负载均衡或故障转移。
