package utils

import (
	"encoding/json"
	"fmt"
	"net"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"Stock_Intelligence_Dashboard/internal/models"
)

type PythonRunner interface {
	RunDbCommand(command, arg string) ([]byte, error)
	RunDbCommandWithOptions(command, arg string, options map[string]string) ([]byte, error)
	RunScore(momentum, volume, sentiment float64) ([]byte, error)
}

var refreshJob = struct {
	mu     sync.Mutex
	status models.RefreshJobStatus
}{
	status: models.RefreshJobStatus{},
}

func GetEnv(key, defaultValue string) string {
	value := os.Getenv(key)
	if value == "" {
		return defaultValue
	}
	return value
}

func GetListenListener(port string) (net.Listener, error) {
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

func GetRootPath() string {
	// First check if VERCEL environment is set
	if os.Getenv("VERCEL") == "1" || os.Getenv("VERCEL_ENV") != "" {
		// On Vercel, files are in /var/task
		if exists("/var/task/frontend") {
			return "/var/task"
		}
	}

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

func FirstNonEmpty(value, fallback string) string {
	if strings.TrimSpace(value) == "" {
		return fallback
	}
	return value
}

func IntFromInterface(value interface{}) int {
	switch v := value.(type) {
	case float64:
		return int(v)
	case int:
		return v
	default:
		return 0
	}
}

func StartRefreshScheduler(pythonRunner PythonRunner) {
	go func() {
		// Train model at startup
		_, _ = pythonRunner.RunDbCommand("train", "")
		// Initial data refresh with retraining
		_ = TriggerBackgroundRefresh("", "startup", pythonRunner)
		ticker := time.NewTicker(3 * time.Minute)
		defer ticker.Stop()
		for range ticker.C {
			_ = TriggerBackgroundRefresh("", "auto", pythonRunner)
		}
	}()
}

func TriggerBackgroundRefresh(symbols, trigger string, pythonRunner PythonRunner) error {
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
		output, err := pythonRunner.RunDbCommandWithOptions("refresh", symbols, map[string]string{})
		status := GetRefreshStatus()
		status.Running = false
		status.LastFinishedAt = time.Now().Format(time.RFC3339)

		if err != nil {
			status.LastError = err.Error()
			SetRefreshStatus(status)
			return
		}

		var result map[string]interface{}
		if err := json.Unmarshal(output, &result); err != nil {
			status.LastError = err.Error()
			SetRefreshStatus(status)
			return
		}

		if message, ok := result["error"].(string); ok && strings.TrimSpace(message) != "" {
			status.LastError = message
			SetRefreshStatus(status)
			return
		}

		status.Updated = IntFromInterface(result["updated"])
		status.UniverseSize = IntFromInterface(result["universe_size"])
		status.LastError = ""
		SetRefreshStatus(status)
	}()

	return nil
}

func GetRefreshStatus() models.RefreshJobStatus {
	refreshJob.mu.Lock()
	defer refreshJob.mu.Unlock()
	return refreshJob.status
}

func SetRefreshStatus(status models.RefreshJobStatus) {
	refreshJob.mu.Lock()
	defer refreshJob.mu.Unlock()
	refreshJob.status = status
}
