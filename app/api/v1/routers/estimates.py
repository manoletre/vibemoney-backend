from __future__ import annotations

import os
import requests
from typing import Dict, List, Optional, Tuple, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "")
ALPHAVANTAGE_URL = "https://www.alphavantage.co/query"


# SCHEMAS

class RevisionSignal(BaseModel):
    revised: bool = Field(..., description="True if there is a revision history with >= 2 values")
    first: Optional[float] = Field(None, description="First observed estimate in the revision history")
    last: Optional[float] = Field(None, description="Last observed estimate in the revision history")
    delta: Optional[float] = Field(None, description="last - first when both are available")
    sign: Optional[str] = Field(
        None, description="good if last>first; bad if last<first; flat if equal; null if insufficient data"
    )


class EstimatePoint(BaseModel):
    fiscal_date_ending: Optional[str] = None
    period: str  # 'annual' or 'quarterly'
    quarter: Optional[str] = None  # if present in API (e.g., '2025-09'/'Q3 2025')
    eps_avg: Optional[float] = None
    eps_low: Optional[float] = None
    eps_high: Optional[float] = None
    eps_num_analysts: Optional[int] = None

    revenue_avg: Optional[float] = None
    revenue_low: Optional[float] = None
    revenue_high: Optional[float] = None
    revenue_num_analysts: Optional[int] = None

    eps_revision: RevisionSignal
    revenue_revision: RevisionSignal


class EstimatesResponse(BaseModel):
    symbol: str
    period: str  # 'annual' | 'quarterly' | 'both'
    points: List[EstimatePoint]


#ROUTER

router = APIRouter(prefix="/estimates", tags=["estimates"])


def _coerce_float(x: Any) -> Optional[float]:
    try:
        if x is None or x == "":
            return None
        return float(x)
    except Exception:
        return None


def _coerce_int(x: Any) -> Optional[int]:
    try:
        if x is None or x == "":
            return None
        return int(x)
    except Exception:
        return None


def _get_path(d: Dict[str, Any], path: Tuple[str, ...]) -> Any:
    cur = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def _pick_first(d: Dict[str, Any], candidates: List[Tuple[str, ...]], cast_float: bool = True) -> Optional[float]:
    for path in candidates:
        v = _get_path(d, path)
        if v is not None:
            return _coerce_float(v) if cast_float else v
    return None


def _extract_revision_values(rev_node: Any, kind: str) -> List[float]:
    """
    Try to extract a sequence of revision values for 'kind' ('eps' or 'revenue')
    across a few plausible Alpha Vantage layouts.
    """
    values: List[float] = []

    if isinstance(rev_node, list):
        # List of snapshots; each snapshot may have eps/revenue averages under different keys
        for snap in rev_node:
            if not isinstance(snap, dict):
                continue
            if kind == "eps":
                v = _pick_first(
                    snap,
                    [
                        ("eps", "avg"),
                        ("eps", "mean"),
                        ("epsAvg",),
                        ("eps_mean",),
                        ("eps_avg",),
                        ("estimate", "eps", "avg"),
                        ("estimate_avg_eps",),
                    ],
                )
            else:
                v = _pick_first(
                    snap,
                    [
                        ("revenue", "avg"),
                        ("revenue", "mean"),
                        ("revenueAvg",),
                        ("revenue_mean",),
                        ("revenue_avg",),
                        ("estimate", "revenue", "avg"),
                        ("estimate_avg_revenue",),
                    ],
                )
            if v is not None:
                values.append(v)

    elif isinstance(rev_node, dict):
        # Sometimes rev_node = {'eps': [...], 'revenue': [...]}
        sub = rev_node.get(kind)
        if isinstance(sub, list):
            for snap in sub:
                if not isinstance(snap, dict):
                    continue
                v = _pick_first(
                    snap,
                    [("avg",), ("mean",), (kind + "Avg",), ("value",)],
                )
                if v is not None:
                    values.append(v)

    # Filter out Nones
    return [v for v in values if v is not None]


def _revision_signal(values: List[float]) -> RevisionSignal:
    if len(values) >= 2:
        first, last = values[0], values[-1]
        delta = last - first
        if last > first:
            sign = "good"
        elif last < first:
            sign = "bad"
        else:
            sign = "flat"
        return RevisionSignal(revised=True, first=first, last=last, delta=delta, sign=sign)
    else:
        return RevisionSignal(revised=False, first=None, last=None, delta=None, sign=None)


