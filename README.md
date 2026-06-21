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
