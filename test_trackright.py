import sqlite3
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from inventory_store import InventoryStore


class InventoryStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = InventoryStore(Path(self.temp_dir.name) / "test.db")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def add_asset(self, serial: str = "TR-001") -> None:
        self.store.create_purchase(
            serial, "Laptop Model X", Decimal("1200.50"), "Brand New", "A. Buyer"
        )

    def test_purchase_creates_asset_and_initial_history_event(self) -> None:
        self.add_asset()

        state = self.store.current_state("TR-001")
        history = self.store.history("TR-001")

        self.assertEqual(state["to_location"], "Samar")
        self.assertEqual(state["destination_company"], "Internal Store")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0][1:6], (
            "Supplier / Vendor",
            "Samar",
            "Internal Store",
            "A. Buyer",
            "Brand New",
        ))

    def test_movement_uses_last_recorded_location_as_origin(self) -> None:
        self.add_asset()
        self.store.record_movement(
            "TR-001", "Office 2", "TrackRight", "B. Handler", "Good", "Relocation"
        )
        self.store.record_movement(
            "TR-001", "Client Site", "Client Co", "C. Handler", "Fair", "Deployment"
        )

        history = self.store.history("TR-001")
        state = self.store.current_state("TR-001")

        self.assertEqual(history[0][1:6], (
            "Office 2",
            "Client Site",
            "Client Co",
            "C. Handler",
            "Fair",
        ))
        self.assertEqual(state["to_location"], "Client Site")
        self.assertEqual(state["destination_company"], "Client Co")
        self.assertEqual(len(history), 3)

    def test_duplicate_serial_is_rejected_without_extra_history(self) -> None:
        self.add_asset()

        with self.assertRaises(sqlite3.IntegrityError):
            self.store.create_purchase(
                "TR-001", "Another model", Decimal("1"), "New", "D. Buyer"
            )
        self.assertEqual(len(self.store.history("TR-001")), 1)

    def test_unknown_asset_movement_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "was not found"):
            self.store.record_movement(
                "missing", "Office", "TrackRight", "Handler", "Good", ""
            )

    def test_inventory_lists_latest_state_and_searches_records(self) -> None:
        self.add_asset()
        self.store.record_movement(
            "TR-001", "Office 2", "Client Co", "B. Handler", "Good", "Deployment"
        )
        self.store.create_purchase(
            "TR-002", "Desktop Model Y", Decimal("750"), "Brand New", "A. Buyer"
        )

        all_assets = self.store.list_inventory()
        matches = self.store.list_inventory("Client Co")
        stored = self.store.list_inventory(location="Samar")
        no_matches = self.store.list_inventory("missing")

        self.assertEqual(len(all_assets), 2)
        self.assertEqual(all_assets[0]["serial_number"], "TR-001")
        self.assertEqual(all_assets[0]["to_location"], "Office 2")
        self.assertEqual(all_assets[0]["destination_company"], "Client Co")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["serial_number"], "TR-001")
        self.assertEqual(
            [row["serial_number"] for row in stored], ["TR-002"]
        )
        self.assertEqual(no_matches, [])

    def test_purchase_date_and_seeded_model_catalog(self) -> None:
        self.store.create_purchase(
            "TR-003", "KL100", Decimal("250"), "Brand New", "A. Buyer", "2026-04-15"
        )

        asset = self.store.list_inventory()[0]
        self.assertEqual(asset["purchase_date"][:10], "2026-04-15")
        self.assertEqual(self.store.list_models(), [
            "AIRTEL SIM", "JC270", "KL100", "MEM CARDS", "SAFARICOM SIM"
        ])
        self.assertEqual(self.store.current_state("TR-003")["to_location"], "Samar")

    def test_filters_history_by_device_product_company_and_location(self) -> None:
        self.store.create_purchase(
            "TR-004", "KL100", Decimal("250"), "Brand New", "A. Buyer", "2026-04-15"
        )
        self.store.record_movement(
            "TR-004", "Proto", "Fuel Rod", "B. Handler", "Good", "Installed",
            "Tata KCP256C",
        )

        records = self.store.history_records(
            product="KL100", company="Fuel Rod", location="Samar"
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(len(self.store.history_records(product="KL100", location="Samar")), 2)
        installed = records[0]
        self.assertEqual(installed["serial_number"], "TR-004")
        self.assertEqual(installed["vehicle_registration"], "Tata KCP256C")
        self.assertEqual(installed["to_location"], "Proto")
        self.assertEqual(
            self.store.list_inventory(product="KL100", company="Fuel Rod")[0][
                "serial_number"
            ],
            "TR-004",
        )

    def test_existing_database_is_migrated_for_vehicle_assignments(self) -> None:
        old_database = Path(self.temp_dir.name) / "legacy.db"
        connection = sqlite3.connect(old_database)
        connection.executescript(
            """
            CREATE TABLE products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                serial_number TEXT UNIQUE NOT NULL,
                variety_name TEXT NOT NULL,
                purchase_date TEXT NOT NULL,
                purchase_cost REAL NOT NULL,
                initial_condition TEXT NOT NULL,
                current_status TEXT NOT NULL
            );
            CREATE TABLE movements (
                movement_id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                from_location TEXT NOT NULL,
                to_location TEXT NOT NULL,
                destination_company TEXT NOT NULL,
                moved_by TEXT NOT NULL,
                item_condition TEXT NOT NULL,
                movement_date TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT ''
            );
            """
        )
        connection.execute(
            """
            INSERT INTO products (
                serial_number, variety_name, purchase_date, purchase_cost,
                initial_condition, current_status
            ) VALUES ('OLD-001', 'KL100', '2025-01-02', 100, 'Good', 'In Store')
            """
        )
        connection.execute(
            """
            INSERT INTO movements (
                product_id, from_location, to_location, destination_company,
                moved_by, item_condition, movement_date, notes
            ) VALUES (1, 'Supplier', 'Samar', 'Internal Store', 'A. Buyer',
                      'Good', '2025-01-02', '')
            """
        )
        connection.commit()
        connection.close()

        migrated_store = InventoryStore(old_database)
        connection = sqlite3.connect(old_database)
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(movements)")
        }
        connection.close()
        self.assertIn("vehicle_registration", columns)
        self.assertEqual(len(migrated_store.list_models()), 5)
        preserved = migrated_store.history_records(serial="OLD-001")
        self.assertEqual(len(preserved), 1)
        self.assertEqual(preserved[0]["to_location"], "Samar")
        self.assertEqual(preserved[0]["vehicle_registration"], "")


if __name__ == "__main__":
    unittest.main()
