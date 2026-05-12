// Stock Agent Backend - Built by a Golang Backend Engineer
// Keywords: Distributed Systems, Microservices, Performance Optimization, RBAC, CI/CD, Docker
package main

import (
	"encoding/json"
	"fmt"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"
)

type Stock struct {
	Symbol               string                 `json:"symbol"`
	Name                 string                 `json:"name"`
	Score                float64                `json:"score"`
	Sentiment            float64                `json:"sentiment"`
	Momentum             float64                `json:"momentum"`
	VolumeSignal         float64                `json:"volume_signal"`
	PriceChange          float64                `json:"price_change"`
	CurrentPrice         float64                `json:"current_price"`
	PredictedPriceChange float64                `json:"predicted_price_change"`
	Confidence           float64                `json:"confidence"`
	Reasoning            map[string]interface{} `json:"reasoning"`
	UpdatedAt            string                 `json:"updated_at"`
}

type ApiResponse struct {
	Success bool        `json:"success"`
	Data    interface{} `json:"data,omitempty"`
	Error   string      `json:"error,omitempty"`
	Count   int         `json:"count,omitempty"`
}

type ScoreResult struct {
	Score   float64 `json:"score"`
	Insight string  `json:"insight"`
}

type StockSnapshot struct {
	Symbol               string                 `json:"symbol"`
	Score                float64                `json:"score"`
	Sentiment            float64                `json:"sentiment"`
	Momentum             float64                `json:"momentum"`
	VolumeSignal         float64                `json:"volume_signal"`
	PriceChange          float64                `json:"price_change"`
	CurrentPrice         float64                `json:"current_price"`
	PredictedPriceChange float64                `json:"predicted_price_change"`
	Confidence           float64                `json:"confidence"`
	Reasoning            map[string]interface{} `json:"reasoning"`
	SnapshotTime         string                 `json:"snapshot_time"`
}

type RefreshJobStatus struct {
	Running        bool   `json:"running"`
	LastStartedAt  string `json:"last_started_at,omitempty"`
	LastFinishedAt string `json:"last_finished_at,omitempty"`
	LastError      string `json:"last_error,omitempty"`
	LastTrigger    string `json:"last_trigger,omitempty"`
	Updated        int    `json:"updated,omitempty"`
	UniverseSize   int    `json:"universe_size,omitempty"`
}

var refreshJob = struct {
	mu     sync.Mutex
	status RefreshJobStatus
}{
	status: RefreshJobStatus{},
}

func main() {
	rootPath := getRootPath()
	frontendPath := filepath.Join(rootPath, "frontend")

	http.HandleFunc("/api/health", healthHandler)
	http.HandleFunc("/api/auth/register", registerHandler)
	http.HandleFunc("/api/auth/login", loginHandler)
	http.HandleFunc("/api/auth/forgot-password", forgotPasswordHandler)
	http.HandleFunc("/api/auth/reset-password", resetPasswordHandler)
	http.HandleFunc("/api/stocks", stocksListHandler)
	http.HandleFunc("/api/stocks/top", topStocksHandler)
	http.HandleFunc("/api/stocks/compare", compareStocksHandler)
	http.HandleFunc("/api/stocks/summary", marketSummaryHandler)
	http.HandleFunc("/api/stocks/refresh", refreshStocksHandler)
	http.HandleFunc("/api/stocks/refresh/status", refreshStatusHandler)
	http.HandleFunc("/api/model", modelInfoHandler)
	http.HandleFunc("/api/stocks/", stockDetailHandler)
	http.HandleFunc("/api/score", scoreHandler)
	http.HandleFunc("/", serveFrontend)

	// Minimal Vercel Fix #1
	port := getEnv("PORT", getEnv("API_PORT", "5004"))

	listener, err := getListenListener(port)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Server failed to bind: %v\n", err)
		os.Exit(1)
	}

	// Minimal Vercel Fix #2
	// Disabled scheduler for Vercel serverless runtime
	// startRefreshScheduler()

	fmt.Printf("Starting Go backend on %s\n", listener.Addr())
	fmt.Printf("Serving frontend from %s\n", frontendPath)

	if err := http.Serve(listener, nil); err != nil {
		fmt.Fprintf(os.Stderr, "Server failed: %v\n", err)
		os.Exit(1)
	}
}

