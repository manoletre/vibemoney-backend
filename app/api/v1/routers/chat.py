from __future__ import annotations

from fastapi import APIRouter, HTTPException
import httpx

from app.schemas.chat import ChatRequest, ChatResponse, ChatResult
from app.services.chat_service import get_client


router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse, summary="Run a browser-use task")
def run_chat(req: ChatRequest) -> ChatResponse:
    try:
        client = get_client()
        # Forward extra fields (req.model_extra contains fields not declared in model)
        extra = getattr(req, 'model_extra', {}) or {}
        result = client.run_task(
            task=req.task,
            llm=req.llm or "o3",
            structured_output_json=req.structured_output_json,
            save_browser_data=req.save_browser_data,
            metadata=req.metadata,
            **extra,
        )

        details = result.get("details", {})
        output_raw = details.get("output")
        parsed = None
        if isinstance(output_raw, str) and req.structured_output_json:
            try:
                parsed = None
                # The API returns output as a JSON string when structured_output_json is used
                parsed = __import__("json").loads(output_raw)
            except Exception:
                parsed = None

        data = ChatResult(
            task_id=result.get("task_id"),
            status=result.get("status"),
            output_raw=output_raw,
            output_parsed=parsed,
            model=req.llm or "o3",
        )
        return ChatResponse(success=True, data=data)
    except httpx.HTTPStatusError as e:
        status = e.response.status_code if e.response is not None else 502
        msg = e.response.text if e.response is not None else str(e)
        raise HTTPException(status_code=status, detail=msg)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


