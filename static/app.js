const loginScreen = document.getElementById("login-screen");
const portfolioScreen = document.getElementById("portfolio-screen");
const budgetScreen = document.getElementById("budget-screen");
const goalsScreen = document.getElementById("goals-screen");
const settingsScreen = document.getElementById("settings-screen");
const loginForm = document.getElementById("login-form");
const pinInput = document.getElementById("pin-input");
const loginError = document.getElementById("login-error");
const refreshBtn = document.getElementById("refresh-btn");
const settingsBtn = document.getElementById("settings-btn");
const budgetRefreshBtn = document.getElementById("budget-refresh-btn");
const budgetSettingsBtn = document.getElementById("budget-settings-btn");
const settingsBackBtn = document.getElementById("settings-back-btn");
const connectBtn = document.getElementById("connect-btn");
const connectAddInvestmentBtn = document.getElementById("connect-add-investment-btn");
const connectBanner = document.getElementById("connect-banner");
const spendConnectBanner = document.getElementById("spend-connect-banner");
const budgetSettingsShortcut = document.getElementById("budget-settings-shortcut");
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
const budgetSpendView = document.getElementById("budget-spend-view");
const budgetIncomeView = document.getElementById("budget-income-view");
const incomePinGate = document.getElementById("income-pin-gate");
const incomePinForm = document.getElementById("income-pin-form");
const incomePinInput = document.getElementById("income-pin-input");
const incomePinError = document.getElementById("income-pin-error");
const incomeContent = document.getElementById("income-content");
const incomeTextarea = document.getElementById("income-textarea");
const incomeSaveBtn = document.getElementById("income-save-btn");
const incomeSaveStatus = document.getElementById("income-save-status");
const incomeSummaryCard = document.getElementById("income-summary-card");
const incomeSummaryText = document.getElementById("income-summary-text");
const incomeAllocationChips = document.getElementById("income-allocation-chips");
const incomeExtractionFailed = document.getElementById("income-extraction-failed");
const goalsListView = document.getElementById("goals-list-view");
const goalsEditorView = document.getElementById("goals-editor-view");
const goalsListEl = document.getElementById("goals-list");
const goalsAddBtn = document.getElementById("goals-add-btn");
const goalsEditorBack = document.getElementById("goals-editor-back");
const goalTextarea = document.getElementById("goal-textarea");
const goalSaveBtn = document.getElementById("goal-save-btn");
const goalDeleteBtn = document.getElementById("goal-delete-btn");
const goalSaveStatus = document.getElementById("goal-save-status");
const goalSummaryCard = document.getElementById("goal-summary-card");
const goalSummaryText = document.getElementById("goal-summary-text");
const goalExtractionFailed = document.getElementById("goal-extraction-failed");
const addInvestmentBtn = document.getElementById("add-investment-btn");
const investmentFormScreen = document.getElementById("investment-form-screen");
const investmentFormBack = document.getElementById("investment-form-back");
const investmentFormTitle = document.getElementById("investment-form-title");
const investmentTypePicker = document.getElementById("investment-type-picker");
const investmentForm = document.getElementById("investment-form");
const investmentIdInput = document.getElementById("investment-id");
const investmentTypeInput = document.getElementById("investment-type");
const investmentNameInput = document.getElementById("investment-name");
const investmentInvestedInput = document.getElementById("investment-invested");
const investmentFdFields = document.getElementById("investment-fd-fields");
const investmentMfFields = document.getElementById("investment-mf-fields");
const investmentStockFields = document.getElementById("investment-stock-fields");
const fdPrincipalInput = document.getElementById("fd-principal");
const fdRateInput = document.getElementById("fd-rate");
const fdStartDateInput = document.getElementById("fd-start-date");
const fdMaturityDateInput = document.getElementById("fd-maturity-date");
const fdBankInput = document.getElementById("fd-bank");
const mfSearchInput = document.getElementById("mf-search");
const mfSearchResults = document.getElementById("mf-search-results");
const mfSchemeCodeInput = document.getElementById("mf-scheme-code");
const mfSelectedEl = document.getElementById("mf-selected");
const mfUnitsInput = document.getElementById("mf-units");
const mfPurchaseNavInput = document.getElementById("mf-purchase-nav");
const stockSymbolInput = document.getElementById("stock-symbol");
const stockQuantityInput = document.getElementById("stock-quantity");
const stockAvgBuyInput = document.getElementById("stock-avg-buy");
const investmentFormError = document.getElementById("investment-form-error");
const investmentSaveBtn = document.getElementById("investment-save-btn");
const investmentDeleteBtn = document.getElementById("investment-delete-btn");
const fxRateEl = document.getElementById("fx-rate");

