from __future__ import annotations

import os
import time
from typing import List, Optional

import requests
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "")
ALPHAVANTAGE_URL = "https://www.alphavantage.co/query"
SECONDS_BETWEEN_CALLS = float(os.getenv("AV_SECONDS_BETWEEN_CALLS", "12.0"))


class SentimentItem(BaseModel):
    ticker: str
    article_count: int
    avg_sentiment: Optional[float] = None
    label: Optional[str] = None
    good: Optional[bool] = None


class SentimentResponse(BaseModel):
    tickers: List[str]
    used_threshold: float = Field(0.07, description="Score threshold for 'good'")
    results: List[SentimentItem]


router = APIRouter(prefix="/sentiment", tags=["sentiment"])


def _label_from_score(score: Optional[float]) -> Optional[str]:
    if score is None:
        return None
    if score > 0:
        return "Positive"
    if score < 0:
        return "Negative"
    return "Neutral"


@router.get(
    "/",
    response_model=SentimentResponse,
    summary="Check Alpha Vantage news sentiment for one or more tickers",
)
def get_sentiment(
    tickers: List[str] = Query(..., description="e.g., tickers=AAPL&tickers=MSFT"),
    good_threshold: float = Query(0.07, description="Avg sentiment threshold to mark ticker as 'good'"),
    limit: int = Query(50, ge=1, le=1000, description="Max news items per ticker to aggregate"),
    topics: Optional[List[str]] = Query(None, description="Optional Alpha Vantage topics filter"),
    time_from: Optional[str] = Query(None, description="YYYYMMDDTHHMM lower bound"),
    time_to: Optional[str] = Query(None, description="YYYYMMDDTHHMM upper bound"),
    sort: Optional[str] = Query("LATEST", description="LATEST | EARLIEST | RELEVANCE"),
    min_relevance: Optional[float] = Query(None, ge=0, le=1, description="Filter ticker_sentiment by relevance_score"),
) -> SentimentResponse:
    if not ALPHAVANTAGE_API_KEY:
        raise HTTPException(status_code=500, detail="ALPHAVANTAGE_API_KEY not configured")

    uniq = []
    seen = set()
    for t in tickers:
        u = t.strip().upper()
        if u and u not in seen:
            uniq.append(u)
            seen.add(u)

    results: List[SentimentItem] = []

    for i, ticker in enumerate(uniq):
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": ticker,
            "apikey": ALPHAVANTAGE_API_KEY,
            "limit": str(limit),
            "sort": sort or "LATEST",
        }
        if topics:
            params["topics"] = ",".join(topics)
        if time_from:
            params["time_from"] = time_from
        if time_to:
            params["time_to"] = time_to

        try:
            resp = requests.get(ALPHAVANTAGE_URL, params=params, timeout=30)
            data = resp.json()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Failed to query Alpha Vantage for {ticker}") from exc

        if "Information" in data or "Note" in data:
            results.append(SentimentItem(ticker=ticker, article_count=0, avg_sentiment=None, label=None, good=None))
        else:
            feed = data.get("feed", []) or []
            scores = []
            for art in feed:
                for ts in art.get("ticker_sentiment", []) or []:
                    if ts.get("ticker") == ticker:
                        if min_relevance is not None:
                            try:
                                rel = float(ts.get("relevance_score", 0))
                            except Exception:
                                rel = 0.0
                            if rel < min_relevance:
                                continue
                        try:
                            scores.append(float(ts.get("ticker_sentiment_score")))
                        except Exception:
                            continue

            avg = sum(scores) / len(scores) if scores else None
            results.append(
                SentimentItem(
                    ticker=ticker,
                    article_count=len(feed),
                    avg_sentiment=avg,
                    label=_label_from_score(avg),
                    good=(avg is not None and avg >= good_threshold),
                )
            )

        if i < len(uniq) - 1:
            time.sleep(SECONDS_BETWEEN_CALLS)

    return SentimentResponse(tickers=uniq, used_threshold=good_threshold, results=results)
