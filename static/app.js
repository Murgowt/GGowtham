const loginScreen = document.getElementById("login-screen");
const portfolioScreen = document.getElementById("portfolio-screen");
const spendingScreen = document.getElementById("spending-screen");
const settingsScreen = document.getElementById("settings-screen");
const loginForm = document.getElementById("login-form");
const pinInput = document.getElementById("pin-input");
const loginError = document.getElementById("login-error");
const refreshBtn = document.getElementById("refresh-btn");
const settingsBtn = document.getElementById("settings-btn");
const spendRefreshBtn = document.getElementById("spend-refresh-btn");
const spendSettingsBtn = document.getElementById("spend-settings-btn");
const settingsBackBtn = document.getElementById("settings-back-btn");
const connectBtn = document.getElementById("connect-btn");
const connectBanner = document.getElementById("connect-banner");
const spendConnectBanner = document.getElementById("spend-connect-banner");
const spendSettingsShortcut = document.getElementById("spend-settings-shortcut");
const spendOverlapHint = document.getElementById("spend-overlap-hint");
const notificationsPanel = document.getElementById("notifications-panel");
const notificationsUnavailable = document.getElementById("notifications-unavailable");
const notificationsStatus = document.getElementById("notifications-status");
const notificationsHint = document.getElementById("notifications-hint");
const enableNotificationsBtn = document.getElementById("enable-notifications-btn");
const testNotificationBtn = document.getElementById("test-notification-btn");
const spendingSettingsPanel = document.getElementById("spending-settings-panel");
const spendingConnectionStatus = document.getElementById("spending-connection-status");
const plaidStatusText = document.getElementById("plaid-status-text");
const splitwiseStatusText = document.getElementById("splitwise-status-text");
const connectPlaidBtn = document.getElementById("connect-plaid-btn");
const splitwiseKeyInput = document.getElementById("splitwise-key-input");
const saveSplitwiseBtn = document.getElementById("save-splitwise-btn");
const spendingSettingsHint = document.getElementById("spending-settings-hint");
const loading = document.getElementById("loading");
const holdingsList = document.getElementById("holdings-list");
const transactionsList = document.getElementById("transactions-list");
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
const spendBudgetRemainingEl = document.getElementById("spend-budget-remaining");
const spendBudgetHeroEl = document.getElementById("spend-budget-hero");
const spendBudgetBarEl = document.getElementById("spend-budget-bar");
const spendBudgetBarFillEl = document.getElementById("spend-budget-bar-fill");
const spendMonthLabelEl = document.getElementById("spend-month-label");
const spendBudgetUsedEl = document.getElementById("spend-budget-used");
const spendCardEl = document.getElementById("spend-card");
const spendSplitwiseNetEl = document.getElementById("spend-splitwise-net");
const spendBudgetTotalEl = document.getElementById("spend-budget-total");
const monthlyBudgetInput = document.getElementById("monthly-budget-input");
const saveBudgetBtn = document.getElementById("save-budget-btn");
const spendStatusEl = document.getElementById("spend-status");
const spendStatusTextEl = document.getElementById("spend-status-text");
const spendUpdatedAtEl = document.getElementById("spend-updated-at");
const spendActivityView = document.getElementById("spend-activity-view");
const spendHistoryView = document.getElementById("spend-history-view");
const spendHistoryDetailView = document.getElementById("spend-history-detail-view");
const historyPeriodsList = document.getElementById("history-periods-list");
const historyBackBtn = document.getElementById("history-back-btn");
const historyDetailTotalEl = document.getElementById("history-detail-total");
const historyDetailLabelEl = document.getElementById("history-detail-label");
const historyDetailCardEl = document.getElementById("history-detail-card");
const historyDetailBankEl = document.getElementById("history-detail-bank");
const historyDetailSharesEl = document.getElementById("history-detail-shares");
const historyDetailExcludedEl = document.getElementById("history-detail-excluded");
const historyDetailTxnsList = document.getElementById("history-detail-txns");

