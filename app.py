import sqlite3
from flask import Flask, render_template, jsonify

app = Flask(__name__)
DATABASE_FILE = 'whale_tracker.db'

def get_db_connection():
    """Creates a database connection that returns rows as dictionaries."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    """Main dashboard page."""
    conn = get_db_connection()
    
    # --- 1. Fetch data for the main leaderboard table ---
    # This query joins the latest leaderboard snapshot with detailed position info.
    positions = conn.execute('''
        SELECT
            ls.rank,
            ls.asset,
            ls.whale_address,
            pd.position_size_usd,
            pd.unrealized_pnl,
            pd.leverage,
            pd.entry_price,
            pd.last_updated
        FROM leaderboard_snapshots ls
        LEFT JOIN position_details pd ON ls.whale_address = pd.whale_address AND ls.asset = pd.asset
        WHERE ls.scrape_time = (SELECT MAX(scrape_time) FROM leaderboard_snapshots)
        ORDER BY ls.rank ASC
    ''').fetchall()

    # --- 2. Calculate KPIs for the Market Overview section ---
    kpi_cards = {
        'total_whales': conn.execute('SELECT COUNT(*) FROM addresses').fetchone()[0],
        'market_sentiment': conn.execute('SELECT SUM(position_size_usd) FROM position_details').fetchone()[0] or 0,
        'avg_leverage': conn.execute('SELECT AVG(leverage) FROM position_details WHERE leverage > 0').fetchone()[0] or 0
    }

    conn.close()
    return render_template('index.html', positions=positions, kpi_cards=kpi_cards)

@app.route('/whale/<address>')
def whale_profile(address):
    """Page for a single whale's profile."""
    conn = get_db_connection()
    
    # Fetch general info about the whale
    whale = conn.execute('SELECT * FROM addresses WHERE address = ?', (address,)).fetchone()
    
    # Fetch all current positions for this whale
    current_positions = conn.execute('''
        SELECT * FROM position_details 
        WHERE whale_address = ? 
        ORDER BY position_size_usd DESC
    ''', (address,)).fetchall()
    
    conn.close()
    return render_template('whale_profile.html', whale=whale, positions=current_positions)

@app.route('/api/whale_history/<address>')
def whale_history_api(address):
    """API endpoint to provide historical rank data for charts."""
    conn = get_db_connection()
    history = conn.execute('''
        SELECT scrape_time, rank, asset FROM leaderboard_snapshots
        WHERE whale_address = ?
        ORDER BY scrape_time ASC
    ''', (address,)).fetchall()
    conn.close()
    
    # Process data for Chart.js
    # We group data by asset to draw multiple lines on the chart
    datasets = {}
    for row in history:
        asset = row['asset']
        if asset not in datasets:
            datasets[asset] = {'labels': [], 'data': []}
        datasets[asset]['labels'].append(row['scrape_time'])
        datasets[asset]['data'].append(row['rank'])
        
    return jsonify(datasets)

if __name__ == '__main__':
    app.run(debug=True)