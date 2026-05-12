const API_BASE_URL = "/api";
const REFRESH_INTERVAL_MS = 180000;
const AUTH_STORAGE_KEY = "nse-stock-intelligence-auth";

let scoreChart = null;
let comparisonChart = null;
let topStocks = [];
let marketStocks = [];
let comparisonHistory = {};
let modelInfo = {};
let currentSearch = "";
let currentSort = "score";
let currentDirection = "desc";
let currentPage = 1;
let pageSize = 50;
let totalStocks = 0;
let currentAuthView = "login";
let autoRefreshTimer = null;
let userActive = false;
let userActivityTimeout = null;
let currentExchange = "nse";
let isRefreshing = false;

document.addEventListener("DOMContentLoaded", () => {
    bindEvents();
    updateAuthUI();
    loadExchangeSetting();
    loadCachedData();  // Show existing stored data immediately
    triggerBackgroundRefresh().catch(() => {});  // Refresh in the background once initial UI is ready
    startAutoRefresh();
    addUserActivityListeners();
});

function startAutoRefresh() {
    autoRefreshTimer = setInterval(() => {
        if (!userActive && !isRefreshing) {
            triggerBackgroundRefresh().catch(() => {});  // Silent background refresh
        }
    }, REFRESH_INTERVAL_MS);
}

function addUserActivityListeners() {
    const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'];
    events.forEach(event => {
        document.addEventListener(event, handleUserActivity, true);
    });
}

function handleUserActivity() {
    userActive = true;
    if (userActivityTimeout) {
        clearTimeout(userActivityTimeout);
    }
    userActivityTimeout = setTimeout(() => {
        userActive = false;
    }, 30000);
}

async function loadExchangeSetting() {
    try {
        const result = await fetchJson(`${API_BASE_URL}/config/exchange`);
        currentExchange = result.data.exchange || "nse";
        if (document.getElementById("exchange-select")) {
            document.getElementById("exchange-select").value = currentExchange;
        }
    } catch (error) {
        console.warn("Could not load exchange setting:", error);
    }
}

function bindEvents() {
    document.getElementById("refresh-btn").addEventListener("click", () => manualRefresh());
    
    const exchangeSelect = document.getElementById("exchange-select");
    if (exchangeSelect) {
        exchangeSelect.addEventListener("change", async (event) => {
            currentExchange = event.target.value;
            try {
                await putJson(`${API_BASE_URL}/config/exchange`, { exchange: currentExchange });
            } catch (error) {
                console.warn("Failed to save exchange selection:", error);
            }
        });
    }

    document.getElementById("login-btn").addEventListener("click", () => openAuthModal("login"));
    document.getElementById("signup-btn").addEventListener("click", () => openAuthModal("signup"));
    document.getElementById("forgot-btn").addEventListener("click", () => openAuthModal("forgot"));
    document.getElementById("logout-btn").addEventListener("click", handleLogout);
    document.getElementById("auth-close-btn").addEventListener("click", closeAuthModal);
    document.querySelectorAll("[data-auth-view]").forEach((button) => {
        button.addEventListener("click", () => switchAuthView(button.dataset.authView));
    });
    document.getElementById("login-form").addEventListener("submit", submitLogin);
    document.getElementById("signup-form").addEventListener("submit", submitSignup);
    document.getElementById("forgot-form").addEventListener("submit", submitForgotPassword);
    document.getElementById("reset-form").addEventListener("submit", submitResetPassword);
    document.getElementById("search-input").addEventListener("input", debounce((event) => {
        currentSearch = event.target.value.trim();
        currentPage = 1;
        loadMarketStocks();
    }, 300));
    document.getElementById("sort-select").addEventListener("change", (event) => {
        currentSort = event.target.value;
        currentPage = 1;
        loadMarketStocks();
    });
    document.getElementById("page-size-select").addEventListener("change", (event) => {
        pageSize = Number(event.target.value || 50);
        currentPage = 1;
        loadMarketStocks();
    });
    document.getElementById("prev-page-btn").addEventListener("click", () => {
        if (currentPage > 1) {
            currentPage -= 1;
            loadMarketStocks();
        }
    });
    document.getElementById("next-page-btn").addEventListener("click", () => {
        if ((currentPage * pageSize) < totalStocks) {
            currentPage += 1;
            loadMarketStocks();
        }
    });
}

