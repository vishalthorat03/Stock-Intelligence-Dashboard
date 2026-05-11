"""
Market data fetchers and refresh pipeline.
"""
from __future__ import annotations

import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests

from config.settings import ROOT_DIR, SCRAPER_RETRY_COUNT, SCRAPER_TIMEOUT, USE_YFINANCE_FALLBACK
from src.api.database import (
    add_model_run,
    get_all_snapshots,
    get_stock_history,
    init_db,
    seed_snapshot_history,
    update_stock,
)
from src.api.logger import setup_logger
from src.ml.openai_reasoning import enhance_reasoning_with_openai
from src.ml.scoring import (
    calculate_composite_score,
    calculate_momentum,
    calculate_price_change_series,
    calculate_volume_signal,
    derive_sentiment_proxy,
    explain_stock,
    predict_price_change,
    train_price_change_model,
)

logger = setup_logger(__name__, "scraper.log")

# Refresh state tracking
_refresh_state = {"running": False, "last_timestamp": None, "total_updated": 0}

DEFAULT_SYMBOLS = ["RELIANCE", "INFY", "TCS", "HINDUNILVR", "ICICIBANK"]
MARKET_INDEX_NAMES = [
    "NIFTY 50",
    "NIFTY NEXT 50",
    "NIFTY MIDCAP 100",
    "NIFTY SMALLCAP 100",
    "NIFTY 500",
    "NIFTY BANK",
]
os.environ.setdefault("YFINANCE_TZ_CACHE_LOCATION", os.path.join(ROOT_DIR, "backend", "data", "yfinance_cache"))
os.makedirs(os.environ["YFINANCE_TZ_CACHE_LOCATION"], exist_ok=True)


