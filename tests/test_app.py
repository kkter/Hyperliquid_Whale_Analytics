import tempfile
import unittest
from pathlib import Path

import database
import app as dashboard


TEST_ADDRESS = "0x2222222222222222222222222222222222222222"


class AppTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.previous_database = database.DATABASE_FILE
        database.DATABASE_FILE = Path(self.temporary.name) / "whales.db"
        database.initialize_database()
        with database.db_session() as connection:
            connection.execute("INSERT INTO addresses (address) VALUES (?)", (TEST_ADDRESS,))
            connection.execute(
                """
                INSERT INTO position_details
                    (whale_address, asset, position_size_usd, unrealized_pnl,
                     leverage, entry_price, last_updated)
                VALUES (?, 'ETH', -5000, 100, 5, 2500, '2026-08-12T00:00:00+00:00')
                """,
                (TEST_ADDRESS,),
            )
            connection.commit()
        self.client = dashboard.app.test_client()

    def tearDown(self):
        database.DATABASE_FILE = self.previous_database
        self.temporary.cleanup()

    def test_health_and_dashboard_use_official_position_data_without_rank(self):
        health = self.client.get("/healthz")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.get_json()["positions"], 1)

        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"ETH", page.data)
        self.assertIn(b"Optional Rank", page.data)

    def test_market_overview_and_address_validation(self):
        overview = self.client.get("/api/market_overview")
        self.assertEqual(overview.status_code, 200)
        self.assertEqual(overview.get_json()["kpi_cards"]["total_whales"], 1)
        self.assertEqual(self.client.get("/whale/not-an-address").status_code, 404)


if __name__ == "__main__":
    unittest.main()