let activeTab = "invest";
let spendView = "activity";
let historyPeriodKey = null;
let settingsReturnTab = "invest";
let plaidScriptPromise = null;
let spendPollTimer = null;
const SPEND_POLL_MS = 15_000;
let spendAlertBootstrapped = false;
const seenSpendAlertKeys = new Set();

function show(el) { el?.classList.remove("hidden"); }
function hide(el) { el?.classList.add("hidden"); }

function setText(el, value) {
  if (el) el.textContent = value;
}

function setLoading(on) {
  on ? show(loading) : hide(loading);
  refreshBtn.classList.toggle("refreshing", on && activeTab === "invest");
  spendRefreshBtn.classList.toggle("refreshing", on && activeTab === "spend");
}

function formatMoney(n) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);
}

function formatSignedMoney(n) {
  if (n > 0) return `+${formatMoney(n)}`;
  if (n < 0) return `−${formatMoney(Math.abs(n))}`;
  return formatMoney(0);
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

function formatSpendAlertBody(txn, budgetRemaining) {
  let desc = String(txn.description || "Expense").trim();
  if (desc.length > 36) desc = `${desc.slice(0, 33)}…`;
  const amount = Number(txn.amount) || 0;
  const amtStr = amount > 0
    ? `+${formatMoney(amount)}`
    : `−${formatMoney(Math.abs(amount))}`;
  const pending = txn.pending ? " · pending" : "";
  const left = formatMoney(budgetRemaining).replace(/\.00$/, "");
  return `${desc} ${amtStr}${pending} · ${left} left`;
}

function spendAlertKey(txn) {
  if ((txn.source === "card" || txn.source === "bank") && txn.pending_transaction_id) {
    return `plaid:${txn.pending_transaction_id}`;
  }
  return txn.id;
}

function isSpendAlertTxn(txn) {
  if (txn.excluded_from_total) return false;
  if (txn.source === "splitwise" && txn.txn_type === "share") return true;
  if (txn.source === "card" && Number(txn.amount) < 0) return true;
  return false;
}

function maybeNotifyNewSpend(data) {
  if (!("Notification" in window) || Notification.permission !== "granted") return;
  const remaining = data.summary?.budget_remaining ?? 0;
  const alertable = (data.transactions || []).filter(isSpendAlertTxn);

  if (!spendAlertBootstrapped) {
    alertable.forEach((t) => seenSpendAlertKeys.add(spendAlertKey(t)));
    spendAlertBootstrapped = true;
    return;
  }

  for (const txn of alertable) {
    const key = spendAlertKey(txn);
    if (seenSpendAlertKeys.has(key)) continue;
    seenSpendAlertKeys.add(key);
    new Notification("Brain · Spend", {
      body: formatSpendAlertBody(txn, remaining),
      icon: "/static/icon-192.png",
      tag: key,
    });
  }
}

function formatShortDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function formatTxnAmount(amount) {
  const sign = amount >= 0 ? "+" : "";
  const cls = amount >= 0 ? "positive" : "negative";
  return `<span class="${cls}">${sign}${formatMoney(amount)}</span>`;
}

function tickerBadge(ticker) {
  return ticker.length <= 4 ? ticker : ticker.slice(0, 3);
}

function sourceLabel(source, txnType, pending = false) {
  if (pending) return "Pending";
  if (txnType === "settlement") return "Settlement";
  if (txnType === "transfer") return "Transfer";
  if (txnType === "cc_payment") return "CC payment";
  return { bank: "Bank", card: "Card", splitwise: "Splitwise" }[source] || source;
}

function sourceBadgeClass(source, txnType, pending = false) {
  if (pending) return "source-badge source-pending";
  if (txnType === "settlement") return "source-badge source-settlement";
  if (txnType === "transfer") return "source-badge source-transfer";
  return `source-badge source-${source}`;
}

function mediumForTransaction(t) {
  if (t.txn_type === "investment") {
    return { key: "robinhood", short: "RH", label: "Robinhood" };
  }
  if (t.medium_key && t.medium_short) {
    return {
      key: t.medium_key,
      short: t.medium_short,
      label: t.medium_label || t.account_name,
    };
  }
  const haystack = `${t.institution_name || ""} ${t.account_name || ""}`.toLowerCase();
  if (t.source === "splitwise") {
    return { key: "splitwise", short: "SW", label: "Splitwise" };
  }
  if (haystack.includes("chase")) {
    return t.source === "card"
      ? { key: "chase_card", short: "CH", label: t.account_name || "Chase Card" }
      : { key: "chase_bank", short: "CH", label: t.account_name || "Chase Bank" };
  }
  if (haystack.includes("discover")) {
    return { key: "discover", short: "DISC", label: t.account_name || "Discover" };
  }
  if (haystack.includes("amex") || haystack.includes("american express")) {
    return { key: "amex", short: "AMEX", label: t.account_name || "Amex" };
  }
  if (t.source === "card") {
    return { key: "card_generic", short: "CARD", label: t.account_name || "Credit Card" };
  }
  return { key: "bank_generic", short: "BANK", label: t.account_name || "Bank" };
}

const STATIC_LOGO_PATHS = {
  chase_bank: "/static/logos/chase.svg",
  chase_card: "/static/logos/chase_card.png",
  discover: "/static/logos/discover.svg",
  amex: "/static/logos/amex.png",
  splitwise: "/static/logos/splitwise.png",
  robinhood: "/static/logos/robinhood.svg",
  capital_one: "/static/logos/capitalone.svg",
  citi: "/static/logos/citi.svg",
  wells_fargo: "/static/logos/wellsfargo.svg",
  bofa: "/static/logos/bankofamerica.svg",
  bank_generic: "/static/logos/bank_generic.svg",
  card_generic: "/static/logos/card_generic.svg",
};

function logoSlugForMedium(mediumKey) {
  const slugs = {
    capital_one: "capitalone",
    wells_fargo: "wellsfargo",
    bofa: "bankofamerica",
  };
  return slugs[mediumKey] || mediumKey;
}

function logoSrcForTransaction(t, logos = {}) {
  const medium = mediumForTransaction(t);
  if (STATIC_LOGO_PATHS[medium.key]) {
    return STATIC_LOGO_PATHS[medium.key];
  }
  if (t.institution_id && logos[t.institution_id]) {
    return logos[t.institution_id];
  }
  return `/static/logos/${logoSlugForMedium(medium.key)}.svg`;
}

function mediumIconHtml(t, logos = {}) {
  const medium = mediumForTransaction(t);
  const kind = t.txn_type === "investment" ? "investment"
    : t.source === "splitwise" ? "splitwise"
    : (t.source === "card" ? "card" : "bank");
  const src = logoSrcForTransaction(t, logos);
  const pngBrand = ["chase_card", "amex", "splitwise", "robinhood"].includes(medium.key) ? " brand-png" : "";
  return `<div class="medium-icon has-logo${pngBrand} medium-${medium.key}" data-kind="${kind}" title="${medium.label}">
    <img src="${src}" alt="" class="medium-logo">
  </div>`;
}

function sortTransactionsForDisplay(transactions) {
  return [...transactions].sort((a, b) => new Date(b.date) - new Date(a.date));
}

function renderExpenseRows(transactions, logos = {}) {
  const sorted = sortTransactionsForDisplay(transactions);
  return sorted.map((t) => {
    const medium = mediumForTransaction(t);
    const excluded = Boolean(t.excluded_from_total);
    const edited = Boolean(t.amount_edited);
    const actionBtn = excluded
      ? `<button type="button" class="txn-exclude-btn txn-include-btn" data-txn-id="${escapeHtml(t.id)}" aria-label="Include in budget" title="Include in budget">✓</button>`
      : `<button type="button" class="txn-exclude-btn" data-txn-id="${escapeHtml(t.id)}" aria-label="Exclude from budget" title="Exclude from budget">×</button>`;
    const editBtn = `
      <button type="button" class="txn-edit-btn" data-txn-id="${escapeHtml(t.id)}" data-current-amount="${t.amount}" data-description=${JSON.stringify(t.description || "")} aria-label="Edit amount" title="Edit amount">
        <svg class="icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M12 20h9"/>
          <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/>
        </svg>
      </button>`;
    return `
    <li class="holding transaction-row expense-txn-row${t.pending ? " transaction-row-pending" : ""}${excluded ? " transaction-row-excluded" : ""}${edited ? " transaction-row-edited" : ""}">
      ${mediumIconHtml(t, logos)}
      <div class="holding-info">
        <div class="ticker">${escapeHtml(t.description)}${excluded ? ' <span class="txn-excluded-tag">Excluded</span>' : ""}${edited ? ' <span class="txn-edited-tag" title="Amount edited">✎</span>' : ""}</div>
        <div class="holding-meta">
          <span class="shares">${medium.label}</span>
          <span class="${sourceBadgeClass(t.source, t.txn_type, t.pending)}">${sourceLabel(t.source, t.txn_type, t.pending)} · ${formatShortDate(t.date)}</span>
        </div>
      </div>
      <div class="holding-right expense-txn-actions">
        <div class="value">${formatTxnAmount(t.amount)}</div>
        ${editBtn}
        ${actionBtn}
      </div>
    </li>`;
  }).join("");
}

function renderHistoryTransactionRows(transactions, logos = {}) {
  return renderExpenseRows(transactions, logos);
}

function escapeHtml(text) {
  return String(text ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

async function toggleExpenseExclusion(txnId, including) {
  if (!including) {
    const ok = window.confirm("Exclude this expense from your budget?");
    if (!ok) return;
  }
  if (including) {
    await api(`/api/spending/exclusions/${encodeURIComponent(txnId)}`, { method: "DELETE" });
  } else {
    await api("/api/spending/exclusions", {
      method: "POST",
      body: JSON.stringify({ txn_id: txnId }),
    });
  }
}

async function editExpenseAmount(txnId, currentAmount, description) {
  const current = Number(currentAmount);
  const defaultVal = Math.abs(current).toFixed(2);
  const raw = window.prompt(`Edit budget amount for "${description}"`, defaultVal);
  if (raw === null) return;

  const parsed = Number(String(raw).replace(/[$,]/g, "").trim());
  if (!Number.isFinite(parsed)) {
    alert("Enter a valid amount.");
    return;
  }

  let signed = parsed;
  if (current < 0 && parsed > 0) signed = -parsed;
  else if (current > 0 && parsed < 0) signed = Math.abs(parsed);

  await api("/api/spending/overrides", {
    method: "PUT",
    body: JSON.stringify({ txn_id: txnId, amount: signed }),
  });
}

async function refreshSpendingAfterTxnChange() {
  if (historyPeriodKey && spendView === "history-detail") {
    await openHistoryPeriod(historyPeriodKey);
  }
  if (activeTab === "spend") {
    await loadSpending(false, { silent: true });
  }
}

function bindExpenseTxnButtons(container) {
  if (!container) return;
  container.querySelectorAll(".txn-edit-btn").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      try {
        await editExpenseAmount(btn.dataset.txnId, btn.dataset.currentAmount, btn.dataset.description);
        await refreshSpendingAfterTxnChange();
      } catch (err) {
        alert(err.message);
      }
    });
  });
  container.querySelectorAll(".txn-exclude-btn").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const txnId = btn.dataset.txnId;
      const including = btn.classList.contains("txn-include-btn");
      try {
        await toggleExpenseExclusion(txnId, including);
        await refreshSpendingAfterTxnChange();
      } catch (err) {
        alert(err.message);
      }
    });
  });
}

