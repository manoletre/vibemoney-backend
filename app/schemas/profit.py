from datetime import datetime
from pydantic import BaseModel, Field


class ProfitResponse(BaseModel):
    symbol: str = Field(..., description="Ticker symbol in uppercase")
    as_of: datetime = Field(..., description="Input reference timestamp (UTC at market close if date only)")
    price_then: float | None = Field(None, description="Price at the reference time")
    price_now: float | None = Field(None, description="Most recent available price")
    profit: float | None = Field(None, description="Difference: price_now - price_then")

    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "AAPL",
                "as_of": "2024-01-15T00:00:00Z",
                "price_then": 186.22,
                "price_now": 221.14,
                "profit": 34.92,
            }
        }


