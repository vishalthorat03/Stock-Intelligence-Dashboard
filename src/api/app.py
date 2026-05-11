"""
NSE/BSE Agentic Stock Intelligence - Main API Application
"""
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import os
import sys
import threading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from config.settings import DEBUG, SECRET_KEY, API_PORT, API_HOST
from src.api.database import init_db, get_top_stocks, get_stock
from src.api.logger import setup_logger
from src.scraper.nse_scraper import scrape_and_update_stocks, get_refresh_status

# Initialize logger
logger = setup_logger(__name__, "app.log")

# Create Flask app
app = Flask(__name__, template_folder='../../frontend', static_folder='../../frontend')
app.config['SECRET_KEY'] = SECRET_KEY
app.config['DEBUG'] = DEBUG
CORS(app)

# Global state
_refresh_thread = None
_current_exchange = "nse"

# Initialize database
try:
    init_db()
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error("Database initialization failed: %s", e)

# Routes

@app.route('/')
def index():
    """Render dashboard."""
    return render_template('index.html')

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'service': 'NSE/BSE Stock Intelligence API'}), 200

@app.route('/api/stocks/top', methods=['GET'])
def get_top_stocks_api():
    """Get top stocks by score."""
    try:
        stocks = get_top_stocks(limit=5)
        return jsonify({
            'success': True,
            'data': stocks,
            'count': len(stocks)
        }), 200
    except Exception as e:
        logger.error("Error fetching top stocks: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stocks/<symbol>', methods=['GET'])
def get_stock_detail(symbol):
    """Get stock details by symbol."""
    try:
        stock = get_stock(symbol.upper())
        if not stock:
            return jsonify({'success': False, 'error': 'Stock not found'}), 404
        return jsonify({'success': True, 'data': stock}), 200
    except Exception as e:
        logger.error("Error fetching stock %s: %s", symbol, e)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stocks/refresh/status', methods=['GET'])
def refresh_status():
    """Get current refresh status (no polling needed)."""
    try:
        status = get_refresh_status()
        return jsonify({
            'success': True,
            'data': {
                'running': status['running'],
                'last_updated': status['last_updated'],
                'total_updated': status['total_updated'],
                'exchange': _current_exchange
            }
        }), 200
    except Exception as e:
        logger.error("Error fetching refresh status: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stocks/refresh', methods=['POST'])
def trigger_refresh():
    """Trigger background refresh (non-blocking)."""
    global _refresh_thread, _current_exchange
    
    try:
        status = get_refresh_status()
        if status['running']:
            return jsonify({
                'success': False, 
                'error': 'Refresh already running'
            }), 409
        
        # Get exchange from request
        data = request.get_json() or {}
        exchange = data.get('exchange', 'nse')
        _current_exchange = exchange
        
        # Start refresh in background thread (non-blocking)
        def background_refresh():
            try:
                logger.info("Background refresh started for %s", exchange)
                scrape_and_update_stocks(retrain_model=False, exchange=exchange)
                logger.info("Background refresh complete")
            except Exception as e:
                logger.error("Background refresh error: %s", e)
        
        _refresh_thread = threading.Thread(target=background_refresh, daemon=True)
        _refresh_thread.start()
        
        return jsonify({
            'success': True,
            'data': {
                'status': 'refresh_started',
                'exchange': exchange
            }
        }), 202  # Accepted, processing
    
    except Exception as e:
        logger.error("Error triggering refresh: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/config/exchange', methods=['GET', 'POST', 'PUT'])
def exchange_config():
    """Get or set current exchange."""
    global _current_exchange
    
    try:
        if request.method == 'GET':
            return jsonify({
                'success': True,
                'data': {'exchange': _current_exchange}
            }), 200
        
        elif request.method in ('POST', 'PUT'):
            data = request.get_json() or {}
            exchange = data.get('exchange', 'nse')
            
            # Validate exchange
            if exchange not in ('nse', 'bse', 'both'):
                return jsonify({
                    'success': False,
                    'error': 'Invalid exchange. Must be nse, bse, or both'
                }), 400
            
            _current_exchange = exchange
            logger.info("Exchange changed to: %s", exchange)
            
            return jsonify({
                'success': True,
                'data': {'exchange': exchange}
            }), 200
    
    except Exception as e:
        logger.error("Error in exchange config: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/styles.css')
def serve_css():
    """Serve CSS file."""
    return app.send_static_file('styles.css')

@app.route('/dashboard.js')
def serve_js():
    """Serve JavaScript file."""
    return app.send_static_file('dashboard.js')

@app.errorhandler(404)

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({'success': False, 'error': 'Internal server error'}), 500

if __name__ == '__main__':
    logger.info("Starting NSE/BSE Stock Intelligence API on %s:%s", API_HOST, API_PORT)
    app.run(host=API_HOST, port=API_PORT, debug=DEBUG)
