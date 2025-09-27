"""
Latest events/news service stubs.

This module will later contain logic to aggregate recent events from the web
or news APIs for a given ticker.
"""

from typing import List

from app.schemas.latestevents import EventItem


def search_latest_events(symbol: str, limit: int) -> List[EventItem]:
    """Placeholder implementation that returns an empty list."""
    return []


