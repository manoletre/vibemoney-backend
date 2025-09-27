from datetime import date
from typing import List

from pydantic import BaseModel, Field


class QuarterlyMetrics(BaseModel):
    """Key quarterly metrics for a company."""

    fiscal_quarter: str = Field(description="Fiscal quarter identifier, e.g., 2025Q1")
    filing_date: date | None = Field(default=None, description="Date the report was filed")
    period_end_date: date | None = Field(default=None, description="Period end date")
    revenue: float | None = Field(default=None, description="Total revenue")
    salesRevenueNet: float | None = Field(default=None, description="Sales revenue net")
    NetIncomeLoss: float | None = Field(default=None, description="Net income or loss")


class QuarterlyResponse(BaseModel):
    """Response model for quarterly fundamentals."""

    symbol: str = Field(description="Ticker symbol")
    quarters: List[QuarterlyMetrics] = Field(default_factory=list, description="List of quarterly metrics")


