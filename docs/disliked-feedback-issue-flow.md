# Disliked Feedback Issue Flow

## 2026-07-03 - Minimal Manual Issue Management

### Scope

This flow lets a developer or administrator manually review disliked feedback, inspect the related conversation and model-call scene, and create or update one primary `agent_issue`.

Current scope:

- disliked feedback list
- disliked feedback detail
- manual issue creation
- issue list and detail
- issue processing update

Out of scope:

- model-based feedback analysis
- automatic issue creation
- automatic prompt repair
- `agent_issue_verification`
- login, JWT, or authentication service integration
- complex admin backend

### Feedback And Issue Responsibilities

`agent_feedback` is the user feedback fact. It stores the visitor evaluation and must not be overwritten by internal processing state.

`agent_issue` is the internal handling record generated manually from a disliked feedback. It stores process status, priority, root cause, solution, processor, and processing time.

One disliked feedback can have at most one primary issue in this version.

### API

Current admin APIs are development/test management APIs. They are not protected by real administrator authentication in this version and should not be exposed directly to a public production network.

```text
GET  /api/admin/feedbacks/disliked
GET  /api/admin/feedbacks/{feedback_key}
POST /api/admin/issues
GET  /api/admin/issues
GET  /api/admin/issues/{issue_key}
PUT  /api/admin/issues/{issue_key}
```

Create issue request:

```json
{
  "feedback_key": "feedback-key",
  "priority": 2
}
```

Update issue request:

```json
{
  "process_status": 3,
  "priority": 2,
  "root_cause_type": 10,
  "root_cause": "manual analysis",
  "solution": "manual handling record",
  "processed_by": "developer"
}
```

### Enums

`process_status`:

- `1`: 待处理
- `2`: 分析中
- `3`: 已定位
- `4`: 已修复
- `5`: 忽略
- `6`: 关闭

`priority`:

- `1`: 低
- `2`: 中
- `3`: 高
- `4`: 紧急

`root_cause_type`:

- `1`: Prompt 问题
- `2`: 模型能力问题
- `3`: 上下文问题
- `4`: 工具选择问题
- `5`: 工具数据问题
- `6`: 业务规则问题
- `7`: 前端展示问题
- `8`: 系统异常
- `9`: 用户输入不明确
- `10`: 其他

### State Transitions

Allowed forward transitions:

- 待处理 -> 分析中
- 待处理 -> 忽略
- 分析中 -> 已定位
- 分析中 -> 忽略
- 已定位 -> 已修复
- 已定位 -> 忽略
- 已修复 -> 关闭
- 忽略 -> 关闭

Allowed rollback transitions:

- 已定位 -> 分析中
- 已修复 -> 已定位

Closed issues cannot be modified by the current API.

Field rules:

- 已定位 requires `root_cause_type` and `root_cause`.
- 已修复 requires `root_cause_type`, `root_cause`, and `solution`.
- 已修复、忽略、关闭 write `processed_at`.

### Scene Association

Disliked feedback detail joins:

```text
agent_feedback
-> agent_conversation
-> assistant agent_message
-> parent user agent_message
-> agent_model_call
-> optional agent_issue
```

List responses only return summaries. Detail responses can return full message text and model-call snapshots after a sensitive marker check. If a snapshot contains API key, Authorization, Bearer, or password markers, it is omitted from the response.

### Future Verification

`agent_issue_verification` remains unused in this version. A future version can create verification records from closed or fixed issues to test new Agent, Prompt, Tool, Provider, or Model versions without overwriting the original feedback or issue.
