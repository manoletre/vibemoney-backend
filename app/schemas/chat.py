from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict


class ChatStructuredField(BaseModel):
    name: str = Field(..., description="Field name")
    type: str = Field(..., description="Pydantic-like type description")
    description: Optional[str] = None


class ChatRequest(BaseModel):
    task: str = Field(..., description="Human instruction for the browser agent")
    llm: str = Field(default="o3", description="LLM model to use. Defaults to 'o3'")
    structured_output_json: Optional[Any] = Field(
        default=None,
        description=(
            "When provided, the backend calls run-task with structured_output_json and returns parsed output."
        ),
    )
    save_browser_data: Optional[bool] = Field(default=None, description="Pass-through flag to save browser data")
    metadata: Optional[Any] = Field(default=None, description="Arbitrary metadata to pass through")

    # Allow additional arbitrary fields to be passed through to Browser Use REST
    model_config = ConfigDict(extra="allow")


class ChatResult(BaseModel):
    task_id: Optional[str] = None
    status: Optional[str] = None
    output_raw: Optional[str] = None
    output_parsed: Optional[Any] = None
    media_urls: Optional[list[str]] = None
    screenshots: Optional[list[str]] = None
    cost_cents_estimate: Optional[float] = None
    model: Optional[str] = None


class ChatResponse(BaseModel):
    success: bool
    data: Optional[ChatResult] = None
    error: Optional[str] = None