let activeTab = "invest";
let budgetView = "spend";
let incomeUnlocked = false;
let incomeSessionPin = "";
let editingGoalId = null;
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
  budgetRefreshBtn?.classList.toggle("refreshing", on && activeTab === "budget");
}

function formatMoney(n) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);
}

function formatInr(n) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(n);
}

function formatInrSigned(n) {
  if (n > 0) return `+${formatInr(n)}`;
  if (n < 0) return `−${formatInr(Math.abs(n))}`;
  return formatInr(0);
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

const APP_TIMEZONE = "America/Chicago";

function formatTime(iso) {
  const d = new Date(iso);
  return d.toLocaleString("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: APP_TIMEZONE,
  });
}

function formatBudgetLeftLine(budgetRemaining) {
  return `${formatMoney(budgetRemaining).replace(/\.00$/, "")} left`;
}

function spendingAlertTone(budgetUsed, budgetRemaining, description) {
  if (budgetRemaining <= 0) return "IDIOT STOP!!!";
  if (budgetUsed > 1500) return "STOP!!!";
  if (budgetUsed > 1000) return "Be careful!!";
  const desc = String(description || "").trim();
  if (!desc) return "Okay!!";
  const label = desc.length > 24 ? `${desc.slice(0, 21)}…` : desc;
  return `Okay ${label}!!`;
}

function formatSpendAlertBody(txn, summary) {
  const remaining = Number(summary?.budget_remaining) || 0;
  const used = Number(summary?.budget_used) || 0;
  return {
    title: formatBudgetLeftLine(remaining),
    body: spendingAlertTone(used, remaining, txn.description),
  };
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
  const summary = data.summary || {};
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
    const alert = formatSpendAlertBody(txn, summary);
    new Notification(alert.title, {
      body: alert.body,
      icon: "/static/icon-192.png",
      tag: key,
    });
  }
}

function formatShortDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    timeZone: APP_TIMEZONE,
  });
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

