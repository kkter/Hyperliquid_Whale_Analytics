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
    # This query is updated to include a 'direction' field.
    positions = conn.execute('''
        SELECT
            ls.rank,
            ls.asset,
            ls.whale_address,
            pd.position_size_usd,
            pd.unrealized_pnl,
            pd.leverage,
            pd.entry_price,
            CASE
                WHEN pd.position_size_usd > 0 THEN 'Long'
                WHEN pd.position_size_usd < 0 THEN 'Short'
                ELSE 'N/A'
            END as direction
        FROM leaderboard_snapshots ls
        LEFT JOIN position_details pd ON ls.whale_address = pd.whale_address AND ls.asset = pd.asset
        WHERE ls.scrape_time = (SELECT MAX(scrape_time) FROM leaderboard_snapshots)
        ORDER BY ls.rank ASC
    ''').fetchall()

    conn.close()
    return render_template('index.html', positions=positions)

@app.route('/whale/<address>')
def whale_profile(address):
    """Page for a single whale's profile."""
    conn = get_db_connection()
    
    whale = conn.execute('SELECT * FROM addresses WHERE address = ?', (address,)).fetchone()
    
    # --- QUERY MODIFIED HERE ---
    # Add the CASE statement to determine position direction.
    current_positions = conn.execute('''
        SELECT *,
            CASE
                WHEN position_size_usd > 0 THEN 'Long'
                WHEN position_size_usd < 0 THEN 'Short'
                ELSE 'N/A'
            END as direction
        FROM position_details 
        WHERE whale_address = ? 
        ORDER BY ABS(position_size_usd) DESC
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

# --- NEW API ENDPOINT FOR OVERVIEW CHARTS ---
@app.route('/api/market_overview')
def market_overview_api():
    """API endpoint to provide data for the overview charts and KPIs."""
    conn = get_db_connection()

    # 1. Calculate KPIs
    kpi_cards = {
        'total_whales': conn.execute('SELECT COUNT(*) FROM addresses').fetchone()[0],
        'net_sentiment': conn.execute('SELECT SUM(position_size_usd) FROM position_details').fetchone()[0] or 0,
        'avg_leverage': conn.execute('SELECT AVG(leverage) FROM position_details WHERE leverage > 0').fetchone()[0] or 0
    }

    # 2. Calculate Asset Distribution for Pie Chart
    asset_dist_data = conn.execute('''
        SELECT asset, SUM(ABS(position_size_usd)) as total_value
        FROM position_details
        GROUP BY asset
        ORDER BY total_value DESC
    ''').fetchall()
    
    asset_distribution = {
        'labels': [row['asset'] for row in asset_dist_data],
        'data': [row['total_value'] for row in asset_dist_data]
    }

    # 3. Calculate Long vs Short for Doughnut Chart
    sentiment_data = conn.execute('''
        SELECT
            SUM(CASE WHEN position_size_usd > 0 THEN position_size_usd ELSE 0 END) as long_value,
            SUM(CASE WHEN position_size_usd < 0 THEN ABS(position_size_usd) ELSE 0 END) as short_value
        FROM position_details
    ''').fetchone()

    market_sentiment = {
        'labels': ['Longs', 'Shorts'],
        'data': [sentiment_data['long_value'] or 0, sentiment_data['short_value'] or 0]
    }

    conn.close()
    
    return jsonify({
        'kpi_cards': kpi_cards,
        'asset_distribution': asset_distribution,
        'market_sentiment': market_sentiment
    })


if __name__ == '__main__':
    app.run(debug=True)