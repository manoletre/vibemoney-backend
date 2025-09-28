from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import httpx

from app.core.config import settings


class PolygonClientKey2:
    """Client for Polygon using the secondary API key (POLYGON_API_KEY_2)."""

    def __init__(self, api_key: str | None, base_url: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def fetch_previous_close(self, symbol: str) -> float | None:
        """Fetch previous close price for a symbol as a proxy for latest."""
        url = f"{self.base_url}/v2/aggs/ticker/{symbol}/prev"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=self._headers(), params={"adjusted": "true"})
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results") or []
            if not results:
                return None
            # Use close price (c)
            return float(results[0].get("c")) if results[0].get("c") is not None else None

    async def fetch_aggregates_day(self, symbol: str, from_date: datetime, to_date: datetime) -> list[dict]:
        """Fetch daily aggregates in a date range (inclusive)."""
        from_str = from_date.strftime("%Y-%m-%d")
        to_str = to_date.strftime("%Y-%m-%d")
        url = f"{self.base_url}/v2/aggs/ticker/{symbol}/range/1/day/{from_str}/{to_str}"
        params: dict[str, str] = {"adjusted": "true", "sort": "asc", "limit": "5000"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=self._headers(), params=params)
            resp.raise_for_status()
            data = resp.json()
            return data.get("results", []) or []


async def compute_profit(symbol: str, as_of: date | datetime) -> tuple[float | None, float | None, float | None, datetime]:
    """Compute price at a given date and latest price using Polygon with key 2.

    Returns (price_then, price_now, profit, normalized_as_of_dt)
    """
    if not settings.polygon_api_key_2:
        raise ValueError("POLYGON_API_KEY_2 is not configured in environment")

    symbol = symbol.upper()
    client = PolygonClientKey2(settings.polygon_api_key_2, settings.polygon_base_url)

    # Normalize as_of to a UTC datetime covering the full day
    if isinstance(as_of, date) and not isinstance(as_of, datetime):
        as_of_date = as_of
        as_of_start = datetime(as_of_date.year, as_of_date.month, as_of_date.day, tzinfo=timezone.utc)
        as_of_end = as_of_start + timedelta(days=1) - timedelta(microseconds=1)
        normalized_as_of_dt = as_of_start
    else:
        dt = as_of if isinstance(as_of, datetime) else datetime.fromisoformat(str(as_of))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        day_start = datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc)
        as_of_start = day_start
        as_of_end = day_start + timedelta(days=1) - timedelta(microseconds=1)
        normalized_as_of_dt = dt

    # Fetch the bar for the as_of day and take close price
    rows = await client.fetch_aggregates_day(symbol, as_of_start, as_of_end)
    price_then: float | None = None
    if rows:
        # For a single day range, Polygon may still return one or more bars; take the last close
        last_row = rows[-1]
        close_value = last_row.get("c")
        price_then = float(close_value) if close_value is not None else None

    # Fetch latest (previous close)
    price_now = await client.fetch_previous_close(symbol)

    profit: float | None
    if price_then is not None and price_now is not None:
        profit = price_now - price_then
    else:
        profit = None

    return price_then, price_now, profit, normalized_as_of_dt


