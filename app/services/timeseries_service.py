from datetime import datetime, timedelta, timezone
from typing import List

import httpx

from app.core.config import settings
from app.schemas.timeseries import TimeSeriesPoint


class PolygonClient:
    """Lightweight client for Polygon REST API focusing on aggregates endpoint."""

    def __init__(self, api_key: str | None, base_url: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _headers(self) -> dict:
        # Polygon supports apiKey in query or Authorization header. We'll use header.
        headers: dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def fetch_aggregates(
        self,
        symbol: str,
        multiplier: int,
        timespan: str,
        from_date: datetime,
        to_date: datetime,
        limit: int | None = None,
    ) -> list[dict]:
        """Call Polygon aggregates endpoint and return raw result rows."""
        from_str = from_date.strftime("%Y-%m-%d")
        to_str = to_date.strftime("%Y-%m-%d")
        url = f"{self.base_url}/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{from_str}/{to_str}"
        params: dict[str, str | int] = {"adjusted": "true", "sort": "asc"}
        if limit is not None:
            params["limit"] = limit

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=self._headers(), params=params)
            resp.raise_for_status()
            data = resp.json()
            # Polygon pattern: { status, results, resultsCount, queryCount, ... }
            return data.get("results", []) or []


def _normalize_points(rows: list[dict]) -> List[TimeSeriesPoint]:
    points: List[TimeSeriesPoint] = []
    for row in rows:
        # Polygon aggregate fields: t (ms unix), o, h, l, c, v
        ts_ms = row.get("t")
        timestamp = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc) if ts_ms is not None else None
        if timestamp is None:
            continue
        points.append(
            TimeSeriesPoint(
                timestamp=timestamp,
                open=float(row.get("o")) if row.get("o") is not None else None,
                high=float(row.get("h")) if row.get("h") is not None else None,
                low=float(row.get("l")) if row.get("l") is not None else None,
                close=float(row.get("c")) if row.get("c") is not None else None,
                volume=float(row.get("v")) if row.get("v") is not None else None,
            )
        )
    return points


async def fetch_time_series(symbol: str, interval: str, limit: int) -> List[TimeSeriesPoint]:
    """Fetch time series for today and previous 365 days using Polygon aggregates.

    Currently supports daily bars (interval "1d"). Other intervals can be extended.
    """
    symbol = symbol.upper()

    # Determine timespan parameters from interval
    if interval != "1d":
        # For now, only support daily; can extend to intraday with /v2/aggs/...
        raise ValueError("Only interval '1d' is supported at this time")

    # Define window: last 365 days including today (UTC)
    today_utc = datetime.now(timezone.utc).date()
    to_dt = datetime(today_utc.year, today_utc.month, today_utc.day, tzinfo=timezone.utc)
    from_dt = to_dt - timedelta(days=365)

    if not settings.polygon_api_key:
        raise ValueError("POLYGON_API_KEY is not configured in environment")

    client = PolygonClient(settings.polygon_api_key, settings.polygon_base_url)
    rows = await client.fetch_aggregates(
        symbol=symbol,
        multiplier=1,
        timespan="day",
        from_date=from_dt,
        to_date=to_dt,
        limit=limit,
    )
    return _normalize_points(rows)


