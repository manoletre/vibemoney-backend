from __future__ import annotations

from datetime import date, datetime, timezone

import httpx

from app.core.config import settings


class AlphaVantageClient:
    def __init__(self, api_key: str | None) -> None:
        self.api_key = api_key or ""
        self.base_url = "https://www.alphavantage.co/query"

    async def fetch_time_series_daily_adjusted(self, symbol: str, outputsize: str = "full") -> dict:
        params = {
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": symbol,
            "apikey": self.api_key,
            "outputsize": outputsize,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(self.base_url, params=params)
            data = resp.json()
            return data


async def compute_profit(symbol: str, as_of: date | datetime) -> tuple[float | None, float | None, float | None, datetime]:
    """Compute price at a given date and latest price using Alpha Vantage.

    Returns (price_then, price_now, profit, normalized_as_of_dt)
    """
    if not settings.alphavantage_api_key:
        raise ValueError("ALPHAVANTAGE_API_KEY is not configured in environment")

    symbol = symbol.upper()
    client = AlphaVantageClient(settings.alphavantage_api_key)

    # Normalize as_of to a UTC date string (YYYY-MM-DD)
    if isinstance(as_of, date) and not isinstance(as_of, datetime):
        as_of_date = as_of
        normalized_as_of_dt = datetime(as_of_date.year, as_of_date.month, as_of_date.day, tzinfo=timezone.utc)
    else:
        dt = as_of if isinstance(as_of, datetime) else datetime.fromisoformat(str(as_of))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        normalized_as_of_dt = dt

    as_of_key = normalized_as_of_dt.strftime("%Y-%m-%d")

    data = await client.fetch_time_series_daily_adjusted(symbol, outputsize="full")

    # Basic error handling for AV informational responses
    if "Error Message" in data or (not data.get("Meta Data") and "Time Series (Daily)" not in data):
        raise ValueError("Failed to fetch Alpha Vantage data")

    series = data.get("Time Series (Daily)") or {}

    def _to_float(val: object) -> float | None:
        try:
            return float(val) if val is not None else None
        except Exception:
            return None

    # Price at as_of date (exact date only; if market closed that day, result may be None)
    price_then: float | None = None
    if as_of_key in series:
        price_then = _to_float(series[as_of_key].get("4. close"))

    # Latest available close = max date key in series
    price_now: float | None = None
    if series:
        latest_key = max(series.keys())
        price_now = _to_float(series[latest_key].get("4. close"))

    profit: float | None
    if price_then is not None and price_now is not None:
        profit = price_now - price_then
    else:
        profit = None

    return price_then, price_now, profit, normalized_as_of_dt


