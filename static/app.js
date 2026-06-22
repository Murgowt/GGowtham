const loginScreen = document.getElementById("login-screen");
const portfolioScreen = document.getElementById("portfolio-screen");
const settingsScreen = document.getElementById("settings-screen");
const loginForm = document.getElementById("login-form");
const pinInput = document.getElementById("pin-input");
const loginError = document.getElementById("login-error");
const refreshBtn = document.getElementById("refresh-btn");
const settingsBtn = document.getElementById("settings-btn");
const settingsBackBtn = document.getElementById("settings-back-btn");
const connectBtn = document.getElementById("connect-btn");
const connectBanner = document.getElementById("connect-banner");
const notificationsPanel = document.getElementById("notifications-panel");
const notificationsUnavailable = document.getElementById("notifications-unavailable");
const notificationsStatus = document.getElementById("notifications-status");
const notificationsHint = document.getElementById("notifications-hint");
const enableNotificationsBtn = document.getElementById("enable-notifications-btn");
const testNotificationBtn = document.getElementById("test-notification-btn");
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

function isStandalone() {
  return window.matchMedia("(display-mode: standalone)").matches
    || window.navigator.standalone === true;
}

function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
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

async function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) return null;
  return navigator.serviceWorker.register("/sw.js", { scope: "/" });
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

function showPortfolio() {
  hide(settingsScreen);
  show(portfolioScreen);
}

function showSettings() {
  hide(portfolioScreen);
  show(settingsScreen);
  loadNotificationsSettings();
}

async function loadNotificationsSettings() {
  hide(notificationsPanel);
  hide(notificationsUnavailable);
  hide(notificationsHint);

  if (!("Notification" in window) || !("serviceWorker" in navigator) || !("PushManager" in window)) {
    show(notificationsUnavailable);
    notificationsUnavailable.textContent = "Notifications are not supported in this browser.";
    return;
  }

  try {
    const config = await api("/api/notifications/config");
    if (!config.enabled || !config.vapid_public_key) {
      show(notificationsUnavailable);
      return;
    }

    show(notificationsPanel);
    const status = await api("/api/notifications/status");
    updateNotificationsUI(status.subscribed);

    if (!isStandalone()) {
      show(notificationsHint);
      notificationsHint.textContent =
        "For iPhone notifications, open Brain from your Home Screen app (not Safari).";
    }
  } catch {
    show(notificationsUnavailable);
  }
}

function updateNotificationsUI(subscribed) {
  if (subscribed) {
    notificationsStatus.textContent = "On";
    notificationsStatus.classList.add("on");
    enableNotificationsBtn.textContent = "Notifications enabled";
    enableNotificationsBtn.disabled = true;
    show(testNotificationBtn);
  } else {
    notificationsStatus.textContent = "Off";
    notificationsStatus.classList.remove("on");
    enableNotificationsBtn.textContent = "Enable notifications";
    enableNotificationsBtn.disabled = false;
    hide(testNotificationBtn);
  }
}

async function enableNotifications() {
  if (!isStandalone()) {
    notificationsHint.textContent =
      "Add Brain to your Home Screen, open it from the icon, then enable notifications.";
    show(notificationsHint);
    return;
  }

  setLoading(true);
  try {
    await registerServiceWorker();
    const config = await api("/api/notifications/config");
    const permission = await Notification.requestPermission();
    if (permission !== "granted") {
      notificationsHint.textContent = "Notification permission denied. Enable in iOS Settings → Brain.";
      show(notificationsHint);
      return;
    }

    const registration = await navigator.serviceWorker.ready;
    let subscription = await registration.pushManager.getSubscription();
    if (!subscription) {
      subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(config.vapid_public_key),
      });
    }

    await api("/api/notifications/subscribe", {
      method: "POST",
      body: JSON.stringify({ subscription: subscription.toJSON() }),
    });
    updateNotificationsUI(true);
    hide(notificationsHint);
  } catch (err) {
    notificationsHint.textContent = err.message;
    show(notificationsHint);
  } finally {
    setLoading(false);
  }
}

async function sendTestNotification() {
  setLoading(true);
  try {
    await api("/api/notifications/test", { method: "POST" });
    notificationsHint.textContent = "Test sent — check your lock screen.";
    show(notificationsHint);
  } catch (err) {
    notificationsHint.textContent = err.message;
    show(notificationsHint);
  } finally {
    setLoading(false);
  }
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
      showPortfolio();
      if (new URLSearchParams(window.location.search).get("connected") === "1") {
        window.history.replaceState({}, "", "/");
      }
      await registerServiceWorker();
      await loadPortfolio(true);
    } else {
      show(loginScreen);
      hide(portfolioScreen);
      hide(settingsScreen);
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
    showPortfolio();
    await registerServiceWorker();
    await loadPortfolio();
  } catch {
    show(loginError);
    loginError.textContent = "Invalid PIN";
  } finally {
    setLoading(false);
  }
});

refreshBtn.addEventListener("click", () => loadPortfolio(true));
settingsBtn.addEventListener("click", showSettings);
settingsBackBtn.addEventListener("click", showPortfolio);
connectBtn.addEventListener("click", connectRobinhood);
enableNotificationsBtn.addEventListener("click", enableNotifications);
testNotificationBtn.addEventListener("click", sendTestNotification);

checkAuth();
