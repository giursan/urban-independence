from typing import Any

_calls: dict[str, list[dict[str, Any]]] = {}


def history(call_sid: str) -> list[dict]:
    return _calls.setdefault(call_sid, [])


def reset(call_sid: str) -> None:
    _calls.pop(call_sid, None)
