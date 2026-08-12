"""Refresh tracked-wallet positions from Hyperliquid's official info API."""

from __future__ import annotations

import math
import os
import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from database import db_session, initialize_database, record_sync_status, utc_now


HYPERLIQUID_API_URL = os.getenv("HYPERLIQUID_API_URL", "https://api.hyperliquid.xyz/info")
POLLING_INTERVAL_SECONDS = int(os.getenv("POSITION_POLL_SECONDS", "300"))
REQUEST_TIMEOUT = (5, 20)


def build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.75,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"POST"}),
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({"Content-Type": "application/json", "User-Agent": "whale-analytics/2.0"})
    return session


def get_addresses_to_track() -> list[str]:
    with db_session() as connection:
        rows = connection.execute("SELECT address FROM addresses ORDER BY first_seen").fetchall()
    return [row["address"] for row in rows]


def _parse_position(raw: dict[str, Any]) -> dict[str, float | str] | None:
    position = raw.get("position")
    if not isinstance(position, dict):
        return None
    try:
        size_in_asset = float(position.get("szi", 0))
        if size_in_asset == 0:
            return None
        leverage_data = position.get("leverage") or {}
        return {
            "asset": str(position["coin"]),
            "position_size_usd": math.copysign(float(position["positionValue"]), size_in_asset),
            "unrealized_pnl": float(position["unrealizedPnl"]),
            "leverage": float(leverage_data["value"]),
            "entry_price": float(position["entryPx"]),
        }
    except (KeyError, TypeError, ValueError, OverflowError):
        return None


def fetch_position_details_from_api(
    address: str, session: requests.Session | None = None
) -> list[dict[str, float | str]] | None:
    """Return positions, or None when the request/response is not trustworthy."""
    client = session or build_session()
    try:
        response = client.post(
            HYPERLIQUID_API_URL,
            json={"type": "clearinghouseState", "user": address},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        raw_positions = payload.get("assetPositions") if isinstance(payload, dict) else None
        if not isinstance(raw_positions, list):
            raise ValueError("response has no assetPositions list")
        return [position for raw in raw_positions if (position := _parse_position(raw)) is not None]
    except (requests.RequestException, ValueError) as exc:
        print(f"Official API refresh failed for {address[:10]}…: {exc}")
        return None


def replace_address_positions(address: str, positions: list[dict[str, float | str]]) -> None:
    """Publish one successful address response in a short atomic transaction."""
    refreshed_at = utc_now()
    assets = [str(position["asset"]) for position in positions]
    with db_session() as connection:
        connection.execute("BEGIN IMMEDIATE")
        for position in positions:
            connection.execute(
                """
                INSERT INTO position_details
                    (whale_address, asset, position_size_usd, unrealized_pnl,
                     leverage, entry_price, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(whale_address, asset) DO UPDATE SET
                    position_size_usd = excluded.position_size_usd,
                    unrealized_pnl = excluded.unrealized_pnl,
                    leverage = excluded.leverage,
                    entry_price = excluded.entry_price,
                    last_updated = excluded.last_updated
                """,
                (
                    address,
                    position["asset"],
                    position["position_size_usd"],
                    position["unrealized_pnl"],
                    position["leverage"],
                    position["entry_price"],
                    refreshed_at,
                ),
            )
        if assets:
            placeholders = ",".join("?" for _ in assets)
            connection.execute(
                f"DELETE FROM position_details WHERE whale_address = ? AND asset NOT IN ({placeholders})",
                (address, *assets),
            )
        else:
            connection.execute("DELETE FROM position_details WHERE whale_address = ?", (address,))
        connection.commit()


def run_update_cycle(session: requests.Session | None = None) -> tuple[int, int]:
    addresses = get_addresses_to_track()
    if not addresses:
        record_sync_status("hyperliquid", False, "no tracked addresses")
        print("No tracked addresses are available; the existing database is unchanged.")
        return 0, 0

    client = session or build_session()
    succeeded = 0
    failed = 0
    for address in addresses:
        positions = fetch_position_details_from_api(address, client)
        if positions is None:
            failed += 1
        else:
            replace_address_positions(address, positions)
            succeeded += 1
            print(f"Updated {len(positions)} position(s) for {address[:10]}…")
        time.sleep(0.2)

    if failed:
        record_sync_status("hyperliquid", False, f"{failed} of {len(addresses)} address requests failed")
    else:
        record_sync_status("hyperliquid", True)
    return succeeded, failed


def main() -> None:
    initialize_database()
    run_once = os.getenv("RUN_ONCE", "0").lower() in {"1", "true", "yes"}
    while True:
        print("Starting Hyperliquid position refresh cycle…")
        succeeded, failed = run_update_cycle()
        print(f"Refresh complete: {succeeded} succeeded, {failed} failed.")
        if run_once:
            raise SystemExit(1 if failed and not succeeded else 0)
        time.sleep(POLLING_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
