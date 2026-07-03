# Anonymous Feedback Flow

## 2026-07-03 - Minimal Anonymous Feedback Loop

### Goal

This flow lets an anonymous visitor submit one feedback record for a saved assistant answer. It supports like and dislike, and updates the same active feedback record when the same visitor changes their choice.

Current scope:

- `POST /api/feedback`
- `agent_feedback`
- anonymous `visitor_id`
- `IdentityContext`

Out of scope:

- login
- JWT
- authentication service calls
- `agent_issue`
- `agent_issue_verification`
- feedback list or admin workflow
- chat history
- multi-turn context

### Visitor Identity

The frontend stores a browser-local anonymous identifier under:

```text
mes_agent_visitor_id
```

Generation order:

1. Use `crypto.randomUUID()` when available.
2. Fall back to `crypto.getRandomValues()`.
3. Fall back to two random browser strings if crypto UUID APIs are unavailable.

The `visitor_id` is only used to group anonymous feedback records. It is not an authentication credential and must not be treated as trusted identity.

### Identity Boundary

The API layer constructs:

```text
IdentityContext(user_id=None, visitor_id=...)
```

`FeedbackApplicationService` only depends on `IdentityContext`; it does not read HTTP headers, localStorage, or future JWTs directly.

Future authentication can replace only the identity parsing layer:

```text
Authorization token
-> Auth adapter
-> IdentityContext(user_id=..., visitor_id=...)
-> FeedbackApplicationService
```

### API Protocol

Endpoint:

```text
POST /api/feedback
```

Request:

```json
{
  "response_message_key": "assistant-message-key",
  "visitor_id": "anonymous-visitor-id",
  "feedback_type": 1,
  "reason_type": null,
  "comment": null
}
```

Response:

```json
{
  "feedback_key": "stable-feedback-key",
  "response_message_key": "assistant-message-key",
  "feedback_type": 1,
  "feedback_type_label": "喜欢",
  "reason_type": null,
  "reason_type_label": null,
  "comment": null,
  "created_at": "2026-07-03T00:00:00",
  "updated_at": "2026-07-03T00:00:00"
}
```

The API does not accept `user_id` and does not return database auto-increment IDs.

### Feedback Enums

`feedback_type`:

- `1`: 喜欢
- `2`: 不喜欢

`reason_type`:

- `1`: 答非所问
- `2`: 事实或数据错误
- `3`: 理解错误
- `4`: 遗漏关键信息
- `5`: 表达不清
- `6`: 响应过慢
- `7`: 其他

### Business Rules

- Feedback can only target an existing assistant message.
- Target message must have normal message status.
- Same `visitor_id` plus same assistant message keeps one active `agent_feedback` row.
- First submit creates feedback.
- Later submit by the same visitor for the same message updates the original row.
- Changing dislike to like clears `reason_type` and `comment`.
- A different visitor can submit a separate feedback row for the same assistant message.
- The feedback service does not call the LLM client.

### Transaction

`FeedbackApplicationService.submit_feedback()` uses one short transaction:

1. Query target message.
2. Validate assistant role and normal status.
3. Query existing active feedback by message and visitor.
4. Create or update `agent_feedback`.
5. Commit.

On SQLAlchemy failure, the session rolls back and the API returns a stable persistence error without exposing SQL or internal stack traces.

### Logging

Feedback logs include:

- submit start
- `response_message_key`
- feedback type
- create or update action
- `feedback_key`
- hashed visitor digest
- persistence exception type

Feedback logs do not include:

- full `visitor_id`
- full comment
- database password
- SQL parameters
- user conversation content
- API key
- Authorization header