function escapeHtml(text) {
  return String(text ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function setBudgetView(view) {
  budgetView = view;
  if (view === "income") {
    incomeUnlocked = false;
    incomeSessionPin = "";
    lockIncomeView();
  }
  document.querySelectorAll(".budget-sub-tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.budgetView === view);
  });
  if (view === "spend") {
    show(budgetSpendView);
    hide(budgetIncomeView);
  } else {
    hide(budgetSpendView);
    show(budgetIncomeView);
  }
}

function lockIncomeView() {
  show(incomePinGate);
  hide(incomeContent);
  if (incomePinInput) incomePinInput.value = "";
  hide(incomePinError);
}

function renderIncomeProfile(data) {
  if (incomeTextarea) incomeTextarea.value = data.raw_text || "";
  if (data.summary) {
    setText(incomeSummaryText, data.summary);
    show(incomeSummaryCard);
    hide(incomeExtractionFailed);
  } else if (data.extraction_status === "failed") {
    hide(incomeSummaryCard);
    show(incomeExtractionFailed);
  } else {
    hide(incomeSummaryCard);
    hide(incomeExtractionFailed);
  }
  const allocations = data.allocations || [];
  if (incomeAllocationChips) {
    incomeAllocationChips.innerHTML = allocations.map((a) => {
      const label = String(a.label || "bucket").replace(/_/g, " ");
      const pct = Number(a.pct) || 0;
      return `<span class="allocation-chip">${escapeHtml(label)} ${pct}%</span>`;
    }).join("");
  }
}

async function unlockIncome(pin) {
  hide(incomePinError);
  setLoading(true);
  try {
    const data = await api("/api/budget/income/unlock", {
      method: "POST",
      body: JSON.stringify({ pin }),
    });
    incomeUnlocked = true;
    incomeSessionPin = pin;
    hide(incomePinGate);
    show(incomeContent);
    if (data.configured === false) {
      if (incomeTextarea) incomeTextarea.value = "";
      hide(incomeSummaryCard);
      hide(incomeExtractionFailed);
      if (incomeAllocationChips) incomeAllocationChips.innerHTML = "";
    } else {
      renderIncomeProfile(data);
    }
  } catch (err) {
    show(incomePinError);
    incomePinError.textContent = err.message;
    incomeUnlocked = false;
    incomeSessionPin = "";
  } finally {
    setLoading(false);
  }
}

async function saveIncome() {
  if (!incomeSessionPin) {
    alert("Unlock income with your PIN first.");
    return;
  }
  const text = incomeTextarea?.value?.trim();
  if (!text) {
    incomeSaveStatus.textContent = "Enter your paycheck and allocation plan.";
    show(incomeSaveStatus);
    return;
  }
  setLoading(true);
  hide(incomeSaveStatus);
  try {
    incomeSaveBtn.disabled = true;
    incomeSaveBtn.textContent = "Brain is reading…";
    const data = await api("/api/budget/income", {
      method: "PUT",
      body: JSON.stringify({ text, pin: incomeSessionPin }),
    });
    renderIncomeProfile(data);
    incomeSaveStatus.textContent = "Saved.";
    show(incomeSaveStatus);
  } catch (err) {
    incomeSaveStatus.textContent = err.message;
    show(incomeSaveStatus);
  } finally {
    incomeSaveBtn.disabled = false;
    incomeSaveBtn.textContent = "Save";
    setLoading(false);
  }
}

function renderGoalsList(goals) {
  if (!goalsListEl) return;
  if (!goals.length) {
    goalsListEl.innerHTML = "";
    return;
  }
  goalsListEl.innerHTML = goals.map((g) => `
    <div class="goal-card" data-goal-id="${g.id}">
      <div class="goal-card-title">${escapeHtml(g.title)}</div>
      <div class="goal-card-summary">${escapeHtml(g.summary || "Brain is still reading this goal.")}</div>
      <div class="goal-card-meta">Updated ${g.updated_at ? formatTime(g.updated_at) : "—"}</div>
      <div class="goal-card-actions">
        <button type="button" class="btn secondary goal-edit-btn" data-goal-id="${g.id}">Edit</button>
      </div>
    </div>
  `).join("");
  goalsListEl.querySelectorAll(".goal-card").forEach((card) => {
    card.addEventListener("click", (e) => {
      if (e.target.closest(".goal-edit-btn")) return;
      openGoalEditor(Number(card.dataset.goalId));
    });
  });
  goalsListEl.querySelectorAll(".goal-edit-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      openGoalEditor(Number(btn.dataset.goalId));
    });
  });
}

function showGoalsList() {
  show(goalsListView);
  hide(goalsEditorView);
  editingGoalId = null;
}

function showGoalEditor() {
  hide(goalsListView);
  show(goalsEditorView);
}

async function openGoalEditor(goalId = null) {
  editingGoalId = goalId;
  hide(goalSaveStatus);
  hide(goalSummaryCard);
  hide(goalExtractionFailed);
  if (goalId) {
    show(goalDeleteBtn);
    setLoading(true);
    try {
      const data = await api(`/api/goals/${goalId}`);
      goalTextarea.value = data.raw_text || "";
      if (data.summary) {
        setText(goalSummaryText, data.summary);
        show(goalSummaryCard);
      }
    } catch (err) {
      alert(err.message);
      return;
    } finally {
      setLoading(false);
    }
  } else {
    hide(goalDeleteBtn);
    goalTextarea.value = "";
  }
  showGoalEditor();
}

