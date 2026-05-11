"""
Scheduler for periodic scraping and data updates
Run with: python scheduler.py
"""
import schedule
import time
from src.scraper.nse_scraper import scrape_and_update_stocks, train_model_only
from src.api.logger import setup_logger

logger = setup_logger(__name__, "scheduler.log")

# Configuration
REFRESH_INTERVAL_MINUTES = 3
RETRAIN_INTERVAL_MINUTES = 30  # Retrain model every 30 minutes, not on every refresh
CURRENT_EXCHANGE = "nse"  # Can be "nse", "bse", or "both"

def refresh_market_data():
    """Refresh market data without retraining model (fast)."""
    try:
        logger.info("Background: Refreshing market data for %s...", CURRENT_EXCHANGE)
        updated, model_meta, universe = scrape_and_update_stocks(
            retrain_model=False,  # Don't retrain on every refresh
            exchange=CURRENT_EXCHANGE
        )
        logger.info("Background: Refresh complete - %d stocks updated", len(updated))
    except Exception as e:
        logger.error("Refresh error: %s", e)

def retrain_model():
    """Retrain model periodically."""
    try:
        logger.info("Background: Retraining model...")
        model_meta = train_model_only()
        logger.info("Background: Model retrained - %s", model_meta.get("model_name"))
    except Exception as e:
        logger.error("Model retrain error: %s", e)

def schedule_jobs():
    """Schedule periodic jobs."""
    # Refresh market data every N minutes (fast, no retraining)
    schedule.every(REFRESH_INTERVAL_MINUTES).minutes.do(refresh_market_data)
    
    # Retrain model periodically (separate from refresh)
    schedule.every(RETRAIN_INTERVAL_MINUTES).minutes.do(retrain_model)
    
    logger.info("Scheduled jobs:")
    logger.info("  - Refresh %s data every %d minutes", CURRENT_EXCHANGE, REFRESH_INTERVAL_MINUTES)
    logger.info("  - Retrain model every %d minutes", RETRAIN_INTERVAL_MINUTES)

def run_scheduler():
    """Run the scheduler loop."""
    logger.info("Starting NSE/BSE Data Scheduler...")
    schedule_jobs()
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(30)  # Check every 30 seconds
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error("Scheduler error: %s", e)

if __name__ == "__main__":
    # Initial scrape with training (one-time)
    logger.info("Running initial data scrape with model training...")
    try:
        updated, model_meta, universe = scrape_and_update_stocks(
            retrain_model=True,  # Train on first run only
            exchange=CURRENT_EXCHANGE
        )
        logger.info("Initial scrape complete - %d stocks loaded, model: %s", 
                   len(updated), model_meta.get("model_name"))
    except Exception as e:
        logger.error("Initial scrape error: %s", e)
    
    # Start scheduler for subsequent background refreshes
    run_scheduler()