def _parse_estimate_node(node: Dict[str, Any], period: str) -> EstimatePoint:
    """
    Alpha Vantage may evolve field names; we defensively probe multiple common shapes.
    """
    # top-level meta
    fiscal_date = _pick_first(
        node,
        [("fiscalDateEnding",), ("fiscal_date_ending",), ("fiscal_date",)],
        cast_float=False,
    )
    quarter = _pick_first(node, [("quarter",), ("fiscalQuarterEnding",)], cast_float=False)

    # estimates can be either nested under "estimate" or flattened
    eps_avg = _pick_first(
        node,
        [("estimate", "eps", "avg"), ("eps", "avg"), ("epsAvg",), ("eps_avg",), ("epsMean",)],
    )
    eps_low = _pick_first(node, [("estimate", "eps", "low"), ("eps", "low"), ("epsLow",), ("eps_low",)])
    eps_high = _pick_first(node, [("estimate", "eps", "high"), ("eps", "high"), ("epsHigh",), ("eps_high",)])
    eps_na = _pick_first(
        node,
        [
            ("estimate", "eps", "numAnalysts"),
            ("eps", "numAnalysts"),
            ("epsNumAnalysts",),
            ("numAnalystsEPS",),
        ],
    )
    eps_num_analysts = _coerce_int(eps_na)

    rev_avg = _pick_first(
        node,
        [
            ("estimate", "revenue", "avg"),
            ("revenue", "avg"),
            ("revenueAvg",),
            ("revenue_avg",),
            ("revenueMean",),
        ],
    )
    rev_low = _pick_first(node, [("estimate", "revenue", "low"), ("revenue", "low"), ("revenueLow",), ("revenue_low",)])
    rev_high = _pick_first(
        node, [("estimate", "revenue", "high"), ("revenue", "high"), ("revenueHigh",), ("revenue_high",)]
    )
    rev_na = _pick_first(
        node,
        [
            ("estimate", "revenue", "numAnalysts"),
            ("revenue", "numAnalysts"),
            ("revenueNumAnalysts",),
            ("numAnalystsRevenue",),
        ],
    )
    revenue_num_analysts = _coerce_int(rev_na)

    # revision history — try a few likely keys
    rev_node = node.get("revisions") or node.get("revisionHistory") or node.get("revision_history") or {}
    eps_rev_values = _extract_revision_values(rev_node, "eps")
    rev_rev_values = _extract_revision_values(rev_node, "revenue")

    return EstimatePoint(
        fiscal_date_ending=fiscal_date,
        period=period,
        quarter=quarter,
        eps_avg=eps_avg,
        eps_low=eps_low,
        eps_high=eps_high,
        eps_num_analysts=eps_num_analysts,
        revenue_avg=rev_avg,
        revenue_low=rev_low,
        revenue_high=rev_high,
        revenue_num_analysts=revenue_num_analysts,
        eps_revision=_revision_signal(eps_rev_values),
        revenue_revision=_revision_signal(rev_rev_values),
    )


def _pluck_lists(payload: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Return (annual_list, quarterly_list) with best-effort key discovery.
    """
    annual = (
        payload.get("annualEarningsEstimates")
        or payload.get("annual_estimates")
        or payload.get("annual")
        or []
    )
    quarterly = (
        payload.get("quarterlyEarningsEstimates")
        or payload.get("quarterly_estimates")
        or payload.get("quarterly")
        or []
    )
    # Some responses may embed under 'data' or 'estimates'
    if not annual or not quarterly:
        data = payload.get("data") or payload.get("estimates") or {}
        if isinstance(data, dict):
            annual = annual or data.get("annualEarningsEstimates") or data.get("annual") or []
            quarterly = quarterly or data.get("quarterlyEarningsEstimates") or data.get("quarterly") or []

    return (annual if isinstance(annual, list) else []), (quarterly if isinstance(quarterly, list) else [])


@router.get(
    "/{symbol}",
    response_model=EstimatesResponse,
    summary="Earnings estimates (EPS & revenue) + revision trend signal",
)
def get_estimates(
    symbol: str,
    period: str = Query(
        default="both",
        pattern=r"^(annual|quarterly|both)$",
        description="Which estimate periods to return",
    ),
    limit: int = Query(
        default=4,
        ge=1,
        le=20,
        description="How many most-recent entries to return for each period",
    ),
) -> EstimatesResponse:
    """
    Pulls Alpha Vantage EARNINGS_ESTIMATES for `symbol`, returns EPS & revenue estimates
    and whether revision histories trended up (**good**), down (**bad**), or **flat**.
    """
    if not ALPHAVANTAGE_API_KEY:
        raise HTTPException(status_code=500, detail="ALPHAVANTAGE_API_KEY not configured")

    params = {"function": "EARNINGS_ESTIMATES", "symbol": symbol.upper(), "apikey": ALPHAVANTAGE_API_KEY}

    try:
        resp = requests.get(ALPHAVANTAGE_URL, params=params, timeout=30)
        payload = resp.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Failed to query Alpha Vantage") from exc

    # Handle common throttling / error notes
    if isinstance(payload, dict) and (payload.get("Information") or payload.get("Note") or payload.get("Error Message")):
        # Surface the provider message if available
        msg = payload.get("Information") or payload.get("Note") or payload.get("Error Message")
        raise HTTPException(status_code=502, detail=f"Alpha Vantage error: {msg}")

    annual_list, quarterly_list = _pluck_lists(payload)

    points: List[EstimatePoint] = []
    if period in ("annual", "both"):
        for node in annual_list[:limit]:
            points.append(_parse_estimate_node(node, period="annual"))
    if period in ("quarterly", "both"):
        for node in quarterly_list[:limit]:
            points.append(_parse_estimate_node(node, period="quarterly"))

    return EstimatesResponse(symbol=symbol.upper(), period=period, points=points)
