# Hyperliquid Whale Analytics

A self-hosted pipeline and dashboard for exploring the public positions of tracked Hyperliquid accounts.

## What it does

- Uses the bundled address registry even when third-party leaderboard collection is unavailable
- Polls Hyperliquid's official `clearinghouseState` endpoint every five minutes with timeouts and retries
- Normalizes position value, direction, unrealized PnL, leverage and entry price in SQLite
- Preserves the last successful position for an address when an API request fails
- Clears closed positions only after a valid official response and publishes each address update atomically
- Optionally collects third-party ranks with Selenium for historical enrichment
- Uses SQLite WAL mode, busy timeouts, sync status and a production health endpoint

The application is read-only. It does not require wallet keys and does not submit transactions.

## Architecture

```text
address registry ──► official Hyperliquid API ──► last-known-good positions
       ▲                                                   │
       │                                                   ▼
optional Coinglass collector ──► rank history           SQLite ──► Flask
```

Docker Compose runs two services by default and exposes a third optional profile:

| Service | Responsibility |
| --- | --- |
| `coinglass_collector` | Optional `coinglass` profile for rank/address enrichment |
| `update_positions` | Refreshes open-position details through the Hyperliquid API |
| `web` | Serves the dashboard and JSON endpoints with Gunicorn |

## Quick start

### Requirements

- Docker with the Compose plugin
- Internet access for the Hyperliquid API

```bash
git clone https://github.com/kkter/Hyperliquid_Whale_Analytics.git
cd Hyperliquid_Whale_Analytics
docker compose up -d --build
```

Open `http://localhost:5103`.

Inspect service output with:

```bash
docker compose logs -f
```

The repository contains a refreshed SQLite snapshot and tracked addresses for immediate exploration. The running services persist subsequent data in `data/`.

The default deployment does not depend on Coinglass. To opt into its failure-tolerant browser collector:

```bash
docker compose --profile coinglass up -d
```

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
RUN_ONCE=1 python update_positions.py
python app.py
```

Run `update_positions.py` without `RUN_ONCE` in a separate terminal for continuous refreshes. `get_address.py` is optional.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_FILE` | `data/whale_tracker.db` | Persistent SQLite database |
| `POSITION_POLL_SECONDS` | `300` | Official API refresh interval |
| `WHALES_BIND_ADDRESS` | `127.0.0.1` | Docker host bind address |
| `WHALES_PORT` | `5103` | Docker host port |
| `COINGLASS_LOOP` | `0` | Repeat the optional collector |

## Web routes

| Route | Purpose |
| --- | --- |
| `GET /` | Current leaderboard and position dashboard |
| `GET /whale/<address>` | Current positions for one tracked address |
| `GET /api/market_overview` | Aggregate position and sentiment data |
| `GET /api/whale_history/<address>` | Historical rank series for one address |
| `GET /healthz` | Database readiness and integrity check |

## Operational notes

- The optional leaderboard collector depends on the current third-party page structure and may require selector updates. Its failure does not stop the dashboard or official API updater.
- Chromium and ChromeDriver are installed together from the Debian image repositories; no driver is downloaded at runtime.
- Hyperliquid position data is public and changes continuously. The dashboard reflects the most recent successful polling cycle, not an execution-grade market feed.
- This project does not provide trading signals or financial advice.