async function saveGoal() {
  const text = goalTextarea?.value?.trim();
  if (!text) {
    goalSaveStatus.textContent = "Enter your goal.";
    show(goalSaveStatus);
    return;
  }
  setLoading(true);
  hide(goalSaveStatus);
  try {
    goalSaveBtn.disabled = true;
    goalSaveBtn.textContent = "Brain is reading…";
    const data = editingGoalId
      ? await api(`/api/goals/${editingGoalId}`, { method: "PUT", body: JSON.stringify({ text }) })
      : await api("/api/goals", { method: "POST", body: JSON.stringify({ text }) });
    if (data.summary) {
      setText(goalSummaryText, data.summary);
      show(goalSummaryCard);
      hide(goalExtractionFailed);
    } else if (data.extraction_status === "failed") {
      hide(goalSummaryCard);
      show(goalExtractionFailed);
    }
    goalSaveStatus.textContent = "Saved.";
    show(goalSaveStatus);
    editingGoalId = data.id;
    show(goalDeleteBtn);
    await loadGoals();
  } catch (err) {
    goalSaveStatus.textContent = err.message;
    show(goalSaveStatus);
  } finally {
    goalSaveBtn.disabled = false;
    goalSaveBtn.textContent = "Save";
    setLoading(false);
  }
}

async function deleteGoal() {
  if (!editingGoalId) return;
  if (!window.confirm("Delete this goal?")) return;
  setLoading(true);
  try {
    await api(`/api/goals/${editingGoalId}`, { method: "DELETE" });
    showGoalsList();
    await loadGoals();
  } catch (err) {
    alert(err.message);
  } finally {
    setLoading(false);
  }
}