async function manualRefresh() {
    if (isRefreshing) {
        setMessage("Refresh already in progress...", "info");
        return;
    }
    setMessage("Refreshing market data...", "info");
    await loadCachedData(false);
    await triggerBackgroundRefresh();
}

async function loadCachedData(showLoadingMessage = true) {
    if (showLoadingMessage) {
        setMessage("Loading cached market data...", "info");
    }

    try {
        const [topResult] = await Promise.all([
            fetchJson(`${API_BASE_URL}/stocks/top?limit=10`),
            fetchJson(`${API_BASE_URL}/stocks/refresh/status`).catch(() => null),
        ]);

        topStocks = Array.isArray(topResult.data) ? topResult.data : [];
        displayTopStocks();
        updateScoreChart();
        updateLastUpdated();
        await loadMarketStocks();

        if (topStocks.length > 0) {
            await viewStock(topStocks[0].symbol, false);
            if (!document.getElementById("page-message").classList.contains("error")) {
                setMessage("", "info");
            }
        } else {
            renderSelectedStock(null, "No stocks available yet.");
            setMessage("Data loading... Check back soon.", "info");
        }
    } catch (error) {
        topStocks = [];
        marketStocks = [];
        totalStocks = 0;
        displayTopStocks();
        displayStocksTable();
        updateScoreChart();
        renderSelectedStock(null, error.message || "Failed to fetch data.");
        setMessage(error.message || "Failed to fetch data.", "error");
    }
}

async function refreshData(showLoadingMessage = true) {
    return loadCachedData(showLoadingMessage);
}

async function triggerBackgroundRefresh() {
    if (isRefreshing) return;
    
    isRefreshing = true;
    try {
        const result = await postJson(`${API_BASE_URL}/stocks/refresh`, { exchange: currentExchange });
        setMessage("Background refresh started in real-time...", "success");
        
        // Reload data after a short delay to get updated values
        setTimeout(() => refreshData(false), 2000);
    } catch (error) {
        if (error.message.includes("already running")) {
            // Silent - already refreshing
        } else {
            setMessage("Could not start refresh. " + error.message, "error");
        }
    } finally {
        isRefreshing = false;
    }
}

async function loadMarketStocks() {
    const offset = (currentPage - 1) * pageSize;
    const url = `${API_BASE_URL}/stocks?limit=${pageSize}&offset=${offset}&search=${encodeURIComponent(currentSearch)}&sort=${encodeURIComponent(currentSort)}&direction=${currentDirection}`;
    const result = await fetchJson(url);
    marketStocks = Array.isArray(result.data) ? result.data : [];
    totalStocks = Number(result.count || 0);
    displayStocksTable();
    updatePager();
}

async function fetchJson(url) {
    const response = await fetch(url, { headers: { Accept: "application/json" } });
    let payload = {};
    try {
        payload = await response.json();
    } catch (error) {
        throw new Error("Server returned an invalid response.");
    }

    if (!response.ok) {
        throw new Error(payload.error || `Request failed with status ${response.status}.`);
    }
    return payload;
}

async function sendJson(url, payload, method = "POST") {
    const response = await fetch(url, {
        method,
        headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
        },
        body: JSON.stringify(payload),
    });

    const text = await response.text();
    let data;
    try {
        data = JSON.parse(text);
    } catch (error) {
        throw new Error(`Invalid JSON response from ${url}: ${text}`);
    }

    if (!response.ok) {
        throw new Error(data.error || `Request failed with status ${response.status}.`);
    }
    return data;
}

async function postJson(url, payload) {
    return sendJson(url, payload, "POST");
}

async function putJson(url, payload) {
    return sendJson(url, payload, "PUT");
}

function displayTopStocks() {
    const container = document.getElementById("top-stocks");
    if (topStocks.length === 0) {
        container.innerHTML = '<div class="stock-item empty-state"><p>No stocks available.</p></div>';
        return;
    }

    container.innerHTML = topStocks.map((stock, index) => `
        <button type="button" class="stock-item" data-symbol="${stock.symbol}">
            <div class="stock-info">
                <div class="stock-symbol">${escapeHtml(stock.symbol)}</div>
                <small>${escapeHtml(stock.name || stock.symbol)}</small>
                <div class="stock-meta">#${index + 1} | Predicted ${formatSignedPercent(stock.predicted_price_change)}</div>
            </div>
            <div class="stock-score score-${getScoreClass(stock.score)}">${Math.round(stock.score)}</div>
        </button>
    `).join("");

    container.querySelectorAll("[data-symbol]").forEach((button) => {
        button.addEventListener("click", () => viewStock(button.dataset.symbol, true));
    });
}