function bindHistoryTxnButtons() {
  bindExpenseTxnButtons(historyDetailTxnsList);
}

function setSpendView(view) {
  spendView = view;
  document.querySelectorAll(".spend-sub-tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.spendView === view);
  });
  const showActivity = view === "activity";
  const showHistory = view === "history";
  const showDetail = view === "history-detail";
  showActivity ? show(spendActivityView) : hide(spendActivityView);
  showHistory ? show(spendHistoryView) : hide(spendHistoryView);
  showDetail ? show(spendHistoryDetailView) : hide(spendHistoryDetailView);
  if (showHistory) loadSpendingHistory();
}

function renderHistoryList(data) {
  const periods = data.periods || [];
  if (!periods.length) {
    historyPeriodsList.innerHTML = "";
    return;
  }

  let html = "";
  let lastYear = null;
  for (const p of periods) {
    const year = p.label.split(", ").pop();
    if (year !== lastYear) {
      html += `<li class="history-year">${year}</li>`;
      lastYear = year;
    }
    const currentBadge = p.is_current ? '<span class="history-current-badge">Current</span>' : "";
    html += `
    <li class="holding history-period-row" data-period-key="${p.key}">
      <div class="holding-info">
        <div class="ticker">${p.label}</div>
        <div class="holding-meta">${currentBadge}</div>
      </div>
    </li>`;
  }
  historyPeriodsList.innerHTML = html;
  historyPeriodsList.querySelectorAll(".history-period-row").forEach((row) => {
    row.addEventListener("click", () => openHistoryPeriod(row.dataset.periodKey));
  });
}

