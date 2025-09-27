from fastapi import APIRouter

from app.schemas.quarterly import QuarterlyResponse


router = APIRouter(prefix="/quarterly", tags=["quarterly"])


@router.get("/{symbol}", response_model=QuarterlyResponse, summary="Get quarterly fundamentals for a stock symbol")
def get_quarterly(symbol: str) -> QuarterlyResponse:
    """
    Dummy endpoint returning structure for quarterly fundamentals like revenue and net income
    with their announcement dates. Real data fetching will be implemented later.
    """
    return QuarterlyResponse(symbol=symbol.upper(), quarters=[])