function displayStocksTable() {
    const tableBody = document.getElementById("table-body");
    if (marketStocks.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="7" class="text-center">No stocks match this search.</td></tr>';
        return;
    }

    tableBody.innerHTML = marketStocks.map((stock) => {
        const priceChangeClass = stock.price_change >= 0 ? "positive" : "negative";
        const sign = stock.price_change >= 0 ? "+" : "-";
        return `
            <tr>
                <td><strong>${escapeHtml(stock.symbol)}</strong><div class="table-subtext">${escapeHtml(stock.name || stock.symbol)}</div></td>
                <td><span class="stock-score score-${getScoreClass(stock.score)}">${Math.round(stock.score)}</span></td>
                <td>${formatSignedPercent(stock.predicted_price_change)}</td>
                <td>${formatPercent(stock.sentiment)}</td>
                <td><span class="${priceChangeClass}">${sign} ${Math.abs(stock.price_change || 0).toFixed(2)}%</span></td>
                <td>${formatCurrency(stock.current_price)}</td>
                <td><button type="button" class="btn-inline" data-view-stock="${stock.symbol}">View</button></td>
            </tr>
        `;
    }).join("");

    tableBody.querySelectorAll("[data-view-stock]").forEach((button) => {
        button.addEventListener("click", () => viewStock(button.dataset.viewStock, true));
    });
}

function updatePager() {
    const totalPages = Math.max(1, Math.ceil(totalStocks / pageSize));
    document.getElementById("pager-status").textContent = `Page ${currentPage} of ${totalPages} | ${totalStocks} stocks`;
    document.getElementById("prev-page-btn").disabled = currentPage <= 1;
    document.getElementById("next-page-btn").disabled = currentPage >= totalPages;
}

async function viewStock(symbol, updateComparison = true) {
    renderSelectedStock(null, `Loading ${symbol}...`);
    try {
        const [stockResult, historyResult] = await Promise.all([
            fetchJson(`${API_BASE_URL}/stocks/${encodeURIComponent(symbol)}`),
            fetchJson(`${API_BASE_URL}/stocks/${encodeURIComponent(symbol)}/history?limit=40`),
        ]);

        const stock = stockResult.data;
        const history = Array.isArray(historyResult.data) ? historyResult.data : [];
        renderSelectedStock(stock, "", history);

        if (updateComparison) {
            comparisonHistory[symbol] = history.map((point) => ({
                snapshot_time: point.snapshot_time,
                score: point.score,
                current_price: point.current_price,
                predicted_price_change: point.predicted_price_change,
            }));
            updateComparisonChart();
        }
    } catch (error) {
        renderSelectedStock(null, error.message || `Failed to load ${symbol}.`);
    }
}

function renderSelectedStock(stock, message = "", history = []) {
    const container = document.getElementById("selected-stock");
    if (message) {
        container.innerHTML = `<p class="subtle-text">${escapeHtml(message)}</p>`;
        return;
    }
    if (!stock) {
        container.innerHTML = '<p class="subtle-text">Choose a stock to see more details.</p>';
        return;
    }

    const reasoning = stock.reasoning || {};
    const comparison = reasoning.comparison || {};
    const summaryText = reasoning.llm_summary || reasoning.summary || "No explanation available.";
    const driverBadges = (reasoning.drivers || []).map((driver) => `<span class="driver-pill">${escapeHtml(driver)}</span>`).join("");
    const sourceBadges = (reasoning.sources || []).map((source) => `<span class="driver-pill source-pill">${escapeHtml(source)}</span>`).join("");
    const lastSnapshots = history.slice(-4).map((point) => `
        <div class="mini-history-row">
            <span>${formatSnapshotLabel(point.snapshot_time)}</span>
            <strong>${Math.round(point.score)}</strong>
        </div>
    `).join("");

    container.innerHTML = `
        <div class="stock-detail-header">
            <div>
                <div class="stock-symbol">${escapeHtml(stock.symbol)}</div>
                <div class="subtle-text">${escapeHtml(stock.name || stock.symbol)}</div>
            </div>
            <div class="stock-score score-${getScoreClass(stock.score)}">${Math.round(stock.score)}</div>
        </div>
        <div class="detail-row"><span>Current Price</span><strong>${formatCurrency(stock.current_price)}</strong></div>
        <div class="detail-row"><span>Predicted Move</span><strong>${formatSignedPercent(stock.predicted_price_change)}</strong></div>
        <div class="detail-row"><span>Confidence</span><strong>${Math.round(stock.confidence || 0)}%</strong></div>
        <div class="detail-grid">
            <div class="metric-chip"><span>Momentum</span><strong>${formatMetric(comparison.momentum_score || stock.momentum)}</strong></div>
            <div class="metric-chip"><span>Volume</span><strong>${formatMetric(comparison.volume_score || stock.volume_signal)}</strong></div>
            <div class="metric-chip"><span>Sentiment</span><strong>${formatMetric(comparison.sentiment_score || normalizeSentiment(stock.sentiment))}</strong></div>
            <div class="metric-chip"><span>Model</span><strong>${escapeHtml(comparison.model_name || modelInfo.model_name || "heuristic")}</strong></div>
        </div>
        <div class="driver-pills">${driverBadges || '<span class="driver-pill">mixed signals</span>'}</div>
        <div class="driver-pills">${sourceBadges || '<span class="driver-pill source-pill">stored</span>'}</div>
        <div class="detail-summary">
            <strong>${escapeHtml(reasoning.stance || "Current view")}</strong>
            <p>${escapeHtml(summaryText)}</p>
        </div>
        <div class="mini-history">
            <strong>Recent saved snapshots</strong>
            ${lastSnapshots || '<p class="subtle-text">Only one snapshot is stored so far.</p>'}
        </div>
    `;
}

function updateScoreChart() {
    const canvas = document.getElementById("scoreChart");
    const fallback = document.getElementById("chart-fallback");
    if (scoreChart) {
        scoreChart.destroy();
        scoreChart = null;
    }

    if (topStocks.length === 0) {
        canvas.classList.add("hidden");
        fallback.classList.remove("hidden");
        fallback.textContent = "Score chart will appear after stocks are loaded.";
        return;
    }

    if (typeof Chart !== "function") {
        canvas.classList.add("hidden");
        fallback.classList.remove("hidden");
        fallback.innerHTML = topStocks.map((stock) => `<div>${escapeHtml(stock.symbol)}: ${Math.round(stock.score)}</div>`).join("");
        return;
    }

    fallback.classList.add("hidden");
    canvas.classList.remove("hidden");
    scoreChart = new Chart(canvas.getContext("2d"), {
        type: "bar",
        data: {
            labels: topStocks.map((stock) => stock.symbol),
            datasets: [
                {
                    label: "Score",
                    data: topStocks.map((stock) => Math.round(stock.score)),
                    backgroundColor: topStocks.map((stock) => getScoreColor(stock.score)),
                    borderRadius: 10,
                    borderSkipped: false,
                },
                {
                    label: "Predicted Move %",
                    data: topStocks.map((stock) => stock.predicted_price_change || 0),
                    type: "line",
                    yAxisID: "y1",
                    borderColor: "#146c94",
                    backgroundColor: "rgba(20,108,148,0.18)",
                    tension: 0.35,
                },
            ],
        },
        options: chartOptions(),
    });
}

async function loadComparisonHistory(symbols) {
    if (!symbols || symbols.length === 0) {
        comparisonHistory = {};
        updateComparisonChart();
        return;
    }

    const result = await fetchJson(`${API_BASE_URL}/stocks/compare?symbols=${encodeURIComponent(symbols.join(","))}&limit=20`);
    comparisonHistory = result.data || {};
    updateComparisonChart();
}

