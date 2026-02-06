import time
from typing import Any, Callable, Dict, Optional


def _default_sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _default_sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_default_sanitize(v) for v in value]
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        return value.replace("\x00", "")
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)


def _default_count(value: Any) -> int:
    if isinstance(value, dict):
        total = 0
        for k, v in value.items():
            total += len(str(k))
            total += _default_count(v)
        return total
    if isinstance(value, list):
        return sum(_default_count(v) for v in value)
    if isinstance(value, str):
        return len(value)
    if isinstance(value, bytes):
        return len(value)
    return 0


class ExtensionContextStore:
    def __init__(
        self,
        sanitize_fn: Optional[Callable[[Any], Any]] = None,
        count_fn: Optional[Callable[[Any], int]] = None,
        max_chars: int = 50_000,
    ) -> None:
        self._sanitize = sanitize_fn or _default_sanitize
        self._count = count_fn or _default_count
        self._max_chars = max_chars
        self._payload: Optional[Dict[str, Any]] = None
        self._timestamp: Optional[float] = None

    def set_context(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        sanitized = self._sanitize(payload)
        total_chars = self._count(sanitized)
        if total_chars > self._max_chars:
            return {"error": f"Payload too large: {total_chars} chars (limit {self._max_chars})"}
        self._payload = sanitized
        self._timestamp = time.time()
        return {"ok": True, "timestamp": self._timestamp, "payload": sanitized}

    def get_context(self) -> Dict[str, Any]:
        if self._payload is None:
            return {"status": "none set"}
        return {"status": "ok", "timestamp": self._timestamp, "payload": self._payload}

    def clear(self) -> Dict[str, Any]:
        self._payload = None
        self._timestamp = None
        return {"ok": True}
