from datetime import datetime, timezone
from typing import List

import httpx

from app.core.config import settings
from app.schemas.timeseries import TimeSeriesPoint


class AlphaVantageClient:
    """Minimal Alpha Vantage client for daily time series endpoints."""

    def __init__(self, api_key: str | None) -> None:
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"

    async def fetch_time_series_daily_adjusted(self, symbol: str, outputsize: str = "full") -> dict:
        params = {
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": symbol,
            "apikey": self.api_key or "",
            "outputsize": outputsize,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(self.base_url, params=params)
            data = resp.json()
            return data


def _normalize_points_from_av_daily(data: dict, limit: int) -> List[TimeSeriesPoint]:
    meta = data.get("Meta Data")
    series = data.get("Time Series (Daily)") or {}
    if not series and ("Error Message" in data or "Note" in data or meta is None):
        raise ValueError("Failed to fetch Alpha Vantage time series data")

    # Sort dates ascending and take last N according to limit
    date_keys = sorted(series.keys())
    if limit is not None and limit > 0:
        date_keys = date_keys[-limit:]

    points: List[TimeSeriesPoint] = []
    for ds in date_keys:
        fields = series.get(ds) or {}
        try:
            # Interpret the date as midnight UTC
            ts = datetime.fromisoformat(ds).replace(tzinfo=timezone.utc)
        except Exception:
            continue

        def _to_float(val: object) -> float | None:
            try:
                return float(val) if val is not None else None
            except Exception:
                return None

        points.append(
            TimeSeriesPoint(
                timestamp=ts,
                open=_to_float(fields.get("1. open")),
                high=_to_float(fields.get("2. high")),
                low=_to_float(fields.get("3. low")),
                close=_to_float(fields.get("4. close")),
                volume=_to_float(fields.get("6. volume")),
            )
        )
    return points


async def fetch_time_series(symbol: str, interval: str, limit: int) -> List[TimeSeriesPoint]:
    """Fetch time series using Alpha Vantage.

    Currently supports daily bars (interval "1d").
    """
    symbol = symbol.upper()

    if interval != "1d":
        raise ValueError("Only interval '1d' is supported at this time")

    if not settings.alphavantage_api_key:
        raise ValueError("ALPHAVANTAGE_API_KEY is not configured in environment")

    client = AlphaVantageClient(settings.alphavantage_api_key)
    data = await client.fetch_time_series_daily_adjusted(symbol, outputsize="full")
    return _normalize_points_from_av_daily(data, limit)


