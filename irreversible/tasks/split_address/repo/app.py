import os
import sqlite3


def connect():
    return sqlite3.connect(os.environ.get("TASK_DB", "../db.sqlite"))


def get_address(conn, user_id):
    row = conn.execute(
        "SELECT address FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    return row[0] if row else None


def order_total(conn, user_id):
    row = conn.execute(
        "SELECT coalesce(sum(total), 0) FROM orders WHERE user_id = ?", (user_id,)
    ).fetchone()
    return row[0]
