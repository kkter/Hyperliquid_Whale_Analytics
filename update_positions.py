import sqlite3
import time
import requests
import math  # <-- Import the math library
from datetime import datetime

# --- Configuration ---
DATABASE_FILE = 'data/whale_tracker.db'
HYPERLIQUID_API_URL = "https://api.hyperliquid.xyz/info"
# The main loop will run every 5 minutes.
POLLING_INTERVAL_SECONDS = 300 

def setup_database():
    """Ensures the database and the 'position_details' table exist."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS position_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                whale_address TEXT NOT NULL,
                asset TEXT NOT NULL,
                position_size_usd REAL,
                unrealized_pnl REAL,
                leverage REAL,
                entry_price REAL,
                last_updated TIMESTAMP,
                FOREIGN KEY (whale_address) REFERENCES addresses (address),
                UNIQUE(whale_address, asset)
            )
        ''')
        conn.commit()
        print("Database table 'position_details' is ready.")
    finally:
        if conn:
            conn.close()

def get_addresses_to_track():
    """Fetches the list of unique whale addresses from the database."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT address FROM addresses")
        addresses = [row[0] for row in cursor.fetchall()]
        print(f"Found {len(addresses)} unique addresses to track.")
        return addresses
    except Exception as e:
        print(f"Error fetching addresses from DB: {e}")
        return []
    finally:
        if conn:
            conn.close()

def fetch_position_details_from_api(address):
    """
    Fetches all open positions for a single address from the Hyperliquid API.
    """
    print(f"Fetching details for {address[:10]}...")
    payload = {"type": "clearinghouseState", "user": address}
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(HYPERLIQUID_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        positions = []
        
        for item in data.get('assetPositions', []):
            pos_data = item.get('position')
            if pos_data and float(pos_data.get('szi', 0)) != 0:
                try:
                    # --- BUG FIX IS HERE ---
                    # 1. Get the size in asset to determine the direction (long/short)
                    size_in_asset = float(pos_data.get('szi', 0))
                    # 2. Get the absolute value of the position in USD
                    value_in_usd = float(pos_data['positionValue'])
                    # 3. Apply the sign from 'szi' to the 'positionValue'
                    signed_position_value = math.copysign(value_in_usd, size_in_asset)

                    position_details = {
                        'asset': pos_data['coin'],
                        'position_size_usd': signed_position_value, # Use the corrected signed value
                        'unrealized_pnl': float(pos_data['unrealizedPnl']),
                        'leverage': float(pos_data['leverage']['value']),
                        'entry_price': float(pos_data['entryPx']),
                    }
                    positions.append(position_details)
                except (KeyError, TypeError, ValueError) as e:
                    print(f"  - Could not parse a position for {address[:10]} asset {pos_data.get('coin', 'N/A')}. Error: {e}")
        
        return positions

    except requests.exceptions.RequestException as e:
        print(f"  - API request failed for {address[:10]}: {e}")
        return []

def update_position_details_in_db(address, position_data):
    """Saves or updates the detailed position data for a given address in the database."""
    if not position_data:
        # This is new: explicitly handle closing of positions
        # print(f"  - No open positions found for {address[:10]}. Checking for positions to clear.")
        return

    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        for position in position_data:
            sql = '''
                INSERT INTO position_details (whale_address, asset, position_size_usd, unrealized_pnl, leverage, entry_price, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(whale_address, asset) DO UPDATE SET
                    position_size_usd = excluded.position_size_usd,
                    unrealized_pnl = excluded.unrealized_pnl,
                    leverage = excluded.leverage,
                    entry_price = excluded.entry_price,
                    last_updated = excluded.last_updated;
            '''
            cursor.execute(sql, (
                address,
                position['asset'],
                position['position_size_usd'],
                position['unrealized_pnl'],
                position['leverage'],
                position['entry_price'],
                datetime.now()
            ))
        
        conn.commit()
        print(f"  - Successfully updated {len(position_data)} positions for address {address[:10]}...")
    except Exception as e:
        print(f"  - Database error for address {address}: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    setup_database()

    while True:
        print(f"\n--- Starting new update cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
        
        addresses = get_addresses_to_track()

        if not addresses:
            print("No addresses found in the database. Run get_address.py first.")
        else:
            for addr in addresses:
                details = fetch_position_details_from_api(addr)
                update_position_details_in_db(addr, details)
                time.sleep(1)

        print(f"--- Cycle finished. Waiting for {POLLING_INTERVAL_SECONDS} seconds... ---")
        time.sleep(POLLING_INTERVAL_SECONDS)