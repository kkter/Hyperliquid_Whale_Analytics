# Hyperliquid Whale Analytics

A self-hosted pipeline and dashboard for exploring the public positions of accounts shown on a third-party Hyperliquid leaderboard.

## What it does

- Collects up to 20 leaderboard entries every four hours with Selenium
- Stores address, asset, rank and observation time as historical snapshots
- Polls Hyperliquid's public `clearinghouseState` endpoint every five minutes
- Normalizes position value, direction, unrealized PnL, leverage and entry price in SQLite
- Presents current positions, market-level summaries and rank history in a Flask dashboard

The application is read-only. It does not require wallet keys and does not submit transactions.

## Architecture

```text
Third-party leaderboard
        │ Selenium / Beautiful Soup (4-hour cycle)
        ▼
 leaderboard_snapshots ───────┐
 addresses                    │
                              ├──► SQLite ──► Flask + Chart.js
 Hyperliquid public API       │
        │ HTTP polling (5-minute cycle)
        ▼                     │
 position_details ────────────┘
```

Docker Compose runs three services from the same image:

| Service | Responsibility |
| --- | --- |
| `get_address` | Maintains the address registry and leaderboard snapshots |
| `update_positions` | Refreshes open-position details through the Hyperliquid API |
| `web` | Serves the dashboard and JSON endpoints with Gunicorn |

## Quick start

### Requirements

- Docker with the Compose plugin
- Internet access for the leaderboard and Hyperliquid API
- An existing Docker network named `app_network`

```bash
git clone https://github.com/kkter/Hyperliquid_Whale_Analytics.git
cd Hyperliquid_Whale_Analytics
docker network create app_network
mkdir -p data logs
docker compose up -d --build
```

Open `http://localhost:5000`.

If `app_network` already exists, skip the network-creation command. Inspect service output with:

```bash
docker compose logs -f
```

The repository contains a sample SQLite snapshot for immediate exploration. The running services persist subsequent data in `data/`.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
mkdir -p data logs
python get_address.py
```

Run `update_positions.py` and `app.py` in separate terminals after the address collector has initialized the database. The Flask development server uses port `5000`.

## Web routes

| Route | Purpose |
| --- | --- |
| `GET /` | Current leaderboard and position dashboard |
| `GET /whale/<address>` | Current positions for one tracked address |
| `GET /api/market_overview` | Aggregate position and sentiment data |
| `GET /api/whale_history/<address>` | Historical rank series for one address |

## Operational notes

- The leaderboard collector depends on the current third-party page structure and may require selector updates when that site changes.
- `webdriver-manager` downloads a compatible browser driver at runtime; production deployments should pin or preinstall the browser and driver for more predictable builds.
- Hyperliquid position data is public and changes continuously. The dashboard reflects the most recent successful polling cycle, not an execution-grade market feed.
- This project does not provide trading signals or financial advice.
