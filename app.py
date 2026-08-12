"""Web dashboard backed by the last successful official API refresh."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from flask import Flask, abort, jsonify, render_template, request
from werkzeug.middleware.proxy_fix import ProxyFix

from database import db_session, initialize_database


ADDRESS_PATTERN = re.compile(r"0x[a-fA-F0-9]{40}")
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
initialize_database()


@app.after_request
def add_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response


@app.get("/")
def index():
    with db_session() as connection:
        positions = connection.execute(
            """
            SELECT
                (
                    SELECT ls.rank
                    FROM leaderboard_snapshots AS ls
                    WHERE ls.whale_address = pd.whale_address
                      AND ls.asset = pd.asset
                    ORDER BY ls.scrape_time DESC, ls.id DESC
                    LIMIT 1
                ) AS rank,
                pd.asset,
                pd.whale_address,
                pd.position_size_usd,
                pd.unrealized_pnl,
                pd.leverage,
                pd.entry_price,
                pd.last_updated,
                CASE WHEN pd.position_size_usd > 0 THEN 'Long' ELSE 'Short' END AS direction
            FROM position_details AS pd
            ORDER BY ABS(pd.position_size_usd) DESC
            LIMIT 200
            """
        ).fetchall()
        status = connection.execute(
            "SELECT last_success, last_error FROM sync_status WHERE component = 'hyperliquid'"
        ).fetchone()
        latest_position = connection.execute(
            "SELECT MAX(last_updated) FROM position_details"
        ).fetchone()[0]
    return render_template(
        "index.html",
        positions=positions,
        last_success=status["last_success"] if status else latest_position,
        sync_warning=status["last_error"] if status else None,
    )


@app.get("/whale/<address>")
def whale_profile(address: str):
    if not ADDRESS_PATTERN.fullmatch(address):
        abort(404)
    normalized_address = address.lower()
    with db_session() as connection:
        whale = connection.execute(
            "SELECT * FROM addresses WHERE address = ?", (normalized_address,)
        ).fetchone()
        if whale is None:
            abort(404)
        current_positions = connection.execute(
            """
            SELECT *,
                CASE WHEN position_size_usd > 0 THEN 'Long' ELSE 'Short' END AS direction
            FROM position_details
            WHERE whale_address = ?
            ORDER BY ABS(position_size_usd) DESC
            """,
            (normalized_address,),
        ).fetchall()
    return render_template("whale_profile.html", whale=whale, positions=current_positions)


@app.get("/api/whale_history/<address>")
def whale_history_api(address: str):
    if not ADDRESS_PATTERN.fullmatch(address):
        return jsonify({"error": "invalid wallet address"}), 400
    with db_session() as connection:
        history = connection.execute(
            """
            SELECT scrape_time, rank, asset
            FROM leaderboard_snapshots
            WHERE whale_address = ?
            ORDER BY scrape_time ASC, id ASC
            """,
            (address.lower(),),
        ).fetchall()
    datasets: dict[str, dict[str, list]] = {}
    for row in history:
        dataset = datasets.setdefault(row["asset"], {"labels": [], "data": []})
        dataset["labels"].append(row["scrape_time"])
        dataset["data"].append(row["rank"])
    return jsonify(datasets)


@app.get("/api/market_overview")
def market_overview_api():
    with db_session() as connection:
        kpi_row = connection.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM addresses) AS total_whales,
                COALESCE(SUM(position_size_usd), 0) AS net_sentiment,
                COALESCE(AVG(CASE WHEN leverage > 0 THEN leverage END), 0) AS avg_leverage
            FROM position_details
            """
        ).fetchone()
        asset_rows = connection.execute(
            """
            SELECT asset, SUM(ABS(position_size_usd)) AS total_value
            FROM position_details
            GROUP BY asset
            ORDER BY total_value DESC
            """
        ).fetchall()
        sentiment = connection.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN position_size_usd > 0 THEN position_size_usd ELSE 0 END), 0) AS long_value,
                COALESCE(SUM(CASE WHEN position_size_usd < 0 THEN ABS(position_size_usd) ELSE 0 END), 0) AS short_value
            FROM position_details
            """
        ).fetchone()
        sync_rows = connection.execute(
            "SELECT component, last_attempt, last_success, last_error FROM sync_status"
        ).fetchall()
    return jsonify(
        {
            "kpi_cards": dict(kpi_row),
            "asset_distribution": {
                "labels": [row["asset"] for row in asset_rows],
                "data": [row["total_value"] for row in asset_rows],
            },
            "market_sentiment": {
                "labels": ["Longs", "Shorts"],
                "data": [sentiment["long_value"], sentiment["short_value"]],
            },
            "sync_status": [dict(row) for row in sync_rows],
        }
    )


@app.get("/healthz")
def healthz():
    try:
        with db_session() as connection:
            integrity = connection.execute("PRAGMA quick_check").fetchone()[0]
            addresses = connection.execute("SELECT COUNT(*) FROM addresses").fetchone()[0]
            positions = connection.execute("SELECT COUNT(*) FROM position_details").fetchone()[0]
        if integrity != "ok" or addresses < 1:
            raise RuntimeError("database is not ready")
        return jsonify(
            {"status": "ok", "database": "ready", "addresses": addresses, "positions": positions}
        )
    except Exception as exc:
        app.logger.error("Health check failed: %s", exc)
        return jsonify({"status": "unhealthy", "database": "unavailable"}), 503


@app.get("/robots.txt")
def robots_txt():
    root = request.url_root.rstrip("/")
    return (
        f"User-agent: *\nAllow: /\nDisallow: /api/\n\nSitemap: {root}/sitemap.xml",
        200,
        {"Content-Type": "text/plain; charset=utf-8"},
    )


@app.get("/sitemap.xml")
def sitemap_xml():
    with db_session() as connection:
        whales = connection.execute("SELECT address FROM addresses ORDER BY address").fetchall()
    root = escape(request.url_root.rstrip("/"))
    today = datetime.now(timezone.utc).date().isoformat()
    urls = [
        f"<url><loc>{root}</loc><lastmod>{today}</lastmod><changefreq>hourly</changefreq><priority>1.0</priority></url>"
    ]
    urls.extend(
        f"<url><loc>{root}/whale/{escape(row['address'])}</loc><lastmod>{today}</lastmod><changefreq>daily</changefreq><priority>0.8</priority></url>"
        for row in whales
    )
    body = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>"
    return body, 200, {"Content-Type": "application/xml; charset=utf-8"}


def main() -> None:
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0").lower() in {"1", "true", "yes"}
    app.run(host="0.0.0.0", port=port, debug=debug)


if __name__ == "__main__":
    main()
