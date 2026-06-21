const loginScreen = document.getElementById("login-screen");
const portfolioScreen = document.getElementById("portfolio-screen");
const loginForm = document.getElementById("login-form");
const pinInput = document.getElementById("pin-input");
const loginError = document.getElementById("login-error");
const refreshBtn = document.getElementById("refresh-btn");
const connectBtn = document.getElementById("connect-btn");
const connectBanner = document.getElementById("connect-banner");
const loading = document.getElementById("loading");
const holdingsList = document.getElementById("holdings-list");
const holdingsCountEl = document.getElementById("holdings-count");
const totalInvestedEl = document.getElementById("total-invested");
const totalValueEl = document.getElementById("total-value");
const heroPnlEl = document.getElementById("hero-pnl");
const totalPnlEl = document.getElementById("total-pnl");
const totalPnlPctEl = document.getElementById("total-pnl-pct");
const totalReturnPctEl = document.getElementById("total-return-pct");
const statusEl = document.getElementById("status");
const statusTextEl = document.getElementById("status-text");
const updatedAtEl = document.getElementById("updated-at");

function show(el) { el.classList.remove("hidden"); }
function hide(el) { el.classList.add("hidden"); }

function setLoading(on) {
  on ? show(loading) : hide(loading);
  refreshBtn.classList.toggle("refreshing", on);
}

function formatMoney(n) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);
}

function formatPct(n) {
  const sign = n >= 0 ? "+" : "";
  return `${sign}${n.toFixed(1)}%`;
}

function formatPnl(n, pct) {
  const sign = n >= 0 ? "+" : "";
  const cls = n >= 0 ? "positive" : "negative";
  return `<span class="${cls}">${sign}${formatMoney(n)} · ${formatPct(pct)}</span>`;
}

function formatTime(iso) {
  const d = new Date(iso);
  return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function tickerBadge(ticker) {
  return ticker.length <= 4 ? ticker : ticker.slice(0, 3);
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  let data = null;
  const text = await res.text();
  if (text) {
    try { data = JSON.parse(text); } catch { data = { detail: text }; }
  }
  if (!res.ok) {
    const msg = data?.detail || `Request failed (${res.status})`;
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return data;
}

function clearSummary() {
  totalValueEl.textContent = "—";
  hide(heroPnlEl);
  totalInvestedEl.textContent = "—";
  totalReturnPctEl.textContent = "—";
  holdingsCountEl.textContent = "—";
}

function renderPortfolio(data) {
  hide(connectBanner);
  totalValueEl.textContent = formatMoney(data.total_value);
  totalInvestedEl.textContent = formatMoney(data.total_invested);
  holdingsCountEl.textContent = String(data.holdings.length);

  const returnPct = data.total_invested
    ? (data.total_pnl / data.total_invested) * 100
    : 0;

  if (data.total_pnl != null) {
    const cls = data.total_pnl >= 0 ? "positive" : "negative";
    const sign = data.total_pnl >= 0 ? "+" : "";
    show(heroPnlEl);
    totalPnlEl.className = `pnl-badge ${cls}`;
    totalPnlEl.textContent = `${sign}${formatMoney(data.total_pnl)}`;
    totalPnlPctEl.className = `pnl-pct ${cls}`;
    totalPnlPctEl.textContent = formatPct(returnPct);
    totalReturnPctEl.className = `metric-value ${cls}`;
    totalReturnPctEl.textContent = formatPct(returnPct);
  } else {
    hide(heroPnlEl);
    totalReturnPctEl.className = "metric-value";
    totalReturnPctEl.textContent = "—";
  }

  const sourceLabels = {
    live: "Live · Robinhood",
    cache: "Cached",
    snapshot: "Saved snapshot",
    mock: "Mock data",
  };
  const isLive = data.source === "live" || data.source === "cache";
  statusEl.classList.toggle("offline", !isLive);
  statusTextEl.textContent = sourceLabels[data.source] || data.source;

  holdingsList.innerHTML = data.holdings.map((h) => {
    const alloc = data.total_value ? (h.value / data.total_value) * 100 : 0;
    return `
    <li class="holding">
      <div class="ticker-badge">${tickerBadge(h.ticker)}</div>
      <div class="holding-info">
        <div class="ticker">${h.ticker}</div>
        <div class="holding-meta">
          <span class="shares">${h.shares} sh</span>
          <div class="allocation-bar" title="${alloc.toFixed(1)}% of portfolio">
            <div class="allocation-fill" style="width: ${Math.max(alloc, 2)}%"></div>
          </div>
        </div>
      </div>
      <div class="holding-right">
        <div class="value">${formatMoney(h.value)}</div>
        <div class="pnl">${formatPnl(h.pnl, h.pnl_pct)}</div>
      </div>
    </li>`;
  }).join("");

  updatedAtEl.textContent = `Updated ${formatTime(data.updated_at)}`;
}

async function checkConnection() {
  const status = await api("/api/connection/status");
  if (!status.connected) {
    show(connectBanner);
    holdingsList.innerHTML = "";
    clearSummary();
    updatedAtEl.textContent = "";
    statusEl.classList.add("offline");
    statusTextEl.textContent = "Not connected";
    return false;
  }
  return true;
}

async function loadPortfolio(refresh = false) {
  setLoading(true);
  try {
    const connected = await checkConnection();
    if (!connected) return;
    const data = await api(`/api/portfolio${refresh ? "?refresh=true" : ""}`);
    renderPortfolio(data);
  } catch (err) {
    if (err.message.includes("not connected")) {
      show(connectBanner);
      statusEl.classList.add("offline");
      statusTextEl.textContent = err.message;
    } else {
      statusEl.classList.add("offline");
      statusTextEl.textContent = err.message;
    }
  } finally {
    setLoading(false);
  }
}

async function connectRobinhood() {
  setLoading(true);
  try {
    const { url } = await api("/api/connection/portal", { method: "POST" });
    window.location.href = url;
  } catch (err) {
    statusEl.classList.add("offline");
    statusTextEl.textContent = err.message;
    setLoading(false);
  }
}

async function checkAuth() {
  setLoading(true);
  try {
    const { authenticated } = await api("/api/me");
    if (authenticated) {
      hide(loginScreen);
      show(portfolioScreen);
      if (new URLSearchParams(window.location.search).get("connected") === "1") {
        window.history.replaceState({}, "", "/");
      }
      await loadPortfolio(true);
    } else {
      show(loginScreen);
      hide(portfolioScreen);
    }
  } catch {
    show(loginScreen);
    hide(portfolioScreen);
  } finally {
    setLoading(false);
  }
}

loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  hide(loginError);
  setLoading(true);
  try {
    await api("/api/login", { method: "POST", body: JSON.stringify({ pin: pinInput.value }) });
    pinInput.value = "";
    hide(loginScreen);
    show(portfolioScreen);
    await loadPortfolio();
  } catch {
    show(loginError);
    loginError.textContent = "Invalid PIN";
  } finally {
    setLoading(false);
  }
});

refreshBtn.addEventListener("click", () => loadPortfolio(true));
connectBtn.addEventListener("click", connectRobinhood);

checkAuth();
