import logging
import sys
from config.settings import LOG_LEVEL, LOG_PATH

def setup_logger(name, log_file=None):
    """Configure logger for the application."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL))
    logger.propagate = False

    if logger.handlers:
        return logger
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler goes to stderr so stdout stays clean for JSON CLIs.
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        file_handler = logging.FileHandler(f"{LOG_PATH}/{log_file}")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger
