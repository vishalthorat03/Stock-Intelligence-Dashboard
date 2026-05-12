package handlers

import (
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

func (h *Handler) HealthHandler(w http.ResponseWriter, r *http.Request) {
	writeJson(w, http.StatusOK, models.ApiResponse{Success: true, Data: map[string]string{"status": "healthy", "service": "NSE Stock Intelligence Go API"}})
}
