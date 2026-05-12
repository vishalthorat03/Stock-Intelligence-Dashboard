package handlers

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"

	"Stock_Intelligence_Dashboard/internal/models"
	"Stock_Intelligence_Dashboard/internal/utils"
)

func (h *Handler) RefreshStocksHandler(w http.ResponseWriter, r *http.Request) {
	symbols := r.URL.Query().Get("symbols")
	trigger := "manual"
	if err := utils.TriggerBackgroundRefresh(symbols, trigger, h.PythonRunner); err != nil {
		writeError(w, http.StatusConflict, err)
		return
	}

	writeJson(w, http.StatusAccepted, models.ApiResponse{
		Success: true,
		Data: map[string]interface{}{
			"message": "refresh started in background",
			"status":  utils.GetRefreshStatus(),
		},
	})
}

func (h *Handler) RefreshStatusHandler(w http.ResponseWriter, r *http.Request) {
	writeJson(w, http.StatusOK, models.ApiResponse{Success: true, Data: utils.GetRefreshStatus()})
}

func (h *Handler) ModelInfoHandler(w http.ResponseWriter, r *http.Request) {
	output, err := h.PythonRunner.RunDbCommandWithOptions("model", "", map[string]string{})
	if err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}

	var payload map[string]interface{}
	if err := json.Unmarshal(output, &payload); err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}

	writeJson(w, http.StatusOK, models.ApiResponse{Success: true, Data: payload})
}

func (h *Handler) ScoreHandler(w http.ResponseWriter, r *http.Request) {
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

	output, err := h.PythonRunner.RunScore(momentum, volume, sentiment)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}

	var result models.ScoreResult
	if err := json.Unmarshal(output, &result); err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}

	writeJson(w, http.StatusOK, models.ApiResponse{Success: true, Data: result})
}

func writeJson(w http.ResponseWriter, status int, payload models.ApiResponse) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(payload)
}

func writeError(w http.ResponseWriter, status int, err error) {
	writeJson(w, status, models.ApiResponse{Success: false, Error: err.Error()})
}
