# Python Type Safety Rules

## Scope

This rule applies to all AI/agent generated Python code in this project, including backend application code, tests, evaluation scripts, and future automation scripts.

## AI Generated Code Mandatory Rules

1. Do not generate variables without explicit types when the inferred type would be ambiguous.
2. Do not use bare `list` or `dict` as default business structures, except in short temporary scripts that are not committed.
3. Prefer `dataclass` for stable internal structures.
4. Use `TypedDict` for stable JSON-like records and API/report payloads when a Pydantic model is not needed.
5. API request and response bodies must use Pydantic models or `TypedDict`-backed schemas where the project boundary allows it.
6. Do not use `Any` as a default type.
7. If `Any` is unavoidable, add a reason comment next to it:
   `# TODO: unknown external schema from <source>`
8. Every list must declare its element type, for example `list[ToolEvent]`.
9. Core event/log structures must have an explicit schema and include:
   - `type`
   - `timestamp`
   - `payload`
10. `payload` may be a JSON object only at external boundaries and must use a constrained project type such as `JsonObject`.
11. New code must pass VSCode Pylance basic mode without `reportUnknownVariableType` warnings.
12. New code must be compatible with `python.analysis.typeCheckingMode = basic` and `reportUnknownVariableType = warning`.
13. New code must keep `reportMissingImports` clean.

## Project Rules

### Rule 1: No Bare Dict For Business Structures

Do not use `dict[str, Any]` for stable business records.

Use one of:

- `dataclass`
- `TypedDict`
- Pydantic `BaseModel`

### Rule 2: Lists Must Declare Element Types

Do not write:

```python
tool_usage = []
```

Write:

```python
tool_usage: list[ToolUsageEvent] = []
```

### Rule 3: Any Must Be Traceable

`Any` is only allowed for external, unknown schemas and must include a TODO comment explaining the source.

Example:

```python
# TODO: unknown external schema from third-party SDK callback
payload: Any
```

### Rule 4: Logs And Events Require Schemas

Core logs and agent events must be represented by explicit schemas.

Do not store core events as plain dictionaries. Use `dataclass`, `TypedDict`, or Pydantic models.

### Rule 5: Typing Imports

When compatibility with `typing` imports is needed, use explicit imports:

```python
from typing import Any, Dict, List, Optional, TypedDict
```

Prefer built-in generic syntax such as `list[str]` and `dict[str, str]` for new Python 3.10+ application code unless a compatibility boundary requires `Dict` or `List`.

## VSCode / Pylance Baseline

The project baseline is:

```json
{
  "python.analysis.typeCheckingMode": "basic",
  "python.analysis.diagnosticSeverityOverrides": {
    "reportUnknownVariableType": "warning",
    "reportMissingImports": "error"
  }
}
```

Upgrade to strict mode only after existing warnings are cleared and tests are stable.
