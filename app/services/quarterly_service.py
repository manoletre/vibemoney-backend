"""
Quarterly fundamentals service stubs.

This module will later contain logic to fetch and normalize quarterly
fundamentals from providers (e.g., SEC EDGAR, FinancialModelingPrep, etc.).
"""

from typing import List

from app.schemas.quarterly import QuarterlyMetrics


def fetch_quarterly(symbol: str) -> List[QuarterlyMetrics]:
    """Placeholder implementation that returns an empty list."""
    return []


