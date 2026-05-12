package handlers

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"

	"Stock_Intelligence_Dashboard/internal/models"
	"Stock_Intelligence_Dashboard/internal/utils"
)

func (h *Handler) RegisterHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, fmt.Errorf("method not allowed"))
		return
	}

	var payload map[string]string
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		writeError(w, http.StatusBadRequest, fmt.Errorf("invalid request body"))
		return
	}

	output, err := h.PythonRunner.RunDbCommandWithOptions("register", "", map[string]string{
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
	writeJson(w, http.StatusOK, models.ApiResponse{Success: true, Data: result})
}

func (h *Handler) LoginHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, fmt.Errorf("method not allowed"))
		return
	}

	var payload map[string]string
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		writeError(w, http.StatusBadRequest, fmt.Errorf("invalid request body"))
		return
	}

	output, err := h.PythonRunner.RunDbCommandWithOptions("login", utils.FirstNonEmpty(payload["identifier"], payload["email"]), map[string]string{
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
	writeJson(w, http.StatusOK, models.ApiResponse{Success: true, Data: result})
}

func (h *Handler) ForgotPasswordHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, fmt.Errorf("method not allowed"))
		return
	}

	var payload map[string]string
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		writeError(w, http.StatusBadRequest, fmt.Errorf("invalid request body"))
		return
	}

	output, err := h.PythonRunner.RunDbCommandWithOptions("forgot-password", utils.FirstNonEmpty(payload["identifier"], payload["email"]), map[string]string{})
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
	writeJson(w, http.StatusOK, models.ApiResponse{Success: true, Data: result})
}

func (h *Handler) ResetPasswordHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, fmt.Errorf("method not allowed"))
		return
	}

	var payload map[string]string
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		writeError(w, http.StatusBadRequest, fmt.Errorf("invalid request body"))
		return
	}

	output, err := h.PythonRunner.RunDbCommandWithOptions("reset-password", utils.FirstNonEmpty(payload["identifier"], payload["email"]), map[string]string{
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
	writeJson(w, http.StatusOK, models.ApiResponse{Success: true, Data: result})
}
