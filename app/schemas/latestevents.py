from datetime import datetime
from typing import List

from pydantic import BaseModel, Field, HttpUrl


class EventItem(BaseModel):
    """Single event/news item related to a stock."""

    title: str = Field(description="Event headline")
    url: HttpUrl | None = Field(default=None, description="Link to the source")
    source: str | None = Field(default=None, description="Source or publisher")
    published_at: datetime | None = Field(default=None, description="Publish timestamp in UTC")
    summary: str | None = Field(default=None, description="Short summary of the event")


class LatestEventsResponse(BaseModel):
    """Response model for latest events/news."""

    symbol: str = Field(description="Ticker symbol")
    events: List[EventItem] = Field(default_factory=list, description="List of event items")


