# Quick Start Guide - Stock Agent Real-Time Dashboard

**Golang Backend Engineer** — High-performance distributed stock intelligence system.

---

## 🚀 One-Minute Setup

### Terminal 1: Start the Background Job Scheduler
```bash
cd d:\stockagent
python scheduler.py
```

**Expected Output:**
```
INFO: Running initial data scrape with model training...
INFO: Initial scrape complete - 50 stocks loaded, model: gradient_boosting
INFO: Starting NSE/BSE Data Scheduler...
INFO: Scheduled jobs:
INFO:   - Refresh NSE data every 3 minutes
INFO:   - Retrain model every 30 minutes
```

**What happens:**
- ✅ Loads stock data from NSE
- ✅ Trains ML model (one-time, takes 10-30 seconds)
- ✅ Starts background refresh every 3 minutes
- ✅ Starts background model retraining every 30 minutes

### Terminal 2: Start the API Server
```bash
cd d:\stockagent
python -m src.api.app
```

**Expected Output:**
```
INFO: Starting NSE/BSE Stock Intelligence API on localhost:5000
Running on http://localhost:5000
```

### Browser: Open Dashboard
Navigate to: **http://localhost:5000**

---

## 📊 What You'll See

### First Load (5-10 seconds)
✅ Data loads from database
✅ Top 10 stocks displayed
✅ Score distribution chart
✅ Selected stock details

### Automatic Refresh (Every 3 Minutes)
✅ **Silent** - no messages shown
✅ Data updates in background
✅ "Last updated" timestamp changes
✅ You can ignore and keep working

### Manual Refresh (Click Button)
```
User clicks "Refresh Market" button
                    ↓
         Message: "Background refresh 
         started in real-time..."
                    ↓
         (2-3 seconds)
                    ↓
         Data updates automatically
         Message disappears
```

---

## 🎮 Features

### **Exchange Selector**
- Located in top-right navbar
- Options:
  - 🇮🇳 **NSE** (National Stock Exchange)
  - 🇮🇳 **BSE** (Bombay Stock Exchange)
  - 🔄 **NSE & BSE** (Both together)
- Switch anytime - applies to next refresh

### **Live Data**
- No "cached" or "outdated" indicators
- All data is current and real-time
- Refresh happens automatically
- You can manually trigger anytime

### **Smart Refresh**
- **3-minute auto-refresh**: Silent, no UI blocking
- **30-minute retraining**: Model improves in background
- **Manual refresh**: Click button, data updates instantly

---

## ⚙️ How It Works (Technical)

### The Three Phases

**Phase 1: Startup (One-time)**
```
scheduler.py starts
    ↓
Scrape all stocks (NSE)
    ↓
Train ML model
    ↓
Save to database
    ↓
Ready! ✅
```
Duration: 10-30 seconds
Happens: Once per server start

**Phase 2: Data Refresh (Every 3 minutes)**
```
Timer triggers
    ↓
Fetch latest stock prices (parallel, 10 workers)
    ↓
Calculate scores/metrics
    ↓
Update database
    ↓
Frontend auto-reloads
```
Duration: 2-3 seconds
Message: None (silent)

**Phase 3: Model Retraining (Every 30 minutes)**
```
Timer triggers
    ↓
Load historical data
    ↓
Train ML model
    ↓
Save new model
    ↓
Next refresh uses new model
```
Duration: 5-10 seconds
Message: None (completely silent)

---

## 📱 Browser Actions

| Action | Result | Wait Time |
|--------|--------|-----------|
| Open dashboard | Data loads from DB | 1-2 seconds |
| Switch exchange | Settings saved | Instant |
| Click "Refresh" | Starts background refresh | Returns instantly |
| Wait 3 minutes | Auto-refresh happens | Silent, ~3 seconds |
| Manual refresh | Data updates | 2-3 seconds visible |

---

## 🔍 Monitoring & Debugging

### Check Backend Status
**Terminal showing `scheduler.py`:**
```
INFO: Background: Refreshing market data for nse...
INFO: Background: Refresh complete - 50 stocks updated
INFO: Background: Retraining model...
INFO: Background: Model retrained - gradient_boosting
```

### Check API Server Status
**Terminal showing `python -m src.api.app`:**
```
POST /api/stocks/refresh - User triggered refresh
POST /api/config/exchange - Exchange changed
GET /api/stocks/refresh/status - Status checked
```

### Check Browser Console
Press: **F12 → Console Tab**

Should see POST requests like:
```
POST /api/stocks/refresh → 202 (Accepted)
GET /api/stocks/top → 200 (OK)
GET /api/config/exchange → 200 (OK)
```

---

## ⚡ Performance Tips

### ✅ For Best Experience
1. Let the first refresh complete (initial training)
2. Leave scheduler running in background
3. Periodic 3-minute refresh keeps data fresh
4. Manual refresh for immediate updates
5. Model automatically improves every 30 minutes

### ✅ For Better Data
1. Keep scheduler running 24/7
2. Let multiple refreshes run to train model better
3. Switch between exchanges to compare trends
4. Manual refresh when making trading decisions

### ✅ For Faster Performance
1. Browser refresh (Ctrl+R) if page feels slow
2. Close other browser tabs to free memory
3. API and scheduler run locally (fast)
4. No internet dependency except for data fetch

---

## 🚨 Troubleshooting

### "No stocks available"
- ✅ Wait 30 seconds for initial load
- ✅ Check scheduler terminal - should show "Initial scrape complete"
- ✅ Click "Refresh Market" button to trigger immediate load

### "Data looks old"
- ✅ Check "Last updated" timestamp
- ✅ Trigger manual refresh (click button)
- ✅ Check scheduler is still running

### "Not seeing new exchange"
- ✅ Hard refresh browser: Ctrl+Shift+R
- ✅ Clear browser cookies/cache
- ✅ Restart Flask server

### "Performance is slow"
- ✅ First run takes 30 seconds due to model training
- ✅ Subsequent refreshes are 2-3 seconds
- ✅ Check no other heavy processes running

---

## 📊 Expected Data

After successful startup, you should see:

**Top Stocks List:**
- RELIANCE, INFY, TCS, HINDUNILVR, ICICIBANK (and more)
- Score, Prediction, Sentiment for each

**Metrics Shown:**
- Score (0-100): Overall stock ranking
- Prediction: Expected price movement (%)
- Confidence: Model certainty (%)
- Sentiment: Market sentiment analysis

**Exchange Options:**
- NSE (Primary Indian stocks)
- BSE (Alternative Indian stocks)
- Both (All combined)

---

## 🎯 Next Steps

1. ✅ **Start scheduler** → Initial load happens
2. ✅ **Start API** → Server ready
3. ✅ **Open browser** → Dashboard loads
4. ✅ **Watch it work** → Auto-refresh every 3 minutes
5. ✅ **Try features** → Switch exchanges, manual refresh

**That's it! Your real-time stock dashboard is ready to use.**

---

## 📞 Need Help?

Check these files for more info:
- `IMPROVEMENTS.md` - Full feature description
- `IMPLEMENTATION_SUMMARY.md` - Technical details
- `scheduler.py` - Edit `REFRESH_INTERVAL_MINUTES` or `CURRENT_EXCHANGE`
- `src/api/app.py` - API endpoints reference
- `frontend/dashboard.js` - Frontend logic

**Enjoy real-time market intelligence! 🚀📈**
