"""
Initialize all modules and run migrations
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.api.database import init_db
from src.api.logger import setup_logger

logger = setup_logger(__name__, "init.log")

def initialize_app():
    """Initialize the application."""
    logger.info("Initializing NSE Stock Intelligence System...")
    
    try:
        # Initialize database
        init_db(verbose=True)
        logger.info("✓ Database initialized")
        
        # Create necessary directories
        os.makedirs('logs', exist_ok=True)
        os.makedirs('data', exist_ok=True)
        logger.info("✓ Directories created")
        
        logger.info("✓ Application initialization complete!")
        return True
    except Exception as e:
        logger.error(f"✗ Initialization failed: {e}")
        return False

if __name__ == "__main__":
    success = initialize_app()
    sys.exit(0 if success else 1)