func getRootPath() string {
	cwd, err := os.Getwd()
	if err == nil {
		if exists(filepath.Join(cwd, "frontend")) {
			return filepath.Clean(cwd)
		}
		parent := filepath.Dir(cwd)
		if exists(filepath.Join(parent, "frontend")) {
			return filepath.Clean(parent)
		}
	}

	execPath, err := os.Executable()
	if err == nil {
		execDir := filepath.Dir(execPath)
		if exists(filepath.Join(execDir, "frontend")) {
			return filepath.Clean(execDir)
		}
		parent := filepath.Dir(execDir)
		if exists(filepath.Join(parent, "frontend")) {
			return filepath.Clean(parent)
		}
	}

	if err != nil {
		return "."
	}
	return filepath.Clean(cwd)
}

func exists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}

func getEnv(key, defaultValue string) string {
	value := os.Getenv(key)
	if value == "" {
		return defaultValue
	}
	return value
}

func getListenListener(port string) (net.Listener, error) {
	for i := 0; i < 5; i++ {
		candidate := port
		if i > 0 {
			portNum, err := strconv.Atoi(port)
			if err != nil {
				return nil, err
			}
			candidate = strconv.Itoa(portNum + i)
		}
		addr := fmt.Sprintf("0.0.0.0:%s", candidate)
		listener, err := net.Listen("tcp", addr)
		if err == nil {
			return listener, nil
		}
		if !strings.Contains(err.Error(), "address already in use") {
			return nil, err
		}
	}
	return nil, fmt.Errorf("could not bind to %s or nearby ports", port)
}

func serveFrontend(w http.ResponseWriter, r *http.Request) {
	frontendPath := filepath.Join(getRootPath(), "frontend")
	requestPath := filepath.Clean("/" + strings.TrimPrefix(r.URL.Path, "/"))

	if requestPath == "/" {
		http.ServeFile(w, r, filepath.Join(frontendPath, "index.html"))
		return
	}

	assetPath := filepath.Join(frontendPath, strings.TrimPrefix(requestPath, "/"))
	if rel, err := filepath.Rel(frontendPath, assetPath); err != nil || strings.HasPrefix(rel, "..") {
		http.NotFound(w, r)
		return
	}

	info, err := os.Stat(assetPath)
	if err == nil && !info.IsDir() {
		http.ServeFile(w, r, assetPath)
		return
	}

	http.ServeFile(w, r, filepath.Join(frontendPath, "index.html"))
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	writeJson(w, http.StatusOK, ApiResponse{Success: true, Data: map[string]string{"status": "healthy", "service": "NSE Stock Intelligence Go API"}})
}

func registerHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, fmt.Errorf("method not allowed"))
		return
	}

	var payload map[string]string
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		writeError(w, http.StatusBadRequest, fmt.Errorf("invalid request body"))
		return
	}

	output, err := runPythonDbCommandWithOptions("register", "", map[string]string{
		"username": payload["username"],
		"email":    payload["email"],
		"password": payload["password"],
	})
	if err != nil {
		writeError(w, http.StatusBadRequest, err)
		return
	}

	var result map[string]interface{}
	if err := json.Unmarshal(output, &result); err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}
	if message, ok := result["error"].(string); ok && strings.TrimSpace(message) != "" {
		writeError(w, http.StatusBadRequest, fmt.Errorf("%s", message))
		return
	}
	writeJson(w, http.StatusOK, ApiResponse{Success: true, Data: result})
}

func loginHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, fmt.Errorf("method not allowed"))
		return
	}

	var payload map[string]string
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		writeError(w, http.StatusBadRequest, fmt.Errorf("invalid request body"))
		return
	}

	output, err := runPythonDbCommandWithOptions("login", firstNonEmpty(payload["identifier"], payload["email"]), map[string]string{
		"password": payload["password"],
	})
	if err != nil {
		writeError(w, http.StatusBadRequest, err)
		return
	}

	var result map[string]interface{}
	if err := json.Unmarshal(output, &result); err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}
	if message, ok := result["error"].(string); ok && strings.TrimSpace(message) != "" {
		writeError(w, http.StatusBadRequest, fmt.Errorf("%s", message))
		return
	}
	writeJson(w, http.StatusOK, ApiResponse{Success: true, Data: result})
}

func forgotPasswordHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, fmt.Errorf("method not allowed"))
		return
	}

	var payload map[string]string
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		writeError(w, http.StatusBadRequest, fmt.Errorf("invalid request body"))
		return
	}

	output, err := runPythonDbCommandWithOptions("forgot-password", firstNonEmpty(payload["identifier"], payload["email"]), map[string]string{})
	if err != nil {
		writeError(w, http.StatusBadRequest, err)
		return
	}

	var result map[string]interface{}
	if err := json.Unmarshal(output, &result); err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}
	if message, ok := result["error"].(string); ok && strings.TrimSpace(message) != "" {
		writeError(w, http.StatusBadRequest, fmt.Errorf("%s", message))
		return
	}
	writeJson(w, http.StatusOK, ApiResponse{Success: true, Data: result})
}

func resetPasswordHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, fmt.Errorf("method not allowed"))
		return
	}

	var payload map[string]string
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		writeError(w, http.StatusBadRequest, fmt.Errorf("invalid request body"))
		return
	}

	output, err := runPythonDbCommandWithOptions("reset-password", firstNonEmpty(payload["identifier"], payload["email"]), map[string]string{
		"code":     payload["code"],
		"password": payload["password"],
	})
	if err != nil {
		writeError(w, http.StatusBadRequest, err)
		return
	}

	var result map[string]interface{}
	if err := json.Unmarshal(output, &result); err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}
	if message, ok := result["error"].(string); ok && strings.TrimSpace(message) != "" {
		writeError(w, http.StatusBadRequest, fmt.Errorf("%s", message))
		return
	}
	writeJson(w, http.StatusOK, ApiResponse{Success: true, Data: result})
}

func topStocksHandler(w http.ResponseWriter, r *http.Request) {
	limit := r.URL.Query().Get("limit")
	if strings.TrimSpace(limit) == "" {
		limit = "5"
	}

	output, err := runPythonDbCommandWithOptions("top", limit, map[string]string{})
	if err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}

	var stocks []Stock
	if err := json.Unmarshal(output, &stocks); err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}

	writeJson(w, http.StatusOK, ApiResponse{Success: true, Data: stocks, Count: len(stocks)})
}

func stocksListHandler(w http.ResponseWriter, r *http.Request) {
	query := r.URL.Query()
	options := map[string]string{
		"limit":     firstNonEmpty(query.Get("limit"), "50"),
		"offset":    firstNonEmpty(query.Get("offset"), "0"),
		"search":    query.Get("search"),
		"sort":      firstNonEmpty(query.Get("sort"), "score"),
		"direction": firstNonEmpty(query.Get("direction"), "desc"),
	}

	output, err := runPythonDbCommandWithOptions("list", "", options)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}

	var payload map[string]interface{}
	if err := json.Unmarshal(output, &payload); err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}

	writeJson(w, http.StatusOK, ApiResponse{
		Success: true,
		Data:    payload["items"],
		Count:   intFromInterface(payload["total"]),
	})
}

func stockDetailHandler(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, "/api/stocks/")
	if strings.HasSuffix(path, "/history") {
		symbol := strings.TrimSuffix(path, "/history")
		symbol = strings.TrimSuffix(symbol, "/")
		if symbol == "" {
			writeError(w, http.StatusBadRequest, fmt.Errorf("stock symbol required"))
			return
		}
		symbol = strings.ToUpper(symbol)
		limit := 30
		if rawLimit := r.URL.Query().Get("limit"); strings.TrimSpace(rawLimit) != "" {
			if parsedLimit, err := strconv.Atoi(rawLimit); err == nil && parsedLimit > 0 {
				limit = parsedLimit
			}
		}
		history, err := stockHistoryHandler(symbol, limit)
		if err != nil {
			writeError(w, http.StatusInternalServerError, err)
			return
		}
		writeJson(w, http.StatusOK, ApiResponse{Success: true, Data: history, Count: len(history)})
		return
	}

	symbol := path
	if symbol == "" {
		writeError(w, http.StatusBadRequest, fmt.Errorf("stock symbol required"))
		return
	}
	symbol = strings.ToUpper(symbol)

	output, err := runPythonDbCommand("symbol", symbol)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}

	var stock Stock
	if err := json.Unmarshal(output, &stock); err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}

	writeJson(w, http.StatusOK, ApiResponse{Success: true, Data: stock})
}

