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
3. Set environment variables:
   - `APP_PIN`, `SECRET_KEY`, `PRODUCTION=true`
   - `APP_BASE_URL=https://your-app.up.railway.app`
   - `SNAPTRADE_CLIENT_ID`, `SNAPTRADE_CONSUMER_KEY`
   - `MOCK_INTEGRATIONS=false`
4. After deploy, connect Robinhood once from the live URL

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
- Use the same Railway volume (`/data`) so Plaid tokens and Splitwise keys survive redeploys

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

Remove any **Custom Build Command** (`npm run build`) from the cron service.

The repo uses `start.sh`: if the service name contains `cron`, it runs `python -m jobs.trigger_daily` and exits. Your **web** service keeps running uvicorn.

If deploy logs show `Uvicorn running` on **brain-cron**, the service name must include `cron` (e.g. `brain-cron`).

### 4. Persist data across redeploys (recommended)

Railway wipes SQLite on each deploy. Add a **Volume** to your **web** service:

1. Mount path: `/data`
2. Set `DATABASE_URL=sqlite:////data/brain.db`

Then push subscriptions survive redeploys. Without a volume, tap **Enable notifications** again after each deploy.

```bash
curl -X POST "https://your-app.up.railway.app/api/notifications/cron/daily" \
  -H "X-Cron-Secret: your-cron-secret"
```