function renderHistoryDetail(data) {
  const spend = data.spend || {};
  historyDetailTotalEl.textContent = formatMoney(spend.total_spend || 0);
  historyDetailLabelEl.textContent = data.label || "";
  historyDetailSharesEl.textContent = formatMoney(
    spend.splitwise_consumption ?? spend.splitwise_your_shares ?? 0,
  );
  historyDetailBankEl.textContent = formatMoney(spend.bank_spend || 0);
  historyDetailCardEl.textContent = formatMoney(spend.card_spend || 0);

  const parts = [];
  if (spend.plaid_matched_to_splitwise > 0) {
    parts.push(`${formatMoney(spend.plaid_matched_to_splitwise)} in bank/card charges linked to Splitwise (not double-counted).`);
  }
  if (spend.excluded_cc_payments > 0) {
    parts.push(`${formatMoney(spend.excluded_cc_payments)} in credit card bill payments excluded.`);
  }
  const userExcluded = (data.transactions || []).filter((t) => t.excluded_from_total).length;
  if (userExcluded > 0) {
    parts.push(`${userExcluded} expense${userExcluded === 1 ? "" : "s"} manually excluded from this total.`);
  }
  if (parts.length) {
    historyDetailExcludedEl.textContent = parts.join(" ");
    show(historyDetailExcludedEl);
  } else {
    hide(historyDetailExcludedEl);
  }

  historyDetailTxnsList.innerHTML = renderHistoryTransactionRows(data.transactions || [], data.logos || {});
  bindHistoryTxnButtons();
}