func stockHistoryHandler(symbol string, limit int) ([]StockSnapshot, error) {
	output, err := runPythonDbCommandWithOptions("history", symbol, map[string]string{
		"limit": strconv.Itoa(limit),
	})
	if err != nil {
		return nil, err
	}

	var history []StockSnapshot
	if err := json.Unmarshal(output, &history); err != nil {
		return nil, err
	}
	return history, nil
}

func compareStocksHandler(w http.ResponseWriter, r *http.Request) {
	symbols := r.URL.Query().Get("symbols")
	limit := firstNonEmpty(r.URL.Query().Get("limit"), "20")

	output, err := runPythonDbCommandWithOptions("compare", symbols, map[string]string{
		"limit": limit,
	})
	if err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}

	var comparison map[string][]StockSnapshot
	if err := json.Unmarshal(output, &comparison); err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}

	writeJson(w, http.StatusOK, ApiResponse{Success: true, Data: comparison, Count: len(comparison)})
}

func marketSummaryHandler(w http.ResponseWriter, r *http.Request) {
	limit := r.URL.Query().Get("limit")
	options := map[string]string{}
	if strings.TrimSpace(limit) != "" {
		options["limit"] = limit
	}

	output, err := runPythonDbCommandWithOptions("summary", "", options)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}

	var summary map[string]interface{}
	if err := json.Unmarshal(output, &summary); err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}

	writeJson(w, http.StatusOK, ApiResponse{Success: true, Data: summary})
}

func refreshStocksHandler(w http.ResponseWriter, r *http.Request) {
	symbols := r.URL.Query().Get("symbols")
	trigger := "manual"
	if err := triggerBackgroundRefresh(symbols, trigger); err != nil {
		writeError(w, http.StatusConflict, err)
		return
	}

	writeJson(w, http.StatusAccepted, ApiResponse{
		Success: true,
		Data: map[string]interface{}{
			"message": "refresh started in background",
			"status":  getRefreshStatus(),
		},
	})
}

func refreshStatusHandler(w http.ResponseWriter, r *http.Request) {
	writeJson(w, http.StatusOK, ApiResponse{Success: true, Data: getRefreshStatus()})
}

func modelInfoHandler(w http.ResponseWriter, r *http.Request) {
	output, err := runPythonDbCommandWithOptions("model", "", map[string]string{})
	if err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}

	var payload map[string]interface{}
	if err := json.Unmarshal(output, &payload); err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}

	writeJson(w, http.StatusOK, ApiResponse{Success: true, Data: payload})
}

func scoreHandler(w http.ResponseWriter, r *http.Request) {
	query := r.URL.Query()
	momentum, err := strconv.ParseFloat(query.Get("momentum"), 64)
	if err != nil {
		writeError(w, http.StatusBadRequest, fmt.Errorf("invalid momentum"))
		return
	}
	volume, err := strconv.ParseFloat(query.Get("volume"), 64)
	if err != nil {
		writeError(w, http.StatusBadRequest, fmt.Errorf("invalid volume"))
		return
	}
	sentiment, err := strconv.ParseFloat(query.Get("sentiment"), 64)
	if err != nil {
		writeError(w, http.StatusBadRequest, fmt.Errorf("invalid sentiment"))
		return
	}

	output, err := runPythonScore(momentum, volume, sentiment)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}

	var result ScoreResult
	if err := json.Unmarshal(output, &result); err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}

	writeJson(w, http.StatusOK, ApiResponse{Success: true, Data: result})
}

func runPythonDbCommand(command, arg string) ([]byte, error) {
	return runPythonDbCommandWithOptions(command, arg, map[string]string{})
}

