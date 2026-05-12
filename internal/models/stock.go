package models

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

type RefreshJobStatus struct {
	Running        bool   `json:"running"`
	LastStartedAt  string `json:"last_started_at,omitempty"`
	LastFinishedAt string `json:"last_finished_at,omitempty"`
	LastError      string `json:"last_error,omitempty"`
	LastTrigger    string `json:"last_trigger,omitempty"`
	Updated        int    `json:"updated,omitempty"`
	UniverseSize   int    `json:"universe_size,omitempty"`
}
