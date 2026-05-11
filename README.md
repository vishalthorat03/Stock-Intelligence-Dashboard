# NSE/BSE Stock Intelligence System

**AI-Powered Real-Time Stock Recommendation Engine**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Go](https://img.shields.io/badge/Go-1.19+-00ADD8.svg)](https://golang.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.0-lightgrey.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A collaborative stock intelligence project built around Git-driven workflows, modern backend engineering, and real-time market insights from NSE and BSE.

---

## 🚀 What this repository contains

- `backend/` — Go backend service with REST endpoints and high-performance patterns
- `src/` — Python API, scraper, ML, and scheduler code
- `frontend/` — Dashboard UI with HTML, CSS, and JavaScript
- `config/` — Shared settings and environment configuration
- `data/` — Storage and cache artifacts
- `tests/` — Automated tests for ML and core logic

---

## 🔧 Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Backend API | Python Flask | REST API service |
| Go Backend | Go | Optional high-performance service |
| ML Engine | scikit-learn | Stock scoring and prediction |
| Scrapers | BeautifulSoup, yfinance | NSE/BSE market data collection |
| Frontend | HTML/CSS/JS | Real-time dashboard |
| Database | SQLite | Local storage and snapshots |
| Scheduling | schedule | Background refresh and retraining |

---

## 📌 Git Workflow

This repository follows a structured Git project workflow designed for collaboration and clean releases.

### Branching strategy

- `main` — stable production-ready code
- `develop` — integration branch for current development work
- `feature/*` — new features and enhancements
- `fix/*` — bug fixes and maintenance
- `release/*` — release preparation

### Commit conventions

Use clear, actionable commit messages:
- `feat: add multi-exchange BSE support`
- `fix: correct exchange endpoint JSON handling`
- `docs: update README with Git workflow`
- `refactor: clean up API error handling`

### Pull request flow

1. Create an issue or pick an existing one.
2. Checkout a new branch: `git checkout -b feature/<short-description>`.
3. Develop and test locally.
4. Commit with descriptive messages.
5. Push branch to remote: `git push origin feature/<short-description>`.
6. Open a Pull Request targeting `develop` or `main`.
7. Request review and apply feedback.
8. Merge once tests pass and reviews are approved.

### Release / deployment

- Create a release branch: `git checkout -b release/v1.0.0`
- Run final testing, update docs, and bump version if needed
- Merge release into `main` and `develop`
- Tag the release: `git tag -a v1.0.0 -m 'Release v1.0.0'`
- Push tags: `git push origin v1.0.0`

---

## 🚀 Getting started

### Prerequisites
- Python 3.8+
- Go 1.19+ (optional)
- pip package manager
- Git

### Installation

```bash
git clone <repository-url>
cd stockagent
pip install -r requirements.txt
```

### Optional package install

```bash
pip install -e .
```

---

## 🧪 Development workflow

### Start backend and scheduler

```bash
# Start background scheduler
python scheduler.py

# In another terminal, start the API server
python -m src.api.app
```

### Running the Go backend

```bash
cd backend
go run main.go
```

### Open dashboard

Browse to `http://localhost:5000`

---

## 📊 Feature overview

- Multi-exchange market coverage: `nse`, `bse`, or `both`
- Automatic refresh every 3 minutes
- Silent retraining every 30 minutes
- AI score ranking and sentiment indicators
- Real-time dashboard with search, sort, pagination
- SQLite snapshot history for repeatability

---

## 📁 Repository structure

```text
stockagent/
├── backend/         # Go backend server
├── config/          # Environment and app settings
├── data/            # Storage and cache files
├── frontend/        # Dashboard UI assets
├── src/             # Python API, scraper, ML, scheduler
├── tests/           # Unit and integration tests
├── scheduler.py     # Background job orchestration
├── requirements.txt # Python dependencies
├── setup.py         # package metadata
└── README.md        # Project documentation
```

---

## 🧩 API endpoints

### Health and config
```bash
GET  /api/health
GET  /api/config/exchange
PUT  /api/config/exchange
```

### Stock data
```bash
GET  /api/stocks/top
GET  /api/stocks?limit=50&offset=0&search=&sort=score&direction=desc
GET  /api/stocks/<symbol>
POST /api/stocks/refresh
```

---

## ⚙️ Configuration

Create a `.env` file in the repository root:

```env
DEBUG=True
SECRET_KEY=your-secret-key
API_HOST=localhost
API_PORT=5000
OPENAI_API_KEY=your-openai-key
```

Modify `config/settings.py` for database paths, logging, and scraper behavior.

---

## ✅ Testing

```bash
python -m pytest tests/test_ml.py -v
python -m pytest tests/ -v
```

### Recommended Git test routine

- `git pull origin develop`
- `git checkout -b feature/<name>`
- make changes
- `pytest` locally
- commit and push
- open PR

---

## 🚢 Deployment

### Docker

```bash
docker build -t stockagent .
docker run -p 5000:5000 stockagent
```

### Production

```bash
gunicorn --bind 0.0.0.0:5000 src.api.app:app
```

Or use the Go service:

```bash
cd backend
go build -o stockagent
./stockagent
```

---

## 🤝 Contributing

1. Choose or create an issue.
2. Branch from `develop`.
3. Add tests for new behavior.
4. Write clear commit messages.
5. Push and open a PR.
6. Use code review, then merge.

### Branch naming examples
- `feature/add-bse-support`
- `fix/exchange-endpoint`
- `chore/update-deps`
- `docs/improve-readme`

---

## 📝 Release notes

- Keep release tags semantic: `v1.0.0`, `v1.1.0`
- Document major changes in release descriptions
- Include any migration or config updates

---

## ⚠️ Disclaimer

This project is for educational and research purposes. It provides AI-based insights, not financial advice.

---

## 📄 License

MIT License. See [LICENSE](LICENSE).