function updateComparisonChart() {
    const canvas = document.getElementById("comparisonChart");
    const fallback = document.getElementById("comparison-fallback");
    if (comparisonChart) {
        comparisonChart.destroy();
        comparisonChart = null;
    }

    const symbols = Object.keys(comparisonHistory || {});
    if (symbols.length === 0) {
        canvas.classList.add("hidden");
        fallback.classList.remove("hidden");
        fallback.textContent = "Historical comparison will appear after snapshots are stored.";
        return;
    }

    if (typeof Chart !== "function") {
        canvas.classList.add("hidden");
        fallback.classList.remove("hidden");
        fallback.innerHTML = symbols.map((symbol) => `<div>${escapeHtml(symbol)}: ${comparisonHistory[symbol].length} snapshots</div>`).join("");
        return;
    }

    const longestSeries = comparisonHistory[symbols[0]] || [];
    const labels = longestSeries.map((point) => formatSnapshotLabel(point.snapshot_time));
    const palette = ["#146c94", "#0f9d7a", "#e58f17", "#d94b67", "#6e7fe8"];

    fallback.classList.add("hidden");
    canvas.classList.remove("hidden");
    comparisonChart = new Chart(canvas.getContext("2d"), {
        type: "line",
        data: {
            labels,
            datasets: symbols.map((symbol, index) => ({
                label: symbol,
                data: (comparisonHistory[symbol] || []).map((point) => point.score),
                borderColor: palette[index % palette.length],
                backgroundColor: `${palette[index % palette.length]}22`,
                tension: 0.3,
                fill: false,
            })),
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { labels: { color: "#203040" } } },
            scales: {
                x: { ticks: { color: "#51606f" }, grid: { color: "#d6dde4" } },
                y: { ticks: { color: "#51606f" }, grid: { color: "#d6dde4" }, min: 0, max: 100 },
            },
        },
    });
}

function chartOptions() {
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { labels: { color: "#203040" } } },
        scales: {
            x: { ticks: { color: "#51606f" }, grid: { color: "#d6dde4" } },
            y: { ticks: { color: "#51606f" }, grid: { color: "#d6dde4" }, min: 0, max: 100 },
            y1: { position: "right", ticks: { color: "#146c94" }, grid: { drawOnChartArea: false } },
        },
    };
}

function generateInsights(summaryData = {}) {
    const container = document.getElementById("ai-insights");
    if (topStocks.length === 0) {
        container.innerHTML = "<p>No insights available right now.</p>";
        return;
    }

    const leader = topStocks[0];
    const avgScore = topStocks.reduce((sum, stock) => sum + stock.score, 0) / topStocks.length;
    const insights = [
        {
            title: `${leader.symbol} leads the board`,
            text: (leader.reasoning && (leader.reasoning.llm_summary || leader.reasoning.summary)) || `${leader.symbol} is at the top on current score and predicted move.`,
        },
        {
            title: "Current scenario",
            text: getMarketInsight(avgScore, topStocks),
        },
        {
            title: "Training loop",
            text: modelInfo && modelInfo.model_name
                ? `Refresh retrains ${modelInfo.model_name} on ${modelInfo.samples || 0} market examples before ranking the next cycle.`
                : "Refresh retrains the market model before ranking the next cycle.",
        },
    ];

    container.innerHTML = insights.map((insight) => `
        <div class="insight-item">
            <div class="insight-title">${escapeHtml(insight.title)}</div>
            <div class="insight-text">${escapeHtml(insight.text)}</div>
        </div>
    `).join("");
}

function renderMarketSummary(summaryData = {}, currentModel = {}) {
    const container = document.getElementById("market-summary");
    const leader = summaryData.top_stock;
    const comparisons = Array.isArray(summaryData.comparisons) ? summaryData.comparisons : [];
    const model = summaryData.model || currentModel || {};

    if (!leader) {
        container.innerHTML = '<p class="subtle-text">Market summary will appear after data is loaded.</p>';
        return;
    }

    const rows = comparisons.slice(0, 6).map((item) => `
        <div class="summary-row">
            <span>${escapeHtml(item.symbol)}</span>
            <strong>${Math.round(item.score)}</strong>
            <small>${formatSignedPercent(item.predicted_price_change)} | ${Math.round(item.confidence || 0)}%</small>
        </div>
    `).join("");

    container.innerHTML = `
        <div class="summary-hero">
            <div class="summary-kicker">Top ranked now</div>
            <div class="summary-symbol">${escapeHtml(leader.symbol)}</div>
            <p>${escapeHtml((leader.reasoning && (leader.reasoning.llm_summary || leader.reasoning.summary)) || summaryData.summary || "No summary available.")}</p>
        </div>
        <div class="model-badge">
            <strong>${escapeHtml(model.model_name || "heuristic")}</strong>
            <span>samples ${Number(model.samples || 0)}</span>
            <span>R2 ${Number(model.r2 || 0).toFixed(3)}</span>
            <span>trained ${escapeHtml(model.trained_at || "n/a")}</span>
        </div>
        <div class="summary-list">${rows}</div>
    `;
}