async function loadSpendingHistory() {
  try {
    const data = await api("/api/spending/history");
    renderHistoryList(data);
  } catch (err) {
    historyPeriodsList.innerHTML = `<li class="history-empty">${err.message}</li>`;
  }
}

async function openHistoryPeriod(periodKey) {
  historyPeriodKey = periodKey;
  setLoading(true);
  try {
    const data = await api(`/api/spending/history/${periodKey}`);
    renderHistoryDetail(data);
    spendView = "history-detail";
    hide(spendActivityView);
    hide(spendHistoryView);
    show(spendHistoryDetailView);
  } catch (err) {
    historyPeriodsList.innerHTML = `<li class="history-empty">${err.message}</li>`;
    setSpendView("history");
  } finally {
    setLoading(false);
  }
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

function setActiveTab(tab) {
  activeTab = tab;
  document.querySelectorAll(".tab-nav .tab:not(.disabled)").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === tab);
  });
}

function startSpendPolling() {
  stopSpendPolling();
  spendPollTimer = setInterval(() => {
    if (activeTab === "spend") loadSpending(true, { silent: true });
  }, SPEND_POLL_MS);
}

function stopSpendPolling() {
  if (spendPollTimer) {
    clearInterval(spendPollTimer);
    spendPollTimer = null;
  }
}

