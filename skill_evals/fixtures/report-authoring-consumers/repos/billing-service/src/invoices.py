"""Synthetic fixture: billing reads open orders only."""


def open_orders(connection):
    return connection.execute("SELECT order_id, total FROM orders WHERE status = 'open'").fetchall()