function renderRefreshStatus(status = {}) {
    const badge = document.getElementById("api-status");
    if (!badge) return;

    if (status.running) {
        badge.textContent = "Refreshing in background";
        badge.classList.add("status-ok");
        badge.classList.remove("status-error");
        return;
    }

    if (status.last_error) {
        badge.textContent = "Refresh fallback mode";
        badge.classList.add("status-error");
        badge.classList.remove("status-ok");
        setMessage(`Live refresh failed, showing last saved data. ${status.last_error}`, "error");
        return;
    }

    if (status.last_finished_at) {
        badge.textContent = `Last refresh ${formatSnapshotLabel(status.last_finished_at)}`;
        badge.classList.add("status-ok");
        badge.classList.remove("status-error");
    }
}

function switchView(viewName) {
    document.querySelectorAll(".page-section").forEach((section) => {
        section.classList.toggle("hidden", section.id !== viewName);
    });
    document.querySelectorAll("[data-view]").forEach((button) => {
        button.classList.toggle("active", button.dataset.view === viewName);
    });
}

function openAuthModal(view) {
    document.getElementById("auth-modal").classList.remove("hidden");
    switchAuthView(view || "login");
}

function closeAuthModal() {
    document.getElementById("auth-modal").classList.add("hidden");
    setAuthFeedback("", "");
}

function switchAuthView(view) {
    currentAuthView = view;
    document.getElementById("auth-modal-title").textContent = {
        login: "Login",
        signup: "Create Account",
        forgot: "Forgot Password",
        reset: "Reset Password",
    }[view] || "Authentication";

    document.getElementById("login-form").classList.toggle("hidden", view !== "login");
    document.getElementById("signup-form").classList.toggle("hidden", view !== "signup");
    document.getElementById("forgot-form").classList.toggle("hidden", view !== "forgot");
    document.getElementById("reset-form").classList.toggle("hidden", view !== "reset");
    document.querySelectorAll("[data-auth-view]").forEach((button) => {
        button.classList.toggle("active", button.dataset.authView === view);
    });
    setAuthFeedback("", "");
}

function setAuthFeedback(message, type) {
    const box = document.getElementById("auth-feedback");
    box.textContent = message;
    box.className = `auth-feedback ${message ? "" : "hidden"} ${type || ""}`.trim();
}

async function submitLogin(event) {
    event.preventDefault();
    try {
        const result = await postJson(`${API_BASE_URL}/auth/login`, {
            identifier: document.getElementById("login-identifier").value.trim(),
            password: document.getElementById("login-password").value,
        });
        const user = result.data;
        saveAuthState({ loggedIn: true, username: user.username, email: user.email, createdAt: user.created_at });
        closeAuthModal();
        setMessage(`Logged in as ${user.username}.`, "success");
    } catch (error) {
        setAuthFeedback(error.message, "error");
    }
}

async function submitSignup(event) {
    event.preventDefault();
    try {
        const result = await postJson(`${API_BASE_URL}/auth/register`, {
            username: document.getElementById("signup-username").value.trim(),
            email: document.getElementById("signup-email").value.trim(),
            password: document.getElementById("signup-password").value,
        });
        const user = result.data;
        saveAuthState({ loggedIn: true, username: user.username, email: user.email, createdAt: user.created_at });
        closeAuthModal();
        setMessage(`Account created for ${user.username}.`, "success");
    } catch (error) {
        setAuthFeedback(error.message, "error");
    }
}

async function submitForgotPassword(event) {
    event.preventDefault();
    try {
        const result = await postJson(`${API_BASE_URL}/auth/forgot-password`, {
            identifier: document.getElementById("forgot-identifier").value.trim(),
        });
        const payload = result.data;
        document.getElementById("reset-identifier").value = payload.email || payload.username || "";
        switchAuthView("reset");
        setAuthFeedback(`Reset code: ${payload.reset_code}. It expires in ${payload.expires_in_minutes} minutes.`, "success");
    } catch (error) {
        setAuthFeedback(error.message, "error");
    }
}

