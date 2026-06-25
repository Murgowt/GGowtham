# Brain V1

Personal PWA that reads your Robinhood USA portfolio via [SnapTrade](https://snaptrade.com). Open in Safari on iPhone and Add to Home Screen.

## Features

- Read-only Robinhood holdings via SnapTrade (no Robinhood password stored)
- PIN-protected web app
- One-time Robinhood connect flow
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

## Cost

$0 — SnapTrade Free plan (1 user) + Railway free tier.

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
| Start command | `python -m jobs.trigger_daily` |
| Cron schedule | `30 21 * * 1-5` (4:30 PM ET weekdays, UTC) |
| Env vars | `APP_BASE_URL`, `CRON_SECRET` only (plus shared vars if needed) |

`trigger_daily` POSTs to `/api/notifications/cron/daily` on your web app, which reads subscriptions and sends the push.

**Test manually:** Railway → cron service → Deploy, then check logs for `Response 200`.

**Test every 5 minutes:** set cron schedule to `*/5 * * * *` (Railway minimum interval). Switch back to `30 21 * * 1-5` when done testing.

**Or from terminal:**

```bash
curl -X POST "https://your-app.up.railway.app/api/notifications/cron/daily" \
  -H "X-Cron-Secret: your-cron-secret"
```
