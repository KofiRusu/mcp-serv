import os
from typing import Any, Dict, Optional



class CodexClient:
    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_sec: int = 30,
        retries: int = 1,
    ) -> None:
        self.endpoint = endpoint or os.environ.get("CODEX_ENDPOINT")
        self.api_key = api_key or os.environ.get("CODEX_API_KEY")
        self.timeout_sec = timeout_sec
        self.retries = retries

    def is_configured(self) -> bool:
        return bool(self.endpoint)

    def request(self, tool_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.endpoint:
            return {"error": "CODEX_ENDPOINT not configured"}

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        body = {"tool": tool_name, "input": payload}
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
                        "error": f"Codex request failed with status {response.status_code}",
                        "body": text,
                    }

                try:
                    data = response.json()
                except Exception:
                    text = response.text
                    if len(text) > 2000:
                        text = text[:2000] + "...(truncated)"
                    return {"error": "Codex response was not valid JSON", "body": text}

                if isinstance(data, dict):
                    return data
                return {"result": data}
            except Exception as exc:
                last_error = str(exc)
                if attempt >= self.retries:
                    return {"error": "Codex request failed", "details": last_error}

        return {"error": "Codex request failed", "details": last_error or "Unknown error"}
