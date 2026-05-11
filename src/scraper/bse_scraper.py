"""
BSE (Bombay Stock Exchange) market data fetcher.
"""
from __future__ import annotations

import os
from datetime import datetime

import pandas as pd
import requests

from config.settings import ROOT_DIR, SCRAPER_RETRY_COUNT, SCRAPER_TIMEOUT, USE_YFINANCE_FALLBACK
from src.api.logger import setup_logger
from src.scraper.nse_scraper import dedupe_symbols

logger = setup_logger(__name__, "bse_scraper.log")

# Popular BSE stocks
DEFAULT_BSE_SYMBOLS = ["RELIANCE", "INFY", "TCS", "HINDUNILVR", "ICICIBANK"]
BSE_INDEX_NAMES = [
    "BSE SENSEX",
    "BSE 100",
    "BSE 500",
]

os.environ.setdefault("YFINANCE_TZ_CACHE_LOCATION", os.path.join(ROOT_DIR, "backend", "data", "yfinance_cache"))
os.makedirs(os.environ["YFINANCE_TZ_CACHE_LOCATION"], exist_ok=True)


class BSEScraper:
    """Fetch stock data from BSE using Yahoo Finance (with .BO suffix)."""

    def __init__(self):
        self.timeout = SCRAPER_TIMEOUT
        self.retry_count = SCRAPER_RETRY_COUNT

    def fetch_stock_data(self, symbol, use_bse=True):
        """Fetch stock data from BSE or NSE ticker."""
        yahoo_quote = self._fetch_from_yfinance(symbol, use_bse=use_bse)
        if yahoo_quote:
            return yahoo_quote
        return None

    def _fetch_from_yfinance(self, symbol, use_bse=True):
        """Fetch from Yahoo Finance using appropriate suffix."""
        try:
            import yfinance as yf

            yf.set_tz_cache_location(os.environ["YFINANCE_TZ_CACHE_LOCATION"])
            
            # Try BSE ticker first if use_bse=True, else NSE
            suffix = ".BO" if use_bse else ".NS"
            ticker = yf.Ticker(f"{symbol}{suffix}")
            
            # Get fast info
            info = getattr(ticker, "fast_info", {}) or {}
            if not info or "lastPrice" not in info:
                # Fallback to historical data
                history = ticker.history(period="5d", interval="1d")
                if history.empty:
                    return None
                latest = history.iloc[-1]
                previous_close = history["Close"].iloc[-2] if len(history) > 1 else latest["Close"]
                change_pct = 0.0 if previous_close == 0 else ((latest["Close"] - previous_close) / previous_close) * 100.0
                ltp = float(latest["Close"] or 0.0)
                volume = float(latest.get("Volume") or 0.0)
            else:
                ltp = float(info.get("lastPrice") or 0.0)
                change_pct = float(info.get("regularMarketChangePercent") or 0.0)
                volume = float(info.get("lastVolume") or 0.0)

            return {
                "symbol": symbol,
                "name": info.get("shortName") or symbol,
                "ltp": ltp,
                "change": change_pct,
                "volume": volume,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "source": "bse" if use_bse else "nse",
                "exchange": "BSE" if use_bse else "NSE",
            }
        except BaseException as exc:
            logger.warning("Yahoo Finance quote failed for %s (%s): %s", symbol, "BSE" if use_bse else "NSE", exc)
            return None

    def fetch_historical_data(self, symbol, days=120, use_bse=True):
        """Fetch historical data for the symbol."""
        if not USE_YFINANCE_FALLBACK:
            return pd.DataFrame()
        try:
            import yfinance as yf

            yf.set_tz_cache_location(os.environ["YFINANCE_TZ_CACHE_LOCATION"])
            suffix = ".BO" if use_bse else ".NS"
            ticker = yf.Ticker(f"{symbol}{suffix}")
            history = ticker.history(period=f"{days}d", interval="1d")
            if history.empty:
                return pd.DataFrame()
            return history.reset_index()
        except BaseException as exc:
            logger.warning("Historical data fetch failed for %s: %s", symbol, exc)
            return pd.DataFrame()

    def fetch_market_universe(self, explicit_symbols=None, use_bse=True):
        """Get list of stocks to process."""
        if explicit_symbols:
            return dedupe_symbols(explicit_symbols)
        
        # For BSE, use same stocks but with BSE suffix
        return dedupe_symbols(DEFAULT_BSE_SYMBOLS)

    @staticmethod
    def fetch_index_constituents(index_name, use_bse=True):
        """Fetch index constituents - BSE index data."""
        # For now, return empty as BSE API is limited
        # In production, you'd integrate with actual BSE API
        logger.info("BSE index fetch for %s (limited BSE API support)", index_name)
        return []