async function loadGoals() {
  try {
    const data = await api("/api/goals");
    renderGoalsList(data.goals || []);
  } catch (err) {
    if (goalsListEl) goalsListEl.innerHTML = `<p class="goal-empty">${escapeHtml(err.message)}</p>`;
  }
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
  if (activeTab === "budget" && budgetView === "spend") {
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
  let pollCount = 0;
  spendPollTimer = setInterval(() => {
    if (activeTab !== "budget" || budgetView !== "spend") return;
    pollCount += 1;
    loadSpending(pollCount % 4 === 0, { silent: true });
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
  hide(budgetScreen);
  hide(goalsScreen);
  show(portfolioScreen);
  setActiveTab("invest");
}

function showBudget() {
  hide(settingsScreen);
  hide(portfolioScreen);
  hide(goalsScreen);
  show(budgetScreen);
  setActiveTab("budget");
  setBudgetView(budgetView === "income" ? "income" : "spend");
  startSpendPolling();
}

function showGoals() {
  stopSpendPolling();
  hide(settingsScreen);
  hide(portfolioScreen);
  hide(budgetScreen);
  show(goalsScreen);
  setActiveTab("goals");
  showGoalsList();
  loadGoals();
}

function showSettings(fromTab = activeTab) {
  stopSpendPolling();
  settingsReturnTab = fromTab;
  hide(portfolioScreen);
  hide(budgetScreen);
  hide(goalsScreen);
  show(settingsScreen);
  loadNotificationsSettings();
  loadSpendingSettings();
}

function showMainFromSettings() {
  if (settingsReturnTab === "budget") {
    showBudget();
    loadSpendingSWR();
  } else if (settingsReturnTab === "goals") {
    showGoals();
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

function holdingMetaLine(h) {
  if (h.type === "fd" && h.meta?.maturity_date) {
    const onTrack = h.meta.on_track_inr ? formatInr(h.meta.on_track_inr) : "";
    return `Est. close today · On track ${onTrack} · Matures ${h.meta.maturity_date}`;
  }
  if (h.region === "IN") {
    const unitLabel = h.type === "mf" ? "units" : "sh";
    return `${h.shares} ${unitLabel}${h.stale ? " · stale quote" : ""}`;
  }
  return `${h.shares} sh`;
}

function holdingBucket(h) {
  if (h.type === "fd") return "fd";
  if (h.type === "mf") return "mf";
  if (h.type === "stock") return "india";
  return "us";
}

const HOLDINGS_SECTIONS = [
  { key: "us", title: "US stocks" },
  { key: "india", title: "Indian stocks" },
  { key: "mf", title: "Mutual funds" },
  { key: "fd", title: "Fixed Deposit" },
];

function renderHoldingRow(h, totalValue) {
  const alloc = totalValue ? (h.value / totalValue) * 100 : 0;
  const inrLine = h.region === "IN" && h.value_inr != null
    ? `<div class="holding-inr">${formatInr(h.value_inr)} · ${formatInrSigned(h.pnl_inr || 0)}</div>`
    : "";
  const editable = h.source === "manual" ? ` data-investment-id="${h.id}"` : "";
  return `
    <li class="holding${h.source === "manual" ? " holding-manual" : ""}"${editable}>
      <div class="ticker-badge">${tickerBadge(h.ticker)}</div>
      <div class="holding-info">
        <div class="ticker">${h.ticker}</div>
        <div class="holding-meta">
          <span class="shares">${holdingMetaLine(h)}</span>
          <div class="allocation-bar" title="${alloc.toFixed(1)}% of portfolio">
            <div class="allocation-fill" style="width: ${Math.max(alloc, 2)}%"></div>
          </div>
        </div>
        ${inrLine}
      </div>
      <div class="holding-right">
        <div class="value">${formatMoney(h.value)}</div>
        <div class="pnl">${formatPnl(h.pnl, h.pnl_pct)}</div>
      </div>
    </li>`;
}

function renderHoldingsGroups(holdings, totalValue) {
  const buckets = { us: [], india: [], mf: [], fd: [] };
  for (const h of holdings) {
    buckets[holdingBucket(h)].push(h);
  }

  return HOLDINGS_SECTIONS
    .filter(({ key }) => buckets[key].length > 0)
    .map(({ key, title }) => `
      <section class="holdings-group">
        <p class="holdings-group-title">${title}</p>
        <ul class="holdings">
          ${buckets[key].map((h) => renderHoldingRow(h, totalValue)).join("")}
        </ul>
      </section>`)
    .join("");
}

function renderPortfolio(data) {
  if (investmentFormScreen && !investmentFormScreen.classList.contains("hidden")) {
    return;
  }
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
    "live+manual": "Live · Robinhood + India",
    cache: "Cached",
    "cache+manual": "Cached + India",
    snapshot: "Saved snapshot",
    mock: "Mock data",
    "mock+manual": "Mock + India",
    manual: "India · Manual",
  };
  const isLive = ["live", "cache", "live+manual", "cache+manual", "manual"].includes(data.source);
  statusEl.classList.toggle("offline", !isLive);
  statusTextEl.textContent = sourceLabels[data.source] || data.source;

  if (data.fx_rate && fxRateEl) {
    show(fxRateEl);
    const fxDate = data.fx_as_of ? formatTime(data.fx_as_of).split(",")[0] : "";
    fxRateEl.textContent = `USD/INR ${Number(data.fx_rate).toFixed(2)}${fxDate ? ` · ${fxDate}` : ""}`;
  } else {
    hide(fxRateEl);
  }

  holdingsList.innerHTML = renderHoldingsGroups(data.holdings, data.total_value);

  holdingsList.querySelectorAll(".holding-manual").forEach((el) => {
    el.addEventListener("click", () => {
      const id = el.dataset.investmentId;
      if (id) openInvestmentEditor(Number(id));
    });
  });

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

let mfSearchTimer = null;

function resetInvestmentForm() {
  investmentForm?.reset();
  if (investmentIdInput) investmentIdInput.value = "";
  if (investmentTypeInput) investmentTypeInput.value = "";
  if (mfSchemeCodeInput) mfSchemeCodeInput.value = "";
  if (mfSearchResults) mfSearchResults.innerHTML = "";
  hide(mfSelectedEl);
  hide(investmentFormError);
  hide(investmentDeleteBtn);
  investmentForm?.classList.add("hidden");
  investmentTypePicker?.classList.remove("hidden");
  [investmentFdFields, investmentMfFields, investmentStockFields].forEach((el) => hide(el));
}

function showInvestmentTypeFields(type) {
  [investmentFdFields, investmentMfFields, investmentStockFields].forEach((el) => hide(el));
  if (type === "fd") show(investmentFdFields);
  if (type === "mf") show(investmentMfFields);
  if (type === "stock") show(investmentStockFields);
}

function openInvestmentForm(type = null, investment = null) {
  resetInvestmentForm();
  portfolioScreen?.querySelector(".holdings-section")?.classList.add("hidden");
  portfolioScreen?.querySelector(".hero-card")?.classList.add("hidden");
  portfolioScreen?.querySelector(".metrics-row")?.classList.add("hidden");
  portfolioScreen?.querySelector(".footer")?.classList.add("hidden");
  portfolioScreen?.querySelector("#connect-banner")?.classList.add("hidden");
  show(investmentFormScreen);
  window.scrollTo(0, 0);

  if (investment) {
    setText(investmentFormTitle, "Edit investment");
    investmentIdInput.value = String(investment.id);
    investmentTypeInput.value = investment.type;
    investmentNameInput.value = investment.name;
    investmentInvestedInput.value = investment.invested_inr;
    hide(investmentTypePicker);
    show(investmentForm);
    showInvestmentTypeFields(investment.type);
    show(investmentDeleteBtn);

    const d = investment.details || {};
    if (investment.type === "fd") {
      fdPrincipalInput.value = d.principal || investment.invested_inr;
      fdRateInput.value = d.rate || "";
      fdStartDateInput.value = d.start_date || "";
      fdMaturityDateInput.value = d.maturity_date || "";
      fdBankInput.value = d.bank || "HDFC";
    } else if (investment.type === "mf") {
      mfSchemeCodeInput.value = d.scheme_code || "";
      mfUnitsInput.value = d.units || "";
      mfPurchaseNavInput.value = d.purchase_nav || "";
      if (d.scheme_name) {
        mfSelectedEl.textContent = d.scheme_name;
        show(mfSelectedEl);
      }
    } else if (investment.type === "stock") {
      stockSymbolInput.value = (d.symbol || "").replace(/\.(NS|BO)$/i, "");
      stockQuantityInput.value = d.quantity || "";
      stockAvgBuyInput.value = d.avg_buy_price || "";
    }
    return;
  }

  setText(investmentFormTitle, "Add investment");
  if (type) {
    investmentTypeInput.value = type;
    hide(investmentTypePicker);
    show(investmentForm);
    showInvestmentTypeFields(type);
    if (type === "fd") fdBankInput.value = "HDFC";
  }
}

function closeInvestmentForm() {
  hide(investmentFormScreen);
  portfolioScreen?.querySelector(".holdings-section")?.classList.remove("hidden");
  portfolioScreen?.querySelector(".hero-card")?.classList.remove("hidden");
  portfolioScreen?.querySelector(".metrics-row")?.classList.remove("hidden");
  portfolioScreen?.querySelector(".footer")?.classList.remove("hidden");
  resetInvestmentForm();
}

async function openInvestmentEditor(id) {
  try {
    const investment = await api(`/api/investments/${id}`);
    openInvestmentForm(null, investment);
  } catch (err) {
    statusTextEl.textContent = err.message;
  }
}

function buildInvestmentPayload() {
  const type = investmentTypeInput.value;
  const invested = Number(investmentInvestedInput.value);
  const details = {};

  if (type === "fd") {
    details.principal = Number(fdPrincipalInput.value || invested);
    details.rate = Number(fdRateInput.value);
    details.start_date = fdStartDateInput.value;
    details.maturity_date = fdMaturityDateInput.value;
    details.bank = fdBankInput.value.trim() || "HDFC";
    details.compounding = "quarterly";
    details.penalty_pct = 1.0;
  } else if (type === "mf") {
    details.scheme_code = Number(mfSchemeCodeInput.value);
    details.scheme_name = mfSelectedEl.textContent || investmentNameInput.value.trim();
    details.units = Number(mfUnitsInput.value);
    const nav = Number(mfPurchaseNavInput.value);
    if (nav > 0) details.purchase_nav = nav;
  } else if (type === "stock") {
    details.symbol = stockSymbolInput.value.trim().toUpperCase();
    details.exchange = "NSE";
    details.quantity = Number(stockQuantityInput.value);
    details.avg_buy_price = Number(stockAvgBuyInput.value);
  }

  return {
    type,
    name: investmentNameInput.value.trim(),
    invested_inr: invested,
    details,
  };
}

async function saveInvestment(e) {
  e.preventDefault();
  hide(investmentFormError);
  setLoading(true);
  try {
    const payload = buildInvestmentPayload();
    const id = investmentIdInput.value;
    if (id) {
      await api(`/api/investments/${id}`, { method: "PUT", body: JSON.stringify(payload) });
    } else {
      await api("/api/investments", { method: "POST", body: JSON.stringify(payload) });
    }
    closeInvestmentForm();
    await loadPortfolio(true);
  } catch (err) {
    investmentFormError.textContent = err.message;
    show(investmentFormError);
  } finally {
    setLoading(false);
  }
}

async function deleteInvestment() {
  const id = investmentIdInput.value;
  if (!id || !window.confirm("Delete this investment?")) return;
  setLoading(true);
  try {
    await api(`/api/investments/${id}`, { method: "DELETE" });
    closeInvestmentForm();
    await loadPortfolio(true);
  } catch (err) {
    investmentFormError.textContent = err.message;
    show(investmentFormError);
  } finally {
    setLoading(false);
  }
}

async function searchMfSchemes(query) {
  if (!query || query.length < 2) {
    mfSearchResults.innerHTML = "";
    return;
  }
  try {
    const { schemes } = await api(`/api/investments/mf/search?q=${encodeURIComponent(query)}`);
    mfSearchResults.innerHTML = schemes.map((s) => `
      <li>
        <button type="button" class="mf-result-btn" data-code="${s.scheme_code}" data-name="${s.scheme_name.replace(/"/g, "&quot;")}">
          ${s.scheme_name}
        </button>
      </li>`).join("");
    mfSearchResults.querySelectorAll(".mf-result-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        mfSchemeCodeInput.value = btn.dataset.code;
        mfSelectedEl.textContent = btn.dataset.name;
        show(mfSelectedEl);
        if (!investmentNameInput.value.trim()) {
          investmentNameInput.value = btn.dataset.name.slice(0, 80);
        }
        mfSearchResults.innerHTML = "";
        mfSearchInput.value = "";
      });
    });
  } catch {
    mfSearchResults.innerHTML = "";
  }
}

async function loadPortfolio(refresh = false, { silent = false } = {}) {
  if (!silent) setLoading(true);
  try {
    const data = await api(`/api/portfolio${refresh ? "?refresh=true" : ""}`);
    if (!data.has_holdings) {
      show(connectBanner);
      holdingsList.innerHTML = "";
      clearSummary();
      updatedAtEl.textContent = "";
      hide(fxRateEl);
      statusEl.classList.add("offline");
      statusTextEl.textContent = data.manual_count > 0 ? "Unable to load" : "Not connected";
      return;
    }
    if (!data.connected && data.manual_count > 0) {
      hide(connectBanner);
    }
    renderPortfolio(data);
  } catch (err) {
    if (err.message.includes("not connected") || err.message.includes("Connect Robinhood")) {
      show(connectBanner);
      holdingsList.innerHTML = "";
      clearSummary();
      updatedAtEl.textContent = "";
      hide(fxRateEl);
    }
    statusEl.classList.add("offline");
    statusTextEl.textContent = err.message;
  } finally {
    if (!silent) setLoading(false);
  }
}

async function loadPortfolioSWR() {
  await loadPortfolio(false);
  loadPortfolio(true, { silent: true }).catch(() => {});
}

async function loadSpending(refresh = false, { silent = false } = {}) {
  if (!silent) setLoading(true);
  try {
    const params = new URLSearchParams();
    if (refresh) params.set("refresh", "true");
    const data = await api(`/api/spending/transactions?${params}`);
    const hasSource = data.plaid_connected || data.splitwise_configured || data.mock;
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
    renderSpending(data);
  } catch (err) {
    spendStatusEl.classList.add("offline");
    spendStatusTextEl.textContent = err.message;
  } finally {
    if (!silent) setLoading(false);
  }
}

async function loadSpendingSWR() {
  await loadSpending(false);
  loadSpending(true, { silent: true }).catch(() => {});
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
          if (activeTab === "budget") await loadSpending(true);
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
    if (activeTab === "budget") await loadSpending(true);
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
    if (activeTab === "budget") await loadSpending(true);
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
      if (openTab === "spend" || openTab === "budget") {
        showBudget();
        await loadSpendingSWR();
      } else if (openTab === "goals") {
        showGoals();
      } else {
        showInvest();
        await loadPortfolioSWR();
      }
    } else {
      show(loginScreen);
      hide(portfolioScreen);
      hide(budgetScreen);
      hide(goalsScreen);
      hide(settingsScreen);
    }
  } catch {
    show(loginScreen);
    hide(portfolioScreen);
    hide(budgetScreen);
    hide(goalsScreen);
  } finally {
    setLoading(false);
  }
}

