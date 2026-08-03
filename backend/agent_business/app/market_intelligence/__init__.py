"""
Market intelligence for the Business agent.

Uses Agreste IPPAP price indices (real CSVs) for dynamic price trends,
optionally enriched with FranceAgriMer RAG + Mistral when enabled.
"""

from app.market_intelligence.provider import get_market_price

__all__ = ["get_market_price"]
