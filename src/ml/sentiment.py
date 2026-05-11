"""
Sentiment Analysis Module
Analyzes news and social media for stock sentiment
"""
from textblob import TextBlob
import requests
from src.api.logger import setup_logger

logger = setup_logger(__name__, "sentiment.log")

def analyze_text_sentiment(text):
    """
    Analyze sentiment of text using TextBlob.
    Returns score from -1 (very negative) to 1 (very positive)
    """
    try:
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        return polarity
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {e}")
        return 0.0

def analyze_stock_sentiment(symbol, headlines):
    """
    Calculate average sentiment for a stock based on news headlines.
    
    Args:
        symbol: Stock symbol
        headlines: List of news headlines
    
    Returns:
        Average sentiment score
    """
    if not headlines:
        return 0.0
    
    sentiments = [analyze_text_sentiment(headline) for headline in headlines]
    average_sentiment = sum(sentiments) / len(sentiments)
    
    logger.info(f"Stock {symbol} sentiment: {average_sentiment:.3f} from {len(headlines)} headlines")
    
    return average_sentiment

def get_news_headlines(symbol):
    """
    Fetch news headlines for a stock.
    This is a placeholder - implement with real news API.
    """
    # TODO: Integrate with NewsAPI, Alpha Vantage, or similar
    logger.warning(f"News fetching not implemented for {symbol}")
    return []

def classify_sentiment(score):
    """
    Classify sentiment score into categories.
    """
    if score > 0.5:
        return "Very Positive"
    elif score > 0.2:
        return "Positive"
    elif score > -0.2:
        return "Neutral"
    elif score > -0.5:
        return "Negative"
    else:
        return "Very Negative"

if __name__ == "__main__":
    # Test sentiment analysis
    test_headlines = [
        "XYZ Company reports record profits and announces expansion plans",
        "XYZ stock drops as competitors enter market",
        "XYZ announces partnership with leading global firm",
    ]
    
    for headline in test_headlines:
        sentiment = analyze_text_sentiment(headline)
        classification = classify_sentiment(sentiment)
        print(f"'{headline}' -> {sentiment:.3f} ({classification})")
    
    avg_sentiment = analyze_stock_sentiment("XYZ", test_headlines)
    print(f"\nAverage sentiment: {avg_sentiment:.3f}")
