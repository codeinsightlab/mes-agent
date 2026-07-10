from typing import Any


class TraceRuntime:
    def __init__(self):
        self._events: dict[str, list[dict[str, Any]]] = {}

    def start(self, request_id: str, user_input: str) -> None:
        self._events[request_id] = [{"stage": "request", "data": {"user_input": user_input}}]

    def record(self, request_id: str, stage: str, data: dict[str, Any]) -> None:
        self._events.setdefault(request_id, []).append({"stage": stage, "data": data})

    def finish(self, request_id: str, status: str) -> list[dict[str, Any]]:
        self.record(request_id, "result", {"status": status})
        return self._events.pop(request_id, [])
