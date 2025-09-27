from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class TimeSeriesPoint(BaseModel):
    """Single observation in a time series."""

    timestamp: datetime = Field(description="Timestamp of the observation in UTC")
    open: float | None = Field(default=None, description="Opening price")
    high: float | None = Field(default=None, description="Highest price")
    low: float | None = Field(default=None, description="Lowest price")
    close: float | None = Field(default=None, description="Closing price")
    volume: float | None = Field(default=None, description="Trading volume")


class TimeSeriesResponse(BaseModel):
    """Response model for a time series request."""

    symbol: str = Field(description="Ticker symbol")
    interval: str = Field(description="Requested interval")
    points: List[TimeSeriesPoint] = Field(default_factory=list, description="Ordered list of observations")