document.querySelectorAll(".tab-nav .tab:not(.disabled)").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const tab = btn.dataset.tab;
    if (tab === "invest") {
      showInvest();
      await loadPortfolioSWR();
    } else if (tab === "budget") {
      showBudget();
      if (budgetView === "spend") await loadSpendingSWR();
    } else if (tab === "goals") {
      showGoals();
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
    await loadPortfolioSWR();
  } catch {
    show(loginError);
    loginError.textContent = "Invalid PIN";
  } finally {
    setLoading(false);
  }
});

refreshBtn.addEventListener("click", () => loadPortfolio(true));
budgetRefreshBtn?.addEventListener("click", () => {
  if (budgetView === "spend") loadSpending(true);
});
settingsBtn.addEventListener("click", () => showSettings("invest"));
budgetSettingsBtn?.addEventListener("click", () => showSettings("budget"));
budgetSettingsShortcut?.addEventListener("click", () => showSettings("budget"));
settingsBackBtn.addEventListener("click", showMainFromSettings);
connectBtn.addEventListener("click", connectRobinhood);
connectAddInvestmentBtn?.addEventListener("click", () => openInvestmentForm());
addInvestmentBtn?.addEventListener("click", () => openInvestmentForm());
investmentFormBack?.addEventListener("click", closeInvestmentForm);
investmentForm?.addEventListener("submit", saveInvestment);
investmentDeleteBtn?.addEventListener("click", deleteInvestment);
investmentTypePicker?.querySelectorAll(".investment-type-btn").forEach((btn) => {
  btn.addEventListener("click", () => openInvestmentForm(btn.dataset.type));
});
mfSearchInput?.addEventListener("input", () => {
  clearTimeout(mfSearchTimer);
  mfSearchTimer = setTimeout(() => searchMfSchemes(mfSearchInput.value.trim()), 300);
});
connectPlaidBtn.addEventListener("click", connectPlaid);
saveSplitwiseBtn.addEventListener("click", saveSplitwiseKey);
saveBudgetBtn?.addEventListener("click", saveMonthlyBudget);
enableNotificationsBtn.addEventListener("click", enableNotifications);
testNotificationBtn.addEventListener("click", sendTestNotification);

document.querySelectorAll(".budget-sub-tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    setBudgetView(btn.dataset.budgetView);
    if (btn.dataset.budgetView === "spend") loadSpendingSWR();
  });
});

incomePinForm?.addEventListener("submit", async (e) => {
  e.preventDefault();
  await unlockIncome(incomePinInput.value);
  incomePinInput.value = "";
});

incomeSaveBtn?.addEventListener("click", saveIncome);
goalsAddBtn?.addEventListener("click", () => openGoalEditor(null));
goalsEditorBack?.addEventListener("click", showGoalsList);
goalSaveBtn?.addEventListener("click", saveGoal);
goalDeleteBtn?.addEventListener("click", deleteGoal);

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible" && activeTab === "budget" && budgetView === "spend") {
    loadSpending(false, { silent: true });
  }
});

checkAuth();
