# MES Agent 会话现场存储设计

## 2026-07-03 - 初始数据库结构

### 目标

为 MES Agent 后续会话现场保存、模型调用追踪、用户反馈、问题处理和版本回归验证创建基础 MySQL 表结构。

本轮只定义数据库和表，不接入后端 ORM，不修改前端，不实现会话业务接口。

### 表关系

```text
agent_conversation
-> agent_message
-> agent_model_call

agent_message
-> agent_feedback
-> agent_issue
-> agent_issue_verification
```

`agent_model_call` 同时关联会话、用户请求消息和可选助手响应消息，用于保存一次真实模型调用的版本和现场快照。

### 表职责

- `agent_conversation`：一次对话现场的容器，保存稳定会话标识、用户或访客标识、状态、消息数量和最后消息时间。
- `agent_message`：保存 system、user、assistant、tool 消息，使用数字角色枚举和会话内序号。
- `agent_model_call`：保存模型调用时的 provider、model、Agent/Prompt/Tool 版本、Prompt、请求、响应、Token、耗时和脱敏错误。
- `agent_feedback`：保存用户对单条助手消息的喜欢或不喜欢反馈，不承载内部处理状态。
- `agent_issue`：将差评反馈转化为内部问题，保存处理状态、优先级、根因和解决方案。
- `agent_issue_verification`：记录同一个问题在不同 Agent、Prompt、Tool、Provider、Model 版本下的回归验证历史。

### 状态枚举

`agent_conversation.status`：

- `1`：进行中
- `2`：已结束
- `3`：已归档

`agent_message.role`：

- `1`：system
- `2`：user
- `3`：assistant
- `4`：tool

`agent_message.content_type`：

- `1`：纯文本
- `2`：JSON
- `3`：Markdown

`agent_message.message_status`：

- `1`：正常
- `2`：生成失败
- `3`：已撤销

`agent_model_call.call_status`：

- `1`：调用中
- `2`：成功
- `3`：失败
- `4`：超时
- `5`：取消

`agent_feedback.feedback_type`：

- `1`：喜欢
- `2`：不喜欢

`agent_feedback.reason_type`：

- `1`：答非所问
- `2`：事实或数据错误
- `3`：理解错误
- `4`：遗漏关键信息
- `5`：表达不清
- `6`：响应过慢
- `7`：其他

`agent_issue.process_status`：

- `1`：待处理
- `2`：分析中
- `3`：已定位
- `4`：已修复
- `5`：忽略
- `6`：关闭

`agent_issue.priority`：

- `1`：低
- `2`：中
- `3`：高
- `4`：紧急

`agent_issue.root_cause_type`：

- `1`：Prompt 问题
- `2`：模型能力问题
- `3`：上下文问题
- `4`：工具选择问题
- `5`：工具数据问题
- `6`：业务规则问题
- `7`：前端展示问题
- `8`：系统异常
- `9`：用户输入不明确
- `10`：其他

`agent_issue_verification.verification_status`：

- `1`：待验证
- `2`：验证通过
- `3`：验证未通过
- `4`：无法验证
- `5`：执行异常

### 版本字段语义

- `agent_version`：Agent 编排和应用逻辑版本。
- `prompt_version`：Prompt 模板和提示词策略版本。
- `tool_version`：工具集合或工具协议版本，可为空。
- `provider` / `model`：实际调用或验证时使用的模型供应商和模型名。

版本字段纵向记录在 `agent_model_call` 和 `agent_issue_verification` 中，不使用 `version1_processed`、`version2_processed` 之类横向扩展字段。

### 为什么拆分反馈、问题处理和版本验证

用户反馈是用户对某条助手回答的事实记录，不能因为内部问题处理状态变化而被覆盖。

问题处理是团队内部对差评反馈的分析和修复流程，状态只表示处理进展，不表示某个版本是否已经验证通过。

版本验证是回归测试历史，同一个问题可以在多个 Agent、Prompt、Tool、Provider、Model 组合下重复验证，每次验证都需要独立保留输入、预期、实际输出和失败原因。

拆表后可以避免把用户评价、内部流程和版本验证结果混成一个字段，也能支持同一问题的多次回归验证。

### 历史现场快照策略

`agent_model_call` 保存模型调用时的 `system_prompt_snapshot`、`request_snapshot`、`response_snapshot`、Token 和耗时。快照字段使用 `longtext`，由上层代码负责序列化为 JSON 文本并做格式校验，避免绑定具体数据库 JSON 类型。

`agent_issue_verification` 保存回归验证时的 `input_snapshot`、`expected_output` 和 `actual_output`，确保后续可以复盘不同版本的行为差异。

### 敏感数据禁止保存项

禁止保存：

- 数据库密码
- API Key
- Authorization Header
- 可直接登录的连接字符串
- 未脱敏的第三方错误响应
- 与当前问题无关的用户隐私数据

`request_snapshot`、`response_snapshot` 和 `error_message` 必须由上层代码在写入前完成脱敏。

### 差评转回归测试

后续流程建议：

1. 用户对助手消息提交不喜欢反馈，写入 `agent_feedback`。
2. 后台或运营人员将差评转换为 `agent_issue`。
3. 分析根因并记录处理状态、根因类型和修复方案。
4. 将原始输入、期望输出和关键判断标准写入 `agent_issue_verification`。
5. 每次 Agent、Prompt、Tool 或模型版本变更后新增验证记录，不覆盖历史验证。

### 应用账号原则

本轮不创建正式应用账号。管理员账号只用于初始化数据库和表。

FastAPI 后续不得使用 `root`。接入 ORM 或数据库访问前必须创建最小权限应用账号，权限范围应限制在 `mes_agent`，默认只考虑 `SELECT`、`INSERT`、`UPDATE`。是否授予 `DELETE` 权限应由逻辑删除策略决定。应用账号禁止拥有 `CREATE`、`DROP`、`ALTER` 和其他数据库权限。
