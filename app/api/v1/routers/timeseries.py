from fastapi import APIRouter, HTTPException, Query
from typing import List

from app.schemas.timeseries import TimeSeriesPoint, TimeSeriesResponse
from app.services.timeseries_service import fetch_time_series


router = APIRouter(prefix="/timeseries", tags=["timeseries"])


@router.get("/{symbol}", response_model=TimeSeriesResponse, summary="Get time series data for a stock symbol")
def get_time_series(
    symbol: str,
    interval: str = Query(
        default="1d",
        description="Time interval between data points. Currently only '1d' is supported.",
        pattern=r"^(1d)$",
    ),
    limit: int = Query(default=100, ge=1, le=5000, description="Maximum number of data points to return"),
) -> TimeSeriesResponse:
    """Return real market data for the given symbol using Alpha Vantage daily series."""
    try:
        # Run async service in a simple blocking way for FastAPI sync path operation
        import anyio

        points: List[TimeSeriesPoint] = anyio.run(fetch_time_series, symbol, interval, limit)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve)) from ve
    except Exception as exc:  # noqa: BLE001 - surface as 502
        raise HTTPException(status_code=502, detail="Failed to fetch time series data") from exc

    return TimeSeriesResponse(symbol=symbol.upper(), interval=interval, points=points)