class NSEScraper:
    """Fetch stock data from NSE and Yahoo-backed sources."""

    def __init__(self):
        self.base_url = "https://www.nseindia.com/api"
        self.timeout = SCRAPER_TIMEOUT
        self.retry_count = SCRAPER_RETRY_COUNT
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json,text/plain,*/*",
            "Referer": "https://www.nseindia.com/",
        }

    def _session(self):
        session = requests.Session()
        session.headers.update(self.headers)
        return session

    def fetch_stock_data(self, symbol):
        quote_sources = []
        nse_quote = self._fetch_from_nse(symbol)
        if nse_quote:
            quote_sources.append("nse")

        yahoo_quote = None
        if USE_YFINANCE_FALLBACK:
            yahoo_quote = self._fetch_from_yfinance(symbol)
            if yahoo_quote:
                quote_sources.append("yfinance")

        quote = merge_quotes(symbol, nse_quote, yahoo_quote)
        if quote:
            quote["sources"] = quote_sources
        return quote

    def _fetch_from_nse(self, symbol):
        session = self._session()
        try:
            session.get("https://www.nseindia.com", timeout=self.timeout)
            url = f"{self.base_url}/quote-equity?symbol={symbol}"
            response = session.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            if not data or "priceInfo" not in data:
                return None

            price_info = data["priceInfo"]
            security_info = data.get("info", {})
            return {
                "symbol": symbol,
                "name": security_info.get("companyName") or security_info.get("companyName") or symbol,
                "ltp": float(price_info.get("lastPrice") or 0.0),
                "change": float(price_info.get("pChange") or 0.0),
                "volume": float(price_info.get("totalTradedVolume") or 0.0),
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "source": "nse",
            }
        except Exception as exc:
            logger.warning("NSE quote failed for %s: %s", symbol, exc)
            return None
        finally:
            session.close()

    def _fetch_from_yfinance(self, symbol):
        try:
            import yfinance as yf

            yf.set_tz_cache_location(os.environ["YFINANCE_TZ_CACHE_LOCATION"])
            ticker = yf.Ticker(f"{symbol}.NS")
            history = ticker.history(period="5d", interval="1d")
            if history.empty:
                return None

            latest = history.iloc[-1]
            previous_close = history["Close"].iloc[-2] if len(history) > 1 else latest["Close"]
            change_pct = 0.0 if previous_close == 0 else ((latest["Close"] - previous_close) / previous_close) * 100.0
            info = getattr(ticker, "fast_info", {}) or {}

            return {
                "symbol": symbol,
                "name": info.get("shortName") or symbol,
                "ltp": float(info.get("lastPrice") or latest["Close"] or 0.0),
                "change": float(change_pct),
                "volume": float(info.get("lastVolume") or latest.get("Volume") or 0.0),
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "source": "yfinance",
            }
        except BaseException as exc:
            logger.warning("yfinance quote failed for %s: %s", symbol, exc)
            return None

    def fetch_historical_data(self, symbol, days=120):
        if not USE_YFINANCE_FALLBACK:
            return pd.DataFrame()
        try:
            import yfinance as yf

            yf.set_tz_cache_location(os.environ["YFINANCE_TZ_CACHE_LOCATION"])
            ticker = yf.Ticker(f"{symbol}.NS")
            history = ticker.history(period=f"{days}d", interval="1d")
            if history.empty:
                return pd.DataFrame()
            return history.reset_index()
        except BaseException as exc:
            logger.warning("Historical data fetch failed for %s: %s", symbol, exc)
            return pd.DataFrame()

    def fetch_market_universe(self, explicit_symbols=None):
        if explicit_symbols:
            return dedupe_symbols(explicit_symbols)

        universe = []
        for index_name in MARKET_INDEX_NAMES:
            universe.extend(self.fetch_index_constituents(index_name))

        if universe:
            return dedupe_symbols(universe)
        return dedupe_symbols(DEFAULT_SYMBOLS)

    def fetch_index_constituents(self, index_name):
        session = self._session()
        try:
            session.get("https://www.nseindia.com", timeout=self.timeout)
            url = f"{self.base_url}/equity-stockIndices?index={requests.utils.quote(index_name)}"
            response = session.get(url, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
            symbols = []
            for row in payload.get("data", []):
                symbol = clean_symbol(row.get("symbol"))
                if symbol:
                    symbols.append(symbol)
            logger.info("Fetched %s constituents for %s", len(symbols), index_name)
            return symbols
        except Exception as exc:
            logger.warning("Index fetch failed for %s: %s", index_name, exc)
            return []
        finally:
            session.close()


def clean_symbol(symbol):
    symbol = (symbol or "").strip().upper()
    if not symbol or symbol in {"NIFTY", "BANKNIFTY"}:
        return ""
    return symbol


def dedupe_symbols(symbols):
    seen = set()
    ordered = []
    for symbol in symbols:
        cleaned = clean_symbol(symbol)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            ordered.append(cleaned)
    return ordered


def merge_quotes(symbol, primary, secondary):
    merged = {}
    for quote in [secondary, primary]:
        if quote:
            merged.update({key: value for key, value in quote.items() if value not in (None, "", [])})
    if not merged:
        return None
    merged.setdefault("symbol", symbol)
    merged.setdefault("name", symbol)
    merged.setdefault("timestamp", datetime.now().isoformat(timespec="seconds"))
    return merged


def compute_stock_metrics(symbol, live_quote, history_df, market_model, model_meta):
    closes = [float(value) for value in history_df.get("Close", pd.Series(dtype=float)).dropna().tolist()]
    volumes = [float(value) for value in history_df.get("Volume", pd.Series(dtype=float)).fillna(0).tolist()]
    if live_quote and live_quote.get("ltp"):
        closes = closes + [float(live_quote["ltp"])]
    if live_quote and live_quote.get("volume"):
        volumes = volumes + [float(live_quote["volume"])]

    price_changes = calculate_price_change_series(closes)
    momentum = calculate_momentum(closes)
    volume_signal = calculate_volume_signal(volumes, price_changes)
    sentiment = derive_sentiment_proxy(closes)
    price_change = float(live_quote.get("change") if live_quote else 0.0)
    score = calculate_composite_score(momentum, volume_signal, sentiment)

    history_rows = get_stock_history(symbol, limit=120)
    row = {
        "score": score,
        "momentum": momentum,
        "volume_signal": volume_signal,
        "sentiment": sentiment,
        "price_change": price_change,
        "current_price": float(live_quote.get("ltp") if live_quote else 0.0),
    }
    predicted_price_change, confidence = predict_price_change(market_model, model_meta, row, history_rows)
    reasoning = explain_stock(
        symbol=symbol,
        score=score,
        sentiment=sentiment,
        momentum=momentum,
        volume_signal=volume_signal,
        price_change=price_change,
        predicted_price_change=predicted_price_change,
        confidence=confidence,
        model_meta=model_meta,
    )
    reasoning["sources"] = live_quote.get("sources", [])

    enhanced_summary = enhance_reasoning_with_openai(
        {
            "symbol": symbol,
            "score": round(score, 2),
            "sentiment": round(sentiment, 4),
            "momentum": round(momentum, 2),
            "volume_signal": round(volume_signal, 2),
            "price_change": round(price_change, 2),
            "predicted_price_change": predicted_price_change,
            "confidence": confidence,
            "model_meta": model_meta,
            "local_reasoning": reasoning,
        }
    )
    if enhanced_summary:
        reasoning["llm_summary"] = enhanced_summary

    return {
        "symbol": symbol,
        "name": live_quote.get("name") or symbol,
        "score": round(score, 2),
        "sentiment": round(sentiment, 4),
        "momentum": round(momentum, 2),
        "volume_signal": round(volume_signal, 2),
        "price_change": round(price_change, 2),
        "current_price": round(float(live_quote.get("ltp") or 0.0), 2),
        "predicted_price_change": predicted_price_change,
        "confidence": confidence,
        "reasoning": reasoning,
        "sources": live_quote.get("sources", []),
    }


def scrape_and_update_stocks(symbols=None, retrain_model=True, exchange="nse"):
    """
    Fetch latest market data, optionally retrain the model on saved snapshots, and persist new market snapshots.
    Supports 'nse', 'bse', or 'both' exchanges. Uses parallel fetching for speed.
    """
    global _refresh_state
    
    # Prevent concurrent refreshes
    if _refresh_state["running"]:
        logger.warning("Refresh already running, skipping concurrent request")
        return [], {"model_name": "heuristic", "status": "running"}, []
    
    _refresh_state["running"] = True
    
    try:
        init_db()
        seed_snapshot_history()

        # Get market universe based on exchange
        market_universe = []
        if exchange in ("nse", "both"):
            scraper_nse = NSEScraper()
            market_universe.extend(scraper_nse.fetch_market_universe(symbols))
        
        if exchange in ("bse", "both"):
            from src.scraper.bse_scraper import BSEScraper
            scraper_bse = BSEScraper()
            bse_universe = scraper_bse.fetch_market_universe(symbols, use_bse=True)
            # Avoid duplicates
            market_universe = dedupe_symbols(market_universe + bse_universe)

        market_model = None
        model_meta = {"model_name": "heuristic", "status": "not_trained"}
        
        if retrain_model:
            existing_snapshots = get_all_snapshots(limit=12000)
            market_model, model_meta = train_price_change_model(existing_snapshots)
            add_model_run(model_meta)

        logger.info(
            "Starting live refresh for %s symbols on %s using %s",
            len(market_universe),
            exchange,
            model_meta.get("model_name", "heuristic"),
        )

        # Parallel fetching for speed
        updated = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_symbol = {}
            
            # Submit all tasks
            for symbol in market_universe:
                future = executor.submit(
                    _process_symbol,
                    symbol, 
                    exchange, 
                    market_model, 
                    model_meta
                )
                future_to_symbol[future] = symbol

            # Process completed tasks
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    metrics = future.result()
                    if metrics:
                        updated.append(metrics)
                except Exception as exc:
                    logger.error("Error processing %s: %s", symbol, exc)

        _refresh_state["last_timestamp"] = datetime.now().isoformat()
        _refresh_state["total_updated"] = len(updated)
        logger.info("Refresh complete, updated %s stocks", len(updated))
        
        return updated, model_meta, market_universe

    finally:
        _refresh_state["running"] = False


def _process_symbol(symbol, exchange, market_model, model_meta):
    """Process a single symbol with live data and compute metrics."""
    live_quote = None
    scraper_nse = NSEScraper()
    scraper_bse = None
    
    try:
        from src.scraper.bse_scraper import BSEScraper
        scraper_bse = BSEScraper()
    except:
        pass
    
    # Try exchange first
    if exchange == "nse":
        live_quote = scraper_nse.fetch_stock_data(symbol)
    elif exchange == "bse" and scraper_bse:
        live_quote = scraper_bse.fetch_stock_data(symbol, use_bse=True)
    elif exchange == "both":
        # Try BSE first, fallback to NSE
        if scraper_bse:
            live_quote = scraper_bse.fetch_stock_data(symbol, use_bse=True)
        if not live_quote:
            live_quote = scraper_nse.fetch_stock_data(symbol)
    
    if not live_quote:
        logger.warning("Live quote unavailable for %s", symbol)
        return None

    history_df = scraper_nse.fetch_historical_data(symbol, days=120)
    metrics = compute_stock_metrics(symbol, live_quote, history_df, market_model, model_meta)
    update_stock(
        symbol=metrics["symbol"],
        name=metrics["name"],
        score=metrics["score"],
        sentiment=metrics["sentiment"],
        momentum=metrics["momentum"],
        volume_signal=metrics["volume_signal"],
        price_change=metrics["price_change"],
        current_price=metrics["current_price"],
        predicted_price_change=metrics["predicted_price_change"],
        confidence=metrics["confidence"],
        reasoning=metrics["reasoning"],
        snapshot_time=live_quote.get("timestamp"),
    )
    return metrics


def get_refresh_status():
    """Get current refresh status."""
    global _refresh_state
    return {
        "running": _refresh_state["running"],
        "last_updated": _refresh_state["last_timestamp"],
        "total_updated": _refresh_state["total_updated"],
    }


def train_model_only():
    """
    Train the model without refreshing data.
    """
    init_db()
    seed_snapshot_history()

    existing_snapshots = get_all_snapshots(limit=12000)
    market_model, model_meta = train_price_change_model(existing_snapshots)
    add_model_run(model_meta)
    
    logger.info("Model trained: %s", model_meta.get("model_name", "heuristic"))
    return model_meta


if __name__ == "__main__":
    refreshed, model_meta, market_universe = scrape_and_update_stocks()
    print({"updated": len(refreshed), "model": model_meta, "universe": len(market_universe)})
