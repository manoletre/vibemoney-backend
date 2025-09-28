from __future__ import annotations

import json
from typing import Any, Optional

import httpx
from browser_use_sdk import BrowserUse  # type: ignore

from app.core.config import settings


class BrowserUseClient:
    """Thin wrapper around Browser Use Cloud SDK and REST for structured outputs."""

    def __init__(self, api_key: Optional[str]) -> None:
        if not api_key:
            raise ValueError("BROWSER_USE_API_KEY not configured")
        self.api_key = api_key
        self.sdk = BrowserUse(api_key=api_key)
        self.base_url = "https://api.browser-use.com/api/v1"
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    def run_task(
        self,
        task: str,
        llm: str = "o3",
        structured_output_json: Optional[Any] = None,
        save_browser_data: Optional[bool] = None,
        metadata: Optional[Any] = None,
        **extra: Any,
    ) -> dict[str, Any]:
        """
        If structured_schema is provided, use REST run-task with structured_output_json to ensure JSON output.
        Otherwise, use the SDK for a synchronous complete().
        """
        if structured_output_json is not None:
            payload: dict[str, Any] = {"task": task, "llm": llm}
            # API expects structured_output_json to be a JSON object; if a pydantic/str is passed, keep it
            payload["structured_output_json"] = structured_output_json
            if save_browser_data is not None:
                payload["save_browser_data"] = save_browser_data
            if metadata is not None:
                payload["metadata"] = metadata
            # Include any additional fields provided by the caller
            if extra:
                payload.update(extra)
            with httpx.Client(timeout=httpx.Timeout(120.0)) as client:
                try:
                    resp = client.post(f"{self.base_url}/run-task", headers=self.headers, json=payload)
                    resp.raise_for_status()
                except httpx.HTTPStatusError as e:
                    # If API expects stringified schema, retry once with json.dumps
                    if (
                        e.response is not None
                        and e.response.status_code == 422
                        and isinstance(payload.get("structured_output_json"), (dict, list))
                    ):
                        payload_retry = payload.copy()
                        payload_retry["structured_output_json"] = json.dumps(payload_retry["structured_output_json"])  # type: ignore[index]
                        resp = client.post(
                            f"{self.base_url}/run-task", headers=self.headers, json=payload_retry
                        )
                        resp.raise_for_status()
                    else:
                        raise
                task_id = resp.json()["id"]

            # Poll for completion (lightweight loop using status + task)
            status = None
            while True:
                with httpx.Client(timeout=httpx.Timeout(120.0)) as client:
                    r = client.get(f"{self.base_url}/task/{task_id}/status", headers=self.headers)
                    r.raise_for_status()
                    status = r.json()
                if status in {"finished", "failed", "stopped"}:
                    break
            with httpx.Client(timeout=httpx.Timeout(120.0)) as client:
                details = client.get(f"{self.base_url}/task/{task_id}", headers=self.headers)
                details.raise_for_status()
                data = details.json()
            return {"task_id": task_id, "status": status, "details": data}
        else:
            t = self.sdk.tasks.create_task(task=task, llm=llm)
            result = t.complete()
            return {
                "task_id": getattr(t, "id", None),
                "status": "finished",
                "details": {"output": getattr(result, "output", None)},
            }


client_singleton: Optional[BrowserUseClient] = None


def get_client() -> BrowserUseClient:
    global client_singleton
    if client_singleton is None:
        client_singleton = BrowserUseClient(settings.browser_use_api_key)
    return client_singleton


