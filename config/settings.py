import os
from dotenv import load_dotenv

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
load_dotenv(os.path.join(ROOT_DIR, '.env'))

# Flask Configuration
DEBUG = os.getenv("DEBUG", "True") == "True"
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
FLASK_ENV = os.getenv("FLASK_ENV", "development")

# Database
DEFAULT_DATABASE_PATH = os.path.join(ROOT_DIR, 'backend', 'data', 'stocks.db')
DATABASE_PATH = os.path.abspath(os.getenv("DATABASE_PATH", DEFAULT_DATABASE_PATH))
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

# Scraper Configuration
NSE_URL = "https://www.nseindia.com/api/equity-stockIndices"
SCRAPER_TIMEOUT = int(os.getenv("SCRAPER_TIMEOUT", "30"))
SCRAPER_RETRY_COUNT = int(os.getenv("SCRAPER_RETRY_COUNT", "3"))
USE_YFINANCE_FALLBACK = os.getenv("USE_YFINANCE_FALLBACK", "True") == "True"

# ML Configuration
MOMENTUM_WINDOW = int(os.getenv("MOMENTUM_WINDOW", "20"))
SENTIMENT_WEIGHT = float(os.getenv("SENTIMENT_WEIGHT", "0.3"))
MOMENTUM_WEIGHT = float(os.getenv("MOMENTUM_WEIGHT", "0.4"))
VOLUME_WEIGHT = float(os.getenv("VOLUME_WEIGHT", "0.3"))

# API Configuration
API_PORT = int(os.getenv("API_PORT", "5000"))
API_HOST = os.getenv("API_HOST", "0.0.0.0")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_PATH = os.path.abspath(os.path.join(ROOT_DIR, os.getenv("LOG_PATH", "logs")))
os.makedirs(LOG_PATH, exist_ok=True)

# Optional OpenAI reasoning
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4")
OPENAI_REASONING_EFFORT = os.getenv("OPENAI_REASONING_EFFORT", "medium")
OPENAI_ENHANCE_REASONING = os.getenv("OPENAI_ENHANCE_REASONING", "False") == "True"
