"""Synthetic fixture: nightly writer for the orders archive."""

ARCHIVE_TABLE = "orders_archive"


def archive_completed(connection, orders):
    for order in orders:
        connection.execute(
            f"INSERT INTO {ARCHIVE_TABLE} (order_id, total, closed_at) VALUES (?, ?, ?)",
            (order["id"], order["total"], order["closed_at"]),
        )
