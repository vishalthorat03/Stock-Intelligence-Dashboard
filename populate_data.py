"""
Populate sample stock data for testing
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.api.database import update_stock
from src.api.logger import setup_logger

logger = setup_logger(__name__, "populate_data.log")

def populate_sample_data():
    """Add sample stocks to database"""
    sample_stocks = [
        ('RELIANCE', 'Reliance Industries', 78.5, 0.65, 72, 68, 2.3, 2850.50),
        ('INFY', 'Infosys Limited', 72.0, 0.45, 68, 65, 1.8, 1750.25),
        ('TCS', 'Tata Consultancy Services', 75.5, 0.55, 70, 72, 2.1, 3200.75),
        ('HINDUNILVR', 'Hindustan Unilever', 68.0, 0.35, 65, 60, 1.2, 2100.40),
        ('ICICIBANK', 'ICICI Bank', 65.5, 0.25, 62, 58, 0.8, 950.80),
    ]
    
    logger.info(f"Populating {len(sample_stocks)} sample stocks...")
    
    for symbol, name, score, sentiment, momentum, volume, price_change, current_price in sample_stocks:
        update_stock(
            symbol=symbol,
            name=name,
            score=score,
            sentiment=sentiment,
            momentum=momentum,
            volume_signal=volume,
            price_change=price_change,
            current_price=current_price
        )
        logger.info(f"Added {symbol}: score={score:.1f}")
    
    logger.info("Sample data population complete!")

if __name__ == "__main__":
    populate_sample_data()
