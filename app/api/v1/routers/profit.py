from datetime import date, datetime

from fastapi import APIRouter, HTTPException, Query

from app.schemas.profit import ProfitResponse
from app.services.profit_service import compute_profit


router = APIRouter(prefix="/profit", tags=["profit"])


@router.get("/{symbol}", response_model=ProfitResponse, summary="Get profit since given date for a ticker")
def get_profit(
    symbol: str,
    as_of: date | datetime = Query(
        ..., description="Reference date (YYYY-MM-DD) or datetime (ISO8601). Uses day close."
    ),
) -> ProfitResponse:
    try:
        import anyio

        price_then, price_now, profit, normalized_as_of_dt = anyio.run(compute_profit, symbol, as_of)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve)) from ve
    except Exception as exc:  # noqa: BLE001 - surface as 502
        raise HTTPException(status_code=502, detail="Failed to compute profit") from exc

    return ProfitResponse(
        symbol=symbol.upper(),
        as_of=normalized_as_of_dt,
        price_then=price_then,
        price_now=price_now,
        profit=profit,
    )


