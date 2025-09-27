from fastapi import APIRouter, Query

from app.schemas.latestevents import LatestEventsResponse


router = APIRouter(prefix="/latestevents", tags=["latestevents"])


@router.get("/", response_model=LatestEventsResponse, summary="Search latest events for a stock symbol")
def get_latest_events(
    symbol: str = Query(description="Ticker symbol to search events for"),
    limit: int = Query(default=10, ge=1, le=100, description="Maximum number of events"),
) -> LatestEventsResponse:
    """
    Dummy endpoint returning the structure for latest events from web/news. Real
    implementation will perform web/news API queries.
    """
    return LatestEventsResponse(symbol=symbol.upper(), events=[])