func runPythonDbCommandWithOptions(command, arg string, options map[string]string) ([]byte, error) {
	pythonExe := getPythonExecutable()
	scriptPath := filepath.Join(getRootPath(), "src", "api", "db_cli.py")
	args := []string{scriptPath, command}
	if strings.TrimSpace(arg) != "" {
		args = append(args, arg)
	}
	for key, value := range options {
		if strings.TrimSpace(value) == "" {
			continue
		}
		args = append(args, "--"+key, value)
	}
	cmd := exec.Command(pythonExe, args...)
	cmd.Env = os.Environ()
	return cmd.Output()
}

func startRefreshScheduler() {
	go func() {
		// Train model at startup
		_, _ = runPythonDbCommand("train", "")
		// Initial data refresh with retraining
		_ = triggerBackgroundRefresh("", "startup")
		ticker := time.NewTicker(3 * time.Minute)
		defer ticker.Stop()
		for range ticker.C {
			_ = triggerBackgroundRefresh("", "auto")
		}
	}()
}

func triggerBackgroundRefresh(symbols, trigger string) error {
	refreshJob.mu.Lock()
	if refreshJob.status.Running {
		refreshJob.mu.Unlock()
		return fmt.Errorf("refresh job already running")
	}
	refreshJob.status.Running = true
	refreshJob.status.LastStartedAt = time.Now().Format(time.RFC3339)
	refreshJob.status.LastError = ""
	refreshJob.status.LastTrigger = trigger
	refreshJob.mu.Unlock()

	go func() {
		output, err := runPythonDbCommandWithOptions("refresh", symbols, map[string]string{})
		status := getRefreshStatus()
		status.Running = false
		status.LastFinishedAt = time.Now().Format(time.RFC3339)

		if err != nil {
			status.LastError = err.Error()
			setRefreshStatus(status)
			return
		}

		var result map[string]interface{}
		if err := json.Unmarshal(output, &result); err != nil {
			status.LastError = err.Error()
			setRefreshStatus(status)
			return
		}

		if message, ok := result["error"].(string); ok && strings.TrimSpace(message) != "" {
			status.LastError = message
			setRefreshStatus(status)
			return
		}

		status.Updated = intFromInterface(result["updated"])
		status.UniverseSize = intFromInterface(result["universe_size"])
		status.LastError = ""
		setRefreshStatus(status)
	}()

	return nil
}

func getRefreshStatus() RefreshJobStatus {
	refreshJob.mu.Lock()
	defer refreshJob.mu.Unlock()
	return refreshJob.status
}

func setRefreshStatus(status RefreshJobStatus) {
	refreshJob.mu.Lock()
	defer refreshJob.mu.Unlock()
	refreshJob.status = status
}

func firstNonEmpty(value, fallback string) string {
	if strings.TrimSpace(value) == "" {
		return fallback
	}
	return value
}

func intFromInterface(value interface{}) int {
	switch v := value.(type) {
	case float64:
		return int(v)
	case int:
		return v
	default:
		return 0
	}
}

func runPythonScore(momentum, volume, sentiment float64) ([]byte, error) {
	pythonExe := getPythonExecutable()
	scriptPath := filepath.Join(getRootPath(), "src", "ml", "cli.py")
	cmd := exec.Command(pythonExe, scriptPath,
		"--momentum", fmt.Sprintf("%f", momentum),
		"--volume", fmt.Sprintf("%f", volume),
		"--sentiment", fmt.Sprintf("%f", sentiment),
	)
	cmd.Env = os.Environ()
	return cmd.Output()
}

func getPythonExecutable() string {
	pythonExe := getEnv("PYTHON_EXECUTABLE", "")
	if pythonExe != "" {
		return pythonExe
	}

	venvPath := filepath.Join(getRootPath(), ".venv", "Scripts", "python.exe")
	if _, err := os.Stat(venvPath); err == nil {
		return venvPath
	}

	return "python"
}

func writeJson(w http.ResponseWriter, status int, payload ApiResponse) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(payload)
}

func writeError(w http.ResponseWriter, status int, err error) {
	writeJson(w, status, ApiResponse{Success: false, Error: err.Error()})
}
