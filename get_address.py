"""Optional Coinglass leaderboard enrichment collector.

The dashboard and official Hyperliquid updater do not depend on this collector.
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from database import db_session, initialize_database, record_sync_status, utc_now


COINGLASS_URL = os.getenv("COINGLASS_URL", "https://www.coinglass.com/zh/hyperliquid")
MAX_ENTRIES_TO_SCRAPE = int(os.getenv("COINGLASS_MAX_ENTRIES", "20"))
SCRAPING_INTERVAL_SECONDS = int(os.getenv("COINGLASS_POLL_SECONDS", "14400"))
CHROME_BIN = os.getenv("CHROME_BIN", "/usr/bin/chromium")
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")
ADDRESS_PATTERN = re.compile(r"0x[a-fA-F0-9]{40}")


def _create_driver() -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1440,1200")
    options.add_argument(
        "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )
    if Path(CHROME_BIN).exists():
        options.binary_location = CHROME_BIN
    service = Service(CHROMEDRIVER_PATH) if Path(CHROMEDRIVER_PATH).exists() else Service()
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(45)
    return driver


def scrape_whale_data() -> list[dict[str, int | str]]:
    driver = None
    try:
        driver = _create_driver()
        driver.get(COINGLASS_URL)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "tr, a[href*='0x']"))
        )
        soup = BeautifulSoup(driver.page_source, "html.parser")
        scraped: list[dict[str, int | str]] = []
        seen: set[tuple[str, str]] = set()

        for row in soup.select("tr"):
            row_text = row.get_text(" ", strip=True)
            address_match = ADDRESS_PATTERN.search(
                " ".join(link.get("href", "") for link in row.select("a[href]")) + " " + row_text
            )
            if not address_match:
                continue
            cells = [cell.get_text(" ", strip=True) for cell in row.select("td")]
            rank_match = next((re.search(r"\b(\d{1,3})\b", cell) for cell in cells if re.search(r"\b\d{1,3}\b", cell)), None)
            if not rank_match:
                continue
            asset = cells[3].strip() if len(cells) > 3 else "Unknown"
            asset = asset.split()[0][:32] or "Unknown"
            address = address_match.group(0).lower()
            unique_key = (address, asset)
            if unique_key in seen:
                continue
            seen.add(unique_key)
            scraped.append({"rank": int(rank_match.group(1)), "asset": asset, "address": address})
            if len(scraped) >= MAX_ENTRIES_TO_SCRAPE:
                break
        return scraped
    except (TimeoutException, WebDriverException) as exc:
        print(f"Optional Coinglass scrape failed: {exc}")
        return []
    finally:
        if driver is not None:
            try:
                driver.quit()
            except WebDriverException:
                pass


def save_data_to_db(whale_data: list[dict[str, int | str]]) -> None:
    if not whale_data:
        raise ValueError("Coinglass returned no validated leaderboard rows")
    scrape_time = utc_now()
    with db_session() as connection:
        connection.execute("BEGIN IMMEDIATE")
        for item in whale_data:
            address = str(item["address"]).lower()
            if not ADDRESS_PATTERN.fullmatch(address):
                raise ValueError(f"invalid wallet address: {address}")
            connection.execute("INSERT OR IGNORE INTO addresses (address) VALUES (?)", (address,))
            connection.execute(
                """
                INSERT INTO leaderboard_snapshots
                    (scrape_time, rank, asset, whale_address)
                VALUES (?, ?, ?, ?)
                """,
                (scrape_time, int(item["rank"]), str(item["asset"]), address),
            )
        connection.commit()


def run_scrape_cycle() -> bool:
    data = scrape_whale_data()
    try:
        save_data_to_db(data)
        record_sync_status("coinglass", True)
        print(f"Saved {len(data)} optional leaderboard rows.")
        return True
    except ValueError as exc:
        record_sync_status("coinglass", False, str(exc))
        print(f"Coinglass enrichment unavailable; existing addresses remain active: {exc}")
        return False


def main() -> None:
    initialize_database()
    loop = os.getenv("COINGLASS_LOOP", "0").lower() in {"1", "true", "yes"}
    while True:
        run_scrape_cycle()
        if not loop:
            break
        time.sleep(SCRAPING_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