async function submitResetPassword(event) {
    event.preventDefault();
    try {
        const result = await postJson(`${API_BASE_URL}/auth/reset-password`, {
            identifier: document.getElementById("reset-identifier").value.trim(),
            code: document.getElementById("reset-code").value.trim(),
            password: document.getElementById("reset-password").value,
        });
        switchAuthView("login");
        setAuthFeedback(`Password updated for ${result.data.username}. You can log in now.`, "success");
    } catch (error) {
        setAuthFeedback(error.message, "error");
    }
}

function handleLogout() {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    updateAuthUI();
    setMessage("You have been logged out.", "info");
}

function saveAuthState(authState) {
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(authState));
    updateAuthUI();
}

function getAuthState() {
    try {
        return JSON.parse(localStorage.getItem(AUTH_STORAGE_KEY)) || { loggedIn: false };
    } catch (error) {
        return { loggedIn: false };
    }
}

function updateAuthUI() {
    const authState = getAuthState();
    const authStatus = document.getElementById("auth-status");
    const loginBtn = document.getElementById("login-btn");
    const signupBtn = document.getElementById("signup-btn");
    const forgotBtn = document.getElementById("forgot-btn");
    const logoutBtn = document.getElementById("logout-btn");

    if (authState.loggedIn) {
        authStatus.textContent = `Signed in: ${authState.username || "User"}${authState.email ? ` (${authState.email})` : ""}`;
        loginBtn.classList.add("hidden");
        signupBtn.classList.add("hidden");
        forgotBtn.classList.add("hidden");
        logoutBtn.classList.remove("hidden");
    } else {
        authStatus.textContent = "Guest session";
        loginBtn.classList.remove("hidden");
        signupBtn.classList.remove("hidden");
        forgotBtn.classList.remove("hidden");
        logoutBtn.classList.add("hidden");
    }
}

function updateApiStatus(isHealthy) {
    const badge = document.getElementById("api-status");
    badge.textContent = isHealthy ? "API online" : "API offline";
    badge.classList.toggle("status-ok", isHealthy);
    badge.classList.toggle("status-error", !isHealthy);
}

function updateLastUpdated() {
    document.getElementById("last-updated").textContent = new Date().toLocaleTimeString("en-IN", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
    });
}

function setMessage(message, type) {
    const box = document.getElementById("page-message");
    box.textContent = message;
    box.className = `page-message ${message ? "" : "hidden"} ${type || ""}`.trim();
}

function getMarketInsight(avgScore, stocks) {
    const positivePredictions = stocks.filter((stock) => (stock.predicted_price_change || 0) > 0).length;
    if (avgScore >= 70 && positivePredictions >= Math.ceil(stocks.length / 2)) {
        return "The board is broadly constructive with multiple stocks still showing positive predicted follow-through.";
    }
    if (avgScore >= 55) {
        return "Conditions are selective. Ranking is being driven by momentum, prediction, and confidence together.";
    }
    return "Current conditions are mixed. Search and comparison matter more than relying on one top-ranked stock.";
}

function getScoreClass(score) {
    if (score >= 70) return "high";
    if (score >= 50) return "medium";
    return "low";
}

function getScoreColor(score) {
    if (score >= 70) return "#0f9d7a";
    if (score >= 50) return "#e58f17";
    return "#d94b67";
}

function normalizeSentiment(value) {
    return ((Number(value || 0) + 1) / 2) * 100;
}

function formatPercent(value) {
    return `${(Number(value || 0) * 100).toFixed(1)}%`;
}

function formatSignedPercent(value) {
    const number = Number(value || 0);
    const sign = number >= 0 ? "+" : "-";
    return `${sign}${Math.abs(number).toFixed(2)}%`;
}

function formatCurrency(value) {
    const number = Number(value);
    if (!Number.isFinite(number) || number <= 0) return "N/A";
    return `Rs ${number.toFixed(2)}`;
}

function formatMetric(value) {
    return Number(value || 0).toFixed(1);
}

function formatSnapshotLabel(value) {
    if (!value) return "Now";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString("en-IN", {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    });
}

function debounce(callback, delay) {
    let timer = null;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => callback(...args), delay);
    };
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}
