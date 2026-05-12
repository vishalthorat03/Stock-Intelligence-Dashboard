package handlers

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"strings"

	"Stock_Intelligence_Dashboard/internal/models"
	"Stock_Intelligence_Dashboard/internal/utils"
)

func (h *Handler) TopStocksHandler(w http.ResponseWriter, r *http.Request) {
	limit := r.URL.Query().Get("limit")
	if strings.TrimSpace(limit) == "" {
		limit = "5"
	}

	output, err := h.PythonRunner.RunDbCommandWithOptions("top", limit, map[string]string{})
	if err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}

	var stocks []models.Stock
	if err := json.Unmarshal(output, &stocks); err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}

	writeJson(w, http.StatusOK, models.ApiResponse{Success: true, Data: stocks, Count: len(stocks)})
}

func (h *Handler) StocksListHandler(w http.ResponseWriter, r *http.Request) {
	query := r.URL.Query()
	options := map[string]string{
		"limit":     utils.FirstNonEmpty(query.Get("limit"), "50"),
		"offset":    utils.FirstNonEmpty(query.Get("offset"), "0"),
		"search":    query.Get("search"),
		"sort":      utils.FirstNonEmpty(query.Get("sort"), "score"),
		"direction": utils.FirstNonEmpty(query.Get("direction"), "desc"),
	}

	output, err := h.PythonRunner.RunDbCommandWithOptions("list", "", options)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}

	var payload map[string]interface{}
	if err := json.Unmarshal(output, &payload); err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}

	writeJson(w, http.StatusOK, models.ApiResponse{
		Success: true,
		Data:    payload["items"],
		Count:   utils.IntFromInterface(payload["total"]),
	})
}

func (h *Handler) StockDetailHandler(w http.ResponseWriter, r *http.Request) {
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
		history, err := h.stockHistoryHandler(symbol, limit)
		if err != nil {
			writeError(w, http.StatusInternalServerError, err)
			return
		}
		writeJson(w, http.StatusOK, models.ApiResponse{Success: true, Data: history, Count: len(history)})
		return
	}

	symbol := path
	if symbol == "" {
		writeError(w, http.StatusBadRequest, fmt.Errorf("stock symbol required"))
		return
	}
	symbol = strings.ToUpper(symbol)

	output, err := h.PythonRunner.RunDbCommand("symbol", symbol)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}

	var stock models.Stock
	if err := json.Unmarshal(output, &stock); err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}

	writeJson(w, http.StatusOK, models.ApiResponse{Success: true, Data: stock})
}

func (h *Handler) stockHistoryHandler(symbol string, limit int) ([]models.StockSnapshot, error) {
	output, err := h.PythonRunner.RunDbCommandWithOptions("history", symbol, map[string]string{
		"limit": strconv.Itoa(limit),
	})
	if err != nil {
		return nil, err
	}

	var history []models.StockSnapshot
	if err := json.Unmarshal(output, &history); err != nil {
		return nil, err
	}
	return history, nil
}

func (h *Handler) CompareStocksHandler(w http.ResponseWriter, r *http.Request) {
	symbols := r.URL.Query().Get("symbols")
	limit := utils.FirstNonEmpty(r.URL.Query().Get("limit"), "20")

	output, err := h.PythonRunner.RunDbCommandWithOptions("compare", symbols, map[string]string{
		"limit": limit,
	})
	if err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}

	var comparison map[string][]models.StockSnapshot
	if err := json.Unmarshal(output, &comparison); err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}

	writeJson(w, http.StatusOK, models.ApiResponse{Success: true, Data: comparison, Count: len(comparison)})
}

func (h *Handler) MarketSummaryHandler(w http.ResponseWriter, r *http.Request) {
	limit := r.URL.Query().Get("limit")
	options := map[string]string{}
	if strings.TrimSpace(limit) != "" {
		options["limit"] = limit
	}

	output, err := h.PythonRunner.RunDbCommandWithOptions("summary", "", options)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}

	var summary map[string]interface{}
	if err := json.Unmarshal(output, &summary); err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}

	writeJson(w, http.StatusOK, models.ApiResponse{Success: true, Data: summary})
}
