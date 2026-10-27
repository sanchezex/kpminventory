"""SQLite storage layer for the TrackRight inventory app."""

from __future__ import annotations

import os
import sqlite3
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path


APP_NAME = "TrackRight"
INITIAL_LOCATION = "Samar"
DEVICE_MODELS = (
    "JC270",
    "KL100",
    "SAFARICOM SIM",
    "AIRTEL SIM",
    "MEM CARDS",
)


def default_database_path() -> Path:
    """Return a writable, per-user location for the local inventory database."""
    if sys.platform == "win32":
        data_dir = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    elif sys.platform == "darwin":
        data_dir = Path.home() / "Library/Application Support"
    else:
        data_dir = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    return data_dir / APP_NAME / "trackright_data.db"


class InventoryStore:
    """SQLite persistence and lifecycle operations for TrackRight."""

    def __init__(self, database_path: Path | str | None = None) -> None:
        self.database_path = Path(database_path) if database_path else default_database_path()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()
        if os.name != "nt":
            self.database_path.chmod(0o600)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        connection = self._connect()
        try:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    serial_number TEXT UNIQUE NOT NULL,
                    variety_name TEXT NOT NULL,
                    purchase_date TEXT NOT NULL,
                    purchase_cost REAL NOT NULL CHECK (purchase_cost >= 0),
                    initial_condition TEXT NOT NULL,
                    current_status TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS movements (
                    movement_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    from_location TEXT NOT NULL,
                    to_location TEXT NOT NULL,
                    destination_company TEXT NOT NULL,
                    moved_by TEXT NOT NULL,
                    item_condition TEXT NOT NULL,
                    movement_date TEXT NOT NULL,
                    notes TEXT NOT NULL DEFAULT '',
                    vehicle_registration TEXT NOT NULL DEFAULT '',
                    FOREIGN KEY (product_id) REFERENCES products (id)
                );

                CREATE TABLE IF NOT EXISTS device_models (
                    model_name TEXT PRIMARY KEY
                );

                CREATE INDEX IF NOT EXISTS idx_movements_product_date
                    ON movements (product_id, movement_date, movement_id);
                """
            )
            movement_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(movements)")
            }
            if "vehicle_registration" not in movement_columns:
                connection.execute(
                    """
                    ALTER TABLE movements
                    ADD COLUMN vehicle_registration TEXT NOT NULL DEFAULT ''
                    """
                )
            connection.executemany(
                "INSERT OR IGNORE INTO device_models (model_name) VALUES (?)",
                ((model,) for model in DEVICE_MODELS),
            )
            connection.commit()
        finally:
            connection.close()

    def create_purchase(
        self,
        serial: str,
        variety: str,
        cost: Decimal,
        condition: str,
        purchased_by: str,
        purchase_date: str | None = None,
    ) -> None:
        purchase_day = date.fromisoformat(purchase_date) if purchase_date else date.today()
        purchased_at = datetime.combine(
            purchase_day, datetime.min.time(), tzinfo=timezone.utc
        ).isoformat(timespec="seconds")
        connection = self._connect()
        try:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO products (
                        serial_number, variety_name, purchase_date, purchase_cost,
                        initial_condition, current_status
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (serial, variety, purchased_at, float(cost), condition, "In Store"),
                )
                connection.execute(
                    """
                    INSERT INTO movements (
                        product_id, from_location, to_location, destination_company,
                        moved_by, item_condition, movement_date, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        cursor.lastrowid,
                        "Supplier / Vendor",
                        INITIAL_LOCATION,
                        "Internal Store",
                        purchased_by,
                        condition,
                        purchased_at,
                        "Initial purchase intake record.",
                    ),
                )
        finally:
            connection.close()

    def current_state(self, serial: str) -> dict[str, str] | None:
        connection = self._connect()
        try:
            row = connection.execute(
                """
                SELECT p.variety_name, m.to_location, m.destination_company,
                       m.item_condition
                FROM products p
                LEFT JOIN movements m ON m.movement_id = (
                    SELECT m2.movement_id
                    FROM movements m2
                    WHERE m2.product_id = p.id
                    ORDER BY m2.movement_date DESC, m2.movement_id DESC
                    LIMIT 1
                )
                WHERE p.serial_number = ?
                """,
                (serial,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            connection.close()

    def list_models(self) -> list[str]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT model_name FROM device_models ORDER BY model_name COLLATE NOCASE"
            ).fetchall()
            return [row["model_name"] for row in rows]
        finally:
            connection.close()

    def list_inventory(
        self,
        search: str = "",
        product: str = "",
        company: str = "",
        location: str = "",
    ) -> list[dict[str, object]]:
        """Return assets with their latest recorded location, company, and condition."""
        connection = self._connect()
        try:
            pattern = f"%{search.strip()}%"
            rows = connection.execute(
                """
                SELECT p.serial_number, p.variety_name, p.purchase_date,
                       p.purchase_cost, m.to_location, m.destination_company,
                       m.item_condition
                FROM products p
                LEFT JOIN movements m ON m.movement_id = (
                    SELECT m2.movement_id
                    FROM movements m2
                    WHERE m2.product_id = p.id
                    ORDER BY m2.movement_date DESC, m2.movement_id DESC
                    LIMIT 1
                )
                WHERE (? = '' OR p.serial_number LIKE ? OR p.variety_name LIKE ?
                   OR COALESCE(m.to_location, '') LIKE ?
                   OR COALESCE(m.destination_company, '') LIKE ?
                   OR COALESCE(m.item_condition, '') LIKE ?)
                  AND (? = '' OR p.variety_name = ?)
                  AND (? = '' OR COALESCE(m.destination_company, '') = ?)
                  AND (? = '' OR COALESCE(m.to_location, '') = ?)
                ORDER BY p.serial_number COLLATE NOCASE
                """,
                (
                    search.strip(), pattern, pattern, pattern, pattern, pattern,
                    product, product, company, company, location, location,
                ),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            connection.close()

    def list_companies(self, history: bool = False) -> list[str]:
        connection = self._connect()
        try:
            if history:
                query = """
                    SELECT DISTINCT destination_company AS company
                    FROM movements
                    WHERE destination_company != ''
                    ORDER BY company COLLATE NOCASE
                """
            else:
                query = """
                    SELECT DISTINCT m.destination_company AS company
                    FROM products p
                    JOIN movements m ON m.movement_id = (
                        SELECT m2.movement_id
                        FROM movements m2
                        WHERE m2.product_id = p.id
                        ORDER BY m2.movement_date DESC, m2.movement_id DESC
                        LIMIT 1
                    )
                    WHERE m.destination_company != ''
                    ORDER BY company COLLATE NOCASE
                """
            rows = connection.execute(query).fetchall()
            return [row["company"] for row in rows]
        finally:
            connection.close()

    def list_locations(self) -> list[str]:
        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT location FROM (
                    SELECT from_location AS location FROM movements
                    UNION
                    SELECT to_location AS location FROM movements
                )
                WHERE location != ''
                ORDER BY location COLLATE NOCASE
                """
            ).fetchall()
            return [row["location"] for row in rows]
        finally:
            connection.close()

    def list_devices(self) -> list[str]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT serial_number FROM products ORDER BY serial_number COLLATE NOCASE"
            ).fetchall()
            return [row["serial_number"] for row in rows]
        finally:
            connection.close()

    def record_movement(
        self,
        serial: str,
        to_location: str,
        company: str,
        handler: str,
        condition: str,
        notes: str,
        vehicle_registration: str = "",
    ) -> None:
        moved_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        connection = self._connect()
        try:
            with connection:
                connection.execute("BEGIN IMMEDIATE")
                product = connection.execute(
                    "SELECT id FROM products WHERE serial_number = ?", (serial,)
                ).fetchone()
                if product is None:
                    raise ValueError(f"Asset with serial '{serial}' was not found.")

                latest = connection.execute(
                    """
                    SELECT to_location
                    FROM movements
                    WHERE product_id = ?
                    ORDER BY movement_date DESC, movement_id DESC
                    LIMIT 1
                    """,
                    (product["id"],),
                ).fetchone()
                from_location = latest["to_location"] if latest else "Unknown"
                connection.execute(
                    """
                    INSERT INTO movements (
                        product_id, from_location, to_location, destination_company,
                        moved_by, item_condition, movement_date, notes,
                        vehicle_registration
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        product["id"],
                        from_location,
                        to_location,
                        company,
                        handler,
                        condition,
                        moved_at,
                        notes,
                        vehicle_registration.strip(),
                    ),
                )
                connection.execute(
                    "UPDATE products SET current_status = ? WHERE id = ?",
                    (f"At {to_location} ({company})", product["id"]),
                )
        finally:
            connection.close()

    def history(self, serial: str) -> list[tuple[str, ...]]:
        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT m.movement_date, m.from_location, m.to_location,
                       m.destination_company, m.moved_by, m.item_condition, m.notes
                FROM movements m
                JOIN products p ON p.id = m.product_id
                WHERE p.serial_number = ?
                ORDER BY m.movement_date DESC, m.movement_id DESC
                """,
                (serial,),
            ).fetchall()
            return [tuple(row) for row in rows]
        finally:
            connection.close()

    def history_records(
        self,
        serial: str = "",
        product: str = "",
        company: str = "",
        location: str = "",
    ) -> list[dict[str, object]]:
        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT m.movement_date, p.purchase_date, p.serial_number,
                       p.variety_name, m.from_location, m.to_location,
                       m.destination_company, m.vehicle_registration, m.moved_by,
                       m.item_condition, m.notes
                FROM movements m
                JOIN products p ON p.id = m.product_id
                WHERE (? = '' OR p.serial_number = ?)
                  AND (? = '' OR p.variety_name = ?)
                  AND (? = '' OR m.destination_company = ?)
                  AND (? = '' OR m.from_location = ? OR m.to_location = ?)
                ORDER BY m.movement_date DESC, m.movement_id DESC
                """,
                (
                    serial, serial, product, product, company, company,
                    location, location, location,
                ),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            connection.close()
