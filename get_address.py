import sqlite3
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# --- Configuration ---
DATABASE_FILE = 'whale_tracker.db'
URL = "https://www.coinglass.com/zh/hyperliquid"
MAX_ENTRIES_TO_SCRAPE = 20

def setup_database():
    """Initializes the database and creates tables if they don't exist."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # Table for unique whale addresses.
        # This table acts as a central registry for all whales.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS addresses (
                address TEXT PRIMARY KEY,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT
            )
        ''')

        # Table for historical leaderboard snapshots.
        # This captures the state of the leaderboard at each scrape.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leaderboard_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scrape_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                rank INTEGER,
                asset TEXT,
                whale_address TEXT,
                FOREIGN KEY (whale_address) REFERENCES addresses (address)
            )
        ''')

        conn.commit()
        print(f"Database '{DATABASE_FILE}' is set up and ready.")
    finally:
        if conn:
            conn.close()

def scrape_whale_data():
    """
    Scrapes whale data from the specified URL using Selenium.
    Returns a list of dictionaries, each containing rank, asset, and address.
    """
    print("Setting up Selenium WebDriver...")
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

    driver = None
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        print(f"Navigating to {URL}...")
        driver.get(URL)

        print("Waiting for table data to load...")
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CLASS_NAME, "ant-table-row"))
        )
        time.sleep(3)  # Allow extra time for any final JS rendering

        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        rows = soup.find_all('tr', class_='ant-table-row')
        print(f"Found {len(rows)} potential data rows on the page.")

        scraped_data = []
        for row in rows:
            cells = row.find_all('td')
            if len(cells) > 3:
                try:
                    rank = cells[1].get_text(strip=True)
                    asset = cells[3].get_text(strip=True)
                    link_tag = cells[2].find('a')

                    if link_tag and link_tag.has_attr('href'):
                        href = link_tag['href']
                        address = href.split('/')[-1]
                        
                        if address.startswith('0x'):
                            scraped_data.append({'rank': rank, 'asset': asset, 'address': address})

                except (IndexError, AttributeError) as e:
                    print(f"Skipping a malformed row: {e}")
                    continue
            
            if len(scraped_data) >= MAX_ENTRIES_TO_SCRAPE:
                break
        
        return scraped_data

    finally:
        if driver:
            driver.quit()
            print("WebDriver has been closed.")

def save_data_to_db(whale_data):
    """Saves the scraped data into the SQLite database."""
    if not whale_data:
        print("No data to save.")
        return

    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        for item in whale_data:
            # First, ensure the address exists in the 'addresses' table.
            # 'INSERT OR IGNORE' is efficient: it does nothing if the address already exists.
            cursor.execute("INSERT OR IGNORE INTO addresses (address) VALUES (?)", (item['address'],))

            # Second, insert the full snapshot record into the 'leaderboard_snapshots' table.
            cursor.execute(
                "INSERT INTO leaderboard_snapshots (rank, asset, whale_address) VALUES (?, ?, ?)",
                (item['rank'], item['asset'], item['address'])
            )

        conn.commit()
        print(f"Successfully saved {len(whale_data)} records to the database.")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    try:
        # 1. Setup the database and tables
        setup_database()

        # 2. Scrape the data from the website
        latest_whale_data = scrape_whale_data()

        # 3. Save the scraped data to the database
        if latest_whale_data:
            save_data_to_db(latest_whale_data)
            print("\n--- Scraping Summary ---")
            for data in latest_whale_data:
                print(f"Rank: {data['rank']}, Asset: {data['asset']}, Address: {data['address']}")
        else:
            print("Scraping did not yield any data.")

    except Exception as e:
        print(f"\nAn unexpected error occurred in the main process: {e}")