# Hyperliquid Whale Analytics

A self-hosted data pipeline and Flask dashboard for studying the public positions of accounts listed on a third-party Hyperliquid leaderboard.

The project combines scheduled browser-based collection, Hyperliquid's public information API, SQLite persistence and server-rendered visualizations. It is a read-only analytics project: it does not connect a wallet or place trades.

## Documentation

- [English](README.en.md)
- [中文](README.zh.md)

## Data flow

```text
Leaderboard page ──► address snapshots ─┐
                                        ├──► SQLite ──► Flask dashboard
Hyperliquid API ──► current positions ──┘
```

## Stack

Python · Flask · SQLite · Selenium · Beautiful Soup · Hyperliquid API · Docker Compose · Gunicorn

## Disclaimer

This project is for engineering demonstration and research. Public position data is not financial advice, and upstream pages or APIs may change without notice.
