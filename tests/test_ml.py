"""
Test suite for NSE Stock Intelligence System
Run with: pytest
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.ml.scoring import (
    calculate_momentum, calculate_volume_signal, 
    calculate_composite_score, normalize_score
)
from src.ml.sentiment import analyze_text_sentiment, classify_sentiment

class TestMLScoring:
    """Test ML scoring module"""
    
    def test_normalize_score(self):
        """Test score normalization"""
        assert normalize_score(0.05, -0.1, 0.1) == 75.0
        assert normalize_score(-0.1, -0.1, 0.1) == 0.0
        assert normalize_score(0.1, -0.1, 0.1) == 100.0
    
    def test_calculate_momentum(self):
        """Test momentum calculation"""
        prices = [100, 102, 104, 106, 108, 110]
        momentum = calculate_momentum(prices)
        assert 50 < momentum < 100  # Uptrend should be >50
    
    def test_calculate_volume_signal(self):
        """Test volume signal calculation"""
        volumes = [1000000] * 20
        changes = [0.01] * 20  # All positive
        signal = calculate_volume_signal(volumes, changes)
        assert 0 <= signal <= 100
    
    def test_composite_score(self):
        """Test composite score calculation"""
        score = calculate_composite_score(70, 60, 0.5)
        assert 0 <= score <= 100

class TestSentiment:
    """Test sentiment analysis module"""
    
    def test_positive_sentiment(self):
        """Test positive sentiment"""
        text = "Great news! Stock reaches all-time high."
        sentiment = analyze_text_sentiment(text)
        assert sentiment > 0
    
    def test_negative_sentiment(self):
        """Test negative sentiment"""
        text = "Stock crashes amid market downturn."
        sentiment = analyze_text_sentiment(text)
        assert sentiment < 0
    
    def test_sentiment_classification(self):
        """Test sentiment classification"""
        assert classify_sentiment(0.8) == "Very Positive"
        assert classify_sentiment(0.3) == "Positive"
        assert classify_sentiment(0.0) == "Neutral"
        assert classify_sentiment(-0.3) == "Negative"
        assert classify_sentiment(-0.8) == "Very Negative"

class TestDatabase:
    """Test database operations"""
    
    def test_db_initialization(self):
        """Test database initialization"""
        from src.api.database import init_db
        try:
            init_db()
            assert True
        except Exception as e:
            pytest.fail(f"Database initialization failed: {e}")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
