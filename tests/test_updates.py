import tempfile
import unittest
from pathlib import Path

import requests

import database
import update_positions


TEST_ADDRESS = "0x1111111111111111111111111111111111111111"


class FailingSession:
    def post(self, *_args, **_kwargs):
        raise requests.ConnectionError("offline")


class UpdateTests(unittest.TestCase):
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
                VALUES (?, 'BTC', 1000, 25, 5, 50000, '2026-01-01T00:00:00+00:00')
                """,
                (TEST_ADDRESS,),
            )
            connection.commit()

    def tearDown(self):
        database.DATABASE_FILE = self.previous_database
        self.temporary.cleanup()

    def test_failed_api_response_preserves_last_successful_position(self):
        succeeded, failed = update_positions.run_update_cycle(FailingSession())
        self.assertEqual((succeeded, failed), (0, 1))
        with database.db_session() as connection:
            position = connection.execute(
                "SELECT asset, position_size_usd FROM position_details WHERE whale_address = ?",
                (TEST_ADDRESS,),
            ).fetchone()
        self.assertEqual((position["asset"], position["position_size_usd"]), ("BTC", 1000))

    def test_successful_empty_response_clears_closed_positions(self):
        update_positions.replace_address_positions(TEST_ADDRESS, [])
        with database.db_session() as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM position_details WHERE whale_address = ?", (TEST_ADDRESS,)
            ).fetchone()[0]
        self.assertEqual(count, 0)

    def test_position_value_uses_asset_size_direction(self):
        parsed = update_positions._parse_position(
            {
                "position": {
                    "coin": "ETH",
                    "szi": "-2",
                    "positionValue": "5000",
                    "unrealizedPnl": "100",
                    "leverage": {"value": 5},
                    "entryPx": "2500",
                }
            }
        )
        self.assertEqual(parsed["position_size_usd"], -5000)


if __name__ == "__main__":
    unittest.main()