function showInvest() {
  stopSpendPolling();
  hide(settingsScreen);
  hide(spendingScreen);
  show(portfolioScreen);
  setActiveTab("invest");
}

function showSpend() {
  hide(settingsScreen);
  hide(portfolioScreen);
  show(spendingScreen);
  setActiveTab("spend");
  setSpendView("activity");
  startSpendPolling();
}

function showSettings(fromTab = activeTab) {
  stopSpendPolling();
  settingsReturnTab = fromTab;
  hide(portfolioScreen);
  hide(spendingScreen);
  show(settingsScreen);
  loadNotificationsSettings();
  loadSpendingSettings();
}

function showMainFromSettings() {
  if (settingsReturnTab === "spend") {
    showSpend();
    loadSpending(true);
  } else {
    showInvest();
  }
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

function resetSpendBudgetUI() {
  setText(spendBudgetRemainingEl, "—");
  setText(spendMonthLabelEl, "—");
  setText(spendBudgetUsedEl, "—");
  setText(spendCardEl, "—");
  setText(spendSplitwiseNetEl, "—");
  setText(spendBudgetTotalEl, "—");
  spendBudgetHeroEl?.classList.remove("over-budget");
  hide(spendBudgetBarEl);
}

function renderSpending(data) {
  const summary = data.summary || {};
  const logos = data.logos || {};
  const budget = summary.monthly_budget ?? 0;
  const used = summary.budget_used ?? 0;
  const remaining = summary.budget_remaining ?? budget;
  const cardSpend = summary.budget_card_spend ?? summary.by_source?.card ?? 0;
  const splitwiseNet = summary.budget_splitwise_net ?? 0;

  setText(spendBudgetRemainingEl, formatMoney(remaining));
  spendBudgetHeroEl?.classList.toggle("over-budget", remaining < 0);
  setText(
    spendMonthLabelEl,
    budget
      ? `${formatMoney(used)} used of ${formatMoney(budget)} · ${summary.month_label || "This period"}`
      : summary.month_label || "This period",
  );
  setText(spendBudgetUsedEl, formatMoney(used));
  setText(spendCardEl, formatMoney(cardSpend));
  setText(spendSplitwiseNetEl, formatSignedMoney(splitwiseNet));
  setText(spendBudgetTotalEl, formatMoney(budget));

  if (budget > 0 && spendBudgetBarEl && spendBudgetBarFillEl) {
    show(spendBudgetBarEl);
    const pct = Math.min(100, Math.max(0, (remaining / budget) * 100));
    spendBudgetBarFillEl.style.width = `${pct}%`;
    spendBudgetBarFillEl.classList.toggle("over", remaining < 0);
  } else {
    hide(spendBudgetBarEl);
  }

  hide(spendOverlapHint);

  const sourceLabels = {
    live: "Live",
    cache: "Cached",
    snapshot: "Saved snapshot",
    mock: "Mock data",
    empty: "No data",
  };
  const isLive = data.source === "live" || data.source === "cache" || data.source === "mock";
  spendStatusEl.classList.toggle("offline", !isLive || data.source === "empty");
  spendStatusTextEl.textContent = sourceLabels[data.source] || data.source;

  if (!data.transactions?.length) {
    transactionsList.innerHTML = "";
  } else {
    transactionsList.innerHTML = renderExpenseRows(data.transactions, logos);
    bindExpenseTxnButtons(transactionsList);
  }

  maybeNotifyNewSpend(data);

  spendUpdatedAtEl.textContent = data.updated_at
    ? `Updated ${formatTime(data.updated_at)}`
    : "";
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

function updateSpendingSettingsUI(status) {
  const connected = status.plaid_connected || status.splitwise_configured;
  spendingConnectionStatus.textContent = connected ? "On" : "Off";
  spendingConnectionStatus.classList.toggle("on", connected);

  if (status.plaid_connected) {
    const names = [...new Set((status.accounts || []).map((a) => a.institution_name).filter(Boolean))];
    plaidStatusText.textContent = names.length
      ? `Plaid: connected (${names.join(", ")})`
      : "Plaid: connected";
    connectPlaidBtn.textContent = "Connect another bank";
  } else if (status.plaid_configured) {
    plaidStatusText.textContent = "Plaid: ready — connect your accounts";
    connectPlaidBtn.textContent = "Connect bank & cards";
  } else {
    plaidStatusText.textContent = "Plaid: server not configured (add PLAID_CLIENT_ID to .env)";
    connectPlaidBtn.disabled = true;
  }

  splitwiseStatusText.textContent = status.splitwise_configured
    ? "Splitwise: configured"
    : "Splitwise: add your personal API key";

  if (monthlyBudgetInput && status.monthly_budget != null) {
    monthlyBudgetInput.value = String(status.monthly_budget);
  }
}

async function loadSpendingSettings() {
  hide(spendingSettingsHint);
  try {
    const status = await api("/api/spending/status");
    updateSpendingSettingsUI(status);
    connectPlaidBtn.disabled = !status.plaid_configured;
  } catch (err) {
    spendingSettingsHint.textContent = err.message;
    show(spendingSettingsHint);
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

async function loadSpending(refresh = false, { silent = false } = {}) {
  if (!silent) setLoading(true);
  try {
    const status = await api("/api/spending/status");
    const hasSource = status.plaid_connected || status.splitwise_configured || status.mock;
    if (!hasSource) {
      show(spendConnectBanner);
      transactionsList.innerHTML = "";
      resetSpendBudgetUI();
      spendStatusEl.classList.add("offline");
      spendStatusTextEl.textContent = "Not connected";
      spendUpdatedAtEl.textContent = "";
      hide(spendOverlapHint);
      return;
    }

    hide(spendConnectBanner);
    const params = new URLSearchParams();
    if (refresh) params.set("refresh", "true");
    params.set("_", String(Date.now()));
    const data = await api(`/api/spending/transactions?${params}`);
    renderSpending(data);
  } catch (err) {
    spendStatusEl.classList.add("offline");
    spendStatusTextEl.textContent = err.message;
  } finally {
    if (!silent) setLoading(false);
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

function loadPlaidScript() {
  if (window.Plaid) return Promise.resolve();
  if (plaidScriptPromise) return plaidScriptPromise;
  plaidScriptPromise = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "https://cdn.plaid.com/link/v2/stable/link-initialize.js";
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Plaid Link"));
    document.head.appendChild(script);
  });
  return plaidScriptPromise;
}

async function connectPlaid() {
  setLoading(true);
  hide(spendingSettingsHint);
  try {
    await loadPlaidScript();
    const { link_token: linkToken } = await api("/api/plaid/link-token", { method: "POST" });
    setLoading(false);

    const handler = window.Plaid.create({
      token: linkToken,
      onSuccess: async (publicToken) => {
        setLoading(true);
        try {
          await api("/api/plaid/exchange", {
            method: "POST",
            body: JSON.stringify({ public_token: publicToken }),
          });
          spendingSettingsHint.textContent = "Bank and cards connected.";
          show(spendingSettingsHint);
          await loadSpendingSettings();
          if (activeTab === "spend") await loadSpending(true);
        } catch (err) {
          spendingSettingsHint.textContent = err.message;
          show(spendingSettingsHint);
        } finally {
          setLoading(false);
        }
      },
      onExit: (err) => {
        if (err?.display_message) {
          spendingSettingsHint.textContent = err.display_message;
          show(spendingSettingsHint);
        }
      },
    });
    handler.open();
  } catch (err) {
    spendingSettingsHint.textContent = err.message;
    show(spendingSettingsHint);
    setLoading(false);
  }
}

async function saveMonthlyBudget() {
  const raw = monthlyBudgetInput?.value?.trim();
  const amount = raw === "" ? 0 : Number(raw);
  if (!Number.isFinite(amount) || amount < 0) {
    spendingSettingsHint.textContent = "Enter a valid budget amount.";
    show(spendingSettingsHint);
    return;
  }

  setLoading(true);
  hide(spendingSettingsHint);
  try {
    await api("/api/spending/budget", {
      method: "PUT",
      body: JSON.stringify({ monthly_budget: amount }),
    });
    spendingSettingsHint.textContent = "Budget saved.";
    show(spendingSettingsHint);
    await loadSpendingSettings();
    if (activeTab === "spend") await loadSpending(true);
  } catch (err) {
    spendingSettingsHint.textContent = err.message;
    show(spendingSettingsHint);
  } finally {
    setLoading(false);
  }
}

async function saveSplitwiseKey() {
  const apiKey = splitwiseKeyInput.value.trim();
  if (!apiKey) {
    spendingSettingsHint.textContent = "Enter a Splitwise API key.";
    show(spendingSettingsHint);
    return;
  }

  setLoading(true);
  hide(spendingSettingsHint);
  try {
    await api("/api/splitwise/configure", {
      method: "POST",
      body: JSON.stringify({ api_key: apiKey }),
    });
    splitwiseKeyInput.value = "";
    spendingSettingsHint.textContent = "Splitwise connected.";
    show(spendingSettingsHint);
    await loadSpendingSettings();
    if (activeTab === "spend") await loadSpending(true);
  } catch (err) {
    spendingSettingsHint.textContent = err.message;
    show(spendingSettingsHint);
  } finally {
    setLoading(false);
  }
}

async function checkAuth() {
  setLoading(true);
  try {
    const { authenticated } = await api("/api/me");
    if (authenticated) {
      hide(loginScreen);
      const params = new URLSearchParams(window.location.search);
      const openTab = params.get("tab");
      if (params.get("connected") === "1" || openTab) {
        window.history.replaceState({}, "", "/");
      }
      await registerServiceWorker();
      if (openTab === "spend") {
        showSpend();
        await loadSpending(true);
      } else {
        showInvest();
        await loadPortfolio(true);
      }
    } else {
      show(loginScreen);
      hide(portfolioScreen);
      hide(spendingScreen);
      hide(settingsScreen);
    }
  } catch {
    show(loginScreen);
    hide(portfolioScreen);
    hide(spendingScreen);
  } finally {
    setLoading(false);
  }
}

document.querySelectorAll(".tab-nav .tab:not(.disabled)").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const tab = btn.dataset.tab;
    if (tab === "invest") {
      showInvest();
      await loadPortfolio();
    } else if (tab === "spend") {
      showSpend();
      await loadSpending(true);
    }
  });
});

loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  hide(loginError);
  setLoading(true);
  try {
    await api("/api/login", { method: "POST", body: JSON.stringify({ pin: pinInput.value }) });
    pinInput.value = "";
    hide(loginScreen);
    showInvest();
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
spendRefreshBtn.addEventListener("click", () => {
  if (spendView === "history") loadSpendingHistory();
  else if (spendView === "history-detail" && historyPeriodKey) {
    openHistoryPeriod(historyPeriodKey);
  } else loadSpending(true);
});
settingsBtn.addEventListener("click", () => showSettings("invest"));
spendSettingsBtn.addEventListener("click", () => showSettings("spend"));
spendSettingsShortcut.addEventListener("click", () => showSettings("spend"));
settingsBackBtn.addEventListener("click", showMainFromSettings);
connectBtn.addEventListener("click", connectRobinhood);
connectPlaidBtn.addEventListener("click", connectPlaid);
saveSplitwiseBtn.addEventListener("click", saveSplitwiseKey);
saveBudgetBtn?.addEventListener("click", saveMonthlyBudget);
enableNotificationsBtn.addEventListener("click", enableNotifications);
testNotificationBtn.addEventListener("click", sendTestNotification);

document.querySelectorAll(".spend-sub-tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    if (btn.dataset.spendView === "activity") setSpendView("activity");
    else setSpendView("history");
  });
});
historyBackBtn.addEventListener("click", () => setSpendView("history"));

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible" && activeTab === "spend") {
    loadSpending(true, { silent: true });
  }
});

checkAuth();
