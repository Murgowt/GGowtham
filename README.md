# Brain V1

Personal PWA that reads your Robinhood USA portfolio via [SnapTrade](https://snaptrade.com). Open in Safari on iPhone and Add to Home Screen.

## Features

- Read-only Robinhood holdings via SnapTrade (no Robinhood password stored)
- Read-only spending: US bank + credit cards via Plaid, Splitwise via personal API key
- Unified spending timeline tagged Bank / Card / Splitwise
- PIN-protected web app with Invest and Spend tabs
- One-time Robinhood connect flow; Plaid Link for bank/cards
- Mock mode for development

## Local setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add SNAPTRADE_CLIENT_ID and SNAPTRADE_CONSUMER_KEY to .env
uvicorn main:app --reload --port 8000
```

Open http://localhost:8000 — default PIN is `1234` (change `APP_PIN` in `.env`).

## SnapTrade setup

1. Sign up at [dashboard.snaptrade.com](https://dashboard.snaptrade.com)
2. Verify email and select the **Free** plan
3. Create a Free API key → copy **Client ID** (`PERS-...`) and **Consumer Key**
4. Add to `.env`:

```bash
MOCK_INTEGRATIONS=false
SNAPTRADE_CLIENT_ID=your-client-id
SNAPTRADE_CONSUMER_KEY=your-consumer-key
APP_BASE_URL=http://localhost:8000
```

Personal keys use signed API requests (not OAuth). Brain auto-discovers your SnapTrade user on first connect — no separate SnapTrade sign-in step.

5. Open Brain → enter PIN → tap **Connect Robinhood**
6. Log in on Robinhood's site and approve access
7. You'll be redirected back — tap Refresh to load holdings

**Never commit your Consumer Key.** It is in `.gitignore` via `.env`.

## iPhone setup

1. Deploy to Railway (see below) or use local network URL
2. Open the URL in **Safari**
3. Enter PIN → Connect Robinhood (once)
4. **Share → Add to Home Screen** → name it **Brain**

## Deploy to Railway

1. Push to GitHub
2. [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. **Add persistent storage** (required — without this, Plaid banks and push subscriptions reset on every deploy):
   - **Option A — Volume (simplest):** Web service → Settings → Volumes → Add volume, mount path `/data`. Brain auto-uses `sqlite:////data/brain.db` on Railway.
   - **Option B — PostgreSQL:** Add a PostgreSQL plugin to the project. Railway sets `DATABASE_URL` automatically; Brain supports it out of the box.
4. Set environment variables on the **web** service:
   - `APP_PIN`, `SECRET_KEY`, `PRODUCTION=true`
   - `APP_BASE_URL=https://your-app.up.railway.app`
   - `SNAPTRADE_CLIENT_ID`, `SNAPTRADE_CONSUMER_KEY`
   - `MOCK_INTEGRATIONS=false`
   - Do **not** set `DATABASE_URL=sqlite:///./brain.db` on Railway — that path is wiped each deploy. Omit it (auto `/data`) or use PostgreSQL.
5. After deploy, connect Robinhood, Plaid, and notifications **once** — they persist across future deploys if step 3 is done.

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web UI |
| `/api/login` | POST | `{ "pin": "1234" }` |
| `/api/connection/status` | GET | SnapTrade connection state |
| `/api/connection/portal` | POST | Get Robinhood connect URL |
| `/api/portfolio` | GET | Holdings (auth + connected) |
| `/api/spending/status` | GET | Plaid/Splitwise connection state |
| `/api/spending/transactions` | GET | Unified spending feed (`?refresh=true`, `?days=30`) |
| `/api/plaid/link-token` | POST | Plaid Link token |
| `/api/plaid/exchange` | POST | `{ "public_token": "..." }` after Link |
| `/api/splitwise/configure` | POST | `{ "api_key": "..." }` personal API key |

## Spending (read-only)

### Plaid — bank and credit cards (US)

1. Create an app at [dashboard.plaid.com](https://dashboard.plaid.com) (Sandbox first, then Production Trial for live data)
2. Add to `.env` and Railway:

```bash
PLAID_CLIENT_ID=your-client-id
PLAID_SECRET=your-secret
PLAID_ENV=sandbox
MOCK_INTEGRATIONS=false
```

3. Open Brain → **Spend** tab → Settings → **Connect bank & cards**
4. Plaid Link supports checking, savings, and credit cards in one connection

### Splitwise

1. Register an app at [secure.splitwise.com/apps](https://secure.splitwise.com/apps)
2. Generate a **personal API key** on the app details page
3. Add to `.env` or paste in Settings → **Save Splitwise key**

```bash
SPLITWISE_API_KEY=your-key
```

### Notes

- V1 shows all sources in one timeline; Splitwise entries may overlap with card charges (dedupe planned later)
- Plaid Production Trial supports up to 10 linked accounts (enough for personal use)
- Plaid tokens, Splitwise keys saved in Settings, and push subscriptions all live in the database — use a Railway volume (`/data`) or PostgreSQL so they survive redeploys (see **Deploy to Railway**)

## Cost

$0 — SnapTrade Free plan (1 user) + Plaid Sandbox / Trial + Splitwise API + Railway free tier.

## Push notifications (iPhone)

Requires iOS 16.4+ and Brain opened from **Home Screen** (not Safari tabs).

### 1. Generate VAPID keys (once)

```bash
npx web-push generate-vapid-keys
```

Add to `.env` and Railway:

```bash
NOTIFICATIONS_ENABLED=true
VAPID_PUBLIC_KEY=your-public-key
VAPID_PRIVATE_KEY=your-private-key
VAPID_SUBJECT=mailto:you@example.com
CRON_SECRET=generate-a-long-random-string
```

### 2. Enable on iPhone

1. Open Brain from **Home Screen icon**
2. Settings (gear) → **Enable notifications** → Allow
3. Tap **Send test** to verify

### 3. Daily summary cron (Railway)

Push subscriptions live on the **web app’s database**. A separate cron container has its own empty SQLite file, so the cron job must **call the web app** instead of running `daily_summary` locally.

**On your main web service**, add `CRON_SECRET` (same value on both services).

Create a second **Cron** service from the same repo:

| Setting | Value |
|---------|--------|
| Config file | `/railway.cron.toml` (in service Settings) |
| Start command | `python -m jobs.trigger_daily` (set by config file) |
| Restart policy | **Never** |
| Cron schedule | `0 17 * * *` (12:00 PM Central during CDT — see below) |
| Env vars | `APP_BASE_URL`, `CRON_SECRET`, `CRON_MODE=daily` |

**12:00 PM Central (every day):** Railway cron uses UTC. Set schedule to:

| Season | Central time | UTC cron |
|--------|----------------|----------|
| Daylight (CDT, most of Mar–Nov) | 12:00 PM | `0 17 * * *` |
| Standard (CST, Nov–Mar) | 12:00 PM | `0 18 * * *` |

Switch the hour when clocks change, or accept ±1 hour during the other season.

For testing every 5 minutes, use `*/5 * * * *` and `CRON_MODE=test`.

### 3b. Spending budget alerts (Railway)

Get a push when a **new card charge** (including pending) or **Splitwise split** hits your budget. The notification shows the purchase and **budget remaining**.

Add a **third Cron** service (or reuse the test cron with a different schedule):

| Setting | Value |
|---------|--------|
| Start command | `python -m jobs.trigger_daily` |
| Config file | `/railway.spending.cron.toml` (in service Settings) |
| Cron schedule | `0 * * * *` (every hour, at :00 UTC) |
| Env vars | `APP_BASE_URL`, `CRON_SECRET`, **`CRON_MODE=spending`** |

Requires notifications enabled in Settings (same VAPID keys as portfolio). The first cron run **seeds** existing transactions without notifying (no flood). Tapping a notification opens the Spend tab.

```bash
curl -X POST "https://your-app.up.railway.app/api/notifications/cron/spending" \
  -H "X-Cron-Secret: your-cron-secret"
```

When the app is open on the Spend tab, it also polls every 15 seconds and shows a local notification immediately.

### 3c. Daily budget remaining (9 AM Central)

Every morning at **9:00 AM Central**, push your **remaining budget** for the current billing period (same `· $X left` format as purchase alerts). This always sends — even if nothing new was spent.

Add a **fourth Cron** service:

| Setting | Value |
|---------|--------|
| Start command | `python -m jobs.trigger_daily` |
| Config file | `/railway.budget-daily.cron.toml` (in service Settings) |
| Cron schedule | `0 14 * * *` (9:00 AM Central during CDT — see below) |
| Env vars | `APP_BASE_URL`, `CRON_SECRET`, **`CRON_MODE=budget_daily`** |

**9:00 AM Central (every day):** Railway cron uses UTC. Set schedule to:

| Season | Central time | UTC cron |
|--------|----------------|----------|
| Daylight (CDT, most of Mar–Nov) | 9:00 AM | `0 14 * * *` |
| Standard (CST, Nov–Mar) | 9:00 AM | `0 15 * * *` |

```bash
curl -X POST "https://your-app.up.railway.app/api/notifications/cron/budget-daily" \
  -H "X-Cron-Secret: your-cron-secret"
```

Remove any **Custom Build Command** (`npm run build`) from the cron service.

The repo uses `start.sh`: if the service name contains `cron`, it runs `python -m jobs.trigger_daily` and exits. Your **web** service keeps running uvicorn.

If deploy logs show `Uvicorn running` on **brain-cron**, the service name must include `cron` (e.g. `brain-cron`).

**Portfolio notifications every few seconds?** The spending cron service is probably using the **web** config (`/railway.toml`) instead of its own cron config. That sets **Restart policy: Always**, so the container restarts immediately after each run, calls `CRON_MODE=daily` (portfolio) in a loop, and floods your phone.

Fix on **Spending-cron** (and any other cron service):

1. **Settings → Config file path:** `/railway.spending.cron.toml` (not `/railway.toml`)
2. Confirm **Restart policy: Never**
3. Set **`CRON_MODE=spending`** (or rely on service name containing `spending`)
4. Redeploy

The web app also rate-limits portfolio summaries to **once per 20 hours** as a safety net.

### 4. Persist data across redeploys

Railway containers have ephemeral filesystems — a default SQLite file is deleted on every deploy, which clears Plaid banks and push subscriptions.

**Fix (pick one):**

1. **Volume:** Web service → Volumes → mount `/data`. Brain auto-switches to `sqlite:////data/brain.db` on Railway.
2. **PostgreSQL:** Add PostgreSQL to the project; Railway injects `DATABASE_URL`.

After adding storage, reconnect Plaid and enable notifications **one last time**. Later deploys keep that data.

Without persistent storage, tap **Enable notifications** again after each deploy.

```bash
curl -X POST "https://your-app.up.railway.app/api/notifications/cron/daily" \
  -H "X-Cron-Secret: your-cron-secret"
```
