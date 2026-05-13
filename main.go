package main

import (
	"fmt"
	"net/http"
	"os"

	"Stock_Intelligence_Dashboard/internal/handlers"
	"Stock_Intelligence_Dashboard/internal/utils"
)

func main() {
	handler := handlers.NewHandler()

	http.HandleFunc("/api/health", handler.HealthHandler)
	http.HandleFunc("/api/auth/register", handler.RegisterHandler)
	http.HandleFunc("/api/auth/login", handler.LoginHandler)
	http.HandleFunc("/api/auth/forgot-password", handler.ForgotPasswordHandler)
	http.HandleFunc("/api/auth/reset-password", handler.ResetPasswordHandler)
	http.HandleFunc("/api/stocks", handler.StocksListHandler)
	http.HandleFunc("/api/stocks/top", handler.TopStocksHandler)
	http.HandleFunc("/api/stocks/compare", handler.CompareStocksHandler)
	http.HandleFunc("/api/stocks/summary", handler.MarketSummaryHandler)
	http.HandleFunc("/api/stocks/refresh", handler.RefreshStocksHandler)
	http.HandleFunc("/api/stocks/refresh/status", handler.RefreshStatusHandler)
	http.HandleFunc("/api/model", handler.ModelInfoHandler)
	http.HandleFunc("/api/stocks/", handler.StockDetailHandler)
	http.HandleFunc("/api/score", handler.ScoreHandler)
	http.HandleFunc("/", handler.ServeFrontend)

	port := utils.GetEnv("PORT", utils.GetEnv("API_PORT", "5004"))
	rootPath := utils.GetRootPath()
	frontendPath := rootPath + "/frontend"

	listener, err := utils.GetListenListener(port)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Server failed to bind: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("Starting Go backend on %s\n", listener.Addr())
	fmt.Printf("Root path: %s\n", rootPath)
	fmt.Printf("Serving frontend from %s\n", frontendPath)
	fmt.Printf("Frontend directory exists: %v\n", dirExists(frontendPath))

	if err := http.Serve(listener, nil); err != nil {
		fmt.Fprintf(os.Stderr, "Server failed: %v\n", err)
		os.Exit(1)
	}
}

func dirExists(path string) bool {
	info, err := os.Stat(path)
	return err == nil && info.IsDir()
}
