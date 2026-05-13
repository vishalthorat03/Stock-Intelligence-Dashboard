package handlers

import (
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"Stock_Intelligence_Dashboard/internal/models"
	"Stock_Intelligence_Dashboard/internal/python"
	"Stock_Intelligence_Dashboard/internal/utils"
)

type Handler struct {
	PythonRunner utils.PythonRunner
}

func NewHandler() *Handler {
	return &Handler{
		PythonRunner: &python.DefaultPythonRunner{},
	}
}

func (h *Handler) ServeFrontend(w http.ResponseWriter, r *http.Request) {
	frontendPath := filepath.Join(utils.GetRootPath(), "frontend")
	requestPath := filepath.Clean("/" + strings.TrimPrefix(r.URL.Path, "/"))

	// Debug logging
	if os.Getenv("DEBUG") == "1" {
		fmt.Fprintf(os.Stderr, "Frontend Request: path=%s, frontend=%s\n", requestPath, frontendPath)
	}

	if requestPath == "/" {
		filePath := filepath.Join(frontendPath, "index.html")
		if _, err := os.Stat(filePath); err == nil {
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			http.ServeFile(w, r, filePath)
			return
		}
	}

	assetPath := filepath.Join(frontendPath, strings.TrimPrefix(requestPath, "/"))
	if rel, err := filepath.Rel(frontendPath, assetPath); err != nil || strings.HasPrefix(rel, "..") {
		// If not found, try to serve index.html for SPA routing
		http.ServeFile(w, r, filepath.Join(frontendPath, "index.html"))
		return
	}

	info, err := os.Stat(assetPath)
	if err == nil && !info.IsDir() {
		http.ServeFile(w, r, assetPath)
		return
	}

	// For SPA routing, serve index.html
	http.ServeFile(w, r, filepath.Join(frontendPath, "index.html"))
}

func (h *Handler) HealthHandler(w http.ResponseWriter, r *http.Request) {
	writeJson(w, http.StatusOK, models.ApiResponse{Success: true, Data: map[string]string{"status": "healthy", "service": "NSE Stock Intelligence Go API"}})
}
