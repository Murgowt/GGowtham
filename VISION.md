# Brain — Vision & Roadmap

> Long-term context for humans and AI agents working on this repo.  
> Repo: [Murgowt/GGowtham](https://github.com/Murgowt/GGowtham) · Production: [web-production-6a751.up.railway.app](https://web-production-6a751.up.railway.app)

---

## Mission

**Brain is a personal financial brain** — one private app on your phone that knows your money in context and helps you act on it, not just view it.

Today it starts with investing (Robinhood USA). Over time it should connect spending, goals, and loans into a single intelligent layer that can answer questions, send timely nudges, and keep you aligned with what you actually care about.

---

## Aim

Build a **PIN-protected PWA** that:

1. **Aggregates** financial data you already have (brokerage, banks, cards, Splitwise, etc.) in read-only, privacy-first integrations.
2. **Understands** your portfolio, spending patterns, and stated goals together — not in silos.
3. **Acts** with useful notifications and suggestions at the right moment (daily summary today; per-purchase budget alerts tomorrow).
4. **Stays simple** on the surface — hero metrics, clear lists, settings — while the intelligence grows underneath.

Brain is for **one user** (personal tool), deployed cheaply ($0 tier: SnapTrade Free + Railway), optimized for **iPhone Home Screen** usage.

---

## Current State

### Invest vertical (V1 — live in production)

| Capability | Status |
|------------|--------|
| PIN-protected portfolio PWA (Safari → Add to Home Screen) | ✅ |
| Live Robinhood USA holdings via SnapTrade Personal key | ✅ |
| Portfolio UI: hero value, invested/return/holdings, allocation bars | ✅ |
| Settings page: push notification opt-in + Send test | ✅ |
| Daily push notification at 12:00 PM Central | ✅ |
| Railway deploy: web service (24/7) + brain-cron service | ✅ |

### Spend vertical (V1 — read-only, implemented)

| Capability | Status |
|------------|--------|
| Invest / Spend tab navigation | ✅ |
| Unified transaction timeline (Bank / Card / Splitwise tags) | ✅ |
| Monthly outflow hero + by-source breakdown | ✅ |
| Plaid Link for US bank + credit cards | ✅ |
| Splitwise personal API key in Settings | ✅ |
| Mock spending data when `MOCK_INTEGRATIONS=true` | ✅ |
| SQLite cache (`SpendingSnapshot`, `PlaidItem`) | ✅ |

**Not in Spend V1:** auto-categorization, budgets, dedupe Splitwise↔card, spending push notifications.

### Architecture (critical invariants)

| Component | Role |
|-----------|------|
| **web** | FastAPI + uvicorn, SQLite, SnapTrade, push subscriptions |
| **brain-cron** | `start.sh` → `python -m jobs.trigger_daily` → HTTP POST to web app |
| **start.sh** | If service name contains `cron` → trigger_daily; else uvicorn |

**Cron must NOT run uvicorn or `jobs.daily_summary` directly.** Subscriptions live on the web DB only. Cron calls:

- `POST /api/notifications/cron/daily` — portfolio summary push
- `POST /api/notifications/cron/test` — simple ping

Auth: header `X-Cron-Secret: <CRON_SECRET>` (must match on web and brain-cron).

### Integrations

- **SnapTrade** — Personal signed-request flow (not OAuth browser flow). Robinhood connected on production.
- **Plaid** — Link token + exchange; `/transactions/get` for read-only US bank and credit card activity.
- **Splitwise** — Personal API key; `GET /get_expenses` for user's share of group expenses.
- **Web Push** — VAPID keys, service worker, subscribe/test/cron endpoints (portfolio daily summary only).

### Persistence

- SQLite on web service. **Volume at `/data`** + `DATABASE_URL=sqlite:////data/brain.db` recommended so push subscriptions survive redeploys.

### Key files

| Path | Purpose |
|------|---------|
| `main.py` | FastAPI app, `/sw.js`, routers |
| `integrations/snaptrade.py` | Portfolio fetch |
| `integrations/spending.py` | Unified spending aggregator + mock |
| `integrations/plaid_client.py` | Plaid Link, transactions |
| `integrations/splitwise_client.py` | Splitwise expenses |
| `integrations/daily_summary.py` | Format + send daily push |
| `integrations/webpush.py` | pywebpush + VAPID |
| `api/spending.py` | spending, plaid, splitwise routes |
| `api/notifications.py` | subscribe, test, cron/daily, cron/test |
| `jobs/trigger_daily.py` | Cron HTTP caller (supports `--dry-run`) |
| `start.sh` | Web vs cron start command |
| `static/app.js` | UI, settings, notifications |

### Local dev

```bash
cd /Users/gowthampollam/Desktop/Brain
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

Test cron against production: `./scripts/test_cron.sh curl` (needs `CRON_SECRET` in `.env`).

---

## Future Plans

The north star comes from three pillars: **Investing**, **Spending**, and **Goals**. They converge into an intelligent, contextual assistant.

```
                    ┌─────────────────┐
                    │     GOALS       │
                    │  (north star)   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │ Investing│  │ Spending │  │  Loans   │
        │ portfolio│  │ CC/bank  │  │  future  │
        │ watchlist│  │ Splitwise│  │  plans   │
        └──────────┘  └──────────┘  └──────────┘
                             │
                             ▼
              Intelligent Brain — full context,
              per-purchase nudges, Q&A with goals in mind
```

### 1. Investing

- **Analyze current investments** — news, price action, and targets tied to each holding.
- **Watchlist** — track names you care about even when you don't hold them; keep momentum on ideas.
- **Portfolio management** — explicit **Safe ↔ Risk** posture; Brain helps you stay within the band you choose.
- **Tighter link to goals** — investments aren't abstract; they connect to loans, future plans, and what you're saving for.

### 2. Spending

- **Access** — credit cards, bank accounts, Splitwise (and similar) in read-only aggregation.
- **Analyze & categorize** — automatic grouping of transactions; trends over time.
- **Suggest control** — proactive guidance on where spending is drifting, not just charts after the fact.

### 3. Goals

- **Intelligent brain with contextual knowledge** — every answer uses the full picture: holdings, cash flow, budgets, and stated goals.
- **Per-purchase awareness** — after a purchase, Brain notifies: *"You have $X left in [category] budget — be careful."*
- **Conversational layer** — ask anything; responses respect goals, not generic finance tips.

---

## Phased Roadmap

Rough sequencing for implementation. Each phase should stay shippable and useful on its own.

### V2 — Smarter investing (next)

- Price alerts (±% moves on holdings or watchlist).
- AI portfolio analysis — news + price action + targets summarized per holding.
- Watchlist (first-class UI + data model).
- Optional: Indian brokerage accounts via SnapTrade or other aggregators.

### V3 — Spending (enhancements beyond V1 read-only)

- Auto transaction categorization and budget envelopes
- Dedupe Splitwise ↔ card charges
- Spending vs. goal dashboards
- Spending push notifications

### V3b — Spending V1 shipped

- Bank / credit card via Plaid Link ✅
- Splitwise personal API key ✅
- Unified read-only timeline ✅

### V4 — Goals & intelligent nudges

- User-defined goals (amount, deadline, priority).
- Loan tracking and "future plans" linkage to portfolio and spending.
- Contextual Q&A over full financial graph.
- Real-time budget notifications on individual purchases.

### Infrastructure (when needed)

- Postgres or libSQL instead of SQLite volume (multi-device, richer queries).
- Background job queue for analysis (beyond single cron HTTP trigger).
- Secrets and env vars stay in Railway / `.env` — never committed.

---

## Principles for Agents & Contributors

1. **Privacy first** — read-only integrations; no storing broker passwords; PIN + single-user scope.
2. **Cron calls web, never the DB directly** — push subscriptions and portfolio state live on the web service database.
3. **PWA-first** — test on iPhone Home Screen, not only desktop Safari tabs.
4. **Ship incrementally** — each feature should work in production before layering AI or new data sources.
5. **Mock off in production** — `MOCK_INTEGRATIONS=false` when SnapTrade is configured.
6. **Preserve working V1** — new phases add modules; don't break daily push, SnapTrade, or PIN auth.

---

## Troubleshooting Quick Reference

| Symptom | Likely fix |
|---------|------------|
| Mock data on Railway | `MOCK_INTEGRATIONS=false` + SnapTrade vars on web |
| Cron stuck "Running" | brain-cron must run `start.sh` / `trigger_daily`, not uvicorn |
| No push after redeploy | Re-enable in Settings; add Railway volume at `/data` |
| Cron URL error | `APP_BASE_URL` = `https://web-production-6a751.up.railway.app` only (no `APP_BASE_URL=` prefix) |
| Cron 401 | `CRON_SECRET` mismatch between web and brain-cron |
| Infinite loading | Force-quit app; hard refresh; check SnapTrade/API |

---

*Last updated: June 2025 — Invest V1 live; Spend V1 read-only shipped locally.*
