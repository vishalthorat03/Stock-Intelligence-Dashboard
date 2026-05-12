package handler

import (
	"net/http"
	"strings"

	"Stock_Intelligence_Dashboard/internal/handlers"
)

var appHandler = handlers.NewHandler()

func Handler(w http.ResponseWriter, r *http.Request) {
	switch {
	case r.URL.Path == "/api/health":
		appHandler.HealthHandler(w, r)
	case r.URL.Path == "/api/auth/register":
		appHandler.RegisterHandler(w, r)
	case r.URL.Path == "/api/auth/login":
		appHandler.LoginHandler(w, r)
	case r.URL.Path == "/api/auth/forgot-password":
		appHandler.ForgotPasswordHandler(w, r)
	case r.URL.Path == "/api/auth/reset-password":
		appHandler.ResetPasswordHandler(w, r)
	case r.URL.Path == "/api/stocks":
		appHandler.StocksListHandler(w, r)
	case r.URL.Path == "/api/stocks/top":
		appHandler.TopStocksHandler(w, r)
	case r.URL.Path == "/api/stocks/compare":
		appHandler.CompareStocksHandler(w, r)
	case r.URL.Path == "/api/stocks/summary":
		appHandler.MarketSummaryHandler(w, r)
	case r.URL.Path == "/api/stocks/refresh":
		appHandler.RefreshStocksHandler(w, r)
	case r.URL.Path == "/api/stocks/refresh/status":
		appHandler.RefreshStatusHandler(w, r)
	case r.URL.Path == "/api/model":
		appHandler.ModelInfoHandler(w, r)
	case r.URL.Path == "/api/score":
		appHandler.ScoreHandler(w, r)
	case strings.HasPrefix(r.URL.Path, "/api/stocks/"):
		appHandler.StockDetailHandler(w, r)
	default:
		appHandler.ServeFrontend(w, r)
	}
}
