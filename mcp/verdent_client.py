import os
from typing import Any, Dict, Optional


class VerdentClient:
    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_sec: int = 30,
        retries: int = 1,
    ) -> None:
        self.endpoint = endpoint or os.environ.get("VERDENT_ENDPOINT")
        self.api_key = api_key or os.environ.get("VERDENT_API_KEY")
        self.timeout_sec = timeout_sec
        self.retries = retries

    def is_configured(self) -> bool:
        return bool(self.endpoint)

    def _request(self, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.endpoint:
            return {"error": "VERDENT_ENDPOINT not configured"}

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        body = {"action": action, "input": payload}
        last_error: Optional[str] = None

        try:
            import httpx
        except Exception as exc:
            return {"error": "httpx is not available", "details": str(exc)}

        for attempt in range(self.retries + 1):
            try:
                with httpx.Client(timeout=self.timeout_sec) as client:
                    response = client.post(self.endpoint, json=body, headers=headers)

                if response.status_code >= 400:
                    text = response.text
                    if len(text) > 2000:
                        text = text[:2000] + "...(truncated)"
                    return {
                        "error": f"Verdent request failed with status {response.status_code}",
                        "body": text,
                    }

                try:
                    data = response.json()
                except Exception:
                    text = response.text
                    if len(text) > 2000:
                        text = text[:2000] + "...(truncated)"
                    return {"error": "Verdent response was not valid JSON", "body": text}

                if isinstance(data, dict):
                    return data
                return {"result": data}
            except Exception as exc:
                last_error = str(exc)
                if attempt >= self.retries:
                    return {"error": "Verdent request failed", "details": last_error}

        return {"error": "Verdent request failed", "details": last_error or "Unknown error"}

    def search(self, query: str, limit: int = 20) -> Dict[str, Any]:
        return self._request("search", {"query": query, "limit": limit})

    def get_trace(self, trace_id: str) -> Dict[str, Any]:
        return self._request("get_trace", {"trace_id": trace_id})

    def get_recent(self, limit: int = 20) -> Dict[str, Any]:
        return self._request("get_recent", {"limit": limit})
