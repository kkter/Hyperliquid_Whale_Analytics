# Hyperliquid Whale Analytics

A self-hosted data pipeline and Flask dashboard for studying public Hyperliquid positions from a durable tracked-address registry.

The official Hyperliquid information API is the primary source. An optional browser collector can enrich the bundled address registry with third-party leaderboard ranks, but the site remains available when that collector fails. It is a read-only analytics project: it does not connect a wallet or place trades.

## Documentation

- [English](README.en.md)
- [中文](README.zh.md)

## Data flow

```text
Tracked addresses ──► Hyperliquid API ──► last-known-good positions ──► SQLite ──► Flask
      ▲
      └──── optional Coinglass rank enrichment (failure-tolerant)
```

## Stack

Python · Flask · SQLite · Selenium · Beautiful Soup · Hyperliquid API · Docker Compose · Gunicorn

## Disclaimer

This project is for engineering demonstration and research. Public position data is not financial advice, and upstream pages or APIs may change without notice.
